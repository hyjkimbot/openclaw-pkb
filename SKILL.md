---
name: pkb
description: Personal Knowledge Base management skill. Use for ingesting documents, creating source notes, and managing a Git-backed Obsidian vault.
---

# PKB Ingest Workflow

Follow these steps for any document ingestion task.

# PKB Skill Definition

This skill manages a local Obsidian vault backed by Git. It prioritizes data integrity (Git) and structure (Zettelkasten).

## Supported Workflows

### 1. Ingestion (`pkb:ingest`)
**Goal:** Capture external knowledge without clutter.
- **Input:** URL or text block.
- **Process:**
  1.  **Deduplicate:** Check `docs/sources/` for existing notes.
  2.  **Fetch:** Get readable content (if URL).
  3.  **Create:** Write `docs/sources/[slug].md`.
      - **Frontmatter:** `id`, `created`, `source`, `tags` (must include `type/source`).
  4.  **Connect:** Add a link to this note in at least one `mocs/` file (e.g., `mocs/inbox.md` or `mocs/topic-name.md`).

### 2. Daily Logging (`pkb:log`)
**Goal:** Frictionless capture of thoughts/events.
- **Input:** "Log [text]" or "Note [text]".
- **Process:**
  1.  Determine today's note: `journal/YYYY-MM-DD.md`.
  2.  Append timestamped entry: `\n- [HH:MM] {text}`.
  3.  (Optional) If specific topic detected (e.g. workout), update domain-specific logs (e.g. `docs/exercise/current-loads.json`).

### 3. Maintenance (`pkb:refactor`)
**Goal:** Rename or move notes without breaking the graph.
- **Input:** "Rename [old] to [new]" or "Move [note] to [folder]".
- **Process:**
  1.  **Do NOT use `mv`.**
  2.  Run `python3 scripts/refactor.py [old_path] [new_path]`.
  3.  This script updates all `[[Wikilinks]]` pointing to the old note.

### 4. Integrity Check (`pkb:validate`)
**Goal:** Ensure the vault adheres to `ontology.md`.
- **Process:**
  1.  Run `python3 scripts/pkb-validate.py`.
  2.  Fix any errors (missing tags, bad frontmatter) before committing.

## Git Operations
- **Always Pull First:** `git -C pkb pull`
- **Always Push After:** `git -C pkb commit ... && git -C pkb push`
- **Commit Messages:** Use conventional commits (`feat:`, `chore:`, `docs:`).

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
