"""Historical 2016 MLIT river-code evidence must not approve current locations or fish."""
import csv
from pathlib import Path
import sqlite3
import tempfile
import unittest

from historical_ledger_crosscheck_v09 import (
    build,search,load_historical_rows,audit_v08_candidates,LEDGER_URL
)

class HistoricalRiverEvidenceV09(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.db=Path(cls.temp.name)/"ledger.sqlite"
        cls.stats=build(cls.db)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_ten_2016_ledger_rows(self):
        rows=load_historical_rows()
        self.assertEqual(len(rows),10)
        self.assertEqual(len({r["national_river_code"] for r in rows}),10)
        self.assertTrue(all(r["ledger_source_url"]==LEDGER_URL for r in rows))

    def test_moroki_is_a_source_checked_historical_id(self):
        result=search(self.db,name="諸木川")
        self.assertEqual(result["total"],1)
        r=result["historical_ledger_matches"][0]
        self.assertEqual(r["river_code"],"8707090023")
        self.assertEqual(r["watershed_name"],"太田川")
        self.assertEqual(r["ledger_administrator_2016"],"広島県")
        self.assertEqual(r["reviewed_ledger_scope"],"historical_code_and_watershed_crosschecked")

    def test_no_present_day_location_claim(self):
        for r in search(self.db)["historical_ledger_matches"]:
            self.assertFalse(r["present_day_prefecture_location_verified"])
            self.assertFalse(r["approved_current_local_to_code_link"])

    def test_no_individual_river_fish_assigned(self):
        for r in search(self.db)["historical_ledger_matches"]:
            self.assertIsNone(r["fish_observed_in_individual_river"])
            self.assertEqual(r["direct_river_fish_status"],"not_assigned")

    def test_ten_foreign_key_linked_candidates(self):
        conn=sqlite3.connect(self.db)
        conn.row_factory=sqlite3.Row
        self.assertTrue(audit_v08_candidates(load_historical_rows(),conn))
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM official_historical_code_crosschecks").fetchone()[0],10)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM official_historical_code_crosschecks h JOIN identity_candidates c ON h.local_id=c.local_id AND h.river_code=c.code_candidate").fetchone()[0],10)
        self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0],"ok")
        self.assertEqual(len(conn.execute("PRAGMA foreign_key_check").fetchall()),0)
        conn.close()

    def test_does_not_modify_164_source_candidate_approvals(self):
        self.assertEqual(self.stats["present_day_geo_approvals"],0)
        self.assertEqual(self.stats["direct_fish_records_created"],0)
        self.assertGreater(self.stats["review_candidates_remain_unapproved"],1000)
        conn=sqlite3.connect(self.db)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM identity_candidates WHERE identity_approved!='false'").fetchone()[0],0)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM narrative_fish_mentions WHERE national_river_code!=''").fetchone()[0],0)
        conn.close()

    def test_ledger_is_historical_not_2026(self):
        rows=load_historical_rows()
        self.assertTrue(all(x["ledger_as_of"]=="2016-12" for x in rows))
        self.assertTrue(all(x["current_geography_status"]=="present_day_precise_location_unverified" for x in rows))
        self.assertTrue(all(x["website_publication_status"]=="not_published" for x in rows))

    def test_river_code_exact_search(self):
        r=search(self.db,code="8707090036")
        self.assertEqual(r["total"],1)
        self.assertEqual(r["historical_ledger_matches"][0]["river_name"],"関川")

    def test_no_overwrite(self):
        with self.assertRaises(FileExistsError):
            build(self.db)

if __name__=="__main__":
    unittest.main()
