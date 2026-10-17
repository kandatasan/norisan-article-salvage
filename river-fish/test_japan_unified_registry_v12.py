"""Nationwide v1.2: actual 47-prefecture shell, 35k code names, 18k fish census."""
import sqlite3
from pathlib import Path
import tempfile
import unittest
from japan_unified_registry_v12 import build,search,fish_context

class UnifiedNationwideResearchV12(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.db=Path(cls.tmp.name)/"unified.sqlite"
        cls.stats=build(cls.db)
    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_actual_existing_national_counts(self):
        self.assertEqual(self.stats["prefecture_directory"],47)
        self.assertEqual(self.stats["nationwide_official_river_code_names"],35449)
        self.assertEqual(self.stats["nationwide_census_watershed_year_fish_name_records"],18814)

    def test_all_local_sources_preserved_without_dedup_by_name(self):
        s=self.stats
        self.assertEqual(s["hiroshima_local_river_register"],66)
        self.assertEqual(s["hiroshima_unreviewed_river_mentions"],98)
        self.assertEqual(s["yamaguchi_river_municipality_mentions"],81)
        self.assertEqual(s["tottori_pdf_river_mentions"],377)
        self.assertEqual(s["chugoku_5pref_watershed_mentions"],87)

    def test_no_invented_42_prefecture_rivers(self):
        tokyo=search(self.db,prefecture="東京都",name="川")
        self.assertEqual(tokyo["total_source_mentions"],0)
        self.assertEqual(tokyo["prefecture_local_river_source_status"],"no_local_river_source_loaded")
        self.assertEqual(tokyo["national_river_codes_assigned_to_selected_prefecture"],None)
        self.assertGreater(tokyo["national_name_code_candidates_total"],1000)
        self.assertTrue(all(r["prefecture"] is None for r in tokyo["national_code_candidates"]))

    def test_source_prefecture_with_no_river_list_is_accurate(self):
        o=search(self.db,prefecture="岡山県",name="旭川")
        self.assertEqual(o["prefecture_local_river_source_status"],"only_watershed_source_mentions")
        self.assertEqual(o["river_species_confirmed_in_selected_prefecture"],None)

    def test_moroki_national_code_not_location_attributed(self):
        x=search(self.db,prefecture="広島県",name="諸木川")
        self.assertEqual(x["total_source_mentions"],1)
        self.assertTrue(any(t["code"]=="8707090023" for t in x["national_code_candidates"]))
        self.assertTrue(all(y["national_river_code"] is None for y in x["source_mentions"]))
        self.assertTrue(all(y["fish_direct_observation"] is None for y in x["source_mentions"]))

    def test_tottori_unreviewed_pdf_source_works(self):
        x=search(self.db,prefecture="鳥取県",name="千代川",limit=30)
        self.assertGreater(x["total_source_mentions"],0)
        self.assertTrue(all(row["evidence_scope"].startswith("tottori_2023_pdf") for row in x["source_mentions"]))
        self.assertTrue(all(row["fish_direct_observation"] is None for row in x["source_mentions"]))
        self.assertTrue(all(row["national_river_code"] is None for row in x["source_mentions"]))

    def test_yamaguchi_same_name_two_municipalities_kept(self):
        x=search(self.db,prefecture="山口県",name="三谷川")
        self.assertEqual(x["total_source_mentions"],2)
        self.assertEqual({y["municipality_in_source"] for y in x["source_mentions"]},{"山口市","防府市"})

    def test_global_lookup_returns_official_codes_without_prefecture(self):
        x=search(self.db,name="諸木川")
        self.assertTrue(any(y["code"]=="8707090023" for y in x["national_code_candidates"]))
        self.assertTrue(all(y["fish_occurrences_at_this_river"] is None for y in x["national_code_candidates"]))
        self.assertEqual(x["prefectures_in_directory"],47)

    def test_river_name_absence_is_unknown_not_absent(self):
        x=search(self.db,prefecture="沖縄県",name="川")
        self.assertEqual(x["total_source_mentions"],0)
        self.assertIn("未収録",x["notice"])
        self.assertIsNone(x["river_species_confirmed_in_selected_prefecture"])

    def test_fish_context_all_real_regions(self):
        x=fish_context(self.db,name="アユ",limit=5)
        self.assertGreater(x["total"],100)
        self.assertTrue(all(y["prefecture_of_observation"] is None for y in x["records"]))
        self.assertTrue(all(y["specific_river_of_observation"] is None for y in x["records"]))

    def test_fish_context_kyushu_only(self):
        x=fish_context(self.db,region="kyushu",watershed="筑後川",limit=100)
        self.assertGreater(x["total"],0)
        self.assertTrue(all(y["region"]=="kyushu" for y in x["records"]))

    def test_no_prefecture_fk_created_from_census(self):
        c=sqlite3.connect(self.db)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM official_station_localization_evidence").fetchone()[0],0)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM verified_watershed_prefecture_links").fetchone()[0],0)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM national_named_river_codes WHERE prefecture_assignment_status!='not_mapped'").fetchone()[0],0)
        self.assertEqual(c.execute("PRAGMA integrity_check").fetchone()[0],"ok")
        self.assertEqual(c.execute("PRAGMA foreign_key_check").fetchall(),[])
        c.close()

    def test_invalid_prefecture_rejected(self):
        with self.assertRaises(ValueError):
            search(self.db,prefecture="海外")
    def test_reject_bad_context_region(self):
        with self.assertRaises(ValueError):
            fish_context(self.db,region="okinawa")

    def test_build_not_overwrite(self):
        with self.assertRaises(FileExistsError):build(self.db)

if __name__=="__main__":unittest.main()
