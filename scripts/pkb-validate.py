#!/usr/bin/env python3
import json, os, re, sys, subprocess

# Generic version of pkb-validate.py
# Removed strict path allow-lists for broader compatibility, but kept frontmatter checks.

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CANONICAL_INDEX_PATH = os.path.join(BASE, '.agent', 'index', 'canonical.json')
CANONICAL_VOCAB_PATH = os.path.join(BASE, '.agent', 'index', 'canonical-keys.md')

# Authority indexing is optional — only loads if the module is present.
sys.path.insert(0, os.path.dirname(__file__))
try:
    from pkb_authority import (  # noqa: E402
        AuthorityError,
        CanonicalIndex,
        build_full_index,
        load_active_keys,
        load_index,
        validate_against_vocabulary,
        write_index,
    )
    AUTHORITY_AVAILABLE = True
except ImportError:
    AUTHORITY_AVAILABLE = False

# Provenance indexing is also optional. v1 is opt-in via citation_status,
# never coercive — the validator surfaces issues as warnings only and
# never blocks commits on provenance metadata.
try:
    from pkb_provenance import (  # noqa: E402
        ProvenanceError,
        build_full_index as build_provenance_index,
        collect_dangling_targets,
        extract_provenance,
    )
    PROVENANCE_AVAILABLE = True
except ImportError:
    PROVENANCE_AVAILABLE = False

frontmatter_re = re.compile(r'^---\n(.*?)\n---\n', re.S)
required_fm = {'id','created','tags'}

# ontology prefixes (customize these as needed)
ONTO_PREFIXES = ('type/', 'status/', 'project/', 'person/', 'area/')

# get staged files
try:
    # Check if we are inside a git repo
    if not os.path.exists(os.path.join(BASE, '.git')):
        print("PKB validate: Not a git repository. Skipping checks.")
        sys.exit(0)

    out = subprocess.check_output(['git','diff','--cached','--name-only'], cwd=BASE).decode().strip()
    files = [f for f in out.split('\n') if f]
except Exception as e:
    # If git fails, just warn and exit
    print(f'PKB validate: warning - git check failed: {e}')
    sys.exit(0)

# Frontmatter enforcement is scoped to vault note files. Control-plane
# directories and repository meta files (README, SKILL, ontology, etc.)
# are not Zettelkasten atoms and do not need id/created/tags.
FRONTMATTER_SKIP_PREFIXES = ('.agent/',)
FRONTMATTER_SKIP_FILES = {
    'README.md',
    'SKILL.md',
    'ontology.md',
    'CHANGELOG.md',
}


def _frontmatter_required(rel_path: str) -> bool:
    if any(rel_path.startswith(p) for p in FRONTMATTER_SKIP_PREFIXES):
        return False
    if rel_path in FRONTMATTER_SKIP_FILES:
        return False
    # Top-level docs/ design notes are also exempt; only files in
    # subdirectories under docs/ are treated as vault notes.
    if rel_path.startswith('docs/') and '/' not in rel_path[len('docs/'):]:
        return False
    return True


# validate format for markdown files
for f in files:
    if f.endswith('.md') and _frontmatter_required(f):
        p = os.path.join(BASE, f)
        if not os.path.exists(p):
            continue # deleted file

        try:
            txt = open(p,'r',encoding='utf-8').read()
        except Exception as e:
            print(f"PKB validate: cannot read {f}: {e}")
            sys.exit(1)
            
        m = frontmatter_re.match(txt)
        if not m:
            print(f"PKB validate: missing frontmatter in {f}")
            sys.exit(1)
            
        fm = m.group(1)
        fields = set(re.findall(r'^(\w+)\s*:', fm, re.M))
        
        # Check required fields
        missing = required_fm - fields
        if missing:
            print(f"PKB validate: missing frontmatter fields {missing} in {f}")
            sys.exit(1)

        # Check tags
        tags_m = re.search(r'^tags:\s*\[(.*?)\]\s*$', fm, re.M)
        if tags_m:
            tags = [t.strip() for t in tags_m.group(1).split(',') if t.strip()]
            if not any(t.startswith(ONTO_PREFIXES) for t in tags):
                print(f"PKB validate: tags in {f} should include an ontology prefix (e.g. type/, status/)")
                # Warning only for starter kit
                # sys.exit(1) 

# --- CSV log validation ---
# To enforce schemas on your CSV logs, add entries to CSV_DIR_SCHEMAS below.
# Each key is a directory prefix; any staged .csv file under it will be validated.
#
# Example:
#   'docs/health/nutrition-log/': {
#       'columns': ['date','meal','intake','cal_lo','cal_hi','status'],
#       'required': ['date','meal','intake'],
#       'integers': ['cal_lo','cal_hi'],
#       'numbers': [],
#       'enums': {'status': {'confirmed','tentative','updated',''}},
#   }

import csv

CSV_DIR_SCHEMAS = {
    # Add your log schemas here. Example commented out above.
}

DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')

csv_files_to_validate = []
for f in files:
    for dir_prefix, schema in CSV_DIR_SCHEMAS.items():
        if f.startswith(dir_prefix) and f.endswith('.csv'):
            csv_files_to_validate.append((f, schema))
            break

for csv_path, schema in csv_files_to_validate:
    full = os.path.join(BASE, csv_path)
    if not os.path.exists(full):
        continue
    try:
        with open(full, 'r', encoding='utf-8', newline='') as fh:
            reader = csv.DictReader(fh)
            header = reader.fieldnames or []

            if list(header) != schema['columns']:
                print(f"PKB validate: {csv_path} header mismatch: expected {schema['columns']}, got {list(header)}")
                sys.exit(1)

            for i, row in enumerate(reader, start=2):
                if all(v.strip() == '' for v in row.values()):
                    continue

                for col in schema.get('required', []):
                    if not row.get(col, '').strip():
                        print(f"PKB validate: {csv_path} row {i}: missing required field '{col}'")
                        sys.exit(1)

                if 'date' in row and row['date'].strip():
                    if not DATE_RE.match(row['date'].strip()):
                        print(f"PKB validate: {csv_path} row {i}: invalid date '{row['date']}' (expected YYYY-MM-DD)")
                        sys.exit(1)

                for col in schema.get('integers', []):
                    val = row.get(col, '').strip()
                    if val and not val.lstrip('-').isdigit():
                        print(f"PKB validate: {csv_path} row {i}: '{col}' must be integer, got '{val}'")
                        sys.exit(1)

                for col in schema.get('numbers', []):
                    val = row.get(col, '').strip()
                    if val:
                        try:
                            float(val)
                        except ValueError:
                            print(f"PKB validate: {csv_path} row {i}: '{col}' must be numeric, got '{val}'")
                            sys.exit(1)

                for col, allowed_vals in schema.get('enums', {}).items():
                    val = row.get(col, '').strip()
                    if val and val not in allowed_vals:
                        print(f"PKB validate: {csv_path} row {i}: '{col}' must be one of {allowed_vals}, got '{val}'")
                        sys.exit(1)

    except csv.Error as e:
        print(f"PKB validate: {csv_path} CSV parse error: {e}")
        sys.exit(1)

# --- Canonical authority indexing (optional) ---
# Activates when scripts/pkb_authority.py is present. Triggers on commits
# that touch markdown or canonical.json. Strategy: full frontmatter
# rebuild as ground truth; staged canonical.json blob must match it.
if AUTHORITY_AVAILABLE:
    md_changed = [f for f in files if f.endswith('.md')]
    rel_index = os.path.relpath(CANONICAL_INDEX_PATH, BASE)
    index_staged = rel_index in files

    if md_changed or index_staged:
        try:
            rebuilt, fm_errors = build_full_index(BASE)
        except AuthorityError as exc:
            print(f"PKB validate: authority error during rebuild: {exc}")
            sys.exit(1)
        if fm_errors:
            print('PKB validate: authority frontmatter errors block index update:')
            for rel, msg in fm_errors:
                print(f"  {rel}: {msg}")
            sys.exit(1)

        active_keys = load_active_keys(CANONICAL_VOCAB_PATH)
        if active_keys is not None:
            try:
                validate_against_vocabulary(rebuilt.records.values(), active_keys)
            except AuthorityError as exc:
                print(f"PKB validate: {exc}")
                sys.exit(1)

        if index_staged:
            try:
                blob = subprocess.check_output(
                    ['git', 'show', f':{rel_index}'],
                    cwd=BASE,
                    stderr=subprocess.DEVNULL,
                )
            except subprocess.CalledProcessError:
                print(f"PKB validate: cannot read staged blob for {rel_index}")
                sys.exit(1)
            blob_text = blob.decode('utf-8')
            staged_entries = json.loads(blob_text) if blob_text.strip() else {}
            if staged_entries != rebuilt.entries:
                print('PKB validate: staged canonical.json does not match a '
                      'frontmatter rebuild (do not hand-edit; run '
                      '`python3 scripts/pkb_authority.py audit` to regenerate):')
                staged_keys = set(staged_entries)
                rebuilt_keys = set(rebuilt.entries)
                for key in sorted(staged_keys - rebuilt_keys):
                    print(f"  in staged but not rebuild: {key} -> "
                          f"{staged_entries[key]}")
                for key in sorted(rebuilt_keys - staged_keys):
                    print(f"  in rebuild but not staged: {key} -> "
                          f"{rebuilt.entries[key]}")
                for key in sorted(staged_keys & rebuilt_keys):
                    if staged_entries[key] != rebuilt.entries[key]:
                        print(f"  {key}: staged={staged_entries[key]} "
                              f"rebuild={rebuilt.entries[key]}")
                sys.exit(1)
        else:
            on_disk = load_index(CANONICAL_INDEX_PATH)
            if on_disk.entries != rebuilt.entries:
                write_index(rebuilt, CANONICAL_INDEX_PATH)
                try:
                    subprocess.check_call(['git', 'add', rel_index], cwd=BASE)
                except subprocess.CalledProcessError as exc:
                    print(f"PKB validate: failed to stage updated {rel_index}: "
                          f"{exc}")
                    sys.exit(1)

# --- Provenance metadata (warnings only, never blocking) ---
# Per design, v1 is opt-in via citation_status. Stage commits never fail
# based on provenance — we only surface issues on staged files that
# already opted in, so users see structural problems they introduced.
if PROVENANCE_AVAILABLE:
    md_changed_for_prov = [f for f in files if f.endswith('.md')]
    for rel in md_changed_for_prov:
        full = os.path.join(BASE, rel)
        if not os.path.exists(full):
            continue
        try:
            with open(full, 'r', encoding='utf-8') as fh:
                text = fh.read()
        except OSError:
            continue
        try:
            rec = extract_provenance(rel, text)
        except ProvenanceError as exc:
            print(f"PKB validate: provenance warning: {exc}")
            continue
        except Exception:
            # YAML parse errors etc. — handled by other validators
            continue
        if rec is None:
            continue
        # Soft check: dangling source_notes / raw_sources
        for target in rec.source_notes + rec.raw_sources:
            target_full = os.path.join(BASE, target)
            if not os.path.exists(target_full):
                print(
                    f"PKB validate: provenance warning: {rel} references "
                    f"missing target {target}"
                )

print('PKB validate: OK')
sys.exit(0)
