from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import build_hinogawa_identity_index_v01 as builder
import search_hinogawa_identity_records_v01 as searcher


class HinoIdentityIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_fields, cls.source_rows = builder.load_records()
        cls.identities = builder.load_identities()
        cls.index = builder.build_index(cls.source_rows, cls.identities)

    def test_two_rivers_have_distinct_official_codes_and_relationships(self):
        self.assertEqual(self.identities[("鳥取県", "日野川水系", "日野川")]["river_code"],
                         "8707030001")
        hoshoji = self.identities[("鳥取県", "日野川水系", "法勝寺川")]
        self.assertEqual(hoshoji["river_code"], "8707030003")
        self.assertEqual(hoshoji["relation_to_hino_mainstem"], "日野川本川への支川")

    def test_exact_join_keeps_all_57_rows_staged_and_nonpublic(self):
        self.assertEqual(len(self.index), 57)
        self.assertEqual(len({row["record_id"] for row in self.index}), 57)
        self.assertEqual(
            {(row["river_as_published"], row["river_code"]) for row in self.index},
            {("日野川", "8707030001"), ("法勝寺川", "8707030003")},
        )
        for row in self.index:
            self.assertEqual(row["river_identity_status"],
                             "official_code_and_system_identity_confirmed")
            self.assertEqual(row["fish_sampling_scope_confirmed"], "false")
            self.assertEqual(row["verification_status"],
                             "official_pdf_index_text_not_visually_verified")
            self.assertEqual(row["fish_publication_approval"], "not_approved")
            self.assertEqual(row["integration_status"], "research_only")

    def test_join_requires_exact_source_river_identity(self):
        invalid = [dict(row) for row in self.source_rows]
        invalid[0]["river_as_published"] = "日野川水系"
        with self.assertRaisesRegex(ValueError, "no exact reviewed river identity"):
            builder.build_index(invalid, self.identities)

    def test_search_works_by_code_and_by_fish_in_both_directions(self):
        hoshoji_ayu = searcher.search(self.index, river_code="8707030003", fish="アユ")
        self.assertEqual(hoshoji_ayu["record_count"], 3)
        self.assertEqual({row["river_as_published"] for row in hoshoji_ayu["records"]},
                         {"法勝寺川"})
        fish_search = searcher.search(self.index, fish="アユ")
        self.assertEqual({row["river_code"] for row in fish_search["records"]},
                         {"8707030001", "8707030003"})
        self.assertTrue(fish_search["historical_count_is_not_current_presence_or_catch_guarantee"])
        self.assertTrue(all(row["fish_publication_approval"] == "not_approved"
                            for row in fish_search["records"]))

    def test_unknown_codes_return_empty_without_claiming_absence(self):
        result = searcher.search(self.index, river_code="9999999999")
        self.assertEqual(result["record_count"], 0)
        self.assertFalse(result["zero_results_mean_absence"])
        with self.assertRaises(ValueError):
            searcher.search(self.index)

    def test_output_is_deterministic_and_original_candidates_remain_unmodified(self):
        self.assertTrue(all(not row["river_code"] for row in self.source_rows))
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "linked.csv"
            builder.write_index(self.index, out, self.source_fields + list(builder.ADD_FIELDS))
            with out.open(encoding="utf-8", newline="") as f:
                saved = list(csv.DictReader(f))
            self.assertEqual(saved, self.index)


if __name__ == "__main__":
    unittest.main()
