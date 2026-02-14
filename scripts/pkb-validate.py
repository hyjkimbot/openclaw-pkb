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

print('PKB validate: OK')
sys.exit(0)
