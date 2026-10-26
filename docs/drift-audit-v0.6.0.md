# Operational drift audit: v0.6.0

Baseline: public template main at `7eba34d`, whose skill declared v0.5.0. This audit compared the shipped code and instructions with reusable procedures from an actively operated vault. It records generic gaps, not a copy of that vault's records or policies.

## Already present at baseline

- Generic directory-prefix `csvSchemas` configuration, including headers, required fields, numbers, integers, and enums. The interface existed; no rules file or personal schemas were shipped.
- Git-index validation of staged CSV, basic Markdown frontmatter, and links from changed Markdown.
- Canonical authority fields, controlled keys, generated lookup, collision checks, and staged-index comparison against a frontmatter rebuild.
- Opt-in document-level provenance and warning-only validation, plus working-tree audit/query tools.
- Journal conventions, CSV storage guidance, a refactor helper, and optional remote/original-file storage concepts.

These are not new v0.6.0 features.

## Gaps addressed

| Observed gap | Shipped response |
| --- | --- |
| Repeated ingestion/Git procedures disagreed; some unconditionally pulled or used broad staging | One root router with shared capture, Git, and validation guides; explicit local-only scope and scoped staging |
| Logging blurred raw human journals, structured facts, and agent continuity | Separate destinations, event-date and reported/completed-state rules |
| An existing target or log could be mistaken for permission to track | Independent consent/pause, visibility, target, and state gates; no default domain activation |
| Documentation referenced a nonexistent current-loads JSON file and recommended schema edits in Python | Generic optional domain state, existing JSON rules interface, CSV-aware writing |
| Dirty-sync recovery prescribed reset/stash without preserving all kinds of work | Inspection, preservation, and isolated-worktree recovery guidance |
| No bundled hook/install path; normal validation could be skipped accidentally | Opt-in portable pre-commit hook and non-overwriting installer |
| Changed-note-only link checks missed unchanged inbound links after deletion | Conditional all-index graph-scope scan and explicit `--full` |
| Provenance/rules used the working tree despite staged-validation claims | Index-based metadata, target membership, and configuration with regression coverage |
| Git errors could report a successful skip; generated authority output could overwrite dirt | Nonzero failures for unreadable staged state; preserve conflicting unstaged generated-index edits |
| Universal frontmatter claims contradicted journal/control-file exemptions | Ontology and validation docs describe actual scope and editorial-only recommendations |
| Optional imports silently disabled checks; source-storage prose implied cloud/read-once behavior | Visible dependency notices, local original preservation, authorized private uploads, evidence-based verification |

## Intentionally not exported

The starter does not include live records, identities, accounts, cloud identifiers, private URLs, absolute user paths, logs, personal targets, schedules, or medical/nutrition policy. It does not install every domain skill from the operated vault, personal reminder masking, taxonomy registries/auditors, connectivity/orphan enforcement, or cloud-upload automation. Only reusable procedures and a small validation/hook extension belong in this release.

Taxonomy guidance separates document kind, subject/entity, and lifecycle. Unknown legacy vocabulary remains an editorial review concern; no mandatory bulk migration or unsupported “reviewed/tested” claims are introduced.

## Verification boundary

Regression tests use synthetic local repositories for staged-vs-working-tree rules/provenance, graph triggers and deletion/rename cases, authority regeneration safety, unreadable-index failure, and hook installation/commit blocking. Existing authority, provenance, and staged workflow tests remain part of the suite. No live services or private records are required. Release verification should run the suite and the complete staged graph audit; neither proves remote sync, storage permissions, or every user's custom hook integration.
