import unittest
from build_name_first_v05 import identity_key,review_name

class NamedRiverTests(unittest.TestCase):
    def test_identity_preserves_region_and_watershed(self):
        base=identity_key("kyushu","九州地方整備局","筑後川","宝満川")
        self.assertEqual(base,identity_key("kyushu","九州地方整備局","筑後川","宝満川"))
        self.assertNotEqual(base,identity_key("kyushu","九州地方整備局","遠賀川","宝満川"))
        self.assertNotEqual(base,identity_key("tohoku","東北地方整備局","筑後川","宝満川"))
        self.assertEqual(len(base),27)
    def test_no_false_river_for_lake_or_dam(self):
        self.assertEqual(review_name("宍道湖"),"nonriver_waterbody")
        self.assertEqual(review_name("十三湖"),"nonriver_waterbody")
        self.assertEqual(review_name("○○ダム"),"nonriver_waterbody")
    def test_composite_sections_remain_review_only(self):
        self.assertEqual(review_name("信濃川（本川下流）"),"parenthesized_river_section")
        self.assertEqual(review_name("○○川・△△川"),"composite_river_label")
        self.assertEqual(review_name("○○川流域"),"general_or_nonriver_label")
    def test_normal_named_rivers_accepted(self):
        self.assertIsNone(review_name("宝満川"))
        self.assertIsNone(review_name("三篠川"))
        self.assertIsNone(review_name("中津川"))
        self.assertIsNone(review_name("本明川"))
if __name__=="__main__":
    unittest.main()
