"""Review-only triage tests: no automatic code or fish publication."""
import copy
import unittest
from build_river_fish_identity_review_queue_v06 import build, CODE_SCHEMA, ATLAS_SCHEMA


def fixtures(code_count=1, atlas_count=1):
    code = {
        "schema": CODE_SCHEMA, "status": "REVIEW_ONLY_DO_NOT_UPLOAD", "region": "chugoku",
        "source_river_name_groups": 1, "source_fish_year_records": 7,
        "river_name_groups": [{
            "region": "chugoku", "watershed": "太田川", "river": "諸木川",
            "official_fish_year_records": 7, "source_fish_label_count": 4,
            "national_river_code_candidates": ["8707090023", "8707090033"][:code_count],
            "status": ("SINGLE_CODE_NAME_CANDIDATE_NOT_VERIFIED" if code_count == 1
                       else "MULTIPLE_CODE_NAME_CANDIDATES" if code_count > 1
                       else "NO_RIVER_CODE_NAME_CANDIDATE"),
            "approved_for_publication": False, "code_identity_verified": False,
            "prefecture_verified": False,
        }],
    }
    atlas = {
        "schema": ATLAS_SCHEMA, "status": "REVIEW_ONLY_DO_NOT_UPLOAD", "region": "chugoku",
        "source_named_river_groups": 1, "source_fish_year_records": 7,
        "groups": [{
            "region": "chugoku", "watershed": "太田川", "river": "諸木川",
            "fish_year_record_count": 7, "fish_name_label_count": 4,
            "atlas_name_candidates": [
                {"prefecture": "広島県", "atlas_id": "a"},
                {"prefecture": "山口県", "atlas_id": "b"},
            ][:atlas_count],
            "status": ("ONE_NAVIGATION_NAME_CANDIDATE_NOT_VERIFIED" if atlas_count == 1
                       else "MULTIPLE_NAVIGATION_NAME_CANDIDATES" if atlas_count > 1
                       else "SOURCE_NAMED_RIVER_NOT_IN_LIVE_ATLAS"),
            "approved_for_publication": False,
            "national_river_code_verified": False, "official_prefecture_verified": False,
        }],
    }
    return code, atlas


class IdentityQueueTests(unittest.TestCase):
    def test_existing_single_both_still_not_published(self):
        c, a = fixtures()
        out = build(c, a)
        self.assertEqual(out["priority_counts"], {"A_EXISTING_ATLAS_IDENTITY_REVIEW": 1})
        x = out["queue"][0]
        self.assertFalse(x["identity_verified"])
        self.assertFalse(x["approved_for_publication"])
        self.assertEqual(x["conservation_publication_review"], "required")
        self.assertNotIn("アユ", str(out))
        self.assertNotIn("recorded_name", str(out))

    def test_new_atlas_candidate_is_review_not_auto_creation(self):
        c, a = fixtures(atlas_count=0)
        x = build(c, a)["queue"][0]
        self.assertEqual(x["review_priority"], "B_NEW_ATLAS_RIVER_IDENTITY_REVIEW")
        self.assertEqual(x["atlas_navigation_name_candidates"], [])

    def test_ambiguous_code_or_atlas_deprioritized(self):
        c, a = fixtures(code_count=2)
        self.assertEqual(build(c, a)["queue"][0]["review_priority"],
                         "C_AMBIGUITY_OR_MISSING_CODE_REVIEW")
        c, a = fixtures(atlas_count=2)
        self.assertEqual(build(c, a)["queue"][0]["review_priority"],
                         "C_AMBIGUITY_OR_MISSING_CODE_REVIEW")

    def test_missing_code_deprioritized(self):
        c, a = fixtures(code_count=0)
        self.assertEqual(build(c, a)["queue"][0]["review_priority"],
                         "C_AMBIGUITY_OR_MISSING_CODE_REVIEW")

    def test_count_mismatch_fails(self):
        c, a = fixtures()
        a["groups"][0]["fish_year_record_count"] = 6
        with self.assertRaises(ValueError):
            build(c, a)

    def test_region_or_publication_drift_fails(self):
        c, a = fixtures()
        a["region"] = "kanto"
        with self.assertRaises(ValueError):
            build(c, a)
        c, a = fixtures()
        c["river_name_groups"][0]["approved_for_publication"] = True
        with self.assertRaises(ValueError):
            build(c, a)

    def test_key_mismatch_and_duplicate_fails(self):
        c, a = fixtures()
        a["groups"][0]["river"] = "別川"
        with self.assertRaises(ValueError):
            build(c, a)
        c, a = fixtures()
        c["river_name_groups"].append(copy.deepcopy(c["river_name_groups"][0]))
        with self.assertRaises(ValueError):
            build(c, a)


if __name__ == "__main__":
    unittest.main()
