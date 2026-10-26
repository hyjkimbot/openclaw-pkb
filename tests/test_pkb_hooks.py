"""Real Git hook installation and blocking behavior in isolated repositories."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class HookTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        self.env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        self.run_cmd("git", "init", "-q")
        self.run_cmd("git", "config", "user.name", "Test")
        self.run_cmd("git", "config", "user.email", "test@example.invalid")
        shutil.copytree(ROOT / "scripts", self.repo / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(ROOT / ".githooks", self.repo / ".githooks")

    def tearDown(self):
        self.tmp.cleanup()

    def run_cmd(self, *args):
        return subprocess.run(args, cwd=self.repo, env=self.env, text=True, capture_output=True)

    def install(self):
        return self.run_cmd(sys.executable, "scripts/install-hooks.py")

    def test_install_idempotent_and_hook_blocks_invalid_commit(self):
        for _ in range(2):
            result = self.install()
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        note = self.repo / "docs/sources/bad.md"
        note.parent.mkdir(parents=True)
        note.write_text("Missing frontmatter\n")
        self.run_cmd("git", "add", "docs/sources/bad.md")
        result = self.run_cmd("git", "commit", "-m", "must fail")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing frontmatter", result.stdout + result.stderr)
        note.write_text("---\nid: example\ncreated: 2026-01-01\ntags: [type/source]\n---\nValid\n")
        self.run_cmd("git", "add", "docs/sources/bad.md")
        result = self.run_cmd("git", "commit", "-m", "valid")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_existing_hooks_path_is_not_overwritten(self):
        self.run_cmd("git", "config", "core.hooksPath", "custom-hooks")
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.run_cmd("git", "config", "--get", "core.hooksPath").stdout.strip(), "custom-hooks")

    def test_existing_default_hook_is_not_overwritten_or_bypassed(self):
        hook = self.repo / ".git/hooks/pre-commit"
        hook.write_text("#!/bin/sh\nexit 0\n")
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(hook.read_text(), "#!/bin/sh\nexit 0\n")
        self.assertEqual(self.run_cmd("git", "config", "--get", "core.hooksPath").returncode, 1)

    def test_inherited_hooks_path_is_not_shadowed(self):
        config = self.repo / "global-test-config"
        config.write_text("[core]\n\thooksPath = inherited-hooks\n")
        self.env["GIT_CONFIG_GLOBAL"] = str(config)
        self.assertNotEqual(self.install().returncode, 0)
        self.assertEqual(self.run_cmd("git", "config", "--local", "--get", "core.hooksPath").returncode, 1)

    def test_existing_nonexecutable_pre_push_is_not_bypassed(self):
        hook = self.repo / ".git/hooks/pre-push"
        hook.write_text("#!/bin/sh\nexit 1\n")
        hook.chmod(0o644)
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("pre-push", result.stdout + result.stderr)
        self.assertEqual(hook.read_text(), "#!/bin/sh\nexit 1\n")
        self.assertEqual(hook.stat().st_mode & 0o777, 0o644)
        self.assertEqual(self.run_cmd("git", "config", "--local", "--get", "core.hooksPath").returncode, 1)

    def test_existing_dangling_hook_symlink_is_not_bypassed(self):
        hook = self.repo / ".git/hooks/commit-msg"
        hook.symlink_to("not-yet-installed-hook")
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("commit-msg", result.stdout + result.stderr)
        self.assertTrue(hook.is_symlink())
        self.assertEqual(os.readlink(hook), "not-yet-installed-hook")
        self.assertEqual(self.run_cmd("git", "config", "--local", "--get", "core.hooksPath").returncode, 1)

    def test_sample_hooks_do_not_prevent_installation(self):
        sample = self.repo / ".git/hooks/pre-push.sample"
        sample.write_text("#!/bin/sh\nexit 1\n")
        sample.chmod(0o755)
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(sample.read_text(), "#!/bin/sh\nexit 1\n")

    def test_linked_worktree_preserves_shared_default_hooks(self):
        self.run_cmd("git", "add", "scripts", ".githooks")
        result = self.run_cmd("git", "commit", "-q", "-m", "hook fixture")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        worktree = self.repo / "linked worktree"
        result = self.run_cmd("git", "worktree", "add", "-q", "-b", "linked", str(worktree))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        hook = self.repo / ".git/hooks/pre-push"
        hook.write_text("#!/bin/sh\nexit 1\n")
        result = subprocess.run(
            [sys.executable, "scripts/install-hooks.py"], cwd=worktree,
            env=self.env, text=True, capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("pre-push", result.stdout + result.stderr)
        self.assertEqual(hook.read_text(), "#!/bin/sh\nexit 1\n")
        self.assertEqual(self.run_cmd("git", "config", "--local", "--get", "core.hooksPath").returncode, 1)
