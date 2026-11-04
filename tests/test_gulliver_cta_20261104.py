import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from apply_editorial_draft_once import build_published_affiliate_swap

CONFIG = {
    "old_shortcode": '[blog_parts id="2843"]',
    "new_shortcode": '[blog_parts id="4172"]',
    "nearest_heading": "中古車を比べる",
    "old_copy": "中古車を見よう。",
    "new_copy": "ガリバーでも中古車を見よう。",
}
OLD = ('<!-- wp:heading -->\n<h2>中古車を比べる</h2>\n<!-- /wp:heading -->\n'
       '<!-- wp:paragraph -->\n<p>中古車を見よう。</p>\n<!-- /wp:paragraph -->\n'
       '<!-- wp:shortcode -->\n[blog_parts id="2843"]\n<!-- /wp:shortcode -->\n'
       '<!-- wp:paragraph -->\n<p>保証も確認しよう。</p>\n<!-- /wp:paragraph -->')

class GulliverSwapTests(unittest.TestCase):
    def test_exact_only_two_substitutions(self):
        new, action = build_published_affiliate_swap(OLD, CONFIG)
        expected = OLD.replace(CONFIG["old_copy"], CONFIG["new_copy"]).replace(
            CONFIG["old_shortcode"], CONFIG["new_shortcode"]
        )
        self.assertEqual(action, "UPDATE")
        self.assertEqual(new, expected)
        self.assertEqual(new.count('[blog_parts id="4172"]'), 1)

    def test_idempotent(self):
        new, _ = build_published_affiliate_swap(OLD, CONFIG)
        newer, action = build_published_affiliate_swap(new, CONFIG)
        self.assertEqual(newer, new)
        self.assertEqual(action, "ALREADY_PRESENT")

    def test_wrong_heading_rejected(self):
        with self.assertRaises(RuntimeError):
            build_published_affiliate_swap(OLD.replace("中古車を比べる", "新車を選ぶ"), CONFIG)

    def test_unexpected_second_banner_rejected(self):
        with self.assertRaises(RuntimeError):
            build_published_affiliate_swap(OLD + '\n[blog_parts id="2843"]', CONFIG)

    def test_microcopy_drift_rejected(self):
        with self.assertRaises(RuntimeError):
            build_published_affiliate_swap(OLD.replace("中古車を見よう。", "新車がいい。"), CONFIG)

    def test_mismatched_managed_part_rejected(self):
        cfg = dict(CONFIG, new_shortcode='[blog_parts id="9999"]')
        with self.assertRaises(RuntimeError):
            build_published_affiliate_swap(OLD, cfg)

if __name__ == "__main__":
    unittest.main()
