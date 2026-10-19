import unittest
from pathlib import Path
from build_prefecture_navigation_v06 import load_existing_official_mentions,source_rows,ROOT

class PrefectureDocumentaryCoverage(unittest.TestCase):
    def test_source_evidence_has_only_explicit_water(self):
        rows=load_existing_official_mentions()
        self.assertGreater(len(rows),600)
        for r in rows:
            self.assertTrue(r["prefecture"] and r["watershed"] and r["source_url"].startswith("https://"))
            self.assertIn(r["kind"],("river","watershed"))
            if r["kind"]=="river":self.assertTrue(r["river"])
            else:self.assertFalse(r["river"])
    def test_no_planning_region_mistaken_for_watershed(self):
        rows=load_existing_official_mentions()
        # Tokyo river lists without explicit watershed labels are not promoted.
        self.assertFalse(any(x["source_registry"]=="v14" and x["prefecture"]=="群馬県" for x in rows))
    def test_old_Hiroshima_document_has_direct_river_mentions(self):
        rows=load_existing_official_mentions()
        self.assertTrue(any(x["prefecture"]=="広島県" and x["watershed"]=="太田川" and
                            x["river"]=="山本川" and x["kind"]=="river" and
                            x["source_registry"]=="hiroshima_v01" for x in rows))

if __name__=="__main__":
    unittest.main()
