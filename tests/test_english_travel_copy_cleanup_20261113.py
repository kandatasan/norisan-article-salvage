import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from apply_en_travel_20261113 import _build

class TravelCopyCleanupTests(unittest.TestCase):
    def test_source_grounded_rewrites_preserve_article_assets(self):
        cfg=json.loads((ROOT/"editorial/english-travel-copy-cleanup-20261113/config.json").read_text(encoding="utf-8"))
        self.assertEqual(len(cfg["targets"]),4)
        self.assertEqual({x["post_id"] for x in cfg["targets"]},{4417,4408,4424,4425})
        for target in cfg["targets"]:
            with self.subTest(slug=target["slug"]):
                original=(ROOT/"editorial"/target["slug"]/"content.html").read_text(encoding="utf-8")
                updated=_build(original,target["edits"])
                self.assertEqual(updated.count(target["marker"]),1)
                self.assertEqual(updated.count("wp-image-"),original.count("wp-image-"))
                self.assertEqual(updated.count("discovercars.com"),original.count("discovercars.com"))
                self.assertEqual(updated.count("<!-- wp:heading"),original.count("<!-- wp:heading"))
                self.assertEqual(target["status"],"publish")
        self.assertIn("/en/sera-kogen-farm/",str(cfg))

if __name__ == "__main__":
    unittest.main()
