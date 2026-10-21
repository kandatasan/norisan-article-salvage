import csv
import unittest
from pathlib import Path
from urllib.parse import urlparse

DATA = Path(__file__).resolve().parent / "chugoku_mainstem_source_scope_status_v02.csv"


class ChugokuMainstemSourceScopeStatusTests(unittest.TestCase):
    def setUp(self):
        with DATA.open(encoding="utf-8", newline="") as f:
            self.rows = list(csv.DictReader(f))
        self.by_id = {r["source_id"]: r for r in self.rows}

    def test_all_sources_are_research_only_and_cited_to_official_domains(self):
        self.assertEqual(len(self.rows), 6)
        self.assertEqual(len(self.by_id), len(self.rows))
        for row in self.rows:
            self.assertEqual(row["fish_publication_approval"], "not_approved")
            self.assertEqual(row["integration_status"], "research_only")
            self.assertTrue(row["source_url"])
            host = urlparse(row["source_url"]).hostname or ""
            self.assertTrue(host.endswith(("nilim.go.jp", "cgr.mlit.go.jp")), host)

    def test_hino_2024_and_old_export_years_are_not_conflated(self):
        hino = self.by_id["HINO_ADVISER_2025"]
        self.assertEqual(hino["survey_years"], "1994;1999;2004;2009;2014;2019;2024")
        self.assertIn("75 fish species", hino["confirmed_result"])
        self.assertIn("water-system totals", hino["scope_limit"])
        export = self.by_id["NILIM_B01_HINO"]
        self.assertEqual(export["survey_years"], "2009;2014;2019")
        self.assertIn("literal-name research match only", export["disposition"])

    def test_wrong_waterbody_and_important_species_locations_are_rejected(self):
        excluded = self.by_id["HII_DIVERSION_MONITORING_EXCLUSION"]
        self.assertIn("神戸川", excluded["target_river"])
        self.assertIn("Exclude", excluded["disposition"])
        protected = self.by_id["NILIM_SENSITIVE_SPECIES_RULE"]
        self.assertIn("Do not infer or restore", protected["scope_limit"])

    def test_ocr_candidate_is_not_treated_as_verified_reach(self):
        lead = self.by_id["HINO_RESTORATION_2025"]
        self.assertIn("OCR-derived", lead["scope_limit"])
        self.assertIn("do not map fish records", lead["disposition"])


if __name__ == "__main__":
    unittest.main()
