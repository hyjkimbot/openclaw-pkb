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
        for name in ("pkb_authority.py", "pkb_frontmatter.py", "pkb_provenance.py"):
            shutil.copy2(REPO_ROOT / "scripts" / name, scripts / name)

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

    def run_validator(self, *args: str) -> subprocess.CompletedProcess:
        return self._run(sys.executable, "scripts/pkb-validate.py", *args, check=False)

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

    def test_wikilinks_inside_code_spans_and_blocks_are_ignored(self) -> None:
        self._write(
            "docs/career/code-links.md",
            "---\n"
            "id: code-links\n"
            "created: 2026-05-09\n"
            "tags: [type/note]\n"
            "---\n"
            "# Code Links\n\n"
            "This script updates all `[[NotARealNote]]` references.\n\n"
            "```\n"
            "[[AnotherFakeTarget]]\n"
            "```\n",
        )
        self._run("git", "add", "docs/career/code-links.md")

        self.assertValidatorPasses()

    def test_unstaged_worktree_only_breakage_with_clean_index_passes(self) -> None:
        self._write(
            "docs/health/nutrition-log/2026-03.csv",
            "bad_date,meal,intake,cal_lo,cal_hi,pro_lo,pro_hi,status,notes\n"
            "2026-03-01,breakfast,eggs,100,200,10,20,confirmed,ok\n",
        )

        self.assertValidatorPasses()

    def _commit_broken_graph(self):
        # Legacy breakage can exist before the hook is installed.
        rel = "docs/sources/source.md"
        path = self.repo / rel
        path.write_text(path.read_text() + "\n[[missing-legacy-note]]\n")
        self._run("git", "add", rel)
        self._run("git", "commit", "-q", "-m", "legacy graph")

    def test_csv_only_skips_graph_but_full_finds_unchanged_broken_link(self):
        self._commit_broken_graph()
        rel = "docs/health/nutrition-log/2026-03.csv"
        path = self.repo / rel
        path.write_text(path.read_text() + "2026-03-02,lunch,soup,100,200,10,20,confirmed,ok\n")
        self._run("git", "add", rel)
        proc = self.run_validator()
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("graph validation skipped", proc.stdout)
        proc = self.run_validator("--full")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("missing-legacy-note", proc.stdout)

    def test_deleted_markdown_checks_unchanged_inbound_links(self):
        self._run("git", "rm", "docs/sources/source.md")
        self.assertValidatorFailsWith("README.md -> docs/sources/source.md")

    def test_rename_out_of_markdown_still_triggers_graph_scan(self):
        self._run("git", "mv", "docs/sources/source.md", "docs/sources/source.txt")
        self.assertValidatorFailsWith("README.md -> docs/sources/source.md")

    def test_control_markdown_does_not_trigger_graph_scan(self):
        self._commit_broken_graph()
        self._write(".agent/index/canonical-keys.md", "# Keys\n\n## Active keys\n")
        self._run("git", "add", ".agent/index/canonical-keys.md")
        self.assertValidatorPasses()

    def test_rules_use_staged_version_despite_unstaged_weakening(self):
        self._write(".agent/pkb-rules.json", "{}\n")
        rel = "docs/health/nutrition-log/2026-03.csv"
        self._write(rel, "wrong,header\n")
        self._run("git", "add", rel)
        self.assertValidatorFailsWith("header mismatch")

    def test_staged_rules_change_is_used_despite_old_worktree_rules(self):
        self._stage_then_restore_worktree(".agent/pkb-rules.json", "{}\n")
        rel = "docs/health/nutrition-log/2026-03.csv"
        self._write(rel, "unconfigured,header\n")
        self._run("git", "add", rel)
        self.assertValidatorPasses()

    def _stage_provenance(self, target):
        rel = "docs/sources/source.md"
        path = self.repo / rel
        original = path.read_text()
        path.write_text(original.replace("tags: [type/source]\n", f"tags: [type/source]\ncitation_status: cited\nsource_notes: [{target}]\n"))
        self._run("git", "add", rel)
        return path, original

    def test_provenance_reads_staged_metadata_and_ignores_worktree_only_target(self):
        target = "docs/sources/worktree-only.md"
        path, original = self._stage_provenance(target)
        path.write_text(original)  # An unstaged fix cannot hide the warning.
        self._write(target, "local only")
        proc = self.run_validator()
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn(f"missing target {target}", proc.stdout)

    def test_provenance_accepts_indexed_target_missing_from_worktree(self):
        self._stage_provenance("docs/career/thesis.md")
        (self.repo / "docs/career/thesis.md").unlink()
        proc = self.run_validator()
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertNotIn("provenance warning", proc.stdout)

    def test_authority_regeneration_preserves_unstaged_index_edits(self):
        rel = "docs/sources/source.md"
        path = self.repo / rel
        path.write_text(path.read_text().replace("tags: [type/source]\n", "tags: [type/source]\ncanonical_for: example\n"))
        self._write(".agent/index/canonical-keys.md", "## Active keys\n\n- `example`\n")
        self._run("git", "add", rel, ".agent/index/canonical-keys.md")
        index_path = self.repo / ".agent/index/canonical.json"
        working = '{"unrelated": "local-edit"}\n'
        index_path.write_text(working)
        self.assertValidatorFailsWith("preserve unstaged changes")
        self.assertEqual(index_path.read_text(), working)

    def test_unreadable_git_index_fails_closed(self):
        (self.repo / ".git/index").write_bytes(b"invalid index")
        self.assertValidatorFailsWith("git check failed")

    def test_missing_indexed_blob_fails_closed(self):
        oid = self._run("git", "rev-parse", ":README.md").stdout.strip()
        (self.repo / ".git/objects" / oid[:2] / oid[2:]).unlink()
        proc = self.run_validator("--full")
        self.assertNotEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("cannot read indexed blob README.md", proc.stdout)

    def test_authority_regeneration_preserves_unstaged_index_deletion(self):
        rel = "docs/sources/source.md"
        path = self.repo / rel
        path.write_text(path.read_text().replace("tags: [type/source]\n", "tags: [type/source]\ncanonical_for: example\n"))
        self._run("git", "add", rel)
        index_path = self.repo / ".agent/index/canonical.json"
        index_path.unlink()
        self.assertValidatorFailsWith("preserve unstaged changes")
        self.assertFalse(index_path.exists())

    def test_generated_authority_file_obeys_optional_path_policy(self):
        rel = "docs/sources/source.md"
        path = self.repo / rel
        path.write_text(path.read_text().replace("tags: [type/source]\n", "tags: [type/source]\ncanonical_for: example\n"))
        self._write(".agent/pkb-rules.json", json.dumps({"allowedWriteRoots": ["docs/", ".agent/pkb-rules.json"]}))
        self._run("git", "add", rel, ".agent/pkb-rules.json")
        self.assertValidatorFailsWith("generated file outside allowed roots")

    def test_optional_path_policy_reads_staged_rules(self):
        self._write(".agent/pkb-rules.json", json.dumps({"allowedWriteRoots": [".agent/"]}))
        self._write("outside.txt", "not allowed\n")
        self._run("git", "add", ".agent/pkb-rules.json", "outside.txt")
        self._write(".agent/pkb-rules.json", "{}\n")
        self.assertValidatorFailsWith("outside allowed roots: outside.txt")

    def test_configured_raw_journal_exemption_preserves_curated_gate(self):
        self._write(".agent/pkb-rules.json", json.dumps({"frontmatterExemptPrefixes": ["docs/life/raw/"]}))
        self._write("docs/life/raw/2026-01-01.md", "A plain journal entry.\n")
        self._run("git", "add", ".agent/pkb-rules.json", "docs/life/raw/2026-01-01.md")
        self.assertValidatorPasses()
        self._write("docs/life/curated.md", "A curated note needs frontmatter.\n")
        self._run("git", "add", "docs/life/curated.md")
        self.assertValidatorFailsWith("missing frontmatter")


if __name__ == "__main__":
    unittest.main()
