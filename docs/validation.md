# Validation and local hooks

The validator checks the **Git index**, not unsaved editor buffers or unstaged working-tree changes. Stage the intended content before running it. It needs a usable Git repository and fails when the staged snapshot cannot be read.

```bash
python3 scripts/pkb-validate.py
python3 scripts/pkb-validate.py --full
```

## What runs

- **Every invocation:** optional allowed-write-path policy; basic frontmatter checks on staged curated Markdown; registered schemas on staged CSVs. Rules come from the indexed `.agent/pkb-rules.json`, so an unstaged rules edit cannot weaken the commit's checks.
- **Graph changes:** when a staged Markdown path is `README.md` or under `docs/`, `mocs/`, `blocks/`, or `journal/`, scan internal links in **all indexed Markdown in that scope**. Deletions and both sides of renames count. This catches inbound links from unchanged notes. `--full` forces this graph scan even for CSV-only commits or a clean index.
- **Canonical authority:** with its dependencies available, any staged Markdown or `canonical.json` triggers a rebuild from indexed frontmatter and indexed key vocabulary. An explicitly staged index must match that rebuild. Otherwise the generated index may be written and staged; conflicting unstaged edits to that file are preserved and block regeneration.
- **Provenance:** with its dependencies available, inspect staged Markdown with provenance fields (`source_notes`, `raw_sources`, or `citation_status`); missing indexed targets and malformed provenance produce warnings, not failures. Unstaged files do not satisfy provenance targets.

`--full` is a whole-graph **link** audit, not an all-CSV/all-frontmatter migration check, connectivity/orphan rule, or external service audit. Graph-scope Markdown excludes repository control files such as SKILL.md, ontology.md, `.agent/`, and presentation materials. Their links are not checked automatically. Deleting a non-Markdown attachment alone does not trigger the graph scan: use `--full` for attachment moves/deletions and other structural changes.

The link checker handles ordinary Markdown links and Obsidian wikilinks, ignoring backtick code examples. It checks target paths and ambiguity, not heading anchors, remote URLs, every Markdown dialect, or the semantic truth of a claim. The current basic frontmatter gate is not a complete YAML/tag-vocabulary validator. See [ontology](../ontology.md) for conventions that remain editorial guidance.

## Install the optional hook

```bash
python3 scripts/install-hooks.py
```

This sets repository-local `core.hooksPath=.githooks` and makes the shipped hook executable. It is idempotent when already configured. It refuses to replace any different effective hooksPath (including an inherited setting) or bypass any existing default hook file or symlink, not just `pre-commit`. Files are preserved even if not currently executable; `.sample` files are ignored. Repository-local settings and default hooks can be shared by linked worktrees; coordinate that choice if others use the same checkout.

If you already have a hook manager, add this command to its existing pre-commit flow, preserving its exit status:

```sh
python3 "$(git rev-parse --show-toplevel)/scripts/pkb-validate.py" || exit 1
```

Do not silently overwrite the old hook. This installer configures only the validator, not remote sync, personal policy checks, or any scheduled job. Hooks are a convenience gate, not a security boundary; review the staged diff as well.

## Optional rules file

Create and stage `.agent/pkb-rules.json` only when needed. No domain schemas are enabled by default. The existing `csvSchemas` interface uses directory-prefix keys:

```json
{
  "csvSchemas": {
    "docs/activities/log/": {
      "columns": ["date", "activity", "minutes", "status", "notes"],
      "required": ["date", "activity"],
      "integers": ["minutes"],
      "numbers": [],
      "enums": {"status": ["planned", "reported", "completed"]}
    }
  }
}
```

This is an example, not a shipped activity tracker. Headers must match in order. Nonblank values in `integers`, `numbers`, and `enums` are checked; put a column in `required` when blank values must fail. A column named `date` is checked for `YYYY-MM-DD` shape, not calendar validity. Keep directory prefixes nonoverlapping (the first matching schema wins). Editing a schema does not automatically revalidate unchanged CSVs.

Two additional optional settings:

- `allowedWriteRoots`: list of exact files or directory prefixes ending in `/`, such as `["docs/", "mocs/", "journal/", ".agent/", "scripts/", ".githooks/", "README.md", "SKILL.md"]`. Omit to impose no path restriction; an empty list permits no staged changes. Tailor it to your vault and maintenance files. It applies to staged additions, edits, and deletions, not filesystem access or privacy authorization.
- `frontmatterExemptPrefixes`: extra directory prefixes ending in `/` for plain-prose journals, for example `["docs/life/raw-journal/"]`. Existing `journal/` and `.agent/` exemptions remain. Exemption from frontmatter does not exempt graph-scope links.

## Dependencies and audits

Basic validation uses Python's standard library and Git. Canonical authority and provenance additionally need the shipped helper modules and PyYAML. Missing optional imports are announced; they do not block basic validation. If your workflow depends on authority/provenance, ensure those checks are available rather than treating the basic `OK` as proof they ran.

`pkb_authority.py audit` and `pkb_provenance.py audit` are separate **working-tree** scans that can write generated indexes. They do not replace the staged pre-commit checks. Run them intentionally after a merge or metadata cleanup, inspect their output, and stage the intended generated changes.
