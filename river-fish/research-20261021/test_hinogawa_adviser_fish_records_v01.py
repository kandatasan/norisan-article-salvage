from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import audit_hinogawa_live_atlas_v01 as atlas_audit
import build_hinogawa_adviser_fish_records_v01 as builder
import search_hinogawa_records_v01 as searcher


class HinoRiverTableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_rows = builder.read_transcription()
        cls.records = builder.expand_records(cls.source_rows)

    def test_expansion_keeps_only_positive_public_table_cells(self):
        self.assertEqual(len(self.records), 57)
        self.assertEqual(len({r["record_id"] for r in self.records}), 57)
        self.assertEqual({r["river_as_published"] for r in self.records}, {"日野川", "法勝寺川"})
        self.assertEqual({r["fish_name_as_published"] for r in self.records}, builder.ALLOWED_FISH)
        self.assertEqual({int(r["survey_year"]) for r in self.records}, set(builder.YEAR_LABELS.values()))
        self.assertTrue(all(int(r["reported_individual_count"]) > 0 for r in self.records))

    def test_published_year_and_count_transcription_examples(self):
        indexed = {(r["river_as_published"], int(r["survey_year"]), r["fish_name_as_published"]):
                   int(r["reported_individual_count"]) for r in self.records}
        self.assertEqual(indexed[("日野川", 1994, "アユ")], 501)
        self.assertEqual(indexed[("日野川", 2009, "チチブ")], 90)
        self.assertEqual(indexed[("日野川", 2024, "ゴクラクハゼ")], 815)
        self.assertEqual(indexed[("法勝寺川", 2024, "アユ")], 35)
        self.assertEqual(indexed[("法勝寺川", 2014, "シマヨシノボリ")], 16)

    def test_no_river_code_station_or_coordinate_is_invented(self):
        self.assertTrue(all(not r["river_code"] for r in self.records))
        prohibited_fields = {"station", "site", "latitude", "longitude", "coordinate", "reach"}
        self.assertFalse(prohibited_fields.intersection(builder.OUT_FIELDS))

    def test_every_record_is_held_for_conservation_and_source_review(self):
        self.assertTrue(all(r["verification_status"] == "official_pdf_index_text_not_visually_verified"
                            for r in self.records))
        self.assertTrue(all(r["conservation_review"] == "pending" for r in self.records))
        self.assertTrue(all(r["fish_publication_approval"] == "not_approved"
                            and r["integration_status"] == "research_only" for r in self.records))

    def test_overlap_review_marks_possible_duplicates_without_counting_them(self):
        summary = builder.build_overlap_summary(self.records)
        self.assertEqual(summary["same_river_name_and_taxon_matches_in_existing_candidate_ledger"], 2)
        self.assertEqual(summary["same_watershed_name_and_taxon_matches_in_curated_system_ledger"], 0)
        self.assertEqual(summary["same_watershed_year_and_taxon_matches_in_nilim_system_ledger"], 19)
        self.assertTrue(summary["nilim_matches_are_watershed_level_not_river_level"])
        self.assertFalse(summary["approved_for_publication"])
        self.assertFalse(summary["site_updated"])

    def test_two_way_query_returns_historical_candidate_notice(self):
        by_river = searcher.search(self.records, river="日野川")
        by_fish = searcher.search(self.records, fish="アユ")
        self.assertEqual(by_river["record_count"], 47)
        self.assertEqual({r["river"] for r in by_fish["records"]}, {"日野川", "法勝寺川"})
        self.assertTrue(by_fish["zero_results_mean_absence"] is False)
        self.assertTrue(all(r["publication_approval"] == "not_approved" for r in by_fish["records"]))
        with self.assertRaises(ValueError):
            searcher.search(self.records)

    def test_live_atlas_join_is_exact_only_and_never_approves(self):
        atlas = {
            "research_display_name_groups": 511,
            "fish_only_mvp": True,
            "entries": [{"id": "r-1", "name": "日野川"}],
            "links": [{"prefecture": "鳥取県", "water": "日野川水系", "river_id": "r-1"}],
        }
        result = atlas_audit.exact_river_review(self.records, atlas, "fixture")
        hino, hoshoji = result["river_review"]
        self.assertEqual(hino["join_status"], "EXACT_SINGLE_NAME_CANDIDATE")
        self.assertFalse(hino["identity_verified"])
        self.assertFalse(hino["approved_for_publication"])
        self.assertEqual(hoshoji["join_status"], "NO_EXACT_CURRENT_ATLAS_ENTRY")
        self.assertTrue(result["name_match_does_not_verify_river_identity"])

    def test_build_files_are_deterministic_and_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            builder.write_records(self.records, out / "records.csv")
            with (out / "records.csv").open(encoding="utf-8", newline="") as f:
                actual = list(csv.DictReader(f))
            self.assertEqual(actual, self.records)


if __name__ == "__main__":
    unittest.main()
