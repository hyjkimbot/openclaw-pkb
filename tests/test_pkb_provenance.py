"""Unit tests for scripts/pkb_provenance.py."""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import pkb_provenance as prov  # noqa: E402


def _doc(frontmatter: str, body: str = "body\n") -> str:
    return f"---\n{frontmatter}\n---\n{body}"


class ExtractProvenanceTests(unittest.TestCase):
    def test_returns_none_when_no_provenance_fields(self):
        text = _doc("title: random\ntags: [type/note]")
        self.assertIsNone(prov.extract_provenance("docs/x.md", text))

    def test_extracts_source_notes_list(self):
        text = _doc(
            "source_notes:\n"
            "  - docs/sources/a.md\n"
            "  - docs/sources/b.md\n"
            "citation_status: cited"
        )
        rec = prov.extract_provenance("docs/synthesis.md", text)
        self.assertIsNotNone(rec)
        self.assertEqual(
            rec.source_notes,
            ["docs/sources/a.md", "docs/sources/b.md"],
        )
        self.assertEqual(rec.citation_status, "cited")

    def test_accepts_string_for_source_notes(self):
        text = _doc("source_notes: docs/sources/a.md")
        rec = prov.extract_provenance("a.md", text)
        self.assertEqual(rec.source_notes, ["docs/sources/a.md"])

    def test_raw_sources_independent_of_source_notes(self):
        text = _doc(
            "raw_sources:\n  - docs/sources/raw/foo.txt\n"
            "citation_status: raw-only"
        )
        rec = prov.extract_provenance("a.md", text)
        self.assertEqual(rec.source_notes, [])
        self.assertEqual(rec.raw_sources, ["docs/sources/raw/foo.txt"])
        self.assertEqual(rec.citation_status, "raw-only")

    def test_unknown_citation_status_is_tolerated(self):
        # Unknown values are warnings, not errors (legacy compatibility)
        text = _doc("citation_status: bogus-value")
        rec = prov.extract_provenance("a.md", text)
        self.assertEqual(rec.citation_status, "bogus-value")

    def test_citation_status_must_be_string(self):
        text = _doc("citation_status:\n  - nope")
        with self.assertRaises(prov.ProvenanceError):
            prov.extract_provenance("a.md", text)

    def test_source_notes_items_must_be_strings(self):
        text = _doc("source_notes:\n  - 123")
        with self.assertRaises(prov.ProvenanceError):
            prov.extract_provenance("a.md", text)


class HasProvenanceIntentTests(unittest.TestCase):
    def test_no_frontmatter(self):
        self.assertFalse(prov.has_provenance_intent("just body"))

    def test_no_provenance_fields(self):
        self.assertFalse(
            prov.has_provenance_intent(_doc("title: x\ntags: [a]"))
        )

    def test_source_notes_field(self):
        self.assertTrue(
            prov.has_provenance_intent(_doc("source_notes:\n  - x.md"))
        )

    def test_citation_status_field(self):
        self.assertTrue(
            prov.has_provenance_intent(_doc("citation_status: cited"))
        )

    def test_raw_sources_field(self):
        self.assertTrue(
            prov.has_provenance_intent(_doc("raw_sources:\n  - x.txt"))
        )


class FullScanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _write(self, rel: str, text: str) -> None:
        full = os.path.join(self.tmp, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(text)

    def test_only_provenance_bearing_files_are_recorded(self):
        self._write(
            "docs/synthesis.md",
            _doc("source_notes:\n  - docs/sources/foo.md\ncitation_status: cited"),
        )
        self._write("docs/random.md", _doc("title: random\ntags: [a]"))
        index, errors = prov.build_full_index(self.tmp)
        self.assertEqual(errors, [])
        self.assertIn("docs/synthesis.md", index.records)
        self.assertNotIn("docs/random.md", index.records)

    def test_collects_errors_without_aborting(self):
        # Good record
        self._write(
            "docs/good.md",
            _doc("source_notes:\n  - docs/sources/foo.md"),
        )
        # Bad: citation_status as a list
        self._write(
            "docs/bad-status.md",
            _doc("citation_status:\n  - nope"),
        )
        index, errors = prov.build_full_index(self.tmp)
        # Good one indexed
        self.assertIn("docs/good.md", index.records)
        # Bad one in errors
        bad_paths = {rel for rel, _ in errors}
        self.assertIn("docs/bad-status.md", bad_paths)

    def test_yaml_error_without_provenance_intent_is_silent(self):
        self._write(
            "docs/bad-yaml-no-intent.md",
            "---\ntitle: bad: colon\n---\nbody\n",
        )
        index, errors = prov.build_full_index(self.tmp)
        self.assertEqual(errors, [])
        self.assertEqual(index.records, {})


class CitationStatusWarningsTests(unittest.TestCase):
    def test_known_statuses_produce_no_warnings(self):
        records = [
            prov.ProvenanceRecord(path="a.md", citation_status="cited"),
            prov.ProvenanceRecord(path="b.md", citation_status="raw-only"),
            prov.ProvenanceRecord(path="c.md", citation_status="needs-review"),
            prov.ProvenanceRecord(path="d.md", citation_status="self-authored"),
        ]
        self.assertEqual(prov.collect_unknown_status_warnings(records), [])

    def test_unknown_status_surfaces(self):
        records = [
            prov.ProvenanceRecord(path="a.md", citation_status="legacy-value"),
        ]
        warnings = prov.collect_unknown_status_warnings(records)
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0][0], "a.md")
        self.assertIn("legacy-value", warnings[0][1])

    def test_none_status_does_not_warn(self):
        records = [prov.ProvenanceRecord(path="a.md", citation_status=None)]
        self.assertEqual(prov.collect_unknown_status_warnings(records), [])


class DanglingTargetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _write(self, rel: str, text: str) -> None:
        full = os.path.join(self.tmp, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(text)

    def test_no_dangling_when_targets_exist(self):
        self._write("docs/sources/a.md", _doc("title: a"))
        index = prov.ProvenanceIndex()
        index.records["docs/syn.md"] = prov.ProvenanceRecord(
            path="docs/syn.md", source_notes=["docs/sources/a.md"]
        )
        self.assertEqual(prov.collect_dangling_targets(index, self.tmp), [])

    def test_missing_source_note_target_is_dangling(self):
        index = prov.ProvenanceIndex()
        index.records["docs/syn.md"] = prov.ProvenanceRecord(
            path="docs/syn.md", source_notes=["docs/sources/missing.md"]
        )
        issues = prov.collect_dangling_targets(index, self.tmp)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0][0], "docs/syn.md")
        self.assertIn("missing", issues[0][1])

    def test_missing_raw_source_target_is_dangling(self):
        index = prov.ProvenanceIndex()
        index.records["docs/syn.md"] = prov.ProvenanceRecord(
            path="docs/syn.md", raw_sources=["docs/sources/raw/missing.txt"]
        )
        issues = prov.collect_dangling_targets(index, self.tmp)
        self.assertEqual(len(issues), 1)


class UncitedSourcesTests(unittest.TestCase):
    def test_uncited_with_no_filter(self):
        index = prov.ProvenanceIndex()
        index.records["docs/syn.md"] = prov.ProvenanceRecord(
            path="docs/syn.md", source_notes=["docs/sources/a.md"]
        )
        all_sources = ["docs/sources/a.md", "docs/sources/b.md"]
        # b is never referenced
        self.assertEqual(
            prov.collect_uncited_sources(index, all_sources),
            ["docs/sources/b.md"],
        )

    def test_active_filter_excludes_archive(self):
        index = prov.ProvenanceIndex()
        # No records reference anything
        all_sources = [
            "docs/sources/active.md",
            "docs/sources/archived.md",
        ]
        # Only consider 'active' a candidate
        active = lambda p: "active" in p
        self.assertEqual(
            prov.collect_uncited_sources(index, all_sources, active_filter=active),
            ["docs/sources/active.md"],
        )


class RawOnlyTests(unittest.TestCase):
    def test_raw_only_records_listed(self):
        index = prov.ProvenanceIndex()
        index.records["docs/raw-only.md"] = prov.ProvenanceRecord(
            path="docs/raw-only.md",
            raw_sources=["docs/sources/raw/x.txt"],
        )
        index.records["docs/cited.md"] = prov.ProvenanceRecord(
            path="docs/cited.md",
            source_notes=["docs/sources/x.md"],
            raw_sources=["docs/sources/raw/x.txt"],
        )
        index.records["docs/source-only.md"] = prov.ProvenanceRecord(
            path="docs/source-only.md",
            source_notes=["docs/sources/y.md"],
        )
        self.assertEqual(prov.collect_raw_only(index), ["docs/raw-only.md"])


class CandidateDetectionTests(unittest.TestCase):
    def test_no_signals_when_provenance_already_present(self):
        text = _doc(
            "kind: synthesis\nsource_notes:\n  - docs/sources/foo.md"
        )
        self.assertEqual(prov.candidate_signals("docs/x.md", text), [])

    def test_kind_synthesis_signal(self):
        text = _doc("kind: synthesis\ntitle: x")
        signals = prov.candidate_signals("docs/x.md", text)
        self.assertTrue(any("synthesis" in s for s in signals))

    def test_kind_reference_signal(self):
        text = _doc("kind: reference\ntitle: x")
        signals = prov.candidate_signals("docs/x.md", text)
        self.assertTrue(any("reference" in s for s in signals))

    def test_path_prefix_signal_for_career(self):
        text = _doc("title: x")
        signals = prov.candidate_signals("docs/career/x.md", text)
        self.assertTrue(any("docs" in s and "career" in s for s in signals))

    def test_no_signal_for_random_doc_in_journal(self):
        text = _doc("title: x")
        self.assertEqual(prov.candidate_signals("journal/2026-05-09.md", text), [])


class SerializationTests(unittest.TestCase):
    def test_serialize_round_trip(self):
        import json

        index = prov.ProvenanceIndex()
        index.records["docs/syn.md"] = prov.ProvenanceRecord(
            path="docs/syn.md",
            source_notes=["docs/sources/b.md", "docs/sources/a.md"],
            raw_sources=[],
            citation_status="cited",
        )
        text = prov.serialize_index(index)
        loaded = json.loads(text)
        self.assertEqual(
            loaded["docs/syn.md"]["source_notes"],
            ["docs/sources/a.md", "docs/sources/b.md"],
        )
        self.assertEqual(loaded["docs/syn.md"]["citation_status"], "cited")
        self.assertTrue(text.endswith("\n"))


class CLITests(unittest.TestCase):
    def test_main_no_args(self):
        self.assertEqual(prov.main(["pkb_provenance.py"]), 2)

    def test_main_unknown_command(self):
        self.assertEqual(prov.main(["pkb_provenance.py", "bogus"]), 2)


if __name__ == "__main__":
    unittest.main()
