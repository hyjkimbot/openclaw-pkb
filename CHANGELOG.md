# Changelog

## 0.6.0 — 2026-10-26

### Added

- Root skill router and bundled capture, local/remote Git, validation, upgrade, and drift-audit guides.
- Independent consent/tracking-pause, visibility, target, event-date, and reported/completed-state guidance; clear human-journal, CSV, and agent-continuity boundaries.
- Opt-in portable pre-commit hook with an installer that preserves existing hook setups.
- Conditional whole-index graph-scope link checks on Markdown changes (including deletions/renames), plus `pkb-validate.py --full`.
- Optional `allowedWriteRoots` and narrow `frontmatterExemptPrefixes` rules.

### Fixed

- Rules and provenance warnings now use indexed content/targets rather than working-tree state.
- Git/index read failures no longer report validation success; authority regeneration preserves conflicting unstaged generated-index edits.
- Optional dependency failures are visible. Documentation matches frontmatter exemptions, existing generic CSV configuration, and the refactor helper's limited link rewriting.
- Consolidated sync instructions honor local-only authorization and preserve unrelated work; removed broad staging and automatic reset/stash recipes.
- Source-storage guidance permits durable local originals, requires authorized restricted uploads, and distinguishes extraction from verification.

### Compatibility

Existing CSV schemas and authority/provenance fields are retained. No personal data, domain trackers, schedules, mandatory tag migration, remote service, or new Python dependency is added. PyYAML remains optional for basic validation and required for authority/provenance. See [upgrade instructions](docs/upgrade-v0.6.0.md) before adopting the wider graph check.

## 0.5.0 — baseline

The preceding skill version included canonical authority, opt-in provenance, generic CSV schemas, and staged frontmatter/CSV/link validation. No earlier release date is asserted here.
