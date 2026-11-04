import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from apply_editorial_draft_once import build_published_affiliate_copy_replacements

BASE = """<!-- wp:paragraph -->
<p>年式の候補を探してみよう。</p>
<!-- /wp:paragraph -->
<!-- wp:shortcode -->
[blog_parts id="2843"]
<!-- /wp:shortcode -->
<!-- wp:paragraph -->
<p>希望の装備も調べてみよう。</p>
<!-- /wp:paragraph -->
<!-- wp:shortcode -->
[blog_parts id="4172"]
<!-- /wp:shortcode -->"""

EDITS = [
    {"before":"年式の候補を探してみよう。","after":"年式と予算を伝えて探してもらおう。"},
    {"before":"希望の装備も調べてみよう。","after":"欲しい装備を確認してから決めよう。"},
]

def cfg_for(content, edits=EDITS):
    altered = content
    for change in edits:
        altered = altered.replace(change["before"],change["after"],1)
    return {"replacements":edits, "expected_after_sha256":hashlib.sha256(altered.encode()).hexdigest()}

class PublishedAffiliateCopyTests(unittest.TestCase):
    def test_exact_text_only_patch_keeps_existing_blocks_and_ads(self):
        new = build_published_affiliate_copy_replacements(BASE,cfg_for(BASE))
        self.assertEqual(new.count('[blog_parts id="2843"]'),1)
        self.assertEqual(new.count('[blog_parts id="4172"]'),1)
        self.assertEqual(new.count('<!-- wp:paragraph -->'),2)
        self.assertEqual(new.count('<!-- wp:shortcode -->'),2)
        self.assertIn("欲しい装備を確認してから決めよう。",new)
        expected = BASE.replace(EDITS[0]["before"],EDITS[0]["after"]).replace(
            EDITS[1]["before"],EDITS[1]["after"])
        self.assertEqual(new,expected)

    def test_original_phrase_drift_refuses(self):
        with self.assertRaises(RuntimeError):
            build_published_affiliate_copy_replacements(
                BASE.replace(EDITS[0]["before"],"掲載順に探そう。"),cfg_for(BASE))

    def test_duplicate_before_refuses(self):
        with self.assertRaises(RuntimeError):
            build_published_affiliate_copy_replacements(
                BASE + "\n" + EDITS[0]["before"], cfg_for(BASE))

    def test_refuses_markup_changes(self):
        changed=[{"before":"希望の装備も調べてみよう。","after":"<strong>特別な装備</strong>"}]
        with self.assertRaises(RuntimeError):
            build_published_affiliate_copy_replacements(BASE,cfg_for(BASE,changed))

    def test_reviewed_target_hash_required(self):
        cfg=cfg_for(BASE)
        cfg["expected_after_sha256"]="0"*64
        with self.assertRaises(RuntimeError):
            build_published_affiliate_copy_replacements(BASE,cfg)

    def test_refuses_duplicate_edits(self):
        cfg=cfg_for(BASE)
        cfg["replacements"]=EDITS+EDITS
        with self.assertRaises(RuntimeError):
            build_published_affiliate_copy_replacements(BASE,cfg)

if __name__ == "__main__":
    unittest.main()
