"""PKB document-level provenance edges.

Records *which* source notes and raw artifacts a synthesized note depends
on, separate from ordinary "related" wikilinks that only mean navigation.
Provenance answers "what evidence produced this note?" — distinct from
canonical authority's "which note should I obey?"

Per the design (docs/document-level-provenance-edges.md):
- v1 is opt-in via `citation_status`. The validator does not coerce the
  long tail of pre-existing notes into a metadata migration.
- An audit reports likely candidates that look like syntheses but lack
  citation_status — recommendations, not failures.
- Schema collisions with the authority module (`status`, `canonical_for`,
  `supersedes`) are intentional avoidance: this module owns the edges,
  the authority module owns the lifecycle / claim node properties.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from typing import Iterable

import yaml

from pkb_frontmatter import (
    FrontmatterError,
    coerce_list as _coerce_list_shared,
    field_present_in_raw,
    iter_markdown_files,
    parse_frontmatter,
)


VALID_CITATION_STATUSES = {
    "cited",
    "raw-only",
    "needs-review",
    "self-authored",
}

PROVENANCE_FIELD_NAMES = (
    "source_notes",
    "raw_sources",
    "citation_status",
)


@dataclass
class ProvenanceRecord:
    """Provenance metadata extracted from a single document."""

    path: str
    source_notes: list[str] = field(default_factory=list)
    raw_sources: list[str] = field(default_factory=list)
    citation_status: str | None = None


@dataclass
class ProvenanceIndex:
    """Generated provenance index."""

    records: dict[str, ProvenanceRecord] = field(default_factory=dict)


class ProvenanceError(Exception):
    """Raised when provenance metadata is structurally invalid."""


def _coerce_list(value, field_name: str, source: str) -> list[str]:
    return _coerce_list_shared(value, field_name, source, ProvenanceError)


def has_provenance_intent(text: str) -> bool:
    """True if the doc's frontmatter mentions any provenance field."""
    return field_present_in_raw(text, PROVENANCE_FIELD_NAMES)


def extract_provenance(path: str, text: str) -> ProvenanceRecord | None:
    """Parse a markdown file's provenance metadata.

    Returns None if the file has no frontmatter or no provenance fields.
    Raises ProvenanceError on malformed metadata.
    """
    try:
        fm = parse_frontmatter(text)
    except FrontmatterError as exc:
        raise ProvenanceError(f"{path}: {exc}") from exc
    if fm is None:
        return None

    source_notes = _coerce_list(fm.get("source_notes"), "source_notes", path)
    raw_sources = _coerce_list(fm.get("raw_sources"), "raw_sources", path)
    citation_status = fm.get("citation_status")

    has_any = bool(source_notes or raw_sources or citation_status is not None)
    if not has_any:
        return None

    if citation_status is not None:
        if not isinstance(citation_status, str):
            raise ProvenanceError(
                f"{path}: 'citation_status' must be a string, "
                f"got {type(citation_status).__name__}"
            )

    return ProvenanceRecord(
        path=path,
        source_notes=source_notes,
        raw_sources=raw_sources,
        citation_status=citation_status,
    )


def build_full_index(
    root: str,
) -> tuple[ProvenanceIndex, list[tuple[str, str]]]:
    """Scan the entire vault and rebuild the provenance index from scratch.

    Returns (index, errors). Files with malformed frontmatter that have
    no provenance intent are skipped silently so legacy YAML noise
    doesn't block the audit.
    """
    index = ProvenanceIndex()
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
            rec = extract_provenance(rel, text)
        except yaml.YAMLError as exc:
            if has_provenance_intent(text):
                errors.append((rel, str(exc)))
            continue
        except ProvenanceError as exc:
            errors.append((rel, str(exc)))
            continue
        if rec is not None:
            index.records[rel] = rec
    return index, errors


def collect_unknown_status_warnings(
    records: Iterable[ProvenanceRecord],
) -> list[tuple[str, str]]:
    """Return (path, message) tuples for records using citation_status
    values outside the known vocabulary. Non-fatal: surfaces hygiene
    issues without blocking audit success."""
    warnings = []
    for rec in records:
        if (
            rec.citation_status is not None
            and rec.citation_status not in VALID_CITATION_STATUSES
        ):
            warnings.append(
                (
                    rec.path,
                    f"unknown citation_status {rec.citation_status!r} "
                    f"(expected one of {sorted(VALID_CITATION_STATUSES)})",
                )
            )
    return warnings


def collect_dangling_targets(
    index: ProvenanceIndex, root: str
) -> list[tuple[str, str]]:
    """Find provenance records whose source_notes or raw_sources point
    at files that don't exist."""
    issues: list[tuple[str, str]] = []
    for rec in index.records.values():
        for target in rec.source_notes + rec.raw_sources:
            full = os.path.join(root, target)
            if not os.path.exists(full):
                issues.append(
                    (rec.path, f"target does not exist: {target}")
                )
    return issues


def collect_uncited_sources(
    index: ProvenanceIndex,
    all_source_paths: Iterable[str],
    active_filter: callable | None = None,
) -> list[str]:
    """Return source notes that are never referenced by any record's
    source_notes list.

    `active_filter` is an optional callable(path) -> bool that limits
    the report to paths the caller considers active (e.g. status:
    current). Without it, all source files are reported, which produces
    noise when archived material is intentionally one-and-done.
    """
    referenced: set[str] = set()
    for rec in index.records.values():
        referenced.update(rec.source_notes)

    out = []
    for path in all_source_paths:
        if path in referenced:
            continue
        if active_filter is not None and not active_filter(path):
            continue
        out.append(path)
    return sorted(out)


def collect_raw_only(index: ProvenanceIndex) -> list[str]:
    """Return paths of records with raw_sources but no source_notes —
    candidates for promotion to processed source notes."""
    return sorted(
        rec.path
        for rec in index.records.values()
        if rec.raw_sources and not rec.source_notes
    )


# --- Candidate detection -----------------------------------------------------
# Suggests which notes look like syntheses without strict metadata enforcement.
# Per the design comment, we don't fail commits based on these heuristics —
# they're recommendations to opt in to citation_status, not requirements.

def candidate_signals(path: str, text: str) -> list[str]:
    """Return a list of signals suggesting this note may be a synthesis
    that would benefit from explicit provenance.

    Empty list = no signal, do not recommend."""
    signals: list[str] = []
    fm = None
    try:
        fm = parse_frontmatter(text)
    except FrontmatterError:
        return signals
    if fm is None:
        return signals
    # Already has provenance intent? Then it's not a candidate, it's done.
    if has_provenance_intent(text):
        return signals

    # Heuristic 1: kind: synthesis | reference (when used)
    kind = fm.get("kind")
    if isinstance(kind, str) and kind.lower() in {"synthesis", "reference"}:
        signals.append(f"kind: {kind}")

    # Heuristic 2: tags include type/synthesis or type/reference
    tags = fm.get("tags") or []
    if isinstance(tags, list):
        for tag in tags:
            if not isinstance(tag, str):
                continue
            if tag in ("type/synthesis", "type/reference"):
                signals.append(f"tag: {tag}")

    # Heuristic 3: file lives in a path conventionally used for syntheses
    syn_prefixes = ("docs/projects/", "docs/career/", "docs/reference/")
    if any(path.startswith(p) for p in syn_prefixes):
        signals.append(f"path prefix: {path.split('/', 2)[:2]}")

    return signals


def find_candidates(root: str) -> list[tuple[str, list[str]]]:
    """Scan the vault and return (path, signals) for notes that look
    like syntheses but lack provenance metadata."""
    candidates: list[tuple[str, list[str]]] = []
    for rel in iter_markdown_files(root):
        full = os.path.join(root, rel)
        try:
            with open(full, "r", encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            continue
        signals = candidate_signals(rel, text)
        if signals:
            candidates.append((rel, signals))
    return candidates


# --- Index serialization -----------------------------------------------------

def serialize_index(index: ProvenanceIndex) -> str:
    """Serialize the index as a deterministic JSON object."""
    payload = {
        path: {
            "source_notes": sorted(rec.source_notes),
            "raw_sources": sorted(rec.raw_sources),
            "citation_status": rec.citation_status,
        }
        for path, rec in sorted(index.records.items())
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def write_index(index: ProvenanceIndex, path: str) -> None:
    """Write the index to disk, creating parent directories as needed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(serialize_index(index))


# --- CLI ---------------------------------------------------------------------

def main(argv: list[str]) -> int:
    """CLI entry point.

    Subcommands:
      audit                 Full rebuild + report errors, warnings, dangling targets
      candidates            List notes that look like syntheses but lack provenance
      uncited-sources       List source notes never cited downstream
      raw-only              List notes with raw_sources but no processed source_notes
    """
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    index_path = os.path.join(base, ".agent", "index", "provenance.json")

    if len(argv) < 2:
        print(
            "usage: pkb_provenance.py {audit|candidates|uncited-sources|raw-only}",
            file=sys.stderr,
        )
        return 2

    cmd = argv[1]
    if cmd == "audit":
        try:
            index, errors = build_full_index(base)
        except ProvenanceError as exc:
            print(f"PKB provenance audit failed: {exc}", file=sys.stderr)
            return 1
        if errors:
            print(
                f"PKB provenance: {len(errors)} file(s) had provenance metadata "
                "issues; index NOT written",
                file=sys.stderr,
            )
            for rel, msg in errors:
                print(f"  {rel}: {msg}", file=sys.stderr)
            return 1
        write_index(index, index_path)
        print(
            f"PKB provenance: wrote {len(index.records)} record(s) to {index_path}"
        )
        warnings = collect_unknown_status_warnings(index.records.values())
        for rel, msg in warnings:
            print(f"  warning: {rel}: {msg}", file=sys.stderr)
        dangling = collect_dangling_targets(index, base)
        for rel, msg in dangling:
            print(f"  dangling: {rel}: {msg}", file=sys.stderr)
        return 0

    if cmd == "candidates":
        for rel, signals in find_candidates(base):
            print(f"{rel}\t{'; '.join(signals)}")
        return 0

    if cmd == "uncited-sources":
        index, _ = build_full_index(base)
        all_sources = [
            rel
            for rel in iter_markdown_files(base)
            if rel.startswith("docs/sources/") and not rel.startswith("docs/sources/raw/")
        ]
        for path in collect_uncited_sources(index, all_sources):
            print(path)
        return 0

    if cmd == "raw-only":
        index, _ = build_full_index(base)
        for path in collect_raw_only(index):
            print(path)
        return 0

    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
