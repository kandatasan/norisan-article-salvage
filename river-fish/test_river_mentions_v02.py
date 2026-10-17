import tempfile
import unittest
from pathlib import Path

from river_mentions_v02 import create_catalog, load_mentions, search

class RiverMentions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.db=Path(cls.tmp.name)/"river.sqlite"
        cls.summary=create_catalog(cls.db)
    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_counts_are_mentions_not_rivers(self):
        self.assertEqual(self.summary["canonical_rivers"],66)
        self.assertEqual(self.summary["unresolved_name_mentions"],98)
        self.assertEqual(self.summary["distinct_unresolved_name_labels"],90)

    def test_small_mihara_river(self):
        x=search(self.db,name="駒月川",municipality="三原市")
        self.assertEqual(x["mention_total"],1)
        r=x["unresolved_mentions"][0]
        self.assertEqual(r["class_as_written_in_source"],"二級河川")
        self.assertIsNone(r["watershed"])
        self.assertIsNone(r["fish_occurrences_for_this_river"])

    def test_moroki_canonical_unchanged(self):
        x=search(self.db,name="諸木川")
        self.assertEqual(x["canonical_total"],1)
        self.assertEqual(x["mention_total"],0)
        self.assertEqual(x["canonical_rivers"][0]["direct_species_records"],0)

    def test_same_name_does_not_merge_rivers(self):
        x=search(self.db,name="大谷川")
        self.assertEqual(x["canonical_total"],2)
        self.assertEqual(x["mention_total"],2)
        self.assertTrue(all(not t["possible_matches_are_verified"] for t in x["unresolved_mentions"]))
        self.assertTrue(all(t["direct_parent"] is None for t in x["unresolved_mentions"]))

    def test_hiroshima_five_quasi_rivers(self):
        x=search(self.db,municipality="広島市",kind="準用河川")
        self.assertEqual(x["mention_total"],5)
        self.assertEqual({m["river_name"] for m in x["unresolved_mentions"]},
                         {"堀川","寺山川","岩上川","榎山川","中道川"})

    def test_city_ordinary_two_examples(self):
        x=search(self.db,municipality="広島市",kind="普通河川")
        self.assertEqual(x["mention_total"],2)
        self.assertEqual({m["river_name"] for m in x["unresolved_mentions"]},
                         {"青原川","大槌川"})

    def test_sera_small_river(self):
        x=search(self.db,name="黒羽田川",municipality="世羅町")
        self.assertEqual(x["mention_total"],1)
        self.assertEqual(x["unresolved_mentions"][0]["class_as_written_in_source"],"一級河川")

    def test_no_inferred_watersheds_or_species(self):
        x=search(self.db,limit=200)
        self.assertEqual(x["mention_total"],98)
        self.assertTrue(all(m["watershed"] is None for m in x["unresolved_mentions"]))
        self.assertTrue(all(m["fish_occurrences_for_this_river"] is None for m in x["unresolved_mentions"]))

    def test_source_host_and_status(self):
        rows=load_mentions()
        self.assertEqual(len(rows),98)
        self.assertTrue(all(r["public_site_status"]=="research_only" for r in rows))
        self.assertTrue(all(r["canonical_review_status"]=="awaiting_identity_review" for r in rows))

    def test_invalid_kind_does_not_silently_match(self):
        with self.assertRaises(ValueError):
            search(self.db,kind="海水魚")

    def test_one_river_can_appear_in_two_municipality_mentions(self):
        x=search(self.db,name="御調川")
        self.assertEqual(x["mention_total"],2)
        self.assertEqual({r["municipality_from_listing"] for r in x["unresolved_mentions"]},{"尾道市","三原市"})

if __name__=="__main__":
    unittest.main()
