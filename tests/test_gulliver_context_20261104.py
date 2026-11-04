import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from apply_editorial_draft_once import build_published_gulliver_context_ctas

def heading(text):
    return '<!-- wp:heading -->\n<h2 class="wp-block-heading">' + text + '</h2>\n<!-- /wp:heading -->'

BASE = ('<!-- wp:paragraph -->\n<p>中古が気になる。</p>\n<!-- /wp:paragraph -->\n\n' +
        heading("前の説明") + '\n' +
        '<!-- wp:paragraph -->\n<p>購入するなら価格も見る。</p>\n<!-- /wp:paragraph -->\n\n' +
        heading("比較表") + '\n' +
        '<!-- wp:paragraph -->\n<p>今の中古価格は個体で違う。</p>\n<!-- /wp:paragraph -->\n\n' +
        heading("具体的に探す") + '\n' +
        '<!-- wp:shortcode -->\n[blog_parts id="4172"]\n<!-- /wp:shortcode -->')
CFG = {
    "banner_before_heading": "比較表",
    "button_slots": [{"before_heading": "具体的に探す", "copy": "条件を決めて中古車を比較しよう。"}],
}

class GulliverContextTests(unittest.TestCase):
    def test_preserves_original_blocks_and_adds_banner_button(self):
        updated, action = build_published_gulliver_context_ctas(BASE, CFG)
        self.assertEqual(action, "UPDATE")
        self.assertEqual(updated.count('[blog_parts id="2843"]'), 1)
        self.assertEqual(updated.count('[blog_parts id="4172"]'), 2)
        self.assertEqual(updated.count('<h2'), 3)
        self.assertIn('<p>購入するなら価格も見る。</p>', updated)
        self.assertLess(updated.index('[blog_parts id="2843"]'), updated.index('<h2 class="wp-block-heading">比較表'))

    def test_idempotence(self):
        updated, _ = build_published_gulliver_context_ctas(BASE, CFG)
        again, action = build_published_gulliver_context_ctas(updated, CFG)
        self.assertEqual(action, "ALREADY_PRESENT")
        self.assertEqual(again, updated)

    def test_reject_duplicate_banner(self):
        with self.assertRaises(RuntimeError):
            build_published_gulliver_context_ctas(BASE + '[blog_parts id="2843"]', CFG)

    def test_reject_missing_anchor(self):
        c = dict(CFG, banner_before_heading="間違った章")
        with self.assertRaises(RuntimeError):
            build_published_gulliver_context_ctas(BASE, c)

    def test_reject_same_banner_and_button_anchor(self):
        c = dict(CFG, banner_before_heading="具体的に探す")
        with self.assertRaises(RuntimeError):
            build_published_gulliver_context_ctas(BASE, c)

    def test_reject_many_extra_buttons(self):
        c = dict(CFG, button_slots=[{"before_heading":str(i), "copy":str(i)} for i in range(3)])
        with self.assertRaises(RuntimeError):
            build_published_gulliver_context_ctas(BASE, c)

    def test_zero_extra_buttons_is_allowed(self):
        c = dict(CFG, button_slots=[])
        updated, action = build_published_gulliver_context_ctas(BASE, c)
        self.assertEqual(action, "UPDATE")
        self.assertEqual(updated.count('[blog_parts id="2843"]'), 1)
        self.assertEqual(updated.count('[blog_parts id="4172"]'), 1)

if __name__ == "__main__":
    unittest.main()
