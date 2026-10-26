# Upgrade to v0.6.0

This is an additive workflow and validation update, not a personal-data or taxonomy migration. Existing CSV schema configuration and authority/provenance fields remain compatible.

1. **Preserve local work.** Inspect the branch, staged changes, unstaged changes, custom rules, and hook configuration. Follow [safe sync/recovery](git-workflow.md) before merging. Do not replace your vault with a fresh public template or overwrite local policy.
2. **Adopt the bundle.** Merge the release or selectively update the root SKILL.md, README/ontology and bundled `docs/` guides, `scripts/pkb-validate.py`, new `scripts/install-hooks.py`, and `.githooks/pre-commit`. Keep the existing authority/provenance/frontmatter helpers. For a copied install, keep the whole bundle accessible and correct your agent's vault-root instructions.
3. **Retain configuration.** Preserve `.agent/pkb-rules.json`, registered canonical keys, domain workflows, and private data. No default personal schemas or trackers are added. Narrow `frontmatterExemptPrefixes` is available for a nonstandard plain-prose journal location; `allowedWriteRoots` is optional.
4. **Check dependencies.** Git and Python 3.10+ provide basic validation. Install PyYAML in the `python3` environment if using authority/provenance. Missing optional checks now print a notice instead of being silent.
5. **Choose the hook.** Run `python3 scripts/install-hooks.py` only if adopting the bundled gate. It refuses a conflicting hooksPath or any existing non-sample default hook file or symlink, including hooks other than `pre-commit`. Otherwise integrate the validator into your current pre-commit flow; do not discard personal checks. Local hook configuration is not distributed by a clone.
6. **Review staged behavior.** Stage intended changes and run `python3 scripts/pkb-validate.py --full` for the initial graph audit. Fix broken/ambiguous links surfaced in unchanged graph notes. Inspect generated canonical changes and provenance warnings, then commit through the normal hook. Push only if authorized.

## Behavior changes to expect

- Graph-scope Markdown edits, deletions, and renames now audit all indexed graph notes, not only changed source notes. This can expose pre-existing broken links. CSV-only changes still avoid a whole-graph scan; `--full` forces it when needed.
- Rules and provenance read the staged snapshot. Stage a new rules file with the changes it governs; a working-tree-only target no longer satisfies a provenance reference.
- Git/index access failures fail validation. Authority regeneration stops rather than overwriting conflicting unstaged changes to its generated index.
- No automatic tracking resumption, inbox deletion, upload, pull, or push is introduced. The router documents consent and local-only boundaries explicitly.
- The refactor helper is unchanged and only rewrites basename wikilinks. Review other links yourself. The validator still does not enforce whole-graph connectivity, heading anchors, or a controlled tag vocabulary.

For source-level detail, see the [drift audit](drift-audit-v0.6.0.md) and [changelog](../CHANGELOG.md). To undo hook adoption, first confirm the current hooksPath is still the one this installer set, then restore the prior Git configuration under your repository's policy. Do not remove another tool's hook configuration.
