#!/usr/bin/env python3
"""Read-only integrity tests for research-only fish-to-river evidence candidates."""
import csv
import pathlib
import unittest
from collections import Counter
from urllib.parse import urlparse

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "fish_river_evidence_candidates_20261021.csv"
FIELDS = {
    "prefecture", "watershed", "river", "evidence_scope", "recorded_name",
    "evidence_kind", "survey_year", "source_id", "source_locator",
    "verification_status", "source_url", "conservation_review",
    "integration_status", "notes",
}
SOURCE_IDS = {"SH22", "HIY", "HIN", "OK19", "TO16", "YA07", "YA04"}
COUNTS = {"島根県": 77, "広島県": 7, "岡山県": 15, "鳥取県": 15, "山口県": 10}
SCOPES = {"named_river", "named_river_context", "watershed_only"}


class FishRiverCandidateQA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with DATA.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            cls.fields = set(reader.fieldnames or [])
            cls.rows = list(reader)

    def test_schema_and_counts(self):
        self.assertEqual(self.fields, FIELDS)
        self.assertEqual(len(self.rows), 124)
        self.assertEqual(Counter(r["prefecture"] for r in self.rows), COUNTS)
        self.assertEqual({r["source_id"] for r in self.rows}, SOURCE_IDS)
        self.assertEqual(Counter(r["evidence_scope"] for r in self.rows),
                         {"named_river": 80, "named_river_context": 35, "watershed_only": 9})

    def test_no_duplicates_or_empty_facts(self):
        seen = set()
        for row in self.rows:
            key = (row["prefecture"], row["watershed"], row["river"],
                   row["recorded_name"], row["source_id"])
            self.assertNotIn(key, seen, key)
            seen.add(key)
            for field in ("prefecture", "watershed", "recorded_name",
                          "source_id", "source_locator", "source_url"):
                self.assertTrue(row[field].strip(), (field, key))
            self.assertTrue(urlparse(row["source_url"]).scheme == "https")

    def test_watershed_only_never_claims_river(self):
        for row in self.rows:
            self.assertIn(row["evidence_scope"], SCOPES)
            self.assertEqual(bool(row["river"]), row["evidence_scope"] != "watershed_only")
            if row["source_id"] == "YA04":
                self.assertEqual(row["evidence_scope"], "watershed_only")
            if row["source_id"] == "YA07" and row["watershed"] == "長沢川":
                self.assertEqual(row["evidence_scope"], "watershed_only")

    def test_survey_year_only_when_stated(self):
        for row in self.rows:
            if row["survey_year"]:
                self.assertEqual(row["source_id"], "YA07")
                self.assertIn((row["river"], row["survey_year"]),
                              {("小島川", "2005"), ("", "2007")})
            elif row["source_id"] == "YA07":
                self.fail("YA07 report must preserve explicit observation year")

    def test_publication_and_provenance_gates(self):
        for row in self.rows:
            self.assertEqual(row["integration_status"], "staged_only")
            self.assertEqual(row["verification_status"],
                             "search_excerpt_only" if row["source_id"] in ("YA04", "YA07")
                             else "source_text_checked")
            self.assertEqual(row["conservation_review"],
                             "required" if row["recorded_name"] in
                             ("アカザ", "スイゲンゼニタナゴ", "シロヒレタビラ",
                              "ミナミメダカ", "ホンモロコ", "カネヒラ") else "not_flagged")

    def test_no_sensitive_location_columns(self):
        for field in self.fields:
            self.assertNotIn(field.lower(), {"latitude", "longitude", "lat", "lon",
                                             "coordinates", "station", "gps",
                                             "address", "site_location"})

    def test_critical_fish_examples(self):
        records = {(r["prefecture"], r["watershed"], r["river"], r["recorded_name"])
                   for r in self.rows}
        for case in [
            ("島根県", "斐伊川", "三刀屋川", "タカハヤ"),
            ("島根県", "斐伊川", "深野川", "タカハヤ"),
            ("広島県", "八幡川", "八幡川", "アマゴ"),
            ("岡山県", "笹ヶ瀬川", "笹ヶ瀬川", "ギギ"),
            ("鳥取県", "日野川", "大川", "ドンコ"),
            ("山口県", "佐波川", "小島川", "ヌマムツ"),
            ("山口県", "長沢川", "", "ヌマムツ"),
        ]:
            self.assertIn(case, records)
        self.assertNotIn(("広島県", "八幡川", "八幡川", "アユ"), records)

if __name__ == "__main__":
    unittest.main()
