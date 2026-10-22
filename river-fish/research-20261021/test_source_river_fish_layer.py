"""Ensure the two-way river/fish research layer does not infer habitat or code identity."""
import csv
import pathlib
import unittest
from build_source_river_fish_layer import build, INPUT, EDITION


class SourceLayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with INPUT.open(encoding="utf-8-sig", newline="") as f:
            cls.source_rows = list(csv.DictReader(f))
        cls.data = build(cls.source_rows)

    def test_schema_and_no_publish(self):
        self.assertEqual(self.data["schema"], EDITION)
        self.assertEqual(self.data["status"], "RESEARCH_ONLY_NOT_FOR_LIVE_SITE")
        self.assertEqual(self.data["verified_river_code_links"], 0)
        self.assertFalse(self.data["current_habitat_verified"])
        self.assertFalse(self.data["catchability_verified"])

    def test_every_river_is_source_scoped_and_no_code(self):
        for river in self.data["river_groups"]:
            self.assertIsNone(river["national_river_code"])
            self.assertFalse(river["national_river_code_identity_verified"])
            self.assertEqual(river["publication_review"], "not_approved")
            self.assertEqual(river["source_river_key"], "|".join(
                (river["prefecture"], river["watershed"], river["river"])))

    def test_exclusion_and_counts(self):
        total = sum(r["source_record_count"] for r in self.data["river_groups"])
        excluded = sum(self.data["excluded_counts"].values())
        self.assertEqual(total + excluded, 134)
        self.assertEqual(self.data["excluded_counts"]["watershed_only"], 18)
        self.assertEqual(self.data["excluded_counts"]["conservation_review_required"], 12)
        self.assertEqual(self.data["excluded_counts"].get("source_not_fully_checked", 0), 0)
        self.assertGreater(self.data["excluded_counts"]["conservation_review_required"], 0)

    def test_conservation_held_source_is_absent_from_both_search_directions(self):
        held_sources = {r["source_id"] for r in self.source_rows
                        if r["source_id"] == "YA07" and r["conservation_review"] == "required"}
        indexed_sources = {fish["source_id"] for river in self.data["river_groups"]
                           for fish in river["fish_labels"]}
        self.assertTrue(held_sources)
        self.assertTrue(held_sources.isdisjoint(indexed_sources))
        reverse_sources = {fish["source_id"] for label in self.data["fish_reverse_index"]
                           for river_key in self.data["fish_reverse_index"][label]
                           for river in self.data["river_groups"]
                           if river["source_river_key"] == river_key
                           for fish in river["fish_labels"] if fish["recorded_name"] == label}
        self.assertTrue(held_sources.isdisjoint(reverse_sources))

    def test_source_scoped_reverse_index(self):
        for river in self.data["river_groups"]:
            for fish in river["fish_labels"]:
                self.assertIn(river["source_river_key"],
                              self.data["fish_reverse_index"][fish["recorded_name"]])
                self.assertTrue(fish["source_url"].startswith("https://"))
                self.assertTrue(fish["source_locator"])

    def test_no_conservation_review_species(self):
        sensitive = {r["recorded_name"] for r in self.source_rows
                     if r["conservation_review"] == "required"}
        exposed = {fish["recorded_name"] for river in self.data["river_groups"]
                   for fish in river["fish_labels"]}
        self.assertTrue(sensitive.isdisjoint(exposed))

    def test_no_source_only_watershed_river_invented(self):
        for river in self.data["river_groups"]:
            self.assertTrue(river["river"])
            self.assertTrue(river["watershed"])
            self.assertNotEqual(river["prefecture"], "")
        for row in self.source_rows:
            if row["evidence_scope"] == "watershed_only":
                self.assertNotIn("|".join((row["prefecture"], row["watershed"], "")),
                                 {x["source_river_key"] for x in self.data["river_groups"]})

    def test_reject_changed_status_and_duplicate(self):
        bad = [dict(r) for r in self.source_rows]
        bad[0]["integration_status"] = "approved"
        with self.assertRaises(ValueError):
            build(bad)
        bad = [dict(r) for r in self.source_rows]
        bad[1] = dict(bad[0])
        with self.assertRaises(ValueError):
            build(bad)


if __name__ == "__main__":
    unittest.main()
