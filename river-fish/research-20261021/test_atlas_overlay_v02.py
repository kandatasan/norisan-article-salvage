import unittest
from build_atlas_overlay_v02 import overlay
from build_river_fish_layer_v02 import build, load_csv, INPUT, HIROSHIMA


class OverlayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layer = build(load_csv(INPUT), load_csv(HIROSHIMA))

    def atlas(self):
        return {
            "research_display_name_groups": 511, "fish_only_mvp": True,
            "entries": [
                {"id": "a", "name": "黒瀬川"},
                {"id": "b", "name": "笹ヶ瀬川"},
                {"id": "c", "name": "笹ヶ瀬川"},
            ],
            "links": [
                {"prefecture": "広島県", "water": "黒瀬川水系", "river_id": "a"},
                {"prefecture": "岡山県", "water": "笹ヶ瀬川", "river_id": "b"},
                {"prefecture": "岡山県", "water": "笹ヶ瀬川", "river_id": "c"},
            ],
        }

    def test_no_auto_approval_and_exact_name_only(self):
        data = overlay(self.layer, self.atlas())
        self.assertEqual(data["publication_status"], "REVIEW_ONLY_DO_NOT_UPLOAD")
        self.assertEqual(data["source_fish_records"], 111)
        self.assertEqual(data["source_river_groups"], 12)
        for row in data["river_links"]:
            self.assertFalse(row["national_river_code_verified"])
            self.assertFalse(row["approved_for_publication"])
        kuro = next(x for x in data["river_links"] if x["river"] == "黒瀬川")
        self.assertEqual(kuro["match_class"], "EXACT_SINGLE_NAME_CANDIDATE")
        self.assertEqual(kuro["candidate_atlas_ids"], ["a"])
        okayama = next(x for x in data["river_links"] if x["river"] == "笹ヶ瀬川")
        self.assertEqual(okayama["match_class"], "AMBIGUOUS_SAME_NAME")

    def test_new_source_name_group_not_fake_atlas_id(self):
        data = overlay(self.layer, self.atlas())
        unmatched = [x for x in data["river_links"] if x["match_class"] == "SOURCE_NAMED_RIVER_NOT_IN_ATLAS"]
        self.assertGreater(len(unmatched), 0)
        self.assertTrue(all(not x["candidate_atlas_ids"] for x in unmatched))

    def test_schema_change_and_dangling_id_fail_closed(self):
        bad = self.atlas()
        bad["fish_only_mvp"] = False
        with self.assertRaises(ValueError):
            overlay(self.layer, bad)
        bad = self.atlas()
        bad["links"][0]["river_id"] = "missing"
        with self.assertRaises(ValueError):
            overlay(self.layer, bad)


if __name__ == "__main__":
    unittest.main()
