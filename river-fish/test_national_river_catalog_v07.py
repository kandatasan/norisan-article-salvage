"""Real-data national river-code SQLite and fish non-attribution tests."""
import tempfile
from pathlib import Path
import unittest

from national_river_catalog_v07 import build_catalog,search

class RealNationalRiverCatalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.db=Path(cls.tmp.name)/"national.sqlite"
        cls.stats=build_catalog(cls.db)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_35000_official_river_id_count(self):
        self.assertEqual(self.stats["river_code_rows"],35449)
        self.assertEqual(self.stats["watershed_code_rows"],5475)

    def test_local_evidence_not_prematurely_confirmed(self):
        self.assertEqual(self.stats["local_evidence_unmatched"],66)
        self.assertEqual(self.stats["official_codes_approved_for_hiroshima_local_evidence"],0)

    def test_exact_moroki_code(self):
        r=search(self.db,river_code="8707090023")
        self.assertEqual(r["total_code_records"],1)
        record=r["rivers"][0]
        self.assertEqual(record["river_name"],"諸木川")
        self.assertEqual(record["watershed_code"],"870709")
        self.assertEqual(record["watershed_name"],"太田川")
        self.assertEqual(record["code_region_prefix"],"87")
        self.assertIsNone(record["prefecture_of_location"])
        self.assertIsNone(record["direct_parent_river"])
        self.assertIsNone(record["river_fish_occurrences"])
        self.assertEqual(len(record["potential_local_evidence_matches_unapproved"]),1)

    def test_same_name_same_watershed_different_river_codes(self):
        r=search(self.db,name="八幡川",watershed="太田川",limit=30)
        ids={x["river_code"] for x in r["rivers"]}
        self.assertIn("8707090003",ids)
        self.assertIn("8707090015",ids)

    def test_name_search_doesnt_merge_different_codes(self):
        r=search(self.db,name="諸木川")
        self.assertGreaterEqual(r["total_code_records"],1)

    def test_code_prefix_not_a_true_prefecture(self):
        r=search(self.db,code_prefix="87",limit=2)
        self.assertGreater(r["total_code_records"],100)
        self.assertTrue(all(x["prefecture_of_location"] is None for x in r["rivers"]))

    def test_pagination(self):
        a=search(self.db,name="川",limit=2)
        b=search(self.db,name="川",limit=2,offset=2)
        self.assertGreater(a["total_code_records"],100)
        self.assertNotEqual(a["rivers"][0]["river_code"],b["rivers"][0]["river_code"])

    def test_reject_invalid_prefix(self):
        with self.assertRaises(ValueError):
            search(self.db,code_prefix="広島")

    def test_no_species_assigned(self):
        r=search(self.db,name="太田川")
        self.assertTrue(all(x["river_fish_occurrences"] is None for x in r["rivers"]))

    def test_not_overwrite(self):
        with self.assertRaises(FileExistsError):
            build_catalog(self.db)

if __name__=="__main__":
    unittest.main()
