from __future__ import annotations

import unittest

from audit_chugoku_remaining_six_identity_v01 import EXPECTED, load, render
from audit_chugoku_seven_river_identity_v01 import load as load_priority_identity


class ChugokuRemainingSixIdentityTests(unittest.TestCase):
    def test_six_groups_are_covered_and_six_codes_confirmed(self):
        rows = load()
        self.assertEqual(len(rows), 6)
        self.assertEqual({(r["prefecture"], r["watershed"], r["river"]) for r in rows}, set(EXPECTED))
        self.assertEqual(sum(bool(r["confirmed_river_code"]) for r in rows), 6)

    def test_combined_identity_ledgers_cover_all_thirteen_groups(self):
        priority = load_priority_identity()
        remaining = load()
        all_groups = {
            (r["prefecture_source_publisher"], r["watershed"], r["river"])
            for r in priority
        } | {(r["prefecture"], r["watershed"], r["river"]) for r in remaining}
        self.assertEqual(len(all_groups), 13)
        self.assertEqual(sum(bool(r["confirmed_river_code"]) for r in remaining)
                         + len(priority), 13)

    def test_akagawa_duplicate_names_resolved_by_relation_not_name_only(self):
        rows = load()
        akagawa = next(r for r in rows if r["river"] == "赤川")
        self.assertEqual(akagawa["river_code_candidates"], "8707040048;8707040161;8707040248")
        self.assertEqual(akagawa["confirmed_river_code"], "8707040161")
        self.assertIn("斐伊川合流点", akagawa["identity_basis"])
        self.assertIn("次数2・1・4", akagawa["identity_basis"])

    def test_yamaguchi_code_identity_is_separate_from_page_checked_fish_evidence(self):
        rows = load()
        kojima = next(r for r in rows if r["river"] == "小島川")
        self.assertEqual(kojima["river_code_candidates"], "8707070003")
        self.assertEqual(kojima["confirmed_river_code"], "8707070003")
        self.assertEqual(kojima["identity_status"], "official_system_identity_confirmed")
        self.assertIn("次数2", kojima["identity_basis"])
        self.assertIn("模式図", kojima["topology_source_locator"])
        self.assertEqual(kojima["fish_source_verification"], "source_text_checked")
        self.assertEqual(kojima["fish_publication_approval"], "not_approved")

    def test_yamaguchi_report_locator_records_page_and_station_limit(self):
        rows = load()
        kojima = next(r for r in rows if r["river"] == "小島川")
        self.assertIn("PDF p.50", kojima["local_source_locator"])
        self.assertIn("採集地点・調査範囲は未確認", kojima["local_source_locator"])
        self.assertIn("p.50", kojima["identity_basis"])
        self.assertEqual(kojima["survey_year_status"],
                         "reported_2005_explicit_in_pdf_p50_station_extent_unverified")
        self.assertEqual(kojima["fish_publication_approval"], "not_approved")

    def test_all_topology_sources_are_primary_and_fish_scope_stays_unapproved(self):
        rows = load()
        self.assertTrue(all(r["topology_source_url"].startswith("https://www.") for r in rows))
        self.assertTrue(all(r["topology_source_locator"] for r in rows))
        self.assertTrue(all(r["fish_publication_approval"] == "not_approved" for r in rows))

    def test_no_fish_record_is_approved_and_watershed_only_rows_stay_unlinked(self):
        rows = load()
        self.assertTrue(all(r["fish_publication_approval"] == "not_approved" for r in rows))
        self.assertTrue(all(r["river"] for r in rows))

    def test_report_states_the_boundary_without_rendering_fish_names(self):
        report = render(load())
        self.assertIn("研究専用", report)
        self.assertIn("魚記録は全件未承認", report)
        self.assertIn("照合判断（推定）", report)
        self.assertIn("13群のうち13群", report)
        self.assertIn("個体の採集地点・調査区間は確認できていない", report)
        self.assertNotIn("カワムツ", report)
        self.assertNotIn("アカザ", report)


if __name__ == "__main__":
    unittest.main()
