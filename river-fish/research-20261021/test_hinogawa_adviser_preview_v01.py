"""Tests for the noindex browser preview built from existing HINO25 records."""
import json
import re
import unittest

from build_hinogawa_adviser_fish_records_v01 import (
    ALLOWED_FISH,
    SOURCE_URL,
    expand_records,
    read_transcription,
)
from build_hinogawa_adviser_preview_v01 import build_layer, render


class HinoAdviserPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = expand_records(read_transcription())
        cls.layer = build_layer(cls.records)
        cls.preview = render(cls.records)

    def test_preview_reuses_existing_57_research_records(self):
        self.assertEqual(self.layer["positive_count_observation_total"], 57)
        self.assertEqual(self.layer["fish_species_total"], 8)
        self.assertEqual(len(self.layer["river_groups"]), 2)
        self.assertEqual(
            {row["river"]: row["positive_count_observation_total"]
             for row in self.layer["river_groups"]},
            {"日野川": 47, "法勝寺川": 10},
        )
        self.assertEqual(
            {fish["recorded_name"] for river in self.layer["river_groups"]
             for fish in river["fish_records"]},
            ALLOWED_FISH,
        )

    def test_two_way_data_has_correct_years_counts_and_source(self):
        hino = next(row for row in self.layer["river_groups"] if row["river"] == "日野川")
        ayu = next(row for row in hino["fish_records"] if row["recorded_name"] == "アユ")
        self.assertEqual(
            [(row["survey_year"], row["individual_count"]) for row in ayu["observations"]],
            [(1994, 501), (1999, 269), (2004, 404), (2009, 469),
             (2014, 130), (2019, 54), (2024, 310)],
        )
        self.assertEqual(
            [row["river"] for row in self.layer["fish_reverse_index"]["アユ"]],
            ["日野川", "法勝寺川"],
        )
        self.assertEqual(self.layer["source_url"], SOURCE_URL)
        self.assertEqual(self.layer["source_document_date"], "2025-09")

    def test_redacted_rows_and_unverified_locations_never_enter_preview(self):
        self.assertFalse(self.layer["protected_or_redacted_rows_exported"])
        self.assertEqual(self.layer["verified_river_code_links"], 0)
        self.assertFalse(self.layer["sampling_stations_identified"])
        self.assertFalse(self.layer["current_habitat_verified"])
        self.assertFalse(self.layer["catchability_verified"])
        self.assertEqual(self.layer["publication_approval"], "not_approved")
        self.assertTrue(all(not row["river_code"] for row in self.records))
        embedded = re.search(
            r'<script id="source-layer" type="application/json">(.*?)</script>',
            self.preview,
            re.S,
        )
        self.assertIsNotNone(embedded)
        exported = json.loads(embedded.group(1))
        names = {row["recorded_name"] for river in exported["river_groups"]
                 for row in river["fish_records"]}
        self.assertEqual(names, ALLOWED_FISH)

    def test_preview_is_offline_noindex_and_explicit_about_historical_records(self):
        self.assertIn('name="robots" content="noindex,nofollow"', self.preview)
        self.assertIn('id="river"', self.preview)
        self.assertIn('id="fish"', self.preview)
        self.assertIn("日野川・法勝寺川", self.preview)
        self.assertIn("現在の生息・個体数・釣果を示しません", self.preview)
        self.assertIn("全記録が未承認", self.preview)
        self.assertIn(SOURCE_URL, self.preview)
        self.assertFalse(self.layer["site_updated"])


if __name__ == "__main__":
    unittest.main()
