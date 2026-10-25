
import io
import unittest

from openpyxl import Workbook

from build_candidates import classify_atlas_pairs, extract_workbook, is_positive_detection, parse_survey_year


def fixture_xlsx(site_name="Sensitive sampling site", species_name="Protected fish label", result=1):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sensitive location title"
    rows = [
        [None, None, None, None, None, None, "調査年度", "令和5年度"],
        [None, None, None, None, None, None, "地点名", site_name],
        [None, None, None, None, None, None, "水系名", "Hidden watershed"],
        [None, None, None, None, None, None, "河川名", "Hidden river"],
        [None, None, None, None, None, None, "市町村", "Hidden municipality"],
        [None, None, None, None, "和名", None, None, None],
        [None, None, None, None, species_name, "Testus fishus", None, None],
        [None, None, None, None, "Non-fish organism", None, None, 7],
    ]
    for row in rows:
        sheet.append(row)
    sheet.cell(row=7, column=8).value = result
    target = io.BytesIO()
    workbook.save(target)
    return target.getvalue()


class CandidateExtractionTests(unittest.TestCase):
    def test_aggregates_positive_fish_by_explicit_river_and_redacts_sensitive_fields(self):
        result = extract_workbook(fixture_xlsx(), "FY2023_water_source_fish", {
            "Protectedfishlabel": "taxon-001",
            "Testusfishus": "taxon-001",
        })
        self.assertEqual(len(result["groups"]), 1)
        key, group = next(iter(result["groups"].items()))
        self.assertEqual(key, ("Hiddenwatershed", "Hiddenriver"))
        self.assertEqual(group["years"], {2023})
        self.assertEqual(group["taxa"], {"taxon-001"})
        self.assertEqual(group["positive_cells"], 1)
        serialized = repr(result)
        for private_value in ("Protected fish label", "Testus fishus", "Sensitive sampling site", "Hidden municipality", "Sensitive location title"):
            self.assertNotIn(private_value, serialized)

    def test_zero_detection_does_not_create_candidate(self):
        result = extract_workbook(fixture_xlsx(result=0), "FY2023_water_source_fish", {
            "Protectedfishlabel": "taxon-001",
        })
        self.assertEqual(result["groups"], {})

    def test_unmatched_taxon_is_not_assumed_to_be_fish(self):
        with self.assertRaises(ValueError):
            extract_workbook(fixture_xlsx(), "FY2023_water_source_fish", {})

    def test_positive_value_rules_are_fail_closed_for_booleans_and_unknown_text(self):
        self.assertTrue(is_positive_detection(0.25))
        self.assertTrue(is_positive_detection("検出"))
        self.assertFalse(is_positive_detection(0))
        self.assertFalse(is_positive_detection(False))
        self.assertFalse(is_positive_detection("未確認"))

    def test_survey_year_parser_handles_japanese_eras_and_fallback(self):
        self.assertEqual(parse_survey_year("令和5年度"), 2023)
        self.assertEqual(parse_survey_year("平成30年度"), 2018)
        self.assertEqual(parse_survey_year("no year", 2024), 2024)

    def test_crosswalk_requires_exact_water_and_river_pair_and_holds_ambiguous_groups(self):
        groups = {
            ("Water A", "River A"): {},
            ("Water B", "River B"): {},
            ("Water C", "River C"): {},
            ("Different Water", "River D"): {},
            ("Water E", "River E"): {},
        }
        atlas = {"entries": [
            {"id": "empty", "kind": "official_river_name_only_v21", "water": "Water A", "name": "River A"},
            {"id": "positive", "kind": "historical_national_river_survey", "water": "Water B", "name": "River B"},
            {"id": "held", "kind": "historical_survey_river_name_multiple_code_candidates", "water": "Water C", "name": "River C"},
            {"id": "same-river-different-water", "kind": "official_river_name_only_v21", "water": "Other Water", "name": "River D"},
        ]}
        labels = {"entries": [
            {"survey_river_group_id": "empty", "fish_name_in_source_records": False},
            {"survey_river_group_id": "positive", "fish_name_in_source_records": True},
            {"survey_river_group_id": "held", "fish_name_in_source_records": False},
        ]}
        layer = {"groups": [{"watershed": "Water E", "river": "River E"}]}
        counts = classify_atlas_pairs(groups, atlas, labels, layer)
        self.assertEqual(counts["exact_empty_group_candidate_prefecture_check_pending"], 1)
        self.assertEqual(counts["already_fish_positive"], 1)
        self.assertEqual(counts["identity_hold_excluded"], 1)
        self.assertEqual(counts["unmatched_exact_water_river_pair_needs_crosswalk"], 1)
        self.assertEqual(counts["already_in_published_source_layer"], 1)


if __name__ == "__main__":
    unittest.main()
