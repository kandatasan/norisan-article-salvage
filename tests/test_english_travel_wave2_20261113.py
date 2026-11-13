"""Regression for the November 13 eight-article English travel improvement wave."""
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from apply_en_travel_20261113 import _build

CONFIG=ROOT/"editorial"/"english-travel-wave2-20261113"/"config.json"
AFF="https://www.discovercars.com/?a_aid=tsurikue"

class EnglishWave2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_exact_eight_distinct_targets(self):
        targets=self.config["targets"]
        self.assertEqual(len(targets),8)
        self.assertEqual(len({x["post_id"] for x in targets}),8)
        self.assertTrue(all(x["status"]=="publish" for x in targets))

    def test_additive_and_safe_article_edits(self):
        for target in self.config["targets"]:
            with self.subTest(target=target["slug"]):
                original=(ROOT/"editorial"/target["slug"]/"content.html").read_text(encoding="utf-8")
                updated=_build(original,target["edits"])
                self.assertEqual(updated.count(target["marker"]),1)
                self.assertEqual(original.count(AFF),updated.count(AFF))
                self.assertEqual(original.count("wp-image-"),updated.count("wp-image-"))
                self.assertEqual(original.count("<img "),updated.count("<img "))
                self.assertEqual(original.count("<!-- wp:heading"),updated.count("<!-- wp:heading"))
                self.assertGreater(len(updated),0)
                with self.assertRaisesRegex(RuntimeError,"ANCHOR_MISMATCH"):
                    _build(updated,target["edits"])

    def test_english_interlinks_are_real_not_future_drafts(self):
        text=CONFIG.read_text(encoding="utf-8")
        self.assertNotIn("/en/sakaiminato-mizuki-road/",text)
        self.assertNotIn("/en/tamatsukuri-onsen-footbath/",text)
        self.assertIn("/en/etajima-island/",text)
        self.assertIn("/en/sera-day-trip/",text)

if __name__=="__main__":
    unittest.main()
