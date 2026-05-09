# Document-Level Provenance Edges

> Authority answers "which doc should I obey?" Provenance answers "what evidence produced this doc?"
> Different operations, different schemas.

## Problem

A normal wikilink between two notes says they are "related." That is useful for navigation, but it under-specifies important epistemic relationships:

- A strategy note may synthesize several source notes, but the graph does not always say which sources it depends on.
- A source note may be derived from a raw file, PDF, transcript, email, or web page, but the raw artifact may not be explicitly linked in structured metadata.
- A note may cite a raw artifact directly without an intermediate processed source note.
- An agent can find related material but still miss the provenance chain behind a claim.

Search returns relevance; this layer returns the dependency edges behind a synthesized claim.

## Solution

A lightweight provenance layer over the PKB:

1. Put dependency edges in YAML frontmatter, not prose.
2. v1 is **opt-in** via `citation_status` — never coercive. The validator surfaces issues on notes that already opted in; it does not pressure the long tail of pre-existing docs into a metadata migration.
3. An audit reports likely synthesis candidates (by path / tag / kind) as recommendations, not failures.
4. Schema is intentionally separate from canonical authority. Authority owns lifecycle and node properties; provenance owns dependency edges.

## Frontmatter schema

```yaml
source_notes:
  - docs/sources/foo.md
raw_sources:
  - docs/sources/raw/foo.txt
citation_status: cited # cited | raw-only | needs-review | self-authored
```

Definitions:

- `source_notes` — processed source notes that support or informed the current note.
- `raw_sources` — raw artifacts directly used by the current note, especially when no processed source note exists yet.
- `citation_status`:
  - `cited` — provenance is captured at document level.
  - `raw-only` — raw artifacts are cited directly; no processed source note exists yet.
  - `needs-review` — the note likely depends on external material but provenance is incomplete.
  - `self-authored` — primarily original reasoning, personal reflection, or operational notes not derived from external source material.

Use paths rather than prose labels so scripts can validate targets. Obsidian wikilinks can still be included in the body for human navigation.

**Naming note:** the field is `citation_status`, not `provenance_status`, to avoid collision with the lifecycle `status:` field defined by the canonical authority schema. They are different axes (lifecycle state vs citation completeness) and should not share a name family.

**Coexistence with `source_ref:`** — the existing convention uses `source_ref: drive:<id>` to point at a durable original artifact in external storage (Drive, S3, etc.). The new `raw_sources:` lists in-vault transcript paths. Both can coexist on a single note; they describe different scopes (durable original vs in-vault transcription). One does not replace the other.

## Edges vs. node properties

Distinguish two kinds of metadata:

**Edges** — relationships between this note and another note or artifact:

- `derived_from` — synthesized note derives from a source note.
- `supports` — source note supports a decision or claim set.
- `raw_capture_of` — raw artifact is the capture behind a processed source note.
- `cites` — note cites a source without necessarily being derived from it.

**Node properties** — claims this note makes about itself:

- `canonical_for` — this note is the current authority for an operating key. Owned by the canonical authority schema, not redefined here.
- `supersedes` / `superseded_by` — lifecycle relationship between this note and the doc(s) it replaces or is replaced by. Also owned by the canonical authority schema.

Provenance implements the edges; canonical authority owns the node properties. Don't redefine `canonical_for` or `supersedes` here — that creates two systems competing over the same field.

## Why not sentence-level citations first?

More granular citations are better for truth, but they are more expensive to maintain. If every sentence needs a citation immediately, the PKB becomes slower to write in and easier to abandon.

A tiered model is better:

1. **Document-level provenance** — default; captures dependency edges cheaply.
2. **Section-level provenance** — use for synthesis/strategy/reference docs where sections draw from different sources.
3. **Claim-level citations** — use for fragile or high-stakes claims (numbers, dates, quotes, compensation/legal/medical facts, causal claims, decisions).

The key insight: if document-level `source_notes` exist, future agents can reprocess the note and sources to add sentence-level citations later. If the dependency edge is missing, future reprocessing must rediscover provenance from scratch.

**Limit on the deferred-granularity bet:** this works well for short syntheses over a few sources. Less well for long synthesis docs over 10+ sources, where reprocessing-to-add-claim-level-citations becomes the same N×M problem upfront. For docs in that regime, plan for section-level provenance from the start rather than deferring.

## CLI

```bash
# Full vault scan + write the provenance index
python3 scripts/pkb_provenance.py audit

# Recommend candidates that look like syntheses but lack provenance fields
python3 scripts/pkb_provenance.py candidates

# Source notes that no synthesis cites downstream
python3 scripts/pkb_provenance.py uncited-sources

# Notes with raw_sources but no processed source_notes
python3 scripts/pkb_provenance.py raw-only
```

The audit writes `.agent/index/provenance.json` only when no errors are found — fix structural issues and re-run.

## Validator behavior

The pre-commit validator (when `pkb_provenance.py` is present) reads each staged markdown file's provenance fields and surfaces:

- structural errors (e.g. `citation_status` is a list instead of a string)
- dangling targets (a `source_notes` entry pointing at a file that doesn't exist)

Both are **warnings only**. The validator does not fail commits on provenance metadata. v1 is deliberately permissive so the system can be adopted gradually without forcing a metadata migration.

## Who should use provenance

A safe rule of thumb: **opt in when a note is doing real synthesis work over multiple sources.** Strategy notes, design docs, hypothesis trees, plans built from multiple inputs, and reference material that aggregates external research all benefit. Daily journal entries, throwaway scratch notes, and pure reflection do not.

The audit's `candidates` command lists notes that look like syntheses (by `kind:`, tags, or path prefix) but haven't opted in. Treat its output as suggestions, not a TODO list.

## Class of problems this solves

- "Where did this number / claim / decision come from?" — answered structurally instead of by guessing.
- "If I update this source, what depends on it?" — answered by reverse-lookup against `source_notes`.
- "Which raw artifacts have we captured but never processed into source notes?" — answered by `raw-only`.
- "Which source notes are stale / never used?" — answered by `uncited-sources` (scope to active status to avoid noise on intentional archive).
- "Which docs are likely syntheses that should record their inputs?" — answered by `candidates`.

The pattern becomes more important, not less, as the PKB grows or is shared across multiple contributors. Without explicit dependency edges, agents end up rediscovering provenance repeatedly — and getting it wrong.
