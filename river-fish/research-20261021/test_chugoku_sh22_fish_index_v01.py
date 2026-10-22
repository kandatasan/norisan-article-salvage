"""Regression tests for the source-scoped, redaction-safe SH22 fish index."""
import json
import re
import unittest

from build_chugoku_sh22_fish_index_v01 import (
    ADDITIONS_INPUT, BASE_INPUT, REVIEW_REQUIRED_NAMES, RIVERS, SOURCE_URL,
    SOURCE_LOCATOR, build, load_csv,
)
from build_chugoku_sh22_fish_preview_v01 import render


class SH22FishIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_rows = load_csv(BASE_INPUT)
        cls.additions = load_csv(ADDITIONS_INPUT)
        cls.layer = build(cls.base_rows, cls.additions)
        cls.preview = render(cls.layer)

    def test_complete_official_table_accounting(self):
        self.assertEqual(sum(RIVERS.values()), 130)
        self.assertEqual(self.layer["source_table_record_total"], 130)
        self.assertEqual(self.layer["searchable_research_record_total"], 94)
        self.assertEqual(self.layer["withheld_review_record_total"], 36)
        self.assertEqual(len(self.layer["river_groups"]), 6)
        self.assertEqual(len(self.additions), 21)

    def test_each_named_river_has_expected_safe_search_count(self):
        counts = {r["river"]: r["source_record_count"] for r in self.layer["river_groups"]}
        self.assertEqual(counts, {"斐伊川": 27, "赤川": 15, "三刀屋川": 15,
                                  "久野川": 13, "深野川": 12, "阿井川": 12})

    def test_bidirectional_lookup_and_source_provenance(self):
        groups = {r["river"]: r for r in self.layer["river_groups"]}
        fish = {x["recorded_name"] for x in groups["斐伊川"]["fish_labels"]}
        self.assertIn("コウライモロコ", fish)
        self.assertEqual(self.layer["fish_reverse_index"]["コウライモロコ"], ["斐伊川"])
        self.assertEqual(self.layer["fish_reverse_index"]["シマドジョウ"],
                         ["三刀屋川", "久野川", "深野川", "赤川"])
        for river in groups.values():
            for row in river["fish_labels"]:
                self.assertEqual(row["source_id"], "SH22")
                self.assertEqual(row["source_url"], SOURCE_URL)
                self.assertEqual(row["source_locator"], SOURCE_LOCATOR)
                self.assertEqual(row["verification_status"], "source_pdf_table_image_checked")

    def test_review_held_species_and_names_are_absent(self):
        names = {x["recorded_name"] for r in self.layer["river_groups"] for x in r["fish_labels"]}
        self.assertTrue(names.isdisjoint(REVIEW_REQUIRED_NAMES))
        self.assertFalse(self.layer["withheld_review_record_names_exported"])
        embedded = re.search(r'<script id="source-layer" type="application/json">(.*?)</script>',
                             self.preview, re.S)
        exported = json.loads(embedded.group(1))
        exported_names = {x["recorded_name"] for r in exported["river_groups"]
                          for x in r["fish_labels"]}
        self.assertTrue(exported_names.isdisjoint(REVIEW_REQUIRED_NAMES))

    def test_not_current_habitat_and_no_river_code_join(self):
        self.assertEqual(self.layer["verified_river_code_links"], 0)
        self.assertFalse(self.layer["current_habitat_verified"])
        self.assertFalse(self.layer["catchability_verified"])
        for river in self.layer["river_groups"]:
            self.assertIsNone(river["national_river_code"])
            self.assertFalse(river["national_river_code_identity_verified"])
            self.assertFalse(river["individual_sampling_station_identified"])
            self.assertEqual(river["publication_review"], "not_approved")

    def test_survey_years_remain_unknown(self):
        for river in self.layer["river_groups"]:
            for row in river["fish_labels"]:
                self.assertIsNone(row["survey_year"])

    def test_no_duplicate_source_river_fish_rows(self):
        keys = [(r["river"], x["recorded_name"])
                for r in self.layer["river_groups"] for x in r["fish_labels"]]
        self.assertEqual(len(keys), len(set(keys)))

    def test_preview_is_offline_two_way_and_noindex(self):
        self.assertIn('name="robots" content="noindex,nofollow"', self.preview)
        self.assertIn("river", self.preview)
        self.assertIn("fish", self.preview)
        self.assertIn("source-layer", self.preview)
        self.assertIn("RESEARCH_ONLY_NOT_FOR_LIVE_SITE", json.dumps(self.layer))

    def test_water_scope_and_river_scope_are_not_expanded(self):
        group_names = {r["river"] for r in self.layer["river_groups"]}
        self.assertEqual(group_names, set(RIVERS))
        hino = next(r for r in self.layer["river_groups"] if r["river"] == "斐伊川")
        self.assertIn("放水路〜尾原ダム", hino["source_scope_note"])
        self.assertIn("支川全体への拡張はしない", hino["source_scope_note"])


if __name__ == "__main__":
    unittest.main()
