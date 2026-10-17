"""Actual nationwide-source regression: 316 official name rows across ten more prefectures."""
import sqlite3
import tempfile
from pathlib import Path
import unittest
from multi_prefecture_registry_v13 import build,query,unified_search,read_source_rows,PREFS,EXPECTED

class SourceBackedTenPrefectures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.db=Path(cls.tmp.name)/"fifteen_pref_sources.sqlite"
        cls.stats=build(cls.db)
    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_all_316_official_mentions_10_new_prefectures(self):
        self.assertEqual(self.stats["source_mentions_added"],316)
        self.assertEqual(self.stats["source_mention_counts_by_prefecture"],EXPECTED)
        self.assertEqual(self.stats["source_types"],{"river":215,"watershed":101})
        self.assertEqual(self.stats["prefectures_with_source_data_after"],15)

    def test_unified_prior_national_data_retained(self):
        self.assertEqual(self.stats["directory_prefectures"],47)
        self.assertEqual(self.stats["national_code_river_name_count"],35449)
        self.assertEqual(self.stats["national_water_system_fish_name_count"],18814)

    def test_shizuoka_71_are_watersheds_not_individual_river_fish(self):
        x=query(self.db,prefecture="静岡県",kind="watershed",limit=100)
        self.assertEqual(x["total_source_mentions"],71)
        self.assertTrue(all(r["evidence_kind"]=="watershed" and
                            r["literal_name"]==r["watershed_in_source"]
                            for r in x["source_mentions"]))

    def test_tone_otagawa_must_not_be_geographical_code_match(self):
        x=unified_search(self.db,prefecture="静岡県",name="太田川")
        self.assertEqual(x["new_prefecture_source_mentions_total"],1)
        self.assertEqual(x["new_prefecture_source_mentions"][0]["evidence_kind"],"watershed")
        self.assertTrue(all(r["prefecture"] is None for r in x["national_code_candidates"]))
        self.assertEqual(x["national_code_to_source_identity_approved"],0)

    def test_miyagi_50_rivers_two_niigawa_same_watershed(self):
        r=query(self.db,prefecture="宮城県",kind="river",limit=100)
        self.assertEqual(r["total_source_mentions"],50)
        s=query(self.db,prefecture="宮城県",name="新川")
        self.assertEqual(s["total_source_mentions"],2)
        self.assertEqual(len({x["evidence_id"] for x in s["source_mentions"]}),2)

    def test_niigata_65_flood_map_labels_not_all_classification(self):
        x=query(self.db,prefecture="新潟県",limit=80)
        self.assertEqual(x["total_source_mentions"],65)
        self.assertTrue(all(r["source_scope"]=="kaetsu_second_class_flood_inundation_map_list_partial" for r in x["source_mentions"]))

    def test_aomori_49_carefully_scoped_names(self):
        x=query(self.db,prefecture="青森県",name="金木川")
        self.assertEqual(x["total_source_mentions"],1)
        self.assertEqual(x["source_mentions"][0]["watershed_in_source"],"岩木川")
        self.assertEqual(query(self.db,prefecture="青森県")["total_source_mentions"],49)

    def test_nagano_city_source_date_separate_from_page_update(self):
        x=query(self.db,prefecture="長野県",name="三念沢")
        self.assertEqual(x["total_source_mentions"],1)
        self.assertEqual(x["source_mentions"][0]["source_as_of"],"2015-03-31")

    def test_fukuoka_city_13_named_second_class_not_all_fukuoka(self):
        x=query(self.db,prefecture="福岡県",limit=30)
        self.assertEqual(x["total_source_mentions"],13)
        self.assertTrue(all(r["source_scope"]=="fukuoka_city_named_second_class_rivers_partial" for r in x["source_mentions"]))

    def test_hokkaido_names_are_basin_plans(self):
        x=query(self.db,prefecture="北海道",kind="watershed")
        self.assertEqual(x["total_source_mentions"],13)
        self.assertTrue(all(r["source_subarea"]=="後志総合振興局" for r in x["source_mentions"]))

    def test_ehime_and_nara_first_class_watersheds(self):
        self.assertEqual(query(self.db,prefecture="奈良県")["total_source_mentions"],4)
        self.assertEqual(query(self.db,prefecture="愛媛県")["total_source_mentions"],5)

    def test_source_only_no_approval(self):
        rows=read_source_rows()
        self.assertEqual(len(rows),316)
        self.assertTrue(all(r["national_river_code_status"]=="not_linked" and
                            r["direct_fish_observation_status"]=="none_from_this_document"
                            for r in rows))
        self.assertEqual(self.stats["new_approved_prefecture_to_10_digit_code_links"],0)
        self.assertEqual(self.stats["new_direct_river_fish_observations"],0)
        self.assertFalse(self.stats["wordpress_updated"])

    def test_all_nationwide_prefectures_not_loaded_are_unknown(self):
        x=unified_search(self.db,prefecture="沖縄県",name="比謝川")
        self.assertEqual(x["new_prefecture_source_mentions_total"],0)
        self.assertIsNone(x["national_river_codes_assigned_to_selected_prefecture"])
        self.assertIn("未収録",x["notice"])

    def test_preserve_hiroshima_tottori_yamaguchi(self):
        self.assertEqual(unified_search(self.db,prefecture="広島県",name="諸木川")["total_source_mentions"],1)
        self.assertGreater(unified_search(self.db,prefecture="鳥取県",name="千代川")["total_source_mentions"],0)
        self.assertEqual(unified_search(self.db,prefecture="山口県",name="三谷川")["total_source_mentions"],2)

    def test_no_inferred_fk_or_fish(self):
        c=sqlite3.connect(self.db)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM verified_watershed_prefecture_links").fetchone()[0],0)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM other_prefecture_official_source_mentions WHERE national_code_status!='not_linked'").fetchone()[0],0)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM other_prefecture_official_source_mentions WHERE direct_fish_status!='none_from_this_document'").fetchone()[0],0)
        self.assertEqual(c.execute("PRAGMA integrity_check").fetchone()[0],"ok")
        self.assertEqual(c.execute("PRAGMA foreign_key_check").fetchall(),[])
        c.close()

    def test_idempotency_refuse_overwrite(self):
        with self.assertRaises(FileExistsError):
            build(self.db)

if __name__=="__main__":unittest.main()
