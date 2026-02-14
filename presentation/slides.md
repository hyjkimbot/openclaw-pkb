# The AI-Native Personal Knowledge Base (PKB)
*Building a Shared Brain with OpenClaw*

---

## 1. The Problem: "Memory Amnesia"

*   **Context**: We talk to AI agents all day, but where does the context go?
*   **The Gap**: 
    *   Chat logs are linear and noisy.
    *   Vector databases are opaque black boxes.
    *   SaaS tools (Notion, etc.) lock your data away from your agents.
*   **The Need**: A shared, structured state that both **Human** and **Agent** can read, write, and trust.

---

## 2. The Solution: "Git as the Backbone"

*   **Concept**: A local folder of Markdown files, version-controlled by Git.
*   **Why Git?**
    *   **Universal**: Every developer tool understands it.
    *   **Versioned**: Mistakes are reversible. History is preserved.
    *   **Offline-First**: No API rate limits for reading your own thoughts.
*   **The Stack**:
    *   **Human Interface**: Obsidian (for thinking/linking).
    *   **Agent Interface**: OpenClaw (for doing/organizing).
    *   **Sync**: GitHub/Git (the source of truth).

---

## 3. Architecture: The "Dual-Interface"

> *"Provenance is Infrastructure."*

*   **The Vault Structure**:
    *   `docs/sources/`: Raw intake (articles, papers). 
    *   `mocs/`: Maps of Content (the "neural pathways").
    *   `journal/`: Daily logs and quantified self data.
*   **The Agent's Role (OpenClaw)**:
    *   **Curator**: It doesn't just "save" files; it formats frontmatter, tags ontologies, and updates indices.
    *   **Analyst**: It tracks trends (e.g., workout loads) and commits data directly to the repo.
    *   **Janitor**: It refactors links and keeps the graph healthy.

---

## 4. Key Workflows

### A. Structured Ingestion
*   **User**: "Save this article."
*   **OpenClaw**: 
    1.  Fetches content.
    2.  Extracts key claims.
    3.  Writes `docs/sources/article.md` with strict metadata.
    4.  Updates `mocs/topic.md`.

### B. Quantified Self (Active State)
*   **User**: "Bench press 225x5, RPE 8."
*   **OpenClaw**:
    1.  Parses the data.
    2.  Updates `docs/exercise/current-loads.json` (structured state).
    3.  Appends to daily log (narrative state).
    4.  Commits & Pushes instantly.

---

## 5. Why OpenClaw?

*   **Tooling**: OpenClaw's `read`, `write`, and `exec` tools make it a native citizen of the file system.
*   **Skills**: We packaged this as the `pkb` skill—a portable definition of *how* to manage knowledge.
*   **Agency**: The agent isn't just answering questions; it's **gardening** your knowledge graph while you sleep.

---

## 6. Call to Action: Own Your Data

*   **The Future**: Agents will come and go. Models will change. **Your data must survive.**
*   **Get Started**: 
    *   Check out the **PKB Starter Kit**.
    *   Clone it, point OpenClaw at it, and start building your shared brain today.

![PKB Starter Kit QR](assets/qr.png)
