"""Smoke tests for the documented validator workflow.

Runs scripts/pkb-validate.py against staged file scenarios in a
temporary git repo. These guard the SKILL.md "add a canonical key"
workflow and ensure control-plane / meta files don't trip the
frontmatter check.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VALIDATOR = os.path.join(REPO_ROOT, "scripts", "pkb-validate.py")


class ValidatorWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # Initialize a real git repo and copy the validator + module in
        subprocess.check_call(["git", "init", "-q", self.tmp])
        subprocess.check_call(
            ["git", "-C", self.tmp, "config", "user.email", "test@example.com"]
        )
        subprocess.check_call(
            ["git", "-C", self.tmp, "config", "user.name", "Test"]
        )
        scripts_dir = os.path.join(self.tmp, "scripts")
        os.makedirs(scripts_dir)
        shutil.copy(VALIDATOR, os.path.join(scripts_dir, "pkb-validate.py"))
        # Copy any helper modules the validator imports so optional
        # features (authority, provenance, shared frontmatter parsing)
        # can run inside the temp repo.
        for name in ("pkb_frontmatter.py", "pkb_authority.py", "pkb_provenance.py"):
            src = os.path.join(REPO_ROOT, "scripts", name)
            if os.path.exists(src):
                shutil.copy(src, os.path.join(scripts_dir, name))

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _write(self, rel: str, text: str) -> None:
        full = os.path.join(self.tmp, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(text)

    def _stage(self, *rels: str) -> None:
        subprocess.check_call(["git", "-C", self.tmp, "add", *rels])

    def _run_validator(self) -> tuple[int, str]:
        result = subprocess.run(
            [sys.executable, "scripts/pkb-validate.py"],
            cwd=self.tmp,
            capture_output=True,
            text=True,
        )
        return result.returncode, result.stdout + result.stderr

    def test_canonical_keys_md_does_not_require_frontmatter(self):
        self._write(
            ".agent/index/canonical-keys.md",
            "# Canonical Key Vocabulary\n\n## Active keys\n\n- `example` — placeholder\n",
        )
        self._stage(".agent/index/canonical-keys.md")
        rc, out = self._run_validator()
        self.assertEqual(rc, 0, f"expected pass, got rc={rc}, output={out}")

    def test_top_level_meta_files_do_not_require_frontmatter(self):
        # A simulated SKILL.md update (real repos have non-vault frontmatter)
        self._write(
            "SKILL.md",
            "---\nname: pkb\nversion: 0.4.0\ndescription: x\n---\n\n# PKB\n",
        )
        self._stage("SKILL.md")
        rc, out = self._run_validator()
        self.assertEqual(rc, 0, f"expected pass, got rc={rc}, output={out}")

    def test_top_level_design_doc_does_not_require_frontmatter(self):
        self._write("docs/canonical-authority-indexing.md", "# Design\n\nbody\n")
        self._stage("docs/canonical-authority-indexing.md")
        rc, out = self._run_validator()
        self.assertEqual(rc, 0, f"expected pass, got rc={rc}, output={out}")

    def test_journal_entry_does_not_require_frontmatter(self):
        self._write("journal/2026-05-09.md", "\n- [09:00] foo (no frontmatter)\n")
        self._stage("journal/2026-05-09.md")
        rc, out = self._run_validator()
        self.assertEqual(rc, 0, f"expected pass, got rc={rc}, output={out}")

    def test_subdir_doc_still_requires_frontmatter(self):
        # Vault note files (under docs/<subdir>/) MUST still have frontmatter
        self._write("docs/sources/no-frontmatter.md", "# Note without frontmatter\n")
        self._stage("docs/sources/no-frontmatter.md")
        rc, out = self._run_validator()
        self.assertNotEqual(
            rc, 0, "expected failure for vault note without frontmatter"
        )
        self.assertIn("missing frontmatter", out)

    def test_provenance_dangling_target_warns_but_does_not_block(self):
        # A doc with provenance metadata pointing at a non-existent target
        # should produce a warning but not fail the commit.
        self._write(
            "docs/sources/has-bad-prov.md",
            "---\n"
            "id: has-bad-prov\n"
            "created: 2026-05-09\n"
            "tags: [type/source, status/draft]\n"
            "source_notes:\n"
            "  - docs/sources/does-not-exist.md\n"
            "citation_status: cited\n"
            "---\n"
            "body\n",
        )
        self._stage("docs/sources/has-bad-prov.md")
        rc, out = self._run_validator()
        self.assertEqual(rc, 0, f"provenance warnings should not block, got rc={rc}")
        self.assertIn("provenance warning", out)
        self.assertIn("does-not-exist.md", out)


if __name__ == "__main__":
    unittest.main()
