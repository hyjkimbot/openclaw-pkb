# Canonical Authority Indexing

> Search answers "what mentions this?" Authority answers "what should I obey?"
> Those are different operations.

## Problem

When multiple notes are related to the same topic, an agent can retrieve a stale planning note instead of the current operating decision. Flat search finds relevant documents, but it does not reliably answer the higher-order question: **which document is authoritative right now?**

Concrete failure mode: a nutrition-target document gets renamed to `current-targets.md` while older planning docs (`reverse-diet-2026.md`, etc.) still exist. An agent searching for "diet target" finds both. Search relevance does not equal authority — and acting on the wrong one produces real-world consequences.

## Solution

A lightweight authority layer over the PKB:

1. Put authority claims in YAML frontmatter, not prose.
2. Maintain a small generated canonical-key index for fast runtime lookup.
3. Validate changed files incrementally against that index on every commit.
4. Run occasional full reconciliation scans as an audit path.

This turns the PKB graph from "many related notes" into a more explicit model of **current state, historical context, open questions, and superseded decisions**.

## Frontmatter schema

Authority lives in YAML frontmatter so it can be parsed without reading the body.

```yaml
status: current | draft | reviewed | stable | historical | superseded | deprecated | planning
canonical_for:
  - decision-key
supersedes:
  - docs/path/to/old.md
superseded_by:
  - docs/path/to/newer.md
authority_scope: optional/free-text  # only when path is insufficient
owner: alice
updated: 2026-05-08
```

Design decisions:

- **Structured `status` is the source of truth, not the `status/*` tag.** Two sources of truth = two places to drift. The tag exists for Obsidian search; the structured field is for machine logic.
- **`canonical_for` keys are namespace-unique by construction.** Two docs claiming the same key is a build error, like duplicate route definitions.
- **`canonical_for` should be a short stable key, not a prose phrase.** Snake-case or kebab-case, no spaces.
- **`authority_scope` is optional, not required.** Path-derived scope (`docs/health/...` → `health`) gives 80% of the value at 0% maintenance cost. The field exists for cases where authority cuts across path boundaries (business unit, product line, customer segment, etc.) — common in corporate/team PKBs.
- **No header-anchor canonical claims.** Whole-file pointers only. If a section becomes canonical, promote it to its own file.
- **Unknown status values are tolerated** with non-fatal warnings during audit. Legacy docs with non-canonical status strings don't block the system; the audit surfaces them as hygiene signals.

## Canonical index

Generated from frontmatter — never hand-edited.

```text
.agent/index/canonical.json
```

Example contents:

```json
{
  "nutrition-targets": "docs/health/current-targets.md",
  "supplement-stack": "docs/health/current-supplement-stack.md"
}
```

Active canonical keys live in `.agent/index/canonical-keys.md` as a controlled vocabulary. Adding a new canonical claim requires registering the key there first — the validator rejects claims for unregistered keys.

## Validator behavior

The validator runs a full frontmatter rebuild and treats it as ground truth on every commit that touches markdown or `canonical.json`:

- **If `canonical.json` is staged**: the staged blob (read via `git show :<path>`, not the working tree) must match the rebuild. Catches injection, deletion, and modification regardless of what else is staged.
- **If only markdown is staged**: the index is regenerated and re-staged.
- **Collision**: two docs claiming the same key produces a structured error naming both files.
- **Vocabulary**: claims for keys not in `.agent/index/canonical-keys.md` are rejected with a hint to register the key first.
- **Status validation**: type validation only (must be a string); unknown values surface as non-fatal warnings during audit.

## CLI

```bash
# Look up the canonical file for a given key
python3 scripts/pkb_authority.py lookup nutrition-targets
# → docs/health/current-targets.md

# Full rebuild from frontmatter (run after merges, bulk edits, or recovery)
python3 scripts/pkb_authority.py audit
```

**When to run a full audit:** after `git pull` of a non-trivial merge, after a bulk-edit pass, or whenever the validator reports drift. The pre-commit validation handles normal day-to-day commits but cannot detect changes the validator didn't write itself.

**Audit failure mode:** when frontmatter errors are collected, the index is **not** written. Fix the underlying frontmatter and re-run. Unknown status values are non-fatal and do not block writing.

## Workflow for adding a new canonical key

1. Edit `.agent/index/canonical-keys.md` and add the key under `## Active keys`.
2. Add `canonical_for: <key>` to the frontmatter of the canonical doc.
3. Commit both changes together. The validator regenerates the index and stages it.

The validator rejects the commit if you skip step 1 — the canonical-keys file is the sanctioned vocabulary.

## Class of problems this solves

This pattern applies whenever the PKB contains multiple versions of an evolving understanding:

- **Personal operating targets:** diet, supplements, workout loads, sleep goals.
- **Business strategy:** current company model, customer segmentation, pricing thesis, org-design assumptions.
- **Technical architecture:** canonical schema, chosen data format, active system boundary, deprecated migration plan.
- **Decision records:** latest accepted decision vs. alternatives considered.
- **Research synthesis:** current best model of a topic vs. old reading notes.

The pattern becomes more important, not less, as the PKB grows or is shared across multiple contributors. Information gathering creates contradictions by default; canonical markers separate raw inputs from reconciled operating understanding.
