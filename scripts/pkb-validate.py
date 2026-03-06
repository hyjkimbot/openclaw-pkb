#!/usr/bin/env python3
import os, re, sys, subprocess

# Generic version of pkb-validate.py
# Removed strict path allow-lists for broader compatibility, but kept frontmatter checks.

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

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

# validate format for markdown files
for f in files:
    if f.endswith('.md'):
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

print('PKB validate: OK')
sys.exit(0)
