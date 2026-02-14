# PKB Ontology & Standards

> "A system is only as good as its constraints."

## Philosophy
This PKB is built on **Zettelkasten** principles, adapted for modern AI-assisted workflows.
1.  **Atomicity**: One concept, one note.
2.  **Connectivity**: Links > Folders. Structure emerges from connections (MOCs), not hierarchy.
3.  **Source vs. Synthesis**: strictly separate *what others said* (Source Notes) from *what I think* (Synthesis/Permanent Notes).

## Folder Structure

| Path | Purpose | Rules |
| :--- | :--- | :--- |
| `docs/sources/` | External knowledge (Articles, Books, PDF transcripts). | **Immutable.** Do not edit the author's words. Add your thoughts in a separate section or note. |
| `docs/projects/` | Active efforts with a goal and a deadline. | Must have `status/` tags. Move to `archive/` when done. |
| `docs/entities/` | People, Organizations, Locations. | Use `type/person`, `type/org`. |
| `mocs/` | **Maps of Content**. The entry points. | These are the "index" pages that link to other notes. |
| `journal/` | Daily logs, meetings, chronological scratchpad. | Date-based filename (`YYYY-MM-DD`). |

## Tag Ontology
We use **Hierarchical Tags** (nested with `/`) to enforce structure.

### 1. Types (`type/*`)
*What is this object?*
- `#type/source` - An external resource (article, video, book).
- `#type/person` - A human being.
- `#type/project` - A finite effort.
- `#type/area` - An ongoing responsibility (e.g., Health, Finance).
- `#type/concept` - An abstract idea or definition.

### 2. Status (`status/*`)
*What is the lifecycle state?*
- `#status/idea` - A shower thought; unrefined.
- `#status/active` - Currently in progress.
- `#status/blocked` - Waiting on something.
- `#status/done` - Completed.
- `#status/archive` - Frozen/deprecated.

### 3. Topics (`topic/*`)
*What is this about? (The domain)*
- `#topic/ai`
- `#topic/bio`
- `#topic/health`
- `#topic/finance`
- *(Add domains as needed, but keep them broad)*

## Frontmatter Schema
Every note **must** have this YAML header:

```yaml
---
id: [Unique ID or UUID]
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: [type/source, topic/ai]
source: [URL or Citation]
---
```

## The "AI Contract"
**Agents must follow these rules when editing:**
1.  **Never break links.** Use `refactor.py` to move/rename.
2.  **Always tag.** A note without tags is lost.
3.  **Link responsibly.** Do not create "orphan" notes. Connect a new note to at least one MOC or existing concept immediately.
