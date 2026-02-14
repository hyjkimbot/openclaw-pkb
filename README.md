# PKB Starter Kit

<img src="assets/qr.png" align="right" width="150" alt="QR Code" />

This directory contains the essential scripts and structure for a Personal Knowledge Base (PKB) managed via Git and OpenClaw.

## Installation

1.  **Clone the Repository**:
    We recommend cloning this into your workspace root (e.g., `~/workspace/pkb`).
    ```bash
    git clone <your-repo-url> pkb
    cd pkb
    ```
    *Note:* The skill expects the vault to be at `./pkb` relative to the agent's workspace. If you place it elsewhere, update the paths in `SKILL.md`.

2.  **Initialize Structure**:
    Create the folders: `docs/sources`, `mocs`, `scripts`.
    
    ```bash
    mkdir -p docs/sources mocs scripts
    ```

3.  **Install Scripts**:
    Copy `pkb-validate.py` and `refactor.py` into the `scripts/` folder.
    Make them executable:
    ```bash
    chmod +x scripts/*.py
    ```

4.  **Install the Skill**:
    Copy `SKILL.md` to your OpenClaw skills directory (e.g. `skills/pkb/SKILL.md`).
    Update the paths in `SKILL.md` if necessary to point to your `pkb` location.

## Usage

- **Ingest**: Use the skill to save new notes to `docs/sources/`. The skill enforces frontmatter (`id`, `tags`, etc.).
- **Refactor**: Use `scripts/refactor.py old.md new.md` to move files and update wikilinks automatically.
- **Validate**: The skill runs `scripts/pkb-validate.py` before committing to ensure data integrity.

## Human Setup (The Viewer)

To view and edit these notes pleasantly:

1.  **Install Obsidian**: [https://obsidian.md](https://obsidian.md)
2.  **Open the Vault**: Select "Open folder as vault" and choose your `pkb` directory.
3.  **Install the Git Plugin**:
    *   Settings → Community Plugins → Turn on Community Plugins.
    *   Browse → Search for **"Obsidian Git"** (by Vinzent03).
    *   Install & Enable.
    *   *Why?* This allows the desktop app to sync changes made by your AI agent automatically (and vice versa).

## Agent Interaction

This skill enables your AI agent to manage the vault. Here are the standard workflows you can use:

### 1. Ingestion
*   **User:** "Save this article to my PKB."
*   **Agent:** Fetches content, creates `docs/sources/article-name.md`, adds frontmatter (`type/source`), and links it to relevant MOCs.

### 2. Logging
*   **User:** "Log a workout: Bench 135x10, felt easy."
*   **Agent:** Appends to `journal/YYYY-MM-DD.md` or specialized logs like `docs/exercise/log.md`.

### 3. Refactoring
*   **User:** "Rename the 'Project X' note to 'Project Y'."
*   **Agent:** Runs `scripts/refactor.py` to move the file and **update all wikilinks** automatically.

### 4. Querying
*   **User:** "What have I saved about 'Bioinformatics'?"
*   **Agent:** Greps for `#topic/bio` or searches text content to summarize findings.

## Directory Layout (Recommended)

```
pkb/
├── docs/
│   ├── sources/    # External knowledge (articles, books)
│   └── projects/   # Active work
├── mocs/           # Maps of Content (indexes)
├── scripts/        # Automation scripts
├── .gitignore      # Standard gitignore
└── README.md
```

## Presentation

Check out the [OpenClaw Event Presentation](presentation/slides.md) for a conceptual overview of the AI-Native PKB.
