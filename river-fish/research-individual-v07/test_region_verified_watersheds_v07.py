import unittest
from build_region_verified_watersheds_v07 import (
    REGION_MAJOR_CODE,ROOT,readcsv,SOURCES
)

class RegionCodedWatershedsTest(unittest.TestCase):
    def test_official_supervising_bureau_numbers_are_not_prefectures(self):
        self.assertEqual(REGION_MAJOR_CODE["kanto"],"83")
        self.assertEqual(REGION_MAJOR_CODE["hokuriku"],"84")
        self.assertEqual(REGION_MAJOR_CODE["kinki"],"86")
        self.assertEqual(REGION_MAJOR_CODE["chugoku"],"87")
        self.assertEqual(REGION_MAJOR_CODE["kyushu"],"89")
        self.assertNotEqual(REGION_MAJOR_CODE["kinki"],"26") # Kyoto is NOT an MLIT bureau code

    def test_unique_first_class_code_with_local_name_collision_stays_reviewable(self):
        rows=readcsv(ROOT/"national-codes-staged/watershed_codes_national_v07.csv")
        pairs={(r["watershed_name"],r["watershed_code"]) for r in rows}
        self.assertIn(("大野川","890918"),pairs)  # Oita national first-class
        self.assertIn(("大野川","430024"),pairs)  # Kumamoto separate local name collision
        self.assertIn(("渡川","880803"),pairs)   # Shikoku national first-class
        self.assertIn(("渡川","380023"),pairs)   # Ehime separate local name collision
        self.assertIn(("淀川","860604"),pairs)
        self.assertIn(("淀川","040023"),pairs)

    def test_independent_national_bureau_specification_sources(self):
        self.assertTrue(SOURCES["mlit_2014_code_spec"].startswith("https://www.cgr.mlit.go.jp/"))
        self.assertTrue(SOURCES["mlit_current_6digit_registry"].startswith("https://nlftp.mlit.go.jp/"))

if __name__=="__main__":unittest.main()
