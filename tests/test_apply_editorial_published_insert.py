import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from apply_editorial_draft_once import build_published_insertion

CONFIG = json.loads((ROOT / "editorial/ux-resale-early-cta-20261025/config.json").read_text(encoding="utf-8"))
FRAGMENT = (ROOT / "editorial/ux-resale-early-cta-20261025/insertion.html").read_text(encoding="utf-8").strip()
OLD = (
    '<!-- wp:heading -->\n<h2 class="wp-block-heading">同じ頃、別の一括査定では500万円前後だった</h2>\n<!-- /wp:heading -->\n\n'
    '<!-- wp:paragraph -->\n<p>500万円前後で、150万円もの差。UXは納得納得。</p>\n<!-- /wp:paragraph -->\n\n'
    '<!-- wp:image -->\n<figure><img src="https://tsurikue.com/sample.jpg"/></figure>\n<!-- /wp:image -->\n\n'
    + CONFIG["anchor_before"] + '\n\n'
    '<!-- wp:paragraph -->\n<p>CTNで査定。</p>\n<!-- /wp:paragraph -->\n\n'
    '<!-- wp:shortcode -->\n[blog_parts id="2184"]\n<!-- /wp:shortcode -->'
)


class PublishedInsertTests(unittest.TestCase):
    def test_pure_insertion_preserves_every_old_byte_and_adds_one_cta(self):
        new, marker = build_published_insertion(OLD, CONFIG, FRAGMENT)
        self.assertEqual(new.replace(FRAGMENT + "\n\n", "", 1), OLD)
        self.assertEqual(new.count(CONFIG["existing_shortcode"]), 2)
        self.assertEqual(new.count(marker), 1)
        self.assertLess(new.index(marker), new.index(CONFIG["anchor_before"]))

    def test_gutenberg_heading_attribute_variation(self):
        altered = OLD.replace('<!-- wp:heading -->',
                              '<!-- wp:heading {"className":"additional"} -->')
        altered = altered.replace('<h2 class="wp-block-heading">納車約1年・1万2,000kmで435万円だった</h2>',
                                  '<h2 class="wp-block-heading additional">納車約1年・1万2,000kmで435万円だった</h2>')
        modified, _ = build_published_insertion(altered, CONFIG, FRAGMENT)
        self.assertEqual(modified.replace(FRAGMENT + "\n\n", "", 1), altered)

    def test_refuses_repeat(self):
        new, _ = build_published_insertion(OLD, CONFIG, FRAGMENT)
        with self.assertRaises(RuntimeError):
            build_published_insertion(new, CONFIG, FRAGMENT)

    def test_refuses_missing_or_duplicated_section(self):
        for old in (OLD.replace("納得納得", "違う"), OLD + CONFIG["anchor_before"]):
            with self.subTest(length=len(old)):
                with self.assertRaises(RuntimeError):
                    build_published_insertion(old, CONFIG, FRAGMENT)

    def test_refuses_existing_ctn_in_target_section(self):
        changed = OLD.replace("<p>500万円前後で、150万円もの差。UXは納得納得。</p>",
                              '<p>500万円前後で、150万円もの差。UXは納得納得。[blog_parts id="2184"]</p>')
        with self.assertRaises(RuntimeError):
            build_published_insertion(changed, CONFIG, FRAGMENT)


if __name__ == "__main__":
    unittest.main()
