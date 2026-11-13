import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from apply_en_travel_20261113 import _build

class OwnerPhotoReturnTests(unittest.TestCase):
    def test_restore_only_two_verified_owner_photos(self):
        cfg=json.loads((ROOT/"editorial/en-rabbit-karato-owner-photos-20261113/config.json").read_text(encoding="utf-8"))
        self.assertEqual({t["post_id"] for t in cfg["targets"]},{4392,4432})
        for t in cfg["targets"]:
            with self.subTest(t=t["slug"]):
                src=(ROOT/"editorial"/t["slug"]/"content.html").read_text(encoding="utf-8")
                out=_build(src,t["edits"])
                self.assertEqual(out.count(t["marker"]),1)
                self.assertEqual(out.count("wp-image-")-src.count("wp-image-"),1)
                self.assertEqual(out.count("discovercars.com"),src.count("discovercars.com"))
                self.assertEqual(out.count("<!-- wp:heading"),src.count("<!-- wp:heading"))
                self.assertEqual(t["status"],"publish")
                self.assertEqual(len(t["expected_media"]),1)
        k=next(t for t in cfg["targets"] if t["post_id"]==4432)
        self.assertIn("not Karato Market",k["edits"][0]["fragment"])

if __name__=="__main__":
    unittest.main()
