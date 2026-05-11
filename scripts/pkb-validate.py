#!/usr/bin/env python3
import collections
import csv
import io
import json
import os
import re
import subprocess
import sys

# Generic version of pkb-validate.py.
# Validates the git index (the staged snapshot) so pre-commit behavior matches
# what will actually be committed, even when the working tree has diverged.

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
RULES_PATH = os.path.join(BASE, '.agent', 'pkb-rules.json')
CANONICAL_INDEX_PATH = os.path.join(BASE, '.agent', 'index', 'canonical.json')
CANONICAL_VOCAB_PATH = os.path.join(BASE, '.agent', 'index', 'canonical-keys.md')

# Authority indexing is optional — only loads if the module is present.
sys.path.insert(0, os.path.dirname(__file__))
try:
    from pkb_authority import (  # noqa: E402
        AuthorityError,
        CanonicalIndex,
        build_full_index,
        build_index_from_markdown_texts,
        load_active_keys,
        load_index,
        parse_active_keys,
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
required_fm = {'id', 'created', 'tags'}

# ontology prefixes (customize these as needed)
ONTO_PREFIXES = ('type/', 'status/', 'project/', 'person/', 'area/')


def _git_output(args, *, binary=False):
    out = subprocess.check_output(args, cwd=BASE, stderr=subprocess.DEVNULL)
    if binary:
        return out
    return out.decode('utf-8')


def _git_zlist(args):
    return [p for p in _git_output(args).split('\0') if p]


def _git_show_index_text(rel_path):
    """Return a file's git-index text, or None when absent from the index."""
    try:
        blob = _git_output(['git', 'show', f':{rel_path}'], binary=True)
    except subprocess.CalledProcessError:
        return None
    return blob.decode('utf-8')


# get staged files and the full index file list
try:
    # Check if we are inside a git repo
    if not os.path.exists(os.path.join(BASE, '.git')):
        print("PKB validate: Not a git repository. Skipping checks.")
        sys.exit(0)

    files = _git_zlist(['git', 'diff', '--cached', '--name-only', '-z'])
    index_files = _git_zlist(['git', 'ls-files', '-z'])
except Exception as e:
    # If git fails, just warn and exit
    print(f'PKB validate: warning - git check failed: {e}')
    sys.exit(0)

index_file_set = set(index_files)


def index_text(rel_path):
    return _git_show_index_text(rel_path)


rules = {}
if os.path.exists(RULES_PATH):
    try:
        with open(RULES_PATH, 'r', encoding='utf-8') as fh:
            rules = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"PKB validate: cannot read {RULES_PATH}: {exc}")
        sys.exit(1)

# Frontmatter enforcement is scoped to vault note files. Control-plane
# directories and repository meta files (README, SKILL, ontology, etc.)
# are not Zettelkasten atoms and do not need id/created/tags.
FRONTMATTER_SKIP_PREFIXES = ('.agent/', 'journal/')
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
        txt = index_text(f)
        if txt is None:
            continue  # deleted file

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
                sys.exit(1)

# --- CSV log validation ---
# To enforce schemas on your CSV logs, add entries under `csvSchemas` in
# .agent/pkb-rules.json. Each key is a directory prefix; any staged .csv file
# under it will be validated. Example:
#
# {
#   "csvSchemas": {
#     "docs/health/nutrition-log/": {
#       "columns": ["date", "meal", "intake", "cal_lo", "cal_hi", "status"],
#       "required": ["date", "meal", "intake"],
#       "integers": ["cal_lo", "cal_hi"],
#       "numbers": [],
#       "enums": {"status": ["confirmed", "tentative", "updated", ""]}
#     }
#   }
# }

CSV_DIR_SCHEMAS = rules.get('csvSchemas', {})
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')

csv_files_to_validate = []
for f in files:
    for dir_prefix, schema in CSV_DIR_SCHEMAS.items():
        if f.startswith(dir_prefix) and f.endswith('.csv'):
            csv_files_to_validate.append((f, schema))
            break

for csv_path, schema in csv_files_to_validate:
    txt = index_text(csv_path)
    if txt is None:
        continue
    try:
        with io.StringIO(txt, newline='') as fh:
            reader = csv.DictReader(fh)
            header = reader.fieldnames or []

            if list(header) != schema['columns']:
                print(f"PKB validate: {csv_path} header mismatch: expected {schema['columns']}, got {list(header)}")
                sys.exit(1)

            for i, row in enumerate(reader, start=2):
                if all((v or '').strip() == '' for v in row.values()):
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
                    if val and val not in set(allowed_vals):
                        print(f"PKB validate: {csv_path} row {i}: '{col}' must be one of {allowed_vals}, got '{val}'")
                        sys.exit(1)

    except csv.Error as e:
        print(f"PKB validate: {csv_path} CSV parse error: {e}")
        sys.exit(1)

# --- Markdown link validation for staged markdown files ---
# Validate staged content against the git index file list, not the working tree.
PATHLIKE_EXTS = ('.md', '.txt', '.csv', '.json', '.pdf', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.html')
WIKILINK_RE = re.compile(r'\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]')
MDLINK_RE = re.compile(r'\[[^\]]+\]\(([^)]+)\)')
FENCED_CODE_RE = re.compile(r'^```.*?^```', re.M | re.S)
INLINE_CODE_RE = re.compile(r'`[^`\n]*`')


def _norm(rel_path: str) -> str:
    return os.path.normpath(rel_path).replace('\\', '/').lstrip('./')


def _strip_markdown_code(txt: str) -> str:
    txt = FENCED_CODE_RE.sub('', txt)
    return INLINE_CODE_RE.sub('', txt)


def _resolve_path_candidates(src_rel: str, target: str, exts_if_missing=('.md',)):
    t = _norm(target)
    if not t:
        return []

    has_ext = bool(os.path.splitext(t)[1])
    variants = [t] if has_ext else [t + ext for ext in exts_if_missing]

    src_dir = os.path.dirname(src_rel)
    candidates = []
    for v in variants:
        for rel_try in (_norm(v), _norm(os.path.join(src_dir, v))):
            hit = all_files_lut.get(rel_try.lower())
            if hit:
                candidates.append(hit)

    out = []
    for c in candidates:
        if c not in out:
            out.append(c)
    return out


all_files_rel = [_norm(rel) for rel in index_files if not rel.startswith(('.git/', '_fit/', '.obsidian/'))]
all_files_lut = {f.lower(): f for f in all_files_rel}
stem_index = collections.defaultdict(list)
for rel in all_files_rel:
    stem = os.path.splitext(os.path.basename(rel))[0].lower()
    stem_index[stem].append(rel)

unresolved = []
ambiguous = []
for src_rel in [f for f in files if f.endswith('.md')]:
    txt = index_text(src_rel)
    if txt is None:
        continue
    txt = _strip_markdown_code(txt)

    for token in WIKILINK_RE.findall(txt):
        tok = token.strip()
        if not tok:
            continue
        if '/' in tok:
            cands = _resolve_path_candidates(src_rel, tok, exts_if_missing=PATHLIKE_EXTS)
        else:
            cands = list(dict.fromkeys(stem_index.get(tok.lower(), [])))
        if len(cands) == 0:
            unresolved.append((src_rel, tok))
        elif len(cands) > 1:
            ambiguous.append((src_rel, tok, cands))

    for href in MDLINK_RE.findall(txt):
        raw = href.strip().split('#', 1)[0].strip()
        if not raw or raw.startswith(('http://', 'https://', 'mailto:')):
            continue
        cands = _resolve_path_candidates(src_rel, raw, exts_if_missing=('.md',))
        if len(cands) == 0:
            unresolved.append((src_rel, raw))
        elif len(cands) > 1:
            ambiguous.append((src_rel, raw, cands))

if unresolved:
    print('PKB validate: unresolved internal links found:')
    for src, tgt in unresolved[:20]:
        print(f"  - {src} -> {tgt}")
    if len(unresolved) > 20:
        print(f"  ... and {len(unresolved) - 20} more")
    sys.exit(1)

if ambiguous:
    print('PKB validate: ambiguous links found (use explicit path):')
    for src, tgt, cands in ambiguous[:20]:
        preview = ', '.join(cands[:3])
        extra = '' if len(cands) <= 3 else f" (+{len(cands) - 3} more)"
        print(f"  - {src} -> {tgt} matches [{preview}{extra}]")
    if len(ambiguous) > 20:
        print(f"  ... and {len(ambiguous) - 20} more")
    sys.exit(1)

# --- Canonical authority indexing (optional) ---
# Activates when scripts/pkb_authority.py is present. Triggers on commits
# that touch markdown or canonical.json. Strategy: rebuild from staged
# markdown as ground truth; staged canonical.json blob must match it.
if AUTHORITY_AVAILABLE:
    def _build_staged_authority_index():
        try:
            raw = _git_output(['git', 'ls-files', '-z', '--', '*.md'])
        except subprocess.CalledProcessError:
            return build_full_index(BASE)

        markdown_texts = {}
        errors = []
        for rel in [p for p in raw.split('\0') if p]:
            text = index_text(rel)
            if text is None:
                errors.append((rel, 'cannot read staged blob'))
            else:
                markdown_texts[rel] = text
        try:
            index, parse_errors = build_index_from_markdown_texts(markdown_texts)
        except AuthorityError:
            raise
        return index, errors + parse_errors

    def _load_staged_active_keys(rel_path):
        text = index_text(rel_path)
        if text is None:
            return load_active_keys(os.path.join(BASE, rel_path))
        return parse_active_keys(text)

    def _load_staged_index(rel_path):
        text = index_text(rel_path)
        if text is None:
            return None
        if not text.strip():
            return CanonicalIndex()
        entries = json.loads(text)
        if not isinstance(entries, dict):
            print(f"PKB validate: staged {rel_path} is not a JSON object")
            sys.exit(1)
        return CanonicalIndex(entries=entries)

    def _print_diff(label_a, entries_a, label_b, entries_b):
        keys_a = set(entries_a)
        keys_b = set(entries_b)
        for key in sorted(keys_a - keys_b):
            print(f"  in {label_a} but not {label_b}: {key} -> {entries_a[key]}")
        for key in sorted(keys_b - keys_a):
            print(f"  in {label_b} but not {label_a}: {key} -> {entries_b[key]}")
        for key in sorted(keys_a & keys_b):
            if entries_a[key] != entries_b[key]:
                print(f"  {key}: {label_a}={entries_a[key]} {label_b}={entries_b[key]}")

    md_changed = [f for f in files if f.endswith('.md')]
    rel_index = os.path.relpath(CANONICAL_INDEX_PATH, BASE)
    index_staged = rel_index in files

    if md_changed or index_staged:
        try:
            rebuilt, fm_errors = _build_staged_authority_index()
        except AuthorityError as exc:
            print(f"PKB validate: authority error during staged rebuild: {exc}")
            sys.exit(1)
        if fm_errors:
            print('PKB validate: authority frontmatter errors block index update:')
            for rel, msg in fm_errors:
                print(f"  {rel}: {msg}")
            sys.exit(1)

        active_keys = _load_staged_active_keys(os.path.relpath(CANONICAL_VOCAB_PATH, BASE))
        if active_keys is not None:
            try:
                validate_against_vocabulary(rebuilt.records.values(), active_keys)
            except AuthorityError as exc:
                print(f"PKB validate: {exc}")
                sys.exit(1)

        if index_staged:
            staged_index = _load_staged_index(rel_index)
            if staged_index is None:
                print(f"PKB validate: cannot read staged blob for {rel_index}")
                sys.exit(1)
            if staged_index.entries != rebuilt.entries:
                print('PKB validate: staged canonical.json does not match a '
                      'staged-frontmatter rebuild (do not hand-edit; run '
                      '`python3 scripts/pkb_authority.py audit` to regenerate):')
                _print_diff('staged', staged_index.entries, 'staged rebuild', rebuilt.entries)
                sys.exit(1)
        else:
            on_disk = load_index(CANONICAL_INDEX_PATH)
            if on_disk.entries != rebuilt.entries:
                write_index(rebuilt, CANONICAL_INDEX_PATH)
                try:
                    subprocess.check_call(['git', 'add', rel_index], cwd=BASE)
                except subprocess.CalledProcessError as exc:
                    print(f"PKB validate: failed to stage updated {rel_index}: {exc}")
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
