# PKB Starter Kit

A local, Git-backed knowledge base for people and their agents. Version **0.6.0** adds practical capture and sync procedures plus an optional pre-commit gate. Markdown and CSV remain ordinary files; Obsidian, cloud storage, and remote Git are optional.

## Start locally

Use this public repository as a template for a **private vault** before adding personal records. Alternatively, copy the starter into a local Git repository. Do not push personal notes back to the public template.

```bash
git clone <your-vault-repo-url> pkb
cd pkb
mkdir -p docs/sources mocs journal
```

Git and Python 3.10+ are required for the scripts. All scripts are already included; no separate copying step is needed. For canonical authority and provenance, install PyYAML into the Python environment used by `python3`:

```bash
python3 -m pip install PyYAML
```

Without PyYAML or the helper modules, basic frontmatter, configured CSV schemas, and link checks still run. The validator prints which optional checks are unavailable; the authority/provenance CLI tools require those dependencies. See [validation](docs/validation.md).

Opt in to the local pre-commit gate:

```bash
python3 scripts/install-hooks.py
```

The installer refuses to bypass any existing default hook file or symlink (apart from `.sample` files), or replace a different `core.hooksPath`. Hooks are local Git configuration, not enabled merely by cloning. Existing users should follow the [upgrade guide](docs/upgrade-v0.6.0.md).

## Connect an agent

Point your agent's workspace instructions at this vault's [SKILL.md](SKILL.md), using the actual vault path. The root skill routes to bundled guides. If your agent requires skills in a separate directory, retain access to the complete bundle and explicitly configure the vault root; don't copy just SKILL.md and lose its linked resources. Nothing in the scripts requires an OpenClaw service.

Examples:

- “Save this article to my PKB.” Deduplicate, create a source note, and connect it to a MOC.
- “Journal this under yesterday's date.” Preserve the prose in the human journal; do not silently activate unrelated trackers.
- “Log this completed activity.” Use an existing authorized domain schema, or agree on a small schema first.
- “Rename this note.” Preview the refactor, check path-style links separately, then audit the staged graph.
- “Keep this change local.” Do not fetch, pull, push, or upload.

## What's included

```text
SKILL.md                    Agent entry point and workflow router
ontology.md                 Note, tag, and record conventions
docs/                       Bundled workflow and design guides
scripts/                    Validator, refactor, authority and provenance tools
.githooks/pre-commit         Optional staged-snapshot gate
.agent/index/               Canonical vocabulary and generated indexes
tests/                      Regression tests using temporary local repositories
```

Your content can use `docs/sources/`, `docs/<domain>/<log-name>/YYYY-MM.csv`, `mocs/`, and `journal/YYYY-MM-DD.md`. These are conventions, not pre-populated personal datasets. Schemas are opt-in through `.agent/pkb-rules.json`; none are hardcoded for a person's health or other domains.

Read [operational workflows](docs/operational-workflows.md), [Git and sync](docs/git-workflow.md), and [validation](docs/validation.md) for the procedures. [Canonical authority](docs/canonical-authority-indexing.md) answers which note governs a decision; [provenance](docs/document-level-provenance-edges.md) records the evidence behind it.

## Optional viewing and storage

Open the vault in [Obsidian](https://obsidian.md). CSV Lite can render structured logs. No plugin is required to write or analyze CSV with ordinary tools.

For multi-device sync, choose a Git client or Obsidian plugin such as Fit. Use a private repository and the least repository access the client supports. Keep credentials out of Git. Fit's `.obsidian/plugins/fit/data.json` and `_fit/` mirror are ignored by this starter; also exclude `_fit/` from Obsidian search/graph. Ignore rules do not untrack a file already committed. Coordinate concurrent editors using the [sync workflow](docs/git-workflow.md).

Original PDFs, scans, and other binary evidence may be kept in an authorized private external store or a durable local location. Record a stable non-secret reference and the actual verification state; see [source storage](docs/operational-workflows.md#preserve-originals-when-needed). No cloud account, public sharing, or upload automation is installed.

## Development and release notes

```bash
python3 -m unittest discover -s tests -v
```

The full test suite uses PyYAML. See [changelog](CHANGELOG.md), [v0.6.0 drift audit](docs/drift-audit-v0.6.0.md), and [upgrade guide](docs/upgrade-v0.6.0.md). The [event presentation](presentation/slides.md) is background material, not the operational specification.
