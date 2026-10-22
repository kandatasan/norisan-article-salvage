"""Guard the separate fish↔watershed search against river-level inference."""
import csv
import unittest

from build_watershed_fish_index_v01 import INPUT, SCHEMA, build
from build_watershed_fish_preview_v01 import render


class WatershedFishIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with INPUT.open(encoding="utf-8-sig", newline="") as handle:
            cls.layer = build(list(csv.DictReader(handle)))

    def test_watershed_only_records_support_two_way_search_without_rivers(self):
        layer = self.layer
        self.assertEqual(layer["schema"], SCHEMA)
        self.assertEqual(len(layer["watershed_groups"]), 18)
        self.assertEqual(layer["source_watershed_rows"], 19)
        self.assertEqual(layer["excluded_counts"], {"conservation_review_required": 1})
        self.assertEqual(set(layer["fish_to_watershed_index"]["オオクチバス"]), {
            "山口県|YA04|錦川", "山口県|YA04|島田川", "山口県|YA04|佐波川",
            "山口県|YA04|椹野川", "山口県|YA04|厚東川", "山口県|YA04|厚狭川",
            "山口県|YA04|木屋川", "山口県|YA04|阿武川", "山口県|YA04|小瀬川",
            "山口県|YA04|長沢川", "山口県|YA04|南若川", "山口県|YA04|土路石川",
            "山口県|YA04|井関川", "山口県|YA04|真締川", "山口県|YA04|有帆川",
            "山口県|YA04|西田川", "山口県|YA04|栗野川", "山口県|YA04|深川川",
        })
        self.assertEqual(layer["individual_river_links"], 0)
        self.assertNotIn("ヌマムツ", layer["fish_to_watershed_index"])
        protected_names = {row["recorded_name"] for row in self._source_rows()
                           if row["conservation_review"] == "required"}
        indexed_names = {fish["recorded_name"] for watershed in layer["watershed_groups"]
                         for fish in watershed["fish_labels"]}
        self.assertTrue(protected_names.isdisjoint(indexed_names))
        for row in layer["watershed_groups"]:
            self.assertFalse(row["individual_river_linked"])
            self.assertEqual(row["publication_review"], "not_approved")
            self.assertNotIn("river", row)
            self.assertNotIn("river_code", row)
            self.assertTrue(all(f["evidence_scope"] == "watershed_only"
                                for f in row["fish_labels"]))

    def test_preview_keeps_watershed_scope_and_noindex_notice(self):
        page = render(self.layer)
        self.assertIn('name="robots" content="noindex,nofollow"', page)
        self.assertIn("水系単位の過去資料", page)
        self.assertIn("個別河川には未接続", page)
        self.assertIn("オオクチバス", page)
        self.assertNotIn("ヌマムツ", page)
        self.assertNotIn("__DATA__", page)

    @staticmethod
    def _source_rows():
        with INPUT.open(encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    def test_changed_source_scope_fails_closed(self):
        with INPUT.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        target = next(row for row in rows if row["source_id"] == "YA04")
        target["river"] = "架空の河川"
        with self.assertRaises(ValueError):
            build(rows)


if __name__ == "__main__":
    unittest.main()
