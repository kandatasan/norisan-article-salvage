"""Test 12 recent prefectural document mentions without geographic overreach."""
import sqlite3
import tempfile
from pathlib import Path
import unittest
from municipality_sources_v09 import build,search,evidence

class MunicipalitySourceEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.db=Path(cls.tmp.name)/"evidence.sqlite"
        cls.summary=build(cls.db)
    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_all_ten_hist_codes_and_twelve_municipality_mentions(self):
        self.assertEqual(len(evidence()),12)
        self.assertEqual(self.summary["historical_code_name_watershed_crosschecks"],10)
        self.assertEqual(self.summary["newer_prefectural_document_municipality_mentions"],12)
        self.assertEqual(self.summary["historically_crosschecked_rivers_with_additional_municipal_evidence"],10)

    def test_moroki_city_evidence_without_fish_claim(self):
        r=search(self.db,"諸木川")
        self.assertEqual(r["total"],1)
        river=r["historical_ledger_matches"][0]
        self.assertEqual(river["river_code"],"8707090023")
        self.assertEqual(len(river["municipalities_in_newer_prefectural_document"]),1)
        self.assertEqual(river["municipalities_in_newer_prefectural_document"][0]["municipality_in_document"],"広島市")
        self.assertFalse(river["complete_river_course_verified"])
        self.assertIsNone(river["individual_river_fish_evidence"])

    def test_two_cities_for_sekigawa(self):
        river=search(self.db,"関川")["historical_ledger_matches"][0]
        self.assertEqual({x["municipality_in_document"] for x in river["municipalities_in_newer_prefectural_document"]},{"広島市","東広島市"})

    def test_two_cities_for_kyobashigawa(self):
        river=search(self.db,"京橋川")["historical_ledger_matches"][0]
        self.assertEqual({x["municipality_in_document"] for x in river["municipalities_in_newer_prefectural_document"]},{"広島市","府中町"})

    def test_fuchu_ogawa_camera_is_not_flood_designation(self):
        river=search(self.db,"府中大川")["historical_ledger_matches"][0]
        m=river["municipalities_in_newer_prefectural_document"][0]
        self.assertEqual(m["source_listing_type"],"prefectural_river_camera_municipality")
        self.assertIsNone(m["designation_date"])
        self.assertEqual(m["pdf_page"],"33")

    def test_no_unknown_code_or_2026_species_claim(self):
        conn=sqlite3.connect(self.db)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM municipal_document_evidence").fetchone()[0],12)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM identity_candidates WHERE identity_approved!='false'").fetchone()[0],0)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM narrative_fish_mentions WHERE national_river_code!=''").fetchone()[0],0)
        self.assertEqual(len(conn.execute("PRAGMA foreign_key_check").fetchall()),0)
        conn.close()

    def test_no_overwrite(self):
        with self.assertRaises(FileExistsError):build(self.db)

if __name__=="__main__":unittest.main()
