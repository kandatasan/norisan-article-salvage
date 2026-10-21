"""Regression: Hiroshima narratives add only source-backed, non-sensitive research records."""
import copy
import unittest
from build_river_fish_layer_v02 import build, load_csv, INPUT, HIROSHIMA, SCHEMA
from build_river_fish_preview_v02 import render


class ExpandedRiverFishTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = load_csv(INPUT)
        cls.hiroshima = load_csv(HIROSHIMA)
        cls.layer = build(cls.base, cls.hiroshima)

    def test_counts_and_provenance(self):
        d = self.layer
        self.assertEqual(d["schema"], SCHEMA)
        self.assertEqual(len(d["river_groups"]), 12)
        self.assertEqual(sum(x["source_record_count"] for x in d["river_groups"]), 111)
        self.assertEqual(sum(d["excluded_counts"].values()), 22)
        self.assertEqual(d["source_inventories"]["narratives_added_research_only"], 7)

    def test_no_sensitive_hiroshima_records(self):
        river = next(x for x in self.layer["river_groups"] if x["source_river_key"] == "広島県|黒瀬川|黒瀬川")
        self.assertEqual(river["source_record_count"], 7)
        names = {x["recorded_name"] for x in river["fish_labels"]}
        self.assertNotIn("スナヤツメ", names)
        self.assertNotIn("メダカ", names)
        self.assertIn("オイカワ", names)
        self.assertIn("アユ", names)
        self.assertTrue(all(x["survey_year"] is None for x in river["fish_labels"]))

    def test_conservation_flagged_records_are_excluded_from_both_indexes(self):
        self.assertEqual(self.layer["excluded_counts"]["conservation_review_required"], 12)
        labels = {fish["recorded_name"] for river in self.layer["river_groups"]
                  for fish in river["fish_labels"]}
        self.assertNotIn("ヤマメ", labels)
        self.assertNotIn("ヤマメ", self.layer["fish_reverse_index"])

    def test_bidirectional_references(self):
        for river in self.layer["river_groups"]:
            self.assertFalse(river["national_river_code_identity_verified"])
            self.assertIsNone(river["national_river_code"])
            self.assertEqual(river["publication_review"], "not_approved")
            for fish in river["fish_labels"]:
                self.assertIn(river["source_river_key"], self.layer["fish_reverse_index"][fish["recorded_name"]])

    def test_reject_status_and_unverified_source(self):
        for field, value in [("publication_status", "published"), ("national_river_code", "1234567890"),
                             ("sensitive_species_flag", "unknown"), ("survey_year", "2024")]:
            bad = copy.deepcopy(self.hiroshima)
            bad[0][field] = value
            with self.assertRaises(ValueError):
                build(self.base, bad)

    def test_sensitive_exclusion_and_fail_closed(self):
        bad = copy.deepcopy(self.hiroshima)
        bad[0]["sensitive_species_flag"] = "true"
        with self.assertRaises(ValueError):
            build(self.base, bad)
        bad = copy.deepcopy(self.hiroshima)
        bad[0]["source_url"] = "https://example.org/untrusted"
        with self.assertRaises(ValueError):
            build(self.base, bad)

    def test_preview_has_data_and_noindex(self):
        page = render(self.layer)
        self.assertIn("noindex,nofollow", page)
        self.assertIn(SCHEMA, page)
        self.assertIn("黒瀬川", page)
        self.assertNotIn("__EMBEDDED_LAYER__", page)


if __name__ == "__main__":
    unittest.main()
