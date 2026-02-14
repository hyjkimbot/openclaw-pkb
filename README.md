# PKB Starter Kit

This directory contains the essential scripts and structure for a Personal Knowledge Base (PKB) managed via Git and OpenClaw.

## Installation

1.  **Create the Repository**:
    ```bash
    mkdir pkb
    cd pkb
    git init
    ```

2.  **Add Structure**:
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
