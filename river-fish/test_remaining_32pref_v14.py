"""Integration tests for all 47 prefectures with source-limited research coverage."""
import sqlite3
import tempfile
from pathlib import Path
import unittest

from remaining_prefecture_registry_v14 import build,source_search,unified_search,read_sources

class NationwideSourceCoverageV14(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.db=Path(cls.tmp.name)/"47-pref.sqlite"
        cls.stats=build(cls.db)
    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_all_47_prefecture_sources_are_present(self):
        self.assertEqual(self.stats["prefecture_directory"],47)
        self.assertEqual(self.stats["prefecture_source_coverage"],47)
        self.assertFalse(self.stats["all_prefecture_rivers_exhaustively_catalogued"])

    def test_new_32_prefectures_and_439_source_mentions(self):
        rows,manifest=read_sources()
        self.assertEqual(len(rows),439)
        self.assertEqual(manifest["new_prefecture_count"],32)
        self.assertEqual(self.stats["new_source_mentions"],439)
        self.assertEqual(self.stats["new_source_types"],{"river":160,"watershed":269,"planning_region":10})
        self.assertEqual(len(set(r["prefecture"] for r in rows)),32)

    def test_prior_national_counts_still_in_sync(self):
        self.assertEqual(self.stats["old_ten_pref_source_mentions"],316)
        self.assertEqual(self.stats["national_code_name_rows"],35449)
        self.assertEqual(self.stats["national_watershed_year_fish_rows"],18814)

    def test_hokkaido_hiroshima_existing_and_new_stay_separate(self):
        result=unified_search(self.db,prefecture="北海道",name="余市川")
        self.assertEqual(result["remaining_prefecture_official_mentions_total"],0)
        self.assertEqual(result["new_prefecture_source_mentions_total"],1)
        h=unified_search(self.db,prefecture="広島県",name="諸木川")
        self.assertEqual(h["total_source_mentions"],1)
        self.assertEqual(h["remaining_prefecture_official_mentions_total"],0)

    def test_tokyo_67_actual_river_listing_mentions(self):
        data=source_search(self.db,prefecture="東京都",kind="river",limit=100)
        self.assertEqual(data["source_matches_total"],67)
        self.assertTrue(any(x["literal_name"]=="石神井川" for x in data["source_matches"]))
        self.assertTrue(all(x["current_river_code"] is None for x in data["source_matches"]))

    def test_chiba_tone_system_35_names(self):
        data=source_search(self.db,prefecture="千葉県",kind="river",limit=100)
        self.assertEqual(data["source_matches_total"],35)
        self.assertTrue(all(x["explicit_watershed"]=="利根川" for x in data["source_matches"]))

    def test_okinawa_not_zero_just_no_mlit_census(self):
        data=source_search(self.db,prefecture="沖縄県",limit=40)
        self.assertEqual(data["source_matches_total"],17)
        self.assertIn("国場川",{r["literal_name"] for r in data["source_matches"]})
        self.assertEqual(self.stats["direct_tributary_fish_confirmations"],0)
        u=unified_search(self.db,prefecture="沖縄県",name="安里川")
        self.assertGreater(u["remaining_prefecture_official_mentions_total"],0)
        self.assertIsNone(u["river_species_confirmed_in_selected_prefecture"])

    def test_gunma_ten_planning_regions_not_ten_rivers(self):
        records=source_search(self.db,prefecture="群馬県")
        self.assertEqual(records["source_matches_total"],10)
        self.assertEqual(source_search(self.db,prefecture="群馬県",kind="river")["source_matches_total"],0)
        self.assertTrue(all(x["source_label_type"]=="planning_region" for x in records["source_matches"]))

    def test_wakayama_19_second_class_water_basin_names(self):
        data=source_search(self.db,prefecture="和歌山県")
        self.assertEqual(data["source_matches_total"],19)
        self.assertTrue(all(x["source_label_type"]=="watershed" for x in data["source_matches"]))

    def test_kochi_original_kainokawa_literal_is_not_fixed(self):
        data=source_search(self.db,prefecture="高知県",name="貝ノ川")
        self.assertEqual(data["source_matches_total"],1)
        self.assertEqual(data["source_matches"][0]["literal_name"],"貝ノ川川")

    def test_saga_irami_original_source_label_not_silent_fix(self):
        data=source_search(self.db,prefecture="佐賀県",name="伊万里川")
        self.assertEqual(data["source_matches_total"],1)
        self.assertEqual(data["source_matches"][0]["literal_name"],"伊万里川系")

    def test_tokyo_akiba_no_prefecture_assignment_to_official_code(self):
        result=unified_search(self.db,prefecture="東京都",name="神田川",limit=20)
        self.assertEqual(result["remaining_prefecture_official_mentions_total"],1)
        self.assertEqual(result["national_code_to_prefecture_link_approved"],0)
        self.assertTrue(all(r["prefecture"] is None for r in result["national_code_candidates"]))
        self.assertIsNone(result["individual_fish_site_from_this_update"])

    def test_new_32_prefectures_not_exhaustively_complete(self):
        for pref in ("秋田県","福島県","神奈川県","熊本県","沖縄県"):
            r=unified_search(self.db,prefecture=pref)
            self.assertFalse(r["all_47_prefecture_rivers_exhaustively_covered"])
            self.assertTrue(r["all_47_prefectures_have_at_least_one_official_page_source"])
            self.assertGreater(r["remaining_prefecture_official_mentions_total"],0)

    def test_implicit_watershed_not_inferred_for_some_river_mentions(self):
        r=source_search(self.db,prefecture="茨城県",kind="river")
        self.assertEqual(r["source_matches_total"],15)
        self.assertTrue(all(x["explicit_watershed"] is None for x in r["source_matches"]))

    def test_which_prefecture_official_sources_not_fish(self):
        c=sqlite3.connect(self.db)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM new_prefecture_official_mentions WHERE national_river_code IS NOT NULL").fetchone()[0],0)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM new_prefecture_official_mentions WHERE direct_fish_status!='not_observed_in_this_source'").fetchone()[0],0)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM official_station_localization_evidence").fetchone()[0],0)
        self.assertEqual(c.execute("PRAGMA integrity_check").fetchone()[0],"ok")
        self.assertEqual(c.execute("PRAGMA foreign_key_check").fetchall(),[])
        c.close()

    def test_47_sources_are_not_47_complete_coverage(self):
        self.assertEqual(self.stats["code_to_prefecture_identity_links_approved"],0)
        self.assertFalse(self.stats["website_published"])

    def test_known_bad_prefecture_and_label_kind_rejected(self):
        with self.assertRaises(ValueError):source_search(self.db,kind="fish")
        with self.assertRaises(ValueError):source_search(self.db,prefecture="火星県")
        with self.assertRaises(ValueError):unified_search(self.db,prefecture="火星県")

    def test_no_db_overwrite(self):
        with self.assertRaises(FileExistsError):build(self.db)

if __name__=="__main__":
    unittest.main()
