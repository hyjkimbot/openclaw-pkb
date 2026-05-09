"""PKB canonical authority indexing.

Solves the "which document is authoritative right now?" problem when
multiple notes are related to the same topic. Search returns relevant
documents; this module returns the one currently designated as the
source of truth for a given decision key.

Parses authority-bearing frontmatter, builds a canonical-key index at
.agent/index/canonical.json, and rejects collisions, drift, and
hand-edits via the validator.

See docs/canonical-authority-indexing.md for the full design.
"""
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Iterable

import yaml

from pkb_frontmatter import (
    FRONTMATTER_RE,
    FrontmatterError,
    coerce_list as _coerce_list_shared,
    field_present_in_raw,
    iter_markdown_files as _iter_markdown_files_shared,
    parse_frontmatter as _parse_frontmatter_shared,
)


VALID_STATUSES = {
    "current",
    "draft",
    "reviewed",
    "stable",
    "historical",
    "superseded",
    "deprecated",
    "planning",
}

CANONICAL_KEY_RE = re.compile(r"^[a-z][a-z0-9_-]*$")

# Backtick-wrapped key inside a list item: `- \`key\` — description`.
# Matches the format used in `.agent/index/canonical-keys.md`.
KEYS_VOCAB_LINE_RE = re.compile(r"^\s*-\s+`([a-z][a-z0-9_-]*)`", re.MULTILINE)
ACTIVE_KEYS_HEADING_RE = re.compile(r"^\s*##\s+Active keys\s*$", re.MULTILINE)
NEXT_HEADING_RE = re.compile(r"^\s*##\s+", re.MULTILINE)

# Field names that signal a doc is making an authority claim. Used to decide
# whether a YAML parse failure is a real problem or unrelated legacy noise
# (e.g. a `title: with: a colon` line in a doc that has no authority intent).
AUTHORITY_FIELD_NAMES = (
    "canonical_for",
    "supersedes",
    "superseded_by",
    "authority_scope",
)


@dataclass
class AuthorityRecord:
    """Authority metadata extracted from a single document."""

    path: str
    status: str | None = None
    canonical_for: list[str] = field(default_factory=list)
    supersedes: list[str] = field(default_factory=list)
    superseded_by: list[str] = field(default_factory=list)
    authority_scope: str | None = None
    owner: str | None = None


@dataclass
class CanonicalIndex:
    """The generated canonical-key → file map.

    `entries` is the lookup; `records` retains full authority metadata for
    every authority-bearing doc so the audit path can re-emit the index
    without re-parsing.
    """

    entries: dict[str, str] = field(default_factory=dict)
    records: dict[str, AuthorityRecord] = field(default_factory=dict)


class AuthorityError(Exception):
    """Raised when authority metadata is invalid or collides."""


def parse_frontmatter(text: str) -> dict | None:
    """Re-export of pkb_frontmatter.parse_frontmatter that surfaces
    structural errors as AuthorityError for callers that catch it."""
    try:
        return _parse_frontmatter_shared(text)
    except FrontmatterError as exc:
        raise AuthorityError(str(exc)) from exc


def has_authority_intent(text: str) -> bool:
    """Cheap regex check for whether a doc looks like it is trying to claim
    authority, without requiring the full YAML to parse cleanly.

    Used so unrelated YAML legacy issues (e.g. unquoted colons in titles)
    don't block the authority audit on documents that have no authority
    intent at all.
    """
    return field_present_in_raw(text, AUTHORITY_FIELD_NAMES)


def _coerce_list(value, field_name: str, source: str) -> list[str]:
    """Normalize a frontmatter field to a list of strings.

    Accepts: list of strings, single string, or None/missing (returns []).
    """
    return _coerce_list_shared(value, field_name, source, AuthorityError)


def extract_authority(path: str, text: str) -> AuthorityRecord | None:
    """Parse a markdown file's authority metadata.

    Returns None if the file has no frontmatter or no authority fields.
    Raises AuthorityError on malformed authority metadata.
    """
    fm = parse_frontmatter(text)
    if fm is None:
        return None

    status = fm.get("status")
    canonical_for = _coerce_list(fm.get("canonical_for"), "canonical_for", path)
    supersedes = _coerce_list(fm.get("supersedes"), "supersedes", path)
    superseded_by = _coerce_list(fm.get("superseded_by"), "superseded_by", path)
    authority_scope = fm.get("authority_scope")
    owner = fm.get("owner")

    has_authority = (
        status is not None
        or canonical_for
        or supersedes
        or superseded_by
        or authority_scope is not None
    )
    if not has_authority:
        return None

    # Unknown status values are tolerated (the doc may still claim
    # canonical_for or supersedes — those drive the index, not status).
    # The audit path can separately surface unknown values as warnings.
    if status is not None and not isinstance(status, str):
        raise AuthorityError(
            f"{path}: 'status' must be a string, got {type(status).__name__}"
        )

    for key in canonical_for:
        if not CANONICAL_KEY_RE.match(key):
            raise AuthorityError(
                f"{path}: canonical_for key {key!r} must match [a-z][a-z0-9_-]* "
                "(snake_case or kebab-case, no spaces)"
            )

    if authority_scope is not None and not isinstance(authority_scope, str):
        raise AuthorityError(
            f"{path}: 'authority_scope' must be a string, "
            f"got {type(authority_scope).__name__}"
        )

    if owner is not None and not isinstance(owner, str):
        raise AuthorityError(
            f"{path}: 'owner' must be a string, got {type(owner).__name__}"
        )

    return AuthorityRecord(
        path=path,
        status=status,
        canonical_for=canonical_for,
        supersedes=supersedes,
        superseded_by=superseded_by,
        authority_scope=authority_scope,
        owner=owner,
    )


def parse_active_keys(text: str) -> set[str]:
    """Return the set of keys listed under '## Active keys' in the
    canonical-keys vocabulary file.

    Only the active section is treated as the sanctioned vocabulary. Reserved
    or out-of-scope keys are ignored.
    """
    heading = ACTIVE_KEYS_HEADING_RE.search(text)
    if not heading:
        return set()
    section_start = heading.end()
    next_heading = NEXT_HEADING_RE.search(text, pos=section_start)
    section_end = next_heading.start() if next_heading else len(text)
    section = text[section_start:section_end]
    return {m.group(1) for m in KEYS_VOCAB_LINE_RE.finditer(section)}


def load_active_keys(path: str) -> set[str] | None:
    """Load active canonical keys from the vocabulary file. Returns None if
    the file doesn't exist (vocabulary enforcement is then skipped)."""
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return parse_active_keys(fh.read())


def validate_against_vocabulary(
    records: Iterable[AuthorityRecord], active_keys: set[str]
) -> None:
    """Raise AuthorityError if any record claims a key not in the active
    vocabulary."""
    unknown: dict[str, list[str]] = {}
    for rec in records:
        for key in rec.canonical_for:
            if key not in active_keys:
                unknown.setdefault(key, []).append(rec.path)
    if unknown:
        details = "\n".join(
            f"  {key} (claimed by {sorted(paths)})"
            for key, paths in sorted(unknown.items())
        )
        raise AuthorityError(
            "canonical_for keys not in active vocabulary "
            "(.agent/index/canonical-keys.md):\n"
            f"{details}\n"
            "  → add the key under '## Active keys' first, then claim it."
        )


def detect_index_drift(
    existing: CanonicalIndex, root: str
) -> list[tuple[str, str]]:
    """Check whether on-disk canonical.json matches actual frontmatter claims.

    Returns a list of (key, message) tuples describing drift. Empty list means
    the index is consistent with the source-of-truth frontmatter.

    Catches the hand-edit / merge-drift case where someone modifies
    canonical.json directly without going through the audit path.
    """
    issues: list[tuple[str, str]] = []
    for key, path in existing.entries.items():
        full = os.path.join(root, path)
        if not os.path.exists(full):
            issues.append(
                (key, f"index points to {path}, but that file does not exist")
            )
            continue
        with open(full, "r", encoding="utf-8") as fh:
            text = fh.read()
        try:
            rec = extract_authority(path, text)
        except (AuthorityError, yaml.YAMLError) as exc:
            issues.append(
                (
                    key,
                    f"index points to {path}, but its frontmatter cannot be "
                    f"parsed: {exc}",
                )
            )
            continue
        if rec is None or key not in rec.canonical_for:
            issues.append(
                (
                    key,
                    f"index points to {path}, but that file does not claim "
                    f"canonical_for: {key}",
                )
            )
    return issues


def collect_status_warnings(records: Iterable[AuthorityRecord]) -> list[tuple[str, str]]:
    """Return (path, message) tuples for records using unknown status values.

    Separate from the index build because unknown status doesn't affect
    canonical resolution; it's a hygiene signal worth surfacing in the audit.
    """
    warnings = []
    for rec in records:
        if rec.status is not None and rec.status not in VALID_STATUSES:
            warnings.append(
                (
                    rec.path,
                    f"unknown status value {rec.status!r} "
                    f"(expected one of {sorted(VALID_STATUSES)})",
                )
            )
    return warnings


def build_index_from_records(records: Iterable[AuthorityRecord]) -> CanonicalIndex:
    """Aggregate per-file records into a canonical index.

    Raises AuthorityError on key collision (two docs claim the same key).
    """
    index = CanonicalIndex()
    claims: dict[str, list[str]] = {}
    for rec in records:
        index.records[rec.path] = rec
        for key in rec.canonical_for:
            claims.setdefault(key, []).append(rec.path)

    collisions = {k: paths for k, paths in claims.items() if len(paths) > 1}
    if collisions:
        details = "\n".join(
            f"  {key}: {sorted(paths)}" for key, paths in sorted(collisions.items())
        )
        raise AuthorityError(
            "canonical_for collision (each key must be claimed by exactly one "
            f"file):\n{details}"
        )

    for key, paths in claims.items():
        index.entries[key] = paths[0]
    return index


def iter_markdown_files(root: str) -> Iterable[str]:
    """Re-export of pkb_frontmatter.iter_markdown_files for back-compat."""
    return _iter_markdown_files_shared(root)


def build_full_index(
    root: str,
) -> tuple[CanonicalIndex, list[tuple[str, str]]]:
    """Scan the entire vault and rebuild the canonical index from scratch.

    Returns (index, errors). `errors` is a list of (relative_path, message)
    tuples for files whose frontmatter could not be parsed or whose authority
    metadata was malformed. The audit completes the scan even when individual
    files fail; the caller decides how to surface the errors.
    """
    records: list[AuthorityRecord] = []
    errors: list[tuple[str, str]] = []
    for rel in iter_markdown_files(root):
        full = os.path.join(root, rel)
        try:
            with open(full, "r", encoding="utf-8") as fh:
                text = fh.read()
        except OSError as exc:
            errors.append((rel, f"cannot read: {exc}"))
            continue
        try:
            rec = extract_authority(rel, text)
        except yaml.YAMLError as exc:
            # Only surface YAML errors when the file looks like it intends
            # to claim authority. Legacy unrelated YAML issues stay quiet.
            if has_authority_intent(text):
                errors.append((rel, str(exc)))
            continue
        except AuthorityError as exc:
            errors.append((rel, str(exc)))
            continue
        if rec is not None:
            records.append(rec)
    index = build_index_from_records(records)
    return index, errors


def update_index_incrementally(
    existing: CanonicalIndex, root: str, changed_paths: Iterable[str]
) -> CanonicalIndex:
    """Apply changes from a set of touched files to an existing index.

    For each changed path:
    - if the file exists and parses with authority metadata, update its record
    - otherwise (deleted or no authority), remove its record

    Then re-aggregate the entries map and check for collisions.

    When called with an `existing` that was loaded from disk, the existing
    records may be empty (load_index does not reconstruct them). In that
    case, this function rebuilds records for the existing canonical files
    so collision detection sees them as incumbents.
    """
    new_records = dict(existing.records)

    # Backfill records for incumbent canonical files when records weren't
    # carried over (e.g. existing came from load_index).
    changed_set = set(changed_paths)
    for incumbent_path in existing.entries.values():
        if incumbent_path in new_records or incumbent_path in changed_set:
            continue
        full = os.path.join(root, incumbent_path)
        if not os.path.exists(full):
            continue
        with open(full, "r", encoding="utf-8") as fh:
            incumbent_text = fh.read()
        try:
            incumbent_rec = extract_authority(incumbent_path, incumbent_text)
        except (AuthorityError, yaml.YAMLError):
            # If the incumbent file is now broken, leave it out; the audit
            # path will surface the problem separately.
            continue
        if incumbent_rec is not None:
            new_records[incumbent_path] = incumbent_rec

    for rel in changed_paths:
        full = os.path.join(root, rel)
        if not os.path.exists(full):
            new_records.pop(rel, None)
            continue
        with open(full, "r", encoding="utf-8") as fh:
            text = fh.read()
        rec = extract_authority(rel, text)
        if rec is None:
            new_records.pop(rel, None)
        else:
            new_records[rel] = rec
    return build_index_from_records(new_records.values())


def serialize_index(index: CanonicalIndex) -> str:
    """Return a stable JSON representation of the entries map."""
    return json.dumps(index.entries, indent=2, sort_keys=True) + "\n"


def write_index(index: CanonicalIndex, path: str) -> None:
    """Write the index to disk, creating parent directories as needed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(serialize_index(index))


def load_index(path: str) -> CanonicalIndex:
    """Load a canonical index from disk. Records are not reconstructed."""
    if not os.path.exists(path):
        return CanonicalIndex()
    with open(path, "r", encoding="utf-8") as fh:
        entries = json.load(fh)
    if not isinstance(entries, dict):
        raise AuthorityError(f"{path}: index must be a JSON object")
    return CanonicalIndex(entries=entries)


def lookup(index: CanonicalIndex, key: str) -> str | None:
    """Return the file path for a canonical key, or None if not registered."""
    return index.entries.get(key)


def main(argv: list[str]) -> int:
    """CLI entry point.

    Subcommands:
      audit         Full rebuild of the canonical index from frontmatter scan
      lookup KEY    Print the file path registered for KEY (exit 1 if missing)
    """
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    index_path = os.path.join(base, ".agent", "index", "canonical.json")
    vocab_path = os.path.join(base, ".agent", "index", "canonical-keys.md")

    if len(argv) < 2:
        print("usage: pkb_authority.py {audit|lookup KEY}", file=sys.stderr)
        return 2

    cmd = argv[1]
    if cmd == "audit":
        try:
            index, errors = build_full_index(base)
        except AuthorityError as exc:
            print(f"PKB authority audit failed: {exc}", file=sys.stderr)
            return 1
        # Vocabulary enforcement: claimed keys must exist in canonical-keys.md.
        active_keys = load_active_keys(vocab_path)
        if active_keys is not None:
            try:
                validate_against_vocabulary(index.records.values(), active_keys)
            except AuthorityError as exc:
                print(f"PKB authority audit failed: {exc}", file=sys.stderr)
                return 1
        # Only write the index when the rebuild was clean. Errors mean the
        # index would not faithfully reflect intended authority — surface
        # them and leave the on-disk file alone for the user to fix and
        # re-run.
        if errors:
            print(
                f"PKB authority audit failed: {len(errors)} file(s) had "
                "frontmatter issues; index NOT written",
                file=sys.stderr,
            )
            for rel, msg in errors:
                print(f"  {rel}: {msg}", file=sys.stderr)
            return 1
        write_index(index, index_path)
        print(f"PKB authority: wrote {len(index.entries)} keys to {index_path}")
        # Unknown-status warnings are surfaced but do not block — they
        # represent legacy hygiene issues, not authority correctness.
        warnings = collect_status_warnings(index.records.values())
        if warnings:
            print(
                f"PKB authority: {len(warnings)} file(s) use unknown status values "
                "(non-fatal):",
                file=sys.stderr,
            )
            for rel, msg in warnings:
                print(f"  {rel}: {msg}", file=sys.stderr)
        return 0

    if cmd == "lookup":
        if len(argv) < 3:
            print("usage: pkb_authority.py lookup KEY", file=sys.stderr)
            return 2
        key = argv[2]
        index = load_index(index_path)
        result = lookup(index, key)
        if result is None:
            print(f"no canonical file registered for key {key!r}", file=sys.stderr)
            return 1
        print(result)
        return 0

    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
