"""Chugoku five-prefecture official source compilation quality gates."""
import sqlite3
import tempfile
from pathlib import Path
import unittest
from chugoku_registry_v10 import build, search, load_sources

class ChugokuFivePrefectures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.db=Path(cls.tmp.name)/"chugoku.sqlite"
        cls.summary=build(cls.db)
    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_actual_five_prefecture_counts(self):
        s=self.summary
        self.assertEqual(s["prefecture_keys"],47)
        self.assertEqual(s["chugoku_prefecture_watershed_mentions"],77)
        self.assertEqual(s["new_watershed_source_mentions"],62)
        self.assertEqual(s["new_yamaguchi_river_municipality_mentions"],81)
        self.assertEqual(s["by_prefecture"],{"広島県":15,"岡山県":22,"山口県":26,"島根県":7,"鳥取県":7})

    def test_existing_hiroshima_retained(self):
        self.assertEqual(self.summary["existing_hiroshima_verified_rivers"],66)
        self.assertEqual(self.summary["existing_hiroshima_unreviewed_mentions"],98)

    def test_tottori_seven_systems(self):
        x=search(self.db,prefecture="鳥取県")
        self.assertEqual(x["watershed_source_mentions_total"],7)
        self.assertIn("蒲生川",{r["watershed_label"] for r in x["watershed_mentions"]})
        self.assertTrue(all(r["classification_as_published"]=="二級水系" for r in x["watershed_mentions"]))

    def test_okayama_all_22_only_its_official_table(self):
        x=search(self.db,prefecture="岡山県",limit=50)
        self.assertEqual(x["watershed_source_mentions_total"],22)
        self.assertIn("笹ヶ瀬川",{r["watershed_label"] for r in x["watershed_mentions"]})

    def test_yamaguchi_selected_26_of_106_not_every_river(self):
        x=search(self.db,prefecture="山口県",limit=100)
        self.assertEqual(x["watershed_source_mentions_total"],26)
        self.assertTrue(all("selected_26" in r["scope"] for r in x["watershed_mentions"]))
        self.assertIn("平田川(岩国)",{r["watershed_label"] for r in x["watershed_mentions"]})

    def test_shimane_seven_plans_not_all_second_rivers(self):
        x=search(self.db,prefecture="島根県",limit=100)
        self.assertEqual(x["watershed_source_mentions_total"],7)
        self.assertIn("美田川",{r["watershed_label"] for r in x["watershed_mentions"]})

    def test_yamaguchi_81_municipality_mentions(self):
        x=search(self.db,prefecture="山口県",limit=100)
        self.assertEqual(x["river_municipality_source_mentions_total"],81)

    def test_same_saba_mitani_in_two_cities_are_separate(self):
        x=search(self.db,prefecture="山口県",watershed="佐波川",river="三谷川")
        self.assertEqual(x["river_municipality_source_mentions_total"],2)
        self.assertEqual({r["municipality_in_source"] for r in x["river_mentions"]},{"山口市","防府市"})
        self.assertTrue(all(r["river_code"] is None for r in x["river_mentions"]))

    def test_small_yamaguchi_stream(self):
        x=search(self.db,prefecture="山口県",watershed="小瀬川",river="駒ヶ迫川")
        self.assertEqual(x["river_municipality_source_mentions_total"],1)
        self.assertEqual(x["river_mentions"][0]["municipality_in_source"],"和木町")

    def test_nishiki_names_are_not_deduced_fish_occurrences(self):
        x=search(self.db,prefecture="山口県",watershed="錦川",limit=100)
        self.assertEqual(x["river_municipality_source_mentions_total"],40)
        self.assertTrue(all(r["species_status"]=="not_examined" for r in x["river_mentions"]))
        self.assertTrue(all(r["river_code"] is None for r in x["river_mentions"]))

    def test_no_automatic_prefecture_code_or_fish_assignments(self):
        c=sqlite3.connect(self.db)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM municipality_river_source_mentions WHERE river_code IS NOT NULL").fetchone()[0],0)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM verified_watershed_prefecture_links").fetchone()[0],0)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM prefecture_watershed_source_mentions WHERE code_identity_status!='unlinked'").fetchone()[0],0)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM municipality_river_source_mentions WHERE species_status!='not_examined'").fetchone()[0],0)
        self.assertEqual(c.execute("PRAGMA integrity_check").fetchone()[0],"ok")
        c.close()

    def test_reject_duplicate_db_overwrite(self):
        with self.assertRaises(FileExistsError):build(self.db)

    def test_reject_invalid_pagination(self):
        with self.assertRaises(ValueError):search(self.db,limit=0)

    def test_source_narrow_scope_unchanged(self):
        a,b=load_sources()
        self.assertEqual(len(a),62);self.assertEqual(len(b),81)
        self.assertTrue(all(x["site_status"]=="research_only" for x in a))
        self.assertTrue(all(x["public_website_status"]=="research_only" for x in b))

if __name__=="__main__":unittest.main()
