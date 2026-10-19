import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_watershed_switcher_v01 import build
class TestAtlas(unittest.TestCase):
 def test_real_data(self):
  d=build()
  self.assertEqual(len(d["watersheds"]),5475)
  self.assertEqual(d["unmatchedCount"],19)
  self.assertEqual(sum(len(w[2]) for w in d["watersheds"]),35430)
  ota=next(w for w in d["watersheds"] if w[0]=="870709")
  self.assertEqual(len(ota[2]),79)
  self.assertTrue(any(r[0]=="8707090029" and r[1]=="三篠川" for r in ota[2]))
 def test_unique_ids(self):
  d=build()
  codes=[r[0] for w in d["watersheds"] for r in w[2]]
  self.assertEqual(len(codes),len(set(codes)))
if __name__=="__main__":unittest.main()
