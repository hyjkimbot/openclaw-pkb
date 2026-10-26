# PKB ontology and standards

Use a small vocabulary that helps retrieve and interpret notes. Source notes preserve what a source said; synthesis notes make the author's reasoning explicit. Connect useful notes through MOCs and links without forcing every journal entry into a curated-note schema.

## Storage boundaries

- `docs/sources/`: source notes and optional raw transcriptions; keep quotations distinct from commentary and corrections.
- `docs/projects/` and other optional domains: curated notes, decisions, and domain workflows.
- `mocs/`: maps of content; use `type/moc` for new curated indexes.
- `journal/`: human raw chronology and reflections, usually date-named.
- `docs/<domain>/<log-name>/YYYY-MM.csv`: structured observations for analysis. Schemas live in `.agent/pkb-rules.json`.
- Agent continuity: outside the human vault, in the agent's own workspace.

Current plans or compiled state can be compact Markdown notes. They are not substitutes for completed history. A journal narrative and a CSV row may describe the same day for different purposes; do not maintain parallel Markdown tables as a second numeric source of truth.

## Separate the metadata axes

**Document kind (`type/*`)** describes what a note is: `type/source`, `type/moc`, `type/reference`, `type/decision`, or another locally defined kind. For new or substantively revised curated notes, choose a supported kind rather than stuffing all meaning into one tag.

**Topic and entity labels** describe what it concerns: `topic/<subject>`, `project/<name>`, `person/<name>`, or another local convention. Being about a project or a person does not imply that the document itself is a project plan or a biography.

**Lifecycle (`status`)** describes an evidenced state. Authority uses the structured `status:` field; a `status/*` tag may help human search but must not contradict it. Do not add `reviewed`, `tested`, `verified`, or `completed` just to fill a field. Missing evidence is a reason to leave the claim out or mark it pending, not invent it.

Existing vocabularies can coexist. Review unknown legacy labels as advisory hygiene findings; this release does not ship a taxonomy auditor or require a bulk migration. The basic validator retains its compatibility check for an ontology prefix in inline tag lists; it does not enforce every recommendation here.

## Frontmatter scope

Curated Markdown notes need `id`, `created`, and `tags`. Source notes should also supply `source`; `updated` is useful when a substantive revision occurs. Example:

```yaml
---
id: source-example
created: 2026-01-01
tags: [type/source, topic/example]
source: "Original source citation"
---
```

The validator exempts plain `journal/` entries, `.agent/` control files, README.md, SKILL.md, ontology.md, CHANGELOG.md, and top-level design/guide files directly under `docs/`. Other staged Markdown, including curated notes in `docs/<subdirectory>/` and `mocs/`, retains the frontmatter gate. Configure additional narrow journal exemptions only when needed; see [validation](docs/validation.md).

## Authority and provenance

Search relevance answers which notes discuss a subject. **Canonical authority** answers which note currently governs a decision. Register a key under `## Active keys` in `.agent/index/canonical-keys.md`, then claim it with `canonical_for` in the intended document. The generated lookup is `.agent/index/canonical.json`; do not hand-edit it. See [canonical authority](docs/canonical-authority-indexing.md).

**Provenance** answers what evidence informed a note. Opt in with `citation_status` and use `source_notes` / `raw_sources` for in-vault dependency paths. This is independent of canonical authority and lifecycle. An external `source_ref` may identify the durable original, but does not imply that extracted data has been verified. See [provenance](docs/document-level-provenance-edges.md).

## Editing contract

Read the relevant domain policy, preserve uncertainty, and use the actual event date. Link new curated notes to an appropriate MOC or existing concept. Preview renames and inspect references the helper does not rewrite. Stage intended files and use the [Git workflow](docs/git-workflow.md) and [validation gate](docs/validation.md); do not imply that editorial guidance is enforced by code when it is not.
