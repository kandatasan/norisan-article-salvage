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
        self.assertEqual(total + excluded, 155)
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

    def test_sh22_safe_fish_delta_is_source_scoped_and_searchable_both_ways(self):
        sh22_rows = [r for r in self.source_rows if r["source_id"] == "SH22"]
        self.assertEqual(len(sh22_rows), 98)
        self.assertEqual(len({(r["river"], r["recorded_name"]) for r in sh22_rows}), 98)
        self.assertTrue(all(r["evidence_scope"] == "named_river" for r in sh22_rows))
        self.assertTrue(all(r["survey_year"] == "" for r in sh22_rows))
        self.assertEqual({r["source_url"] for r in sh22_rows}, {"https://www.pref.shimane.lg.jp/infra/river/kasen/hoshin/hiikawachuryusisen_kawadukuri/index.data/chuuryuuikifuzokusiryou.pdf"})
        self.assertTrue(all(r["source_locator"] == "表2-4 資料p20 PDF p21"
                            for r in sh22_rows))
        self.assertTrue(all(r["verification_status"] == "source_text_checked"
                            for r in sh22_rows))
        self.assertTrue(all(r["integration_status"] == "staged_only"
                            for r in sh22_rows))

        expected_additions = {
            ("斐伊川", "コイ"), ("斐伊川", "フナ類"), ("斐伊川", "タイリクバラタナゴ"),
            ("斐伊川", "モツゴ"), ("斐伊川", "ゼゼラ"), ("斐伊川", "コウライモロコ"),
            ("斐伊川", "ニシシマドジョウ（シマドジョウ）"), ("斐伊川", "ワカサギ"),
            ("斐伊川", "ウキゴリ"), ("斐伊川", "マハゼ"), ("斐伊川", "旧トウヨシノボリ類"),
            ("斐伊川", "ヌマチチブ"),
            ("赤川", "シマドジョウ"), ("赤川", "ヒメダカ"), ("赤川", "旧トウヨシノボリ類"),
            ("三刀屋川", "シマドジョウ"), ("三刀屋川", "旧トウヨシノボリ類"),
            ("久野川", "シマドジョウ"), ("久野川", "旧トウヨシノボリ類"),
            ("深野川", "シマドジョウ"), ("阿井川", "旧トウヨシノボリ類"),
        }
        source_pairs = {(r["river"], r["recorded_name"]) for r in sh22_rows}
        self.assertTrue(expected_additions.issubset(source_pairs))

        indexed = [(river["river"], fish["recorded_name"])
                   for river in self.data["river_groups"]
                   for fish in river["fish_labels"] if fish["source_id"] == "SH22"]
        self.assertEqual(len(indexed), 94)
        visible_counts = {}
        for river, _name in indexed:
            visible_counts[river] = visible_counts.get(river, 0) + 1
        self.assertEqual(visible_counts, {
            "斐伊川": 27, "赤川": 15, "三刀屋川": 15,
            "久野川": 13, "深野川": 12, "阿井川": 12,
        })
        # Table-2.4 reconciliation: 130 river×fish labels, 94 searchable,
        # and 36 held back from preview pending conservation/editorial review.
        self.assertEqual(130 - len(indexed), 36)

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
