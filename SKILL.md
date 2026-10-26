---
name: pkb
version: 0.6.0
description: "Manage a local Git-backed PKB: ingest sources, capture journals and structured records, resolve canonical authority, preserve provenance, and validate staged changes. Remote sync and domain tracking are opt-in."
---

# PKB workflow router

Resolve the user's vault root first; run commands there. A vault need not be at `./pkb`. Read the relevant bundled guide before editing. Keep this file with its `docs/` and `scripts/` resources; a standalone copied SKILL.md is not the complete skill.

## Route the task

| Task | Read |
| --- | --- |
| Ingest a source, journal, log records, or move notes | [Operational workflows](docs/operational-workflows.md) |
| Stage, commit, sync, recover a dirty checkout | [Git and sync](docs/git-workflow.md) |
| Configure schemas, install hooks, audit links | [Validation](docs/validation.md) |
| Resolve the current authority for a decision | [Canonical authority](docs/canonical-authority-indexing.md) |
| Record a synthesis's source dependencies | [Provenance](docs/document-level-provenance-edges.md) |
| Choose metadata and tags | [Ontology](ontology.md) |
| Adopt this version in an existing vault | [Upgrade guide](docs/upgrade-v0.6.0.md) |

For a configured domain, read that domain's own workflow before using its schemas or targets. This starter does not install domain trackers, schedules, or personal policies. Add domain routes only when needed.

## Shared rules

- Preserve the user's current consent, tracking pauses, display preferences, and targets as separate policy gates. A target document or historical log does not authorize new tracking. Hidden metrics are not automatically permitted to be stored. Explicit local-only and read-only requests override usual sync habits.
- Put human raw journal prose in `journal/` (or the user's configured PKB journal path); put structured observations in the applicable CSV; keep agent continuity and operating notes outside the vault. Don't copy a whole agent memory archive into the human journal.
- Record what was actually reported, keeping plans, requests, estimates, and completed events distinct. Use the event date and timezone, not automatically the message date. Never invent completion, verification, or review status.
- Inspect the branch, index, and working tree before editing. Preserve unrelated work, stage only intended paths, and use the installed pre-commit gate. If no hook is installed, run `python3 scripts/pkb-validate.py` after staging. After structural work, use `python3 scripts/pkb-validate.py --full`.
- Remote sync, uploads, and deletion of inbox originals require applicable authorization. A configured remote or storage provider is not authorization. Finish local-only work locally and say what remains unsynced.
- Verify the saved content before confirming success. Distinguish edited, committed, pushed, and externally stored states; report partial failures without repeating successful writes.

Commands such as `pkb:ingest` or `pkb:log` are conversational labels, not installed executables. The shipped CLI commands are in the guides above.
