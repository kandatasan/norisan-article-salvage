"""Regression: official survey x national code list remains review-only."""
import copy
import unittest
from build_official_river_code_candidates_v05 import (
    compare, basin, SOURCE_RIVER_URL, SOURCE_WATER_URL, load_codes
)
from extract_official_named_river_fish_nationwide_v04 import manifest_for


def source(water="太田川", river="諸木川", fish="アユ"):
    m = manifest_for("chugoku")
    return {
        "region": "chugoku", "watershed": water, "river_name": river,
        "survey_year": "2021", "recorded_name": fish,
        "source_url": m["source_url"], "source_sha256": m["source_sha256"],
        "review_status": "unapproved_requires_conservation_and_identity_review",
    }


def codes():
    return [
        {"river_code": "8707090023", "river_name": "諸木川",
         "watershed_code": "870709", "watershed_name": "太田川",
         "code_region_prefix": "87", "source_url": SOURCE_RIVER_URL,
         "identity_status": "coded_name_only_not_geographically_verified",
         "site_status": "research_only"},
        {"river_code": "8707090001", "river_name": "諸木川",
         "watershed_code": "870709", "watershed_name": "太田川",
         "code_region_prefix": "87", "source_url": SOURCE_RIVER_URL,
         "identity_status": "coded_name_only_not_geographically_verified",
         "site_status": "research_only"},
    ]


def waters():
    return [{"watershed_code": "870709", "watershed_name": "太田川",
             "code_region_prefix": "87", "source_url": SOURCE_WATER_URL,
             "identity_status": "coded_watershed_name_only"}]


class NationalCodeCandidatesTests(unittest.TestCase):
    def test_all_35449_code_rows_load(self):
        rivers, ws = load_codes()
        self.assertEqual(len(rivers), 35449)
        self.assertEqual(len(ws), 5475)
        self.assertTrue(any(x["river_code"] == "8707090023" and x["river_name"] == "諸木川" for x in rivers))

    def test_one_name_code_candidate_still_unverified(self):
        d = compare([source()], codes()[:1], waters(), "chugoku", manifest_for("chugoku"))
        x = d["river_name_groups"][0]
        self.assertEqual(x["status"], "SINGLE_CODE_NAME_CANDIDATE_NOT_VERIFIED")
        self.assertEqual(x["national_river_code_candidates"], ["8707090023"])
        self.assertFalse(x["code_identity_verified"])
        self.assertFalse(x["approved_for_publication"])
        self.assertEqual(d["status"], "REVIEW_ONLY_DO_NOT_UPLOAD")

    def test_two_codes_ambiguous(self):
        x = compare([source()], codes(), waters(), "chugoku", manifest_for("chugoku"))["river_name_groups"][0]
        self.assertEqual(x["status"], "MULTIPLE_CODE_NAME_CANDIDATES")
        self.assertEqual(len(x["national_river_code_candidates"]), 2)

    def test_missing_watershed_or_river(self):
        x = compare([source("未登録水系")], codes(), waters(), "chugoku", manifest_for("chugoku"))["river_name_groups"][0]
        self.assertEqual(x["status"], "WATERSHED_NOT_IN_CODE_LIST")
        x = compare([source(river="別の川")], codes(), waters(), "chugoku", manifest_for("chugoku"))["river_name_groups"][0]
        self.assertEqual(x["status"], "NO_RIVER_CODE_NAME_CANDIDATE")

    def test_no_inference_from_watershed_to_river(self):
        x = compare([source("太田川", "別の川")], codes(), waters(), "chugoku", manifest_for("chugoku"))["river_name_groups"][0]
        self.assertEqual(x["national_river_code_candidates"], [])
        self.assertFalse(x["prefecture_verified"])

    def test_deduplicate_fish_name_count_without_exposing_labels(self):
        d = compare([source(), source(fish="アユ"), source(fish="オイカワ")],
                    codes()[:1], waters(), "chugoku", manifest_for("chugoku"))
        x = d["river_name_groups"][0]
        self.assertEqual(x["official_fish_year_records"], 3)
        self.assertEqual(x["source_fish_label_count"], 2)
        self.assertNotIn("recorded_name", str(d))
        self.assertNotIn("アユ", str(d))

    def test_source_provenance_mismatch_fails_closed(self):
        bad = source()
        bad["review_status"] = "approved"
        with self.assertRaises(ValueError):
            compare([bad], codes(), waters(), "chugoku", manifest_for("chugoku"))
        bad = source()
        bad["source_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            compare([bad], codes(), waters(), "chugoku", manifest_for("chugoku"))

    def test_basin_normalizes_only_suffix(self):
        self.assertEqual(basin("太田川水系"), "太田川")
        self.assertEqual(basin("太田川"), "太田川")
        self.assertEqual(basin("太田川支流"), "太田川支流")


if __name__ == "__main__":
    unittest.main()
