import unittest

from build_chugoku_seven_river_fish_crosswalk_v01 import build


class SevenRiverFishCrosswalkTests(unittest.TestCase):
    def test_only_seventy_nine_eligible_named_river_rows_are_enriched(self):
        rows, fields = build()
        self.assertEqual(len(rows), 79)
        self.assertIn("river_code", fields)
        self.assertIn("fish_publication_approval", fields)
        self.assertEqual(len({r["river_code"] for r in rows}), 7)

    def test_source_scope_and_publication_gate_are_preserved(self):
        rows, _ = build()
        self.assertTrue(all(r["evidence_scope"] == "named_river"
                            for r in rows))
        self.assertTrue(all(r["verification_status"] == "source_text_checked"
                            for r in rows))
        self.assertTrue(all(r["conservation_review"] == "not_flagged"
                            for r in rows))
        self.assertTrue(all(r["integration_status"] == "staged_only"
                            for r in rows))
        self.assertTrue(all(r["fish_publication_approval"] == "not_approved"
                            for r in rows))

    def test_code_mappings_match_the_seven_identity_audit_groups(self):
        rows, _ = build()
        pairs = {(r["watershed"], r["river"], r["river_code"])
                 for r in rows}
        self.assertEqual(len(pairs), 7)
        self.assertIn(("斐伊川", "深野川", "8707040211"), pairs)
        self.assertIn(("日野川", "大川", "8707030012"), pairs)


if __name__ == "__main__":
    unittest.main()
