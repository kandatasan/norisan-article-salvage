import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from apply_editorial_draft_once import build_published_gulliver_extra_buttons

def h2(text):
    return '<!-- wp:heading -->\n<h2 class="wp-block-heading">' + text + '</h2>\n<!-- /wp:heading -->'

BASE = (h2("結論") + '\n\n'
        '<!-- wp:paragraph -->\n<p>中古車を選ぼう。</p>\n<!-- /wp:paragraph -->\n\n'
        + h2("気になる車種の違い") + '\n\n'
        '<!-- wp:paragraph -->\n<p>比べてみた。</p>\n<!-- /wp:paragraph -->\n\n'
        + '<!-- wp:shortcode -->\n[blog_parts id="2843"]\n<!-- /wp:shortcode -->\n\n'
        + h2("まとめ") + '\n\n'
        '<!-- wp:shortcode -->\n[blog_parts id="3788"]\n<!-- /wp:shortcode -->')
ONE = [{"before_heading":"まとめ", "copy":"条件を決めて中古車の候補を探そう。"}]
TWO = [
    {"before_heading":"気になる車種の違い", "copy":"気になる中古車を条件から探してみよう。"},
    {"before_heading":"まとめ", "copy":"予算を決めて欲しい中古車を探してみよう。"},
]

class GulliverExtraButtonTests(unittest.TestCase):
    def test_preserves_banner_ctn_links_and_existing_copy(self):
        cfg = {"button_slots": ONE}
        new, action = build_published_gulliver_extra_buttons(BASE, cfg)
        self.assertEqual(action, "UPDATE")
        self.assertEqual(new.count('[blog_parts id="2843"]'), 1)
        self.assertEqual(new.count('[blog_parts id="4172"]'), 1)
        self.assertEqual(new.count('[blog_parts id="3788"]'), 1)
        self.assertEqual(new.count('<h2'), 3)
        self.assertIn('<p>比べてみた。</p>', new)
        self.assertLess(new.index(ONE[0]["copy"]), new.index('<h2 class="wp-block-heading">まとめ'))

    def test_two_buttons_and_idempotence(self):
        content = BASE.replace(h2("気になる車種の違い"),h2("気になる車種の違い") + '\n' + '<!-- wp:paragraph -->\n<p>' + ('長文を挟む。'*100) + '</p>\n<!-- /wp:paragraph -->')
        # The second CTA remains at least 700 bytes away from the old banner.
        content = content.replace(h2("まとめ"), '<!-- wp:paragraph -->\n<p>' + ('追加の解説。'*110) + '</p>\n<!-- /wp:paragraph -->\n' + h2("まとめ"))
        new, action = build_published_gulliver_extra_buttons(content, {"button_slots": TWO})
        self.assertEqual(action, "UPDATE")
        self.assertEqual(new.count('[blog_parts id="4172"]'), 2)
        same, action = build_published_gulliver_extra_buttons(new, {"button_slots": TWO})
        self.assertEqual(action, "ALREADY_PRESENT")
        self.assertEqual(same, new)

    def test_reject_already_button(self):
        with self.assertRaises(RuntimeError):
            build_published_gulliver_extra_buttons(BASE + '[blog_parts id="4172"]', {"button_slots":ONE})

    def test_reject_missing_heading(self):
        with self.assertRaises(RuntimeError):
            build_published_gulliver_extra_buttons(BASE, {"button_slots":[{"before_heading":"なし","copy":"探す"}]})

    def test_reject_duplicate_banner(self):
        with self.assertRaises(RuntimeError):
            build_published_gulliver_extra_buttons(BASE + '[blog_parts id="2843"]', {"button_slots":ONE})

    def test_reject_too_many_buttons(self):
        with self.assertRaises(RuntimeError):
            build_published_gulliver_extra_buttons(BASE, {"button_slots":ONE*3})

    def test_reject_cta_adjacent_to_banner(self):
        with self.assertRaises(RuntimeError):
            build_published_gulliver_extra_buttons(BASE, {"button_slots":[
                {"before_heading":"まとめ", "copy":"確認しよう"}
            ]})

if __name__ == "__main__":
    unittest.main()
