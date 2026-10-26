#!/usr/bin/env python3
"""Opt in to the bundled hook without replacing an existing hook setup."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, text=True, capture_output=True)


def main():
    if not (ROOT / '.git').exists():
        sys.exit('Hook installation requires the PKB repository root.')
    result = git('config', '--get', 'core.hooksPath')
    if result.returncode not in (0, 1):
        sys.exit(result.stderr or 'Cannot read Git hook configuration.')
    configured = result.stdout.strip() if result.returncode == 0 else None
    if configured is not None and configured != '.githooks':
        sys.exit('Existing core.hooksPath preserved. Add the validator to your existing hook manually; see docs/validation.md.')
    if configured is None:
        result = git('rev-parse', '--git-path', 'hooks')
        if result.returncode:
            sys.exit(result.stderr or 'Cannot locate Git hooks.')
        existing = Path(result.stdout.strip())
        if not existing.is_absolute():
            existing = ROOT / existing
        if existing.exists():
            for entry in sorted(existing.iterdir()):
                if not entry.name.endswith('.sample') and (entry.is_file() or entry.is_symlink()):
                    sys.exit(f'Existing default hook {entry.name} preserved. Integrate manually; see docs/validation.md.')
    hook = ROOT / '.githooks' / 'pre-commit'
    hook.chmod(hook.stat().st_mode | 0o111)
    result = git('config', '--local', 'core.hooksPath', '.githooks')
    if result.returncode:
        sys.exit(result.stderr or 'Cannot configure hooks.')
    print('Installed PKB pre-commit hook (core.hooksPath=.githooks).')


if __name__ == '__main__':
    main()
