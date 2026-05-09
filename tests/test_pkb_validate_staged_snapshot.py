"""End-to-end regression tests for staged-snapshot PKB validation.

These tests build tiny git repos and run scripts/pkb-validate.py as a script.
They ensure validation checks the git index (what will be committed), not the
working tree.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class PkbValidateStagedSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_obj = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp_obj.name)
        self._make_repo()

    def tearDown(self) -> None:
        self.tmp_obj.cleanup()

    def _run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        proc = subprocess.run(
            args,
            cwd=self.repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if check and proc.returncode != 0:
            self.fail(f"command failed ({proc.returncode}): {' '.join(args)}\n{proc.stdout}")
        return proc

    def _write(self, rel: str, text: str) -> None:
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _make_repo(self) -> None:
        self._run("git", "init", "-q")
        self._run("git", "config", "user.email", "validator-test@example.local")
        self._run("git", "config", "user.name", "Validator Test")

        scripts = self.repo / "scripts"
        scripts.mkdir()
        shutil.copy2(REPO_ROOT / "scripts" / "pkb-validate.py", scripts / "pkb-validate.py")
        shutil.copy2(REPO_ROOT / "scripts" / "pkb_authority.py", scripts / "pkb_authority.py")

        self._write(
            ".agent/pkb-rules.json",
            json.dumps(
                {
                    "csvSchemas": {
                        "docs/health/nutrition-log/": {
                            "columns": [
                                "date",
                                "meal",
                                "intake",
                                "cal_lo",
                                "cal_hi",
                                "pro_lo",
                                "pro_hi",
                                "status",
                                "notes",
                            ],
                            "required": ["date", "meal", "intake"],
                            "integers": ["cal_lo", "cal_hi", "pro_lo", "pro_hi"],
                            "enums": {"status": ["confirmed", "tentative", "updated", ""]},
                        }
                    }
                }
            ),
        )
        self._write(".agent/index/canonical.json", "{}\n")

        self._write(
            "README.md",
            "# Tiny PKB fixture\n\n"
            "- [Source](docs/sources/source.md)\n"
            "- [MOC](mocs/root.md)\n"
            "- [Career](docs/career/thesis.md)\n",
        )
        self._write(
            "docs/sources/source.md",
            "---\n"
            "id: source\n"
            "created: 2026-05-09\n"
            "title: Source\n"
            "tags: [type/source]\n"
            "---\n"
            "[Home](../../README.md)\n",
        )
        self._write(
            "mocs/root.md",
            "---\n"
            "id: root-moc\n"
            "created: 2026-05-09\n"
            "title: Root MOC\n"
            "tags: [type/moc]\n"
            "---\n"
            "[Home](../README.md)\n",
        )
        self._write(
            "docs/career/thesis.md",
            "---\n"
            "id: thesis\n"
            "created: 2026-05-09\n"
            "tags: [type/note]\n"
            "---\n"
            "# Thesis\n\n[Home](../../README.md)\n",
        )
        self._write(
            "docs/health/nutrition-log/2026-03.csv",
            "date,meal,intake,cal_lo,cal_hi,pro_lo,pro_hi,status,notes\n"
            "2026-03-01,breakfast,eggs,100,200,10,20,confirmed,ok\n",
        )

        self._run("git", "add", ".")
        self._run("git", "commit", "-q", "-m", "fixture")
        self.assertValidatorPasses()

    def _stage_then_restore_worktree(self, rel: str, new_text: str) -> None:
        (self.repo / rel).write_text(new_text, encoding="utf-8")
        self._run("git", "add", rel)
        self._run("git", "restore", "--source=HEAD", "--worktree", "--", rel)

    def run_validator(self) -> subprocess.CompletedProcess:
        return self._run(sys.executable, "scripts/pkb-validate.py", check=False)

    def assertValidatorPasses(self) -> None:
        proc = self.run_validator()
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("PKB validate: OK", proc.stdout)

    def assertValidatorFailsWith(self, expected: str) -> None:
        proc = self.run_validator()
        self.assertNotEqual(proc.returncode, 0, proc.stdout)
        self.assertIn(expected, proc.stdout)

    def test_invalid_moc_ontology_tags_staged_while_worktree_fixed_fails(self) -> None:
        self._stage_then_restore_worktree(
            "mocs/root.md",
            "---\n"
            "id: root-moc\n"
            "created: 2026-05-09\n"
            "title: Root MOC\n"
            "tags: [topic/repro]\n"
            "---\n"
            "[Home](../README.md)\n",
        )

        self.assertValidatorFailsWith("should include an ontology prefix")

    def test_invalid_csv_header_staged_while_worktree_fixed_fails(self) -> None:
        self._stage_then_restore_worktree(
            "docs/health/nutrition-log/2026-03.csv",
            "bad_date,meal,intake,cal_lo,cal_hi,pro_lo,pro_hi,status,notes\n"
            "2026-03-01,breakfast,eggs,100,200,10,20,confirmed,ok\n",
        )

        self.assertValidatorFailsWith("header mismatch")

    def test_unresolved_markdown_link_staged_while_worktree_fixed_fails(self) -> None:
        self._stage_then_restore_worktree(
            "docs/career/thesis.md",
            "---\n"
            "id: thesis\n"
            "created: 2026-05-09\n"
            "tags: [type/note]\n"
            "---\n"
            "# Thesis\n\n[Home](../../README.md)\n[[missing-repro-target]]\n",
        )

        self.assertValidatorFailsWith("unresolved internal links found")

    def test_unstaged_worktree_only_breakage_with_clean_index_passes(self) -> None:
        self._write(
            "docs/health/nutrition-log/2026-03.csv",
            "bad_date,meal,intake,cal_lo,cal_hi,pro_lo,pro_hi,status,notes\n"
            "2026-03-01,breakfast,eggs,100,200,10,20,confirmed,ok\n",
        )

        self.assertValidatorPasses()


if __name__ == "__main__":
    unittest.main()
