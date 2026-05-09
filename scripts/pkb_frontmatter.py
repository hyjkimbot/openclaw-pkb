"""Shared frontmatter utilities used by pkb_authority and pkb_provenance.

Both modules need YAML frontmatter parsing, vault traversal, and
common type-coercion helpers. Keeping them here avoids divergence on
parsing rules or audit semantics across the schema extensions.
"""
from __future__ import annotations

import os
import re
from typing import Iterable

import yaml


FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)

# Directories to skip when walking the vault for any frontmatter scan.
SKIP_DIRS = frozenset({".git", ".obsidian", "node_modules", "_fit"})


class FrontmatterError(Exception):
    """Raised when frontmatter is malformed at the type / structural level
    (e.g. not a YAML mapping). Catch yaml.YAMLError separately for parse
    errors that may not indicate authority/provenance intent."""


def parse_frontmatter(text: str) -> dict | None:
    """Return the YAML-parsed frontmatter dict, or None if no frontmatter.

    Returns an empty dict for empty frontmatter blocks. Raises
    FrontmatterError if the frontmatter is structurally invalid (e.g. a
    YAML list at the top level instead of a mapping).
    """
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None
    raw = match.group(1)
    if not raw.strip():
        return {}
    parsed = yaml.safe_load(raw)
    if parsed is None:
        return {}
    if not isinstance(parsed, dict):
        raise FrontmatterError(
            f"frontmatter must be a YAML mapping, got {type(parsed).__name__}"
        )
    return parsed


def coerce_list(
    value, field_name: str, source: str, error_class: type = FrontmatterError
) -> list[str]:
    """Normalize a frontmatter field to a list of strings.

    Accepts: list of strings, single string, or None/missing (returns []).
    Raises `error_class` for type violations so callers can surface
    domain-appropriate exceptions (AuthorityError, ProvenanceError, etc.).
    """
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        for item in value:
            if not isinstance(item, str):
                raise error_class(
                    f"{source}: '{field_name}' must be a list of strings, "
                    f"got {type(item).__name__}: {item!r}"
                )
        return list(value)
    raise error_class(
        f"{source}: '{field_name}' must be a string or list of strings, "
        f"got {type(value).__name__}"
    )


def iter_markdown_files(root: str) -> Iterable[str]:
    """Yield repo-relative paths of all markdown files under root.

    Skips .git, .obsidian, node_modules, and similar non-vault directories.
    """
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith(".md"):
                full = os.path.join(dirpath, name)
                yield os.path.relpath(full, root).replace(os.sep, "/")


def field_present_in_raw(text: str, field_names: Iterable[str]) -> bool:
    """Cheap regex check for whether a doc's frontmatter mentions any of
    the given field names, without requiring the full YAML to parse.

    Useful for distinguishing legacy YAML errors on docs with no relevant
    intent from real errors on docs that ARE trying to use the schema.
    """
    match = FRONTMATTER_RE.match(text)
    if not match:
        return False
    raw = match.group(1)
    pattern = re.compile(
        r"^\s*(?:" + "|".join(re.escape(n) for n in field_names) + r")\s*:",
        re.MULTILINE,
    )
    return bool(pattern.search(raw))
