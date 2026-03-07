---
name: pkb
version: 0.3.0
description: Personal Knowledge Base management skill. Use for ingesting documents, creating source notes, structured logging, and managing a Git-backed Obsidian vault.
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

## External Services (Optional)

The PKB works fully offline with just local Git. External services enhance durability and collaboration but are never required.

- **Git remote (GitHub, etc.):** Recommended for backup and multi-device sync. If not configured, skip `git push`/`git pull` — local commits still provide version history.
- **External file storage (Google Drive, S3, etc.):** Recommended for preserving original binary sources (PDFs, scans, images) that are too large or lossy to store as raw text in Git. If not configured, the raw text transcription in `docs/sources/raw/` is the only source copy.

### Durable Source Storage (Optional)

Documents requiring later verification (lab reports, legal/tax docs, scanned receipts) should preserve the original file outside Git. Text transcriptions (OCR, copy-paste) are lossy and error-prone — the original binary is the only reliable audit trail.

If external storage is configured:
1. **Upload original** to a `pkb/` folder in your storage provider (e.g., Google Drive `pkb/Health/Lab Reports/`). Keep files **private/restricted**.
2. **Add provenance frontmatter** to the source note:
   ```yaml
   source_ref: drive:<fileId>    # or s3:<key>, local:<path>, etc.
   extraction_method: pdf-direct  # or ocr, manual, llm
   verification: verified         # or pending, disputed
   ```
   - `source_ref` uses a stable identifier (Drive file ID, S3 key), not a URL that may change.
   - `verification` tracks whether extracted data has been confirmed against the original.

**Token cost rule:** Read the original document once during ingestion to extract structured data (CSV rows, markdown summary). For all subsequent queries, use the extracted data only. Re-read the original only if a value is disputed.

## Git Operations
- **Always Pull First:** `git -C pkb pull` (skip if no remote configured)
- **Always Push After:** `git -C pkb commit ... && git -C pkb push` (skip push if no remote)
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

## 6. Structured Logging (CSV)

### General Principles
- Time-series data (nutrition, mood, symptoms, workouts, finances, etc.) should be stored as CSV, not markdown tables.
- CSV files are the single source of truth — do not maintain parallel markdown copies.
- Obsidian renders CSVs via the **CSV Lite** community plugin.
- When plotting or analyzing log data, read CSVs directly with code (e.g., `pd.read_csv()` / `glob` + `concat`). Do NOT use LLM calls to extract data from logs.
- Every CSV file must include a header row matching its schema exactly.

### File Structure
Logs are stored as monthly CSV files in per-topic directories to keep files small and in-place edits cheap:

```
docs/<domain>/<log-name>/YYYY-MM.csv
```

Example:
```
docs/health/nutrition-log/2026-03.csv
docs/health/daily-checkin/2026-03.csv
docs/finance/expenses/2026-03.csv
```

Each log directory should have an index file (`docs/<domain>/<log-name>.md`) with wikilinks to each monthly CSV for Obsidian navigation.

### Workflow

1. **Pull first**: `git pull` before any edits.
2. **Determine the file**: Use the entry's date to pick the correct monthly file. If the file doesn't exist yet (new month), create it with the header row first, then add a wikilink to the corresponding index `.md` file.
3. **Append**: Add new rows to the end of the monthly CSV using shell append:
   ```
   echo 'col1,col2,...' >> docs/health/nutrition-log/2026-03.csv
   ```
   Do NOT sort or reorder existing rows.
4. **In-place update**: When correcting a previously logged entry, edit the existing row in place rather than appending a duplicate. Match on date + identifying columns to find the row.
5. **Commit & Push**: Stage the changed CSV, commit with a descriptive message, and push.

### Defining a Log Schema
Each log needs a documented schema. Example:

```
# Nutrition Log
Columns: date,meal,intake,cal_lo,cal_hi,pro_lo,pro_hi,status,notes
- date: YYYY-MM-DD
- cal_lo, cal_hi: integer calorie bounds (same value if single estimate)
- status: one of confirmed, tentative, updated
```

Register schemas in `scripts/pkb-validate.py` to enforce column headers, types, and enums on commit.

### Rules
- No units in numeric columns (no `kcal`, no `g`, no `$`).
- Wrap values in double quotes if they contain commas.
- Do NOT add computed summary rows (e.g., "Day Total"). Totals are derived from the data.
