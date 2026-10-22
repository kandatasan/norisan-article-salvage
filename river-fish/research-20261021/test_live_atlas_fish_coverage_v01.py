"""Offline fail-closed tests for the live fish-coverage audit."""
import unittest

from audit_live_atlas_fish_coverage_v01 import summarize


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.atlas = {
            "fish_only_mvp": True,
            "location_sensitive_data_excluded": True,
            "fish_editorial_work_is_still_unverified": True,
            "strictly_source_named_river_groups_not_geographically_unique_rivers": True,
            "entries": [
                {"id": "rn_a", "kind": "historical_national_river_survey"},
                {"id": "held_b", "kind": "historical_survey_river_name_multiple_code_candidates"},
                {"id": "official_c", "kind": "official_river_name_only_v21"},
                {"id": "edna_d", "kind": "prefectural_environmental_DNA_only"},
                {"id": "water_e", "kind": "official_watershed_name_only_v21"},
            ],
        }
        self.labels = {
            "schema": "tsurikue-original-survey-fish-label-counts-v25",
            "original_source_groups": 3,
            "historical_fish_labels_do_not_confirm_current_presence": True,
            "DNA_positive_labels_do_not_mean_capture_or_visual_confirmation": True,
            "is_recorded_name_label_count_not_distinct_taxonomic_species": True,
            "entries": [
                {"survey_river_group_id": "rn_a", "historical_fish_literal_name_count": 2,
                 "environmental_DNA_fish_literal_name_rows": 0, "fish_name_in_source_records": True},
                {"survey_river_group_id": "held_b", "historical_fish_literal_name_count": 1,
                 "environmental_DNA_fish_literal_name_rows": 0, "fish_name_in_source_records": True},
                {"survey_river_group_id": "edna_d", "historical_fish_literal_name_count": 0,
                 "environmental_DNA_fish_literal_name_rows": 3, "fish_name_in_source_records": True},
            ],
        }

    def test_excludes_watershed_names_and_identity_hold_from_qualifying_numerator(self):
        result = summarize(self.atlas, self.labels)
        self.assertEqual(result["river_name_display_groups"], 4)
        self.assertEqual(result["fish_evidence_groups_including_identity_holds"], 3)
        self.assertEqual(result["coverage_percent_including_identity_holds"], 75.0)
        self.assertEqual(result["identity_hold_groups_in_denominator"], 1)
        self.assertEqual(result["identity_hold_groups_with_fish_evidence_excluded"], 1)
        self.assertEqual(result["fish_evidence_groups_excluding_identity_holds"], 2)
        self.assertEqual(result["coverage_percent_excluding_identity_holds"], 50.0)
        self.assertEqual(result["target_groups_at_current_denominator"], 2)
        self.assertEqual(result["additional_qualifying_groups_needed"], 0)
        self.assertEqual(result["watershed_only_entries_excluded_from_denominator"], 1)

    def test_fails_closed_when_fish_flag_disagrees_with_counts(self):
        self.labels["entries"][0]["fish_name_in_source_records"] = False
        with self.assertRaises(ValueError):
            summarize(self.atlas, self.labels)

    def test_fails_closed_on_unreviewed_entry_kind(self):
        self.atlas["entries"].append({"id": "new", "kind": "unreviewed_type"})
        with self.assertRaises(ValueError):
            summarize(self.atlas, self.labels)

    def test_fails_closed_when_research_group_sets_drift(self):
        self.atlas["entries"].pop(0)
        with self.assertRaises(ValueError):
            summarize(self.atlas, self.labels)

    def test_fails_closed_if_required_caveat_disappears(self):
        self.labels["DNA_positive_labels_do_not_mean_capture_or_visual_confirmation"] = False
        with self.assertRaises(ValueError):
            summarize(self.atlas, self.labels)


if __name__ == "__main__":
    unittest.main()
