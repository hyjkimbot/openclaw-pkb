"""Unit tests for scripts/pkb_authority.py."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import pkb_authority as auth  # noqa: E402


def _doc(frontmatter: str, body: str = "body\n") -> str:
    return f"---\n{frontmatter}\n---\n{body}"


class ParseFrontmatterTests(unittest.TestCase):
    def test_returns_none_when_no_frontmatter(self):
        self.assertIsNone(auth.parse_frontmatter("just a body, no frontmatter\n"))

    def test_returns_empty_dict_when_frontmatter_empty(self):
        self.assertEqual(auth.parse_frontmatter("---\n\n---\nbody\n"), {})

    def test_parses_yaml_lists(self):
        fm = auth.parse_frontmatter(
            _doc("canonical_for:\n  - a\n  - b\nstatus: current")
        )
        self.assertEqual(fm["canonical_for"], ["a", "b"])
        self.assertEqual(fm["status"], "current")

    def test_rejects_non_mapping_frontmatter(self):
        with self.assertRaises(auth.AuthorityError):
            auth.parse_frontmatter("---\n- just a list\n---\nbody\n")


class ExtractAuthorityTests(unittest.TestCase):
    def test_returns_none_when_no_authority_fields(self):
        text = _doc("title: Random note\ntags: [type/note]")
        self.assertIsNone(auth.extract_authority("docs/x.md", text))

    def test_extracts_canonical_for_and_status(self):
        text = _doc("canonical_for:\n  - nutrition-targets\nstatus: current")
        rec = auth.extract_authority("docs/health/current-targets.md", text)
        self.assertIsNotNone(rec)
        self.assertEqual(rec.canonical_for, ["nutrition-targets"])
        self.assertEqual(rec.status, "current")

    def test_accepts_string_for_canonical_for(self):
        text = _doc("canonical_for: nutrition-targets")
        rec = auth.extract_authority("a.md", text)
        self.assertEqual(rec.canonical_for, ["nutrition-targets"])

    def test_unknown_status_tolerated_at_extract_time(self):
        # Unknown status is captured but doesn't block extraction. Audit
        # surfaces it separately as a warning.
        text = _doc("status: yolo")
        rec = auth.extract_authority("a.md", text)
        self.assertIsNotNone(rec)
        self.assertEqual(rec.status, "yolo")

    def test_status_must_be_string(self):
        text = _doc("status:\n  - nope")
        with self.assertRaises(auth.AuthorityError):
            auth.extract_authority("a.md", text)

    def test_rejects_canonical_key_with_spaces(self):
        text = _doc("canonical_for:\n  - nutrition targets")
        with self.assertRaises(auth.AuthorityError):
            auth.extract_authority("a.md", text)

    def test_rejects_canonical_key_starting_with_digit(self):
        text = _doc("canonical_for:\n  - 1nutrition")
        with self.assertRaises(auth.AuthorityError):
            auth.extract_authority("a.md", text)

    def test_supersedes_and_superseded_by(self):
        text = _doc(
            "status: current\n"
            "supersedes:\n  - docs/health/old.md\n"
            "superseded_by:\n  - docs/health/newer.md"
        )
        rec = auth.extract_authority("a.md", text)
        self.assertEqual(rec.supersedes, ["docs/health/old.md"])
        self.assertEqual(rec.superseded_by, ["docs/health/newer.md"])

    def test_authority_scope_optional(self):
        text = _doc("status: current\nauthority_scope: health/nutrition")
        rec = auth.extract_authority("a.md", text)
        self.assertEqual(rec.authority_scope, "health/nutrition")

    def test_authority_scope_must_be_string(self):
        text = _doc("status: current\nauthority_scope:\n  - nope")
        with self.assertRaises(auth.AuthorityError):
            auth.extract_authority("a.md", text)


class BuildIndexTests(unittest.TestCase):
    def _record(self, path: str, canonical: list[str]) -> auth.AuthorityRecord:
        return auth.AuthorityRecord(path=path, canonical_for=canonical)

    def test_builds_entries_from_records(self):
        idx = auth.build_index_from_records(
            [
                self._record("a.md", ["alpha"]),
                self._record("b.md", ["beta"]),
                self._record("c.md", []),
            ]
        )
        self.assertEqual(idx.entries, {"alpha": "a.md", "beta": "b.md"})
        self.assertIn("c.md", idx.records)

    def test_collision_raises(self):
        with self.assertRaises(auth.AuthorityError) as cm:
            auth.build_index_from_records(
                [
                    self._record("a.md", ["alpha"]),
                    self._record("b.md", ["alpha"]),
                ]
            )
        self.assertIn("collision", str(cm.exception))
        self.assertIn("a.md", str(cm.exception))
        self.assertIn("b.md", str(cm.exception))


class FullScanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp)

    def _write(self, rel: str, text: str) -> None:
        full = os.path.join(self.tmp, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(text)

    def test_full_scan_finds_only_authority_bearing_files(self):
        self._write(
            "docs/health/current.md",
            _doc("canonical_for:\n  - nutrition-targets\nstatus: current"),
        )
        self._write("docs/health/old.md", _doc("status: historical"))
        self._write("docs/health/random.md", _doc("title: just notes\ntags: [a]"))

        idx, errors = auth.build_full_index(self.tmp)
        self.assertEqual(errors, [])
        self.assertEqual(idx.entries, {"nutrition-targets": "docs/health/current.md"})
        # old.md has authority status but no canonical_for, still kept as a record
        self.assertIn("docs/health/old.md", idx.records)
        # random.md has no authority fields, not tracked
        self.assertNotIn("docs/health/random.md", idx.records)

    def test_full_scan_skips_dot_dirs(self):
        self._write(
            ".git/hooks/x.md",
            _doc("canonical_for:\n  - should-not-appear"),
        )
        self._write(
            "docs/x.md",
            _doc("canonical_for:\n  - real-key"),
        )
        idx, errors = auth.build_full_index(self.tmp)
        self.assertEqual(errors, [])
        self.assertEqual(idx.entries, {"real-key": "docs/x.md"})

    def test_full_scan_collects_errors_without_aborting(self):
        # File with a valid canonical claim
        self._write(
            "docs/good.md",
            _doc("canonical_for:\n  - good-key\nstatus: current"),
        )
        # File with malformed YAML in frontmatter (unquoted colon in title)
        # AND no authority intent — should be skipped silently
        self._write(
            "docs/bad-yaml-no-authority.md",
            "---\ntitle: A title: with bad colon\n---\nbody\n",
        )
        # File with malformed YAML AND authority intent — must surface
        self._write(
            "docs/bad-yaml-with-authority.md",
            "---\ntitle: A title: with bad colon\n"
            "canonical_for:\n  - intended-key\n---\nbody\n",
        )

        idx, errors = auth.build_full_index(self.tmp)
        # Good record still indexed
        self.assertEqual(idx.entries, {"good-key": "docs/good.md"})
        # Authority-intent bad files surface; non-authority YAML noise does not
        bad_paths = {rel for rel, _ in errors}
        self.assertIn("docs/bad-yaml-with-authority.md", bad_paths)
        self.assertNotIn("docs/bad-yaml-no-authority.md", bad_paths)

    def test_unknown_status_surfaces_as_warning_not_error(self):
        self._write(
            "docs/legacy.md",
            _doc("status: status/stable"),
        )
        idx, errors = auth.build_full_index(self.tmp)
        # Not an error
        self.assertEqual(errors, [])
        # But surfaced via collect_status_warnings
        warnings = auth.collect_status_warnings(idx.records.values())
        warned_paths = {rel for rel, _ in warnings}
        self.assertIn("docs/legacy.md", warned_paths)


class VocabularyTests(unittest.TestCase):
    def test_parse_active_keys_extracts_backticked_keys(self):
        text = (
            "# Canonical Key Vocabulary\n\n"
            "Some preamble.\n\n"
            "## Active keys\n\n"
            "- `nutrition-targets` — current diet target\n"
            "- `supplement-stack` — supplement protocol\n"
            "\n"
            "## Reserved\n\n"
            "- `workout-program` — not yet active\n"
        )
        self.assertEqual(
            auth.parse_active_keys(text),
            {"nutrition-targets", "supplement-stack"},
        )

    def test_parse_active_keys_no_active_section_returns_empty(self):
        text = "# Canonical Key Vocabulary\n\nNo active section here.\n"
        self.assertEqual(auth.parse_active_keys(text), set())

    def test_validate_against_vocabulary_passes_when_all_keys_active(self):
        rec = auth.AuthorityRecord(path="a.md", canonical_for=["foo"])
        # Should not raise
        auth.validate_against_vocabulary([rec], {"foo", "bar"})

    def test_validate_against_vocabulary_fails_on_unknown_key(self):
        rec1 = auth.AuthorityRecord(path="a.md", canonical_for=["foo"])
        rec2 = auth.AuthorityRecord(path="b.md", canonical_for=["unknown"])
        with self.assertRaises(auth.AuthorityError) as cm:
            auth.validate_against_vocabulary([rec1, rec2], {"foo"})
        self.assertIn("unknown", str(cm.exception))
        self.assertIn("b.md", str(cm.exception))


class DriftDetectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp)

    def _write(self, rel: str, text: str) -> None:
        full = os.path.join(self.tmp, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(text)

    def test_no_drift_when_index_matches_frontmatter(self):
        self._write(
            "docs/x.md",
            _doc("canonical_for:\n  - good\nstatus: current"),
        )
        existing = auth.CanonicalIndex(entries={"good": "docs/x.md"})
        self.assertEqual(auth.detect_index_drift(existing, self.tmp), [])

    def test_drift_when_index_points_to_missing_file(self):
        existing = auth.CanonicalIndex(entries={"orphan": "docs/gone.md"})
        drift = auth.detect_index_drift(existing, self.tmp)
        self.assertEqual(len(drift), 1)
        key, msg = drift[0]
        self.assertEqual(key, "orphan")
        self.assertIn("does not exist", msg)

    def test_drift_when_file_no_longer_claims_key(self):
        # File exists but its canonical_for is different from what the index says
        self._write(
            "docs/x.md",
            _doc("canonical_for:\n  - new-key\nstatus: current"),
        )
        existing = auth.CanonicalIndex(entries={"old-key": "docs/x.md"})
        drift = auth.detect_index_drift(existing, self.tmp)
        self.assertEqual(len(drift), 1)
        key, msg = drift[0]
        self.assertEqual(key, "old-key")
        self.assertIn("does not claim", msg)

    def test_drift_when_file_has_unparseable_frontmatter_with_authority(self):
        # File has authority intent but malformed YAML
        self._write(
            "docs/x.md",
            "---\ntitle: bad: colon\ncanonical_for:\n  - the-key\n---\nbody\n",
        )
        existing = auth.CanonicalIndex(entries={"the-key": "docs/x.md"})
        drift = auth.detect_index_drift(existing, self.tmp)
        self.assertEqual(len(drift), 1)


class FullRebuildVsStagedIndexTests(unittest.TestCase):
    """Tests for the property the hand-edit detection path relies on:
    a fresh build_full_index of the on-disk frontmatter must equal whatever
    the legitimate canonical.json should contain. The validator uses this
    equality check to detect injected, deleted, or modified entries.
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp)

    def _write(self, rel: str, text: str) -> None:
        full = os.path.join(self.tmp, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(text)

    def test_rebuild_matches_legitimate_index(self):
        self._write(
            "docs/a.md",
            _doc("canonical_for:\n  - alpha\nstatus: current"),
        )
        self._write(
            "docs/b.md",
            _doc("canonical_for:\n  - beta\nstatus: current"),
        )
        rebuilt, errors = auth.build_full_index(self.tmp)
        self.assertEqual(errors, [])
        self.assertEqual(rebuilt.entries, {"alpha": "docs/a.md", "beta": "docs/b.md"})

    def test_rebuild_omits_injected_key(self):
        # Only one canonical claim on disk
        self._write(
            "docs/a.md",
            _doc("canonical_for:\n  - alpha\nstatus: current"),
        )
        rebuilt, _ = auth.build_full_index(self.tmp)
        # A staged index that contains an injected key should NOT match rebuild
        injected = auth.CanonicalIndex(
            entries={"alpha": "docs/a.md", "fake": "docs/a.md"}
        )
        self.assertNotEqual(rebuilt.entries, injected.entries)

    def test_rebuild_includes_key_missing_from_staged(self):
        # On-disk frontmatter claims two keys
        self._write(
            "docs/a.md",
            _doc("canonical_for:\n  - alpha\nstatus: current"),
        )
        self._write(
            "docs/b.md",
            _doc("canonical_for:\n  - beta\nstatus: current"),
        )
        rebuilt, _ = auth.build_full_index(self.tmp)
        # A staged index missing one key must not match rebuild
        partial = auth.CanonicalIndex(entries={"alpha": "docs/a.md"})
        self.assertNotEqual(rebuilt.entries, partial.entries)


class HasAuthorityIntentTests(unittest.TestCase):
    def test_no_frontmatter(self):
        self.assertFalse(auth.has_authority_intent("just body"))

    def test_frontmatter_without_authority_fields(self):
        self.assertFalse(auth.has_authority_intent(_doc("title: x\ntags: [a]")))

    def test_frontmatter_with_canonical_for(self):
        self.assertTrue(auth.has_authority_intent(_doc("canonical_for:\n  - k")))

    def test_frontmatter_with_supersedes(self):
        self.assertTrue(
            auth.has_authority_intent(_doc("supersedes:\n  - docs/x.md"))
        )

    def test_frontmatter_with_authority_scope(self):
        self.assertTrue(auth.has_authority_intent(_doc("authority_scope: x")))


class IncrementalUpdateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp)

    def _write(self, rel: str, text: str) -> None:
        full = os.path.join(self.tmp, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(text)

    def test_adds_new_canonical_claim(self):
        existing = auth.CanonicalIndex()
        self._write(
            "docs/a.md",
            _doc("canonical_for:\n  - new-key\nstatus: current"),
        )
        new = auth.update_index_incrementally(existing, self.tmp, ["docs/a.md"])
        self.assertEqual(new.entries, {"new-key": "docs/a.md"})

    def test_removes_claim_when_canonical_for_dropped(self):
        rec = auth.AuthorityRecord(path="docs/a.md", canonical_for=["k"])
        existing = auth.build_index_from_records([rec])
        # File now has frontmatter but no canonical_for
        self._write("docs/a.md", _doc("status: draft"))
        new = auth.update_index_incrementally(existing, self.tmp, ["docs/a.md"])
        self.assertEqual(new.entries, {})

    def test_removes_claim_when_file_deleted(self):
        rec = auth.AuthorityRecord(path="docs/a.md", canonical_for=["k"])
        existing = auth.build_index_from_records([rec])
        # File does not exist on disk -> treated as deleted
        new = auth.update_index_incrementally(existing, self.tmp, ["docs/a.md"])
        self.assertEqual(new.entries, {})

    def test_collision_on_incremental_add(self):
        rec = auth.AuthorityRecord(path="docs/a.md", canonical_for=["shared-key"])
        existing = auth.build_index_from_records([rec])
        self._write(
            "docs/b.md",
            _doc("canonical_for:\n  - shared-key\nstatus: current"),
        )
        with self.assertRaises(auth.AuthorityError) as cm:
            auth.update_index_incrementally(existing, self.tmp, ["docs/b.md"])
        self.assertIn("shared-key", str(cm.exception))

    def test_collision_detected_against_disk_loaded_index(self):
        # Simulate the pre-commit case: index loaded from disk has entries
        # but no records; an incumbent canonical file already exists on disk.
        self._write(
            "docs/incumbent.md",
            _doc("canonical_for:\n  - shared-key\nstatus: current"),
        )
        # Existing index loaded from disk: entries populated, records empty
        existing = auth.CanonicalIndex(
            entries={"shared-key": "docs/incumbent.md"},
        )
        # Now a new file tries to claim the same key
        self._write(
            "docs/new-claimant.md",
            _doc("canonical_for:\n  - shared-key\nstatus: draft"),
        )
        with self.assertRaises(auth.AuthorityError) as cm:
            auth.update_index_incrementally(
                existing, self.tmp, ["docs/new-claimant.md"]
            )
        self.assertIn("shared-key", str(cm.exception))
        self.assertIn("docs/incumbent.md", str(cm.exception))
        self.assertIn("docs/new-claimant.md", str(cm.exception))

    def test_unrelated_changed_file_does_not_affect_index(self):
        rec = auth.AuthorityRecord(path="docs/a.md", canonical_for=["alpha"])
        existing = auth.build_index_from_records([rec])
        # The actual on-disk file for the existing record
        self._write(
            "docs/a.md",
            _doc("canonical_for:\n  - alpha\nstatus: current"),
        )
        # Now stage an unrelated non-authority file
        self._write("docs/notes.md", _doc("title: random\ntags: [type/note]"))
        new = auth.update_index_incrementally(existing, self.tmp, ["docs/notes.md"])
        self.assertEqual(new.entries, {"alpha": "docs/a.md"})


class SerializationTests(unittest.TestCase):
    def test_serialize_is_sorted_and_stable(self):
        idx = auth.CanonicalIndex(
            entries={"beta": "b.md", "alpha": "a.md"},
        )
        text = auth.serialize_index(idx)
        # Keys must be sorted for stable diffs
        self.assertEqual(
            json.loads(text),
            {"alpha": "a.md", "beta": "b.md"},
        )
        self.assertTrue(text.endswith("\n"))
        # alpha must come before beta in the raw text
        self.assertLess(text.index('"alpha"'), text.index('"beta"'))

    def test_load_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "index", "canonical.json")
            idx = auth.CanonicalIndex(entries={"k": "docs/x.md"})
            auth.write_index(idx, path)
            loaded = auth.load_index(path)
            self.assertEqual(loaded.entries, idx.entries)

    def test_load_missing_returns_empty(self):
        loaded = auth.load_index("/nonexistent/path/canonical.json")
        self.assertEqual(loaded.entries, {})


class LookupTests(unittest.TestCase):
    def test_lookup_hit(self):
        idx = auth.CanonicalIndex(entries={"k": "docs/x.md"})
        self.assertEqual(auth.lookup(idx, "k"), "docs/x.md")

    def test_lookup_miss(self):
        idx = auth.CanonicalIndex(entries={"k": "docs/x.md"})
        self.assertIsNone(auth.lookup(idx, "other"))


class CLITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # Set up a fake repo structure: scripts/ next to the tmp root, since
        # main() computes index_path relative to the script's own directory.
        # We patch via overriding HOME-style behavior: instead, we test the
        # functions main delegates to (already covered above) and just smoke
        # test argument parsing here.

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp)

    def test_main_no_args_usage(self):
        rc = auth.main(["pkb_authority.py"])
        self.assertEqual(rc, 2)

    def test_main_unknown_command(self):
        rc = auth.main(["pkb_authority.py", "bogus"])
        self.assertEqual(rc, 2)

    def test_main_lookup_requires_key(self):
        rc = auth.main(["pkb_authority.py", "lookup"])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
