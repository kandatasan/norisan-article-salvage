import unittest
import csv
from pathlib import Path

from build_chugoku_seven_river_fish_crosswalk_v01 import (
    OUTPUT_FIELDS_EXTRA,
    build,
)

ROOT = Path(__file__).resolve().parent
STAGED = ROOT.parent / "review-staged" / "chugoku_seven_river_fish_records_identity_v01.csv"


class SevenRiverFishCrosswalkTests(unittest.TestCase):
    def test_only_seventy_six_nonflagged_source_rows_are_enriched(self):
        rows, fields = build()
        self.assertEqual(len(rows), 76)
        self.assertIn("river_code", fields)
        self.assertIn("fish_publication_approval", fields)
        self.assertEqual(fields[-len(OUTPUT_FIELDS_EXTRA):], OUTPUT_FIELDS_EXTRA)
        self.assertEqual(len({r["river_code"] for r in rows}), 7)

    def test_source_scope_and_publication_gate_are_preserved(self):
        rows, _ = build()
        scope_counts = {}
        for r in rows:
            scope_counts[r["evidence_scope"]] = scope_counts.get(r["evidence_scope"], 0) + 1
        self.assertEqual(scope_counts, {"named_river": 61, "named_river_context": 15})
        self.assertTrue(all(r["evidence_scope"] == ("named_river" if r["prefecture"] == "島根県" else "named_river_context") for r in rows))
        self.assertEqual(sum(r["verification_status"] == "official_pdf_table_image_checked"
                             for r in rows), 61)
        self.assertEqual(sum(r["verification_status"] == "source_text_checked"
                             for r in rows), 15)
        for row in rows:
            self.assertEqual(row["survey_year"], "")
            self.assertEqual(row["survey_year_status"],
                             "not_reported_per_species_in_source")
            if row["source_id"] == "SH22":
                self.assertEqual(row["source_document_date"], "2022-03")
                self.assertEqual(row["source_document_title"],
                                 "斐伊川水系中流支川域河川整備計画【第1回変更】付属資料")
                self.assertIn("PDF p.21/81", row["source_locator"])
            else:
                self.assertEqual(row["source_document_date"], "2016-01")
                self.assertEqual(row["source_document_title"],
                                 "日野川水系（指定区間）河川整備計画")
        self.assertTrue(all(r["conservation_review"] == "not_flagged"
                            for r in rows))
        self.assertTrue(all(r["integration_status"] == "staged_only"
                            for r in rows))
        self.assertTrue(all(r["fish_publication_approval"] == "not_approved"
                            for r in rows))
        self.assertNotIn("ヤマメ", {r["recorded_name"] for r in rows})

    def test_only_three_environment_nt_yamame_rows_are_withheld(self):
        candidates = ROOT / "fish_river_evidence_candidates_20261021.csv"
        with candidates.open(encoding="utf-8-sig", newline="") as f:
            source_rows = list(csv.DictReader(f))
        flagged = [r for r in source_rows if r["recorded_name"] == "ヤマメ"]
        self.assertEqual({(r["river"], r["source_id"]) for r in flagged},
                         {("三刀屋川", "SH22"), ("久野川", "SH22"), ("阿井川", "SH22")})
        self.assertTrue(all(r["conservation_review"] == "required"
                            and "環NT" in r["notes"] for r in flagged))

    def test_code_mappings_match_the_seven_identity_audit_groups(self):
        rows, _ = build()
        pairs = {(r["watershed"], r["river"], r["river_code"])
                 for r in rows}
        self.assertEqual(len(pairs), 7)
        self.assertIn(("斐伊川", "深野川", "8707040211"), pairs)
        self.assertIn(("日野川", "大川", "8707030012"), pairs)

    def test_staged_crosswalk_is_reproducible_from_the_builder(self):
        rows, fields = build()
        with STAGED.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            self.assertEqual(tuple(reader.fieldnames or ()), fields)
            committed = list(reader)
        self.assertEqual(committed, rows)


if __name__ == "__main__":
    unittest.main()
