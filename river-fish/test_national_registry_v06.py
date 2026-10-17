"""Offline national registry crosswalk safeguard tests."""
import tempfile
from pathlib import Path
import unittest
from national_registry_v06 import build,coverage

class NationalRiverRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.db=Path(cls.tmp.name)/"national.sqlite"
        cls.stats=build(cls.db)
    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_47_prefecture_keys_and_9_source_regions(self):
        self.assertEqual(self.stats["prefectures"],47)
        self.assertEqual(self.stats["national_fish_source_regions"],9)

    def test_legacy_region_rivers_not_lost(self):
        self.assertEqual(self.stats["existing_verified_river_names"],66)
        self.assertEqual(self.stats["additional_unreviewed_river_mentions"],98)

    def test_no_fake_national_rivers(self):
        tokyo=coverage(self.db,"東京都")["prefecture_records"][0]
        self.assertEqual(tokyo["verified_river_count"],0)
        self.assertEqual(tokyo["unreviewed_name_mentions"],0)
        self.assertIsNone(tokyo["total_rivers_in_prefecture"])
        self.assertIsNone(tokyo["national_fish_survey_prefecture_records"])

    def test_hiroshima_kept(self):
        h=coverage(self.db,"広島県")["prefecture_records"][0]
        self.assertEqual(h["verified_river_count"],66)
        self.assertEqual(h["unreviewed_name_mentions"],98)

    def test_no_derived_crosswalk(self):
        self.assertEqual(self.stats["verified_prefecture_watershed_species_crosswalk_rows"],0)
        self.assertFalse(self.stats["web_deployed"])

    def test_all_prefectures(self):
        self.assertEqual(len(coverage(self.db)["prefecture_records"]),47)

    def test_refuse_db_overwrite(self):
        with self.assertRaises(FileExistsError):
            build(self.db)

if __name__=="__main__":
    unittest.main()
