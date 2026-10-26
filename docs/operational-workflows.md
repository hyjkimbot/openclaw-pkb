# Operational workflows

Use these procedures after checking the user's current instructions and the [Git workflow](git-workflow.md). They describe agent behavior, not an automated ingestion service.

## Capture without changing policy

Before logging in an optional domain, distinguish four decisions:

1. **Consent:** Is this type of capture authorized? A tracking pause remains in effect until the user resumes it. A single requested entry does not necessarily resume ongoing tracking.
2. **Visibility:** Which details may be displayed, and where? A request to hide a metric does not itself authorize storing it secretly; a storage permission does not authorize displaying it everywhere.
3. **Targets:** Which current decision document governs any comparisons? Resolve a canonical key when configured. Targets supply context, not consent.
4. **State:** Was the event requested, planned, estimated, reported, or completed? Record the supported state. A request to schedule an activity is not evidence it happened.

Keep those decisions independent in local policy. Domain tracking, reminders, and thresholds are not installed by this template. Do not infer permission to resume one domain from a request in another.

## Journal and structured records

- Save the human's raw journal/day-log prose in `journal/YYYY-MM-DD.md` by default. Preserve meaning and attribution; a short timestamped entry is fine. Use the event date in the user's timezone, not automatically the message receipt date. Resolve genuinely ambiguous dates before assigning an exact date.
- Put atomic observations needed for analysis in the configured CSV log. Multiple real events can become multiple rows; do not replace the human narrative with an overcompressed row.
- Keep agent continuity (tool fixes, operating preferences, task handoffs) in the agent workspace outside the PKB. Backfill human history only from relevant authorized material, preserving uncertainty and attribution; do not bulk-copy agent memory files.
- Keep plans separate from completed history. For an optional activity workflow, a current plan can be a compact Markdown state sheet; completed history can be CSV. Update history and then refresh the current plan only when the source supports completion. This template does not ship a domain-specific activity tracker.

A different journal path is fine. Record the path in the user's local instructions. For a plain-prose journal under another vault directory, use the documented `frontmatterExemptPrefixes` setting in [validation](validation.md); do not exempt all curated notes.

## Structured CSV logging

Use `docs/<domain>/<log-name>/YYYY-MM.csv` for recurring observations. Choose a small schema for the domain; preserve an existing schema when editing. Register it under `csvSchemas` in `.agent/pkb-rules.json` (not in Python source).

1. Choose the monthly partition from the **event** date. Keep receipt/source timestamps separately if needed. Unknown values remain unknown; do not manufacture zeroes, exact quantities, or confirmed status.
2. Create a new month's file with its exact header. Add a navigation link from a log index or MOC when useful.
3. Append observations with a CSV-aware writer such as Python's `csv.DictWriter`; it handles commas, quotes, and newlines. Do not use shell `echo` to assemble user-supplied CSV values.
4. Correct an existing row in place using the schema's identifying columns. Preserve unrelated rows and their order; avoid duplicates on retries.
5. Read back the affected rows and any dependent state. Stage the intended files, commit through the gate, and sync only when authorized.

The CSV is the source of truth for structured history. Derive totals/charts directly with code, not LLM extraction from Markdown copies. Don't append computed total rows to observation logs. Keep units in the schema, not numeric cells. A narrative journal and a current-state note serve different purposes and need not duplicate every CSV row.

## Ingest a source

1. Check existing source notes by title, citation, and stable source reference. Update a material revision deliberately rather than creating a near-duplicate.
2. Read the supplied content or authorized source. Preserve a raw transcription in `docs/sources/raw/<slug>.txt` when useful and permitted; label OCR or other extraction uncertainty.
3. Create `docs/sources/<slug>.md` with `id`, `created`, `source`, and tags including a document-kind tag such as `type/source`. See [ontology](../ontology.md). Include a summary and the key claims relevant to the task; distinguish the author's claims from your own synthesis.
4. Link the note from a relevant MOC or existing note. Add provenance for a synthesis when useful; see [provenance](document-level-provenance-edges.md).
5. Read back the saved content and source references. Confirm any requested durable original storage before cleanup. Remove inbox or temporary originals only after successful ingestion and when deletion is authorized; prefer recoverable cleanup. Do not change email labels or delete remote originals as an unrequested side effect.

### Preserve originals when needed

Lossy text extraction may not be enough to verify exact numbers, quotes, or scans later. Preserve the original in an authorized private external store **or a durable local location outside Git**. Lack of cloud storage is not a reason to discard the only original.

- Upload only when the content and destination are authorized; retain restricted sharing. Check the returned object/reference and access state rather than treating command completion as proof of durability.
- Store a stable, non-secret `source_ref` such as a provider object identifier or a vault-relative reference to a local source registry. Never put credentials, signed access URLs, or machine-specific private paths into a public template.
- Record `extraction_method` (`manual`, `ocr`, or another accurate label) and `verification` (`pending`, `verified`, or `disputed`). Use `verified` only after comparison with the original; an upload alone is not verification.
- Prefer extracted data for routine queries, but revisit originals when accuracy, changed requirements, or disputed values require it. Do not enforce a “read once forever” rule.

`source_ref` is an external-storage convention, not a connectivity check performed by the validator. `raw_sources` and `source_notes` are separate, in-vault provenance paths.

## Move or rename notes

Preview the shipped helper before applying it:

```bash
python3 scripts/refactor.py docs/sources/old.md docs/sources/new.md --dry-run
python3 scripts/refactor.py docs/sources/old.md docs/sources/new.md
```

It updates basename wikilinks, including aliases/heading suffixes. It does **not** rewrite every Markdown link, path-qualified wikilink, or frontmatter dependency. Review the diff, update those references explicitly, and avoid the helper if duplicate basenames make its substitutions ambiguous. Stage the move and all intended link edits; run `python3 scripts/pkb-validate.py --full` before committing. Provenance warnings are advisory, so inspect them as well.
