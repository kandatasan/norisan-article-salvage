"""River master search regression: never infer a small river's fish by watershed."""
import csv
import tempfile
import unittest
from pathlib import Path
from river_registry_v01 import (create_database,find_rivers,load_csv,
                                RIVER_FIELDS,RIVER_CSV,ROOT)

class RiverRegister(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.db=Path(cls.temp.name)/"registry.sqlite"
        cls.stats=create_database(cls.db)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_seeded_river_and_watershed_counts(self):
        self.assertEqual(self.stats["rivers"],66)
        self.assertEqual(self.stats["watersheds"],15)
        self.assertEqual(self.stats["official_watershed_year_name_records"],2285)
        self.assertEqual(self.stats["direct_species_evidence"],0)

    def test_moroki_exists_without_direct_fish(self):
        x=find_rivers(self.db,name="諸木川",prefecture="広島県")
        self.assertEqual(x["total_rivers"],1)
        river=x["rivers"][0]
        self.assertEqual(river["watershed"],"太田川")
        self.assertEqual(river["direct_species_records"],0)
        self.assertGreater(river["same_watershed_survey_records_context_only"],0)
        self.assertFalse(river["watershed_context_is_direct_river_evidence"])
        self.assertIsNone(river["parent_river"])

    def test_duplicate_name_across_watersheds_is_not_merged(self):
        x=find_rivers(self.db,name="大谷川")
        self.assertEqual(x["total_rivers"],2)
        self.assertEqual({r["watershed"] for r in x["rivers"]},{"沼田川","大谷川"})

    def test_river_not_fish_occurrence(self):
        x=find_rivers(self.db,watershed="太田川")
        self.assertGreater(x["total_rivers"],5)
        self.assertTrue(all(r["direct_species_records"]==0 for r in x["rivers"]))

    def test_other_prefecture_does_not_inherit_watersheds(self):
        x=find_rivers(self.db,prefecture="岡山県")
        self.assertEqual(x["total_rivers"],0)

    def test_source_not_w05_noncommercial_dataset(self):
        rivers=load_csv(ROOT/RIVER_CSV,RIVER_FIELDS)
        self.assertTrue(all("pref.hiroshima.lg.jp/" in r["source_url"] for r in rivers))
        self.assertTrue(all(r["publication_status"]=="registry_staged" for r in rivers))

    def test_limit_and_kanji_lookup(self):
        x=find_rivers(self.db,name="川",limit=5)
        self.assertGreater(x["total_rivers"],5)
        self.assertEqual(len(x["rivers"]),5)
        self.assertEqual(find_rivers(self.db,municipality="東広島市")["total_rivers"],12)

    def test_no_direct_parent_inferred(self):
        self.assertTrue(all(r["parent_river"] is None for r in find_rivers(self.db,limit=100)["rivers"]))

    def test_reject_unsupported_limit(self):
        with self.assertRaises(ValueError):
            find_rivers(self.db,limit=0)

if __name__=="__main__":
    unittest.main()
