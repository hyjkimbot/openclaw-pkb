---
name: pkb
description: Personal Knowledge Base management skill. Use for ingesting documents, creating source notes, and managing a Git-backed Obsidian vault.
---

# PKB Ingest Workflow

Follow these steps for any document ingestion task.

## 1. Preparation
- **Pull Latest**: Always run `git -C pkb pull` before starting.
- **Deduplication**: Check `docs/sources/` for existing notes with similar titles.

## 2. Ingesting
- **Raw Text**: Save the full content to `docs/sources/raw/[slugified-title].txt` (optional).
- **Source Note**: Create `docs/sources/[slugified-title].md`.
  - **Frontmatter**: Must include `id`, `created`, `source`, and `tags`.
  - **Tags**: Must include at least one ontology prefix (`type/`, `status/`, `project/`, `person/`).
  - **Content**: Include Executive Summary, Summary, Key Points, Claims/Hypotheses, and a link to the raw source.
- **MOC Updates**: Add the new note to relevant Maps of Content in `mocs/`.

## 3. Cleanup
- **Local Files**: Delete any temporary export files (e.g., in `/tmp/`).

## 4. Finalize
- **Validate**: Run `python3 scripts/pkb-validate.py` (ensure changes are staged first).
- **Push**: `git -C pkb add .`, `git -C pkb commit -m "Ingest: [Title]"`, and `git -C pkb push`.

## 5. Maintenance
- **Refactor**: Use `scripts/refactor.py old.md new.md` to safely move files and update wikilinks.
