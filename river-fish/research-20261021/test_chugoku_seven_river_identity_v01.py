import unittest

from audit_chugoku_seven_river_identity_v01 import EXPECTED, load, render


class SevenRiverIdentityAuditTests(unittest.TestCase):
    def test_exact_seven_source_river_groups_are_mapped_once(self):
        rows = load()
        self.assertEqual(len(rows), 7)
        self.assertEqual(
            {(r["prefecture_source_publisher"], r["watershed"], r["river"])
             for r in rows},
            set(EXPECTED),
        )
        self.assertEqual(len({r["river_code"] for r in rows}), 7)

    def test_all_rows_keep_publication_boundary_and_source_scope(self):
        for row in load():
            self.assertEqual(row["identity_status"],
                             "official_system_identity_confirmed")
            self.assertEqual(row["fish_record_approval"], "not_approved")
            self.assertTrue(row["source_locators"].strip())
            self.assertTrue(row["notes"].strip())

    def test_report_states_limitations_and_no_publication(self):
        report = render(load())
        self.assertIn("公開承認は0件", report)
        self.assertIn("GIS形状のダウンロードや市町境界との交差照合は未実施", report)
        self.assertIn("現在の生息", report)
        self.assertIn("8707040211", report)
        self.assertIn("8707030012", report)


if __name__ == "__main__":
    unittest.main()
