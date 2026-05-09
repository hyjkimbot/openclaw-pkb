# Canonical Key Vocabulary

This file lists every key that may appear in a `canonical_for:` frontmatter
field. Keys are namespace-unique by construction (one canonical file per
key); see `.agent/index/canonical.json` for the current key → file mapping.

Adding a new key here is a deliberate act, not a side effect of writing a
new doc. The intent is to keep the canonical-key namespace small and
audit-able rather than letting it sprawl through typos or inconsistent
naming.

## Naming rules

- snake_case or kebab-case
- Lowercase only
- Must start with `[a-z]`, then `[a-z0-9_-]*`
- No spaces, no slashes, no domain prefixes (path is implicit from the
  canonical file's location, not the key)

## Active keys

<!--
Replace the examples below with your actual canonical decisions, then
add the matching `canonical_for:` frontmatter to each file.

  - `<key-name>` — short description of what the canonical doc decides
-->

- `example-key` — placeholder; remove once you register a real key

## Reserved / planned (not yet active)

<!--
Optional section for keys you intend to register later. Useful when a
team plans a future canonical doc and wants to prevent typo-aliases in
the meantime. Keys listed here are NOT enforced — only the active
section above is treated as the sanctioned vocabulary.
-->

## Out of scope (intentionally not canonicalized)

<!--
Document categories you've decided NOT to canonicalize, with rationale.
Helps future-you remember why something isn't in the index. Examples:

  - Strategy docs that accrete history rather than have a single
    "current" version
  - Project-level work logs that are episodic, not standing decisions
  - Personal reflections that are not authority-bearing by nature
-->
