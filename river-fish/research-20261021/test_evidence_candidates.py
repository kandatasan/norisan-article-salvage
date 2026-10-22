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
COUNTS = {"島根県": 77, "広島県": 7, "岡山県": 15, "鳥取県": 15, "山口県": 20}
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
        self.assertEqual(len(self.rows), 134)
        self.assertEqual(Counter(r["prefecture"] for r in self.rows), COUNTS)
        self.assertEqual({r["source_id"] for r in self.rows}, SOURCE_IDS)
        self.assertEqual(Counter(r["evidence_scope"] for r in self.rows),
                         {"named_river": 80, "named_river_context": 35, "watershed_only": 19})

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
            self.assertEqual(row["verification_status"], "source_text_checked")
            self.assertEqual(row["conservation_review"],
                             "required" if row["recorded_name"] in
                             ("アカザ", "スイゲンゼニタナゴ", "シロヒレタビラ",
                              "ミナミメダカ", "ホンモロコ", "カネヒラ",
                              "ヤマメ") else "not_flagged")

    def test_yamaguchi_report_page_50_verifies_text_without_expanding_scope(self):
        kojima = next(r for r in self.rows if r["source_id"] == "YA07" and r["river"] == "小島川")
        longsawa = next(r for r in self.rows if r["source_id"] == "YA07" and r["watershed"] == "長沢川")
        self.assertEqual(kojima["verification_status"], "source_text_checked")
        self.assertEqual(kojima["source_locator"], "山口県水産研究センター研究報告第07号 PDF p.50")
        self.assertEqual((kojima["evidence_scope"], kojima["survey_year"]), ("named_river", "2005"))
        self.assertIn("佐波川水系小島川", kojima["notes"])
        self.assertEqual(longsawa["verification_status"], "source_text_checked")
        self.assertEqual(longsawa["source_locator"], kojima["source_locator"])
        self.assertEqual((longsawa["river"], longsawa["evidence_scope"], longsawa["survey_year"]),
                         ("", "watershed_only", "2007"))
        self.assertIn("長沢川水系", longsawa["notes"])
        self.assertEqual(kojima["integration_status"], "staged_only")
        self.assertEqual(longsawa["integration_status"], "staged_only")

    def test_ya04_table_3_is_checked_but_never_expanded_to_named_rivers(self):
        rows = [r for r in self.rows if r["source_id"] == "YA04"]
        self.assertEqual(len(rows), 18)
        self.assertEqual({r["watershed"] for r in rows},
                         {"錦川", "島田川", "佐波川", "椹野川",
                          "厚東川", "厚狭川", "木屋川", "阿武川",
                          "小瀬川", "長沢川", "南若川", "土路石川", "井関川",
                          "真締川", "有帆川", "西田川", "栗野川", "深川川"})
        self.assertTrue(all(
            r["recorded_name"] == "オオクチバス"
            and r["river"] == ""
            and r["evidence_scope"] == "watershed_only"
            and r["verification_status"] == "source_text_checked"
            and r["survey_year"] == ""
            and "PDF p.126" in r["source_locator"]
            and "水系単位" in r["notes"]
            and r["integration_status"] == "staged_only"
            for r in rows
        ))

    def test_environment_nt_yamame_rows_are_held_for_conservation_review(self):
        rows = [r for r in self.rows if r["recorded_name"] == "ヤマメ"]
        self.assertEqual({(r["prefecture"], r["river"], r["source_id"])
                          for r in rows}, {
            ("島根県", "三刀屋川", "SH22"),
            ("島根県", "久野川", "SH22"),
            ("島根県", "阿井川", "SH22"),
        })
        self.assertTrue(all(r["conservation_review"] == "required"
                            and "環NT" in r["notes"] for r in rows))

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
