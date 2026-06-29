import importlib.util
import pathlib
import sys
import unittest

MODULE_PATH = pathlib.Path(__file__).parents[1] / "scripts" / "tsurikue_internal_link_dry_run.py"
spec = importlib.util.spec_from_file_location("tsurikue_dry_run", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
assert spec.loader
spec.loader.exec_module(module)


class DryRunTests(unittest.TestCase):
    def test_url_variants_are_normalized(self):
        variants = [
            "/fishingpage/",
            "https://tsurikue.com/fishingpage",
            "http://www.tsurikue.com/fishingpage/?x=1#top",
        ]
        self.assertTrue(all(module.is_target(value) for value in variants))
        self.assertFalse(module.is_target("https://example.com/fishingpage/"))

    def test_substantive_paragraph_keeps_text(self):
        source = '<!-- wp:paragraph -->\n<p><a href="/hanabiramenn/">華火のラーメン</a>は、魚介系ダシで濃厚です。</p>\n<!-- /wp:paragraph -->'
        result = module.transform(source)
        self.assertIn("<p>華火のラーメンは、魚介系ダシで濃厚です。</p>", result.updated)
        self.assertEqual([action.kind for action in result.actions], ["unwrap_anchor"])

    def test_navigation_paragraph_is_removed_with_comments(self):
        source = '前\n<!-- wp:paragraph -->\n<p>感想は、<a href="/hanabiramenn/">個別記事</a>で紹介しています。</p>\n<!-- /wp:paragraph -->\n後'
        result = module.transform(source)
        self.assertNotIn("hanabiramenn", result.updated)
        self.assertNotIn("wp:paragraph", result.updated)
        self.assertEqual([action.kind for action in result.actions], ["delete_block"])

    def test_single_link_list_is_removed(self):
        source = '<!-- wp:list -->\n<ul class="wp-block-list"><!-- wp:list-item -->\n<li><a href="/fishingpage/">釣りの部屋へ</a></li>\n<!-- /wp:list-item --></ul>\n<!-- /wp:list -->'
        result = module.transform(source)
        self.assertEqual(result.updated.strip(), "")

    def test_unrelated_list_item_is_preserved(self):
        source = '<!-- wp:list -->\n<ul><!-- wp:list-item -->\n<li><a href="/fishingpage/">削除</a></li>\n<!-- /wp:list-item -->\n<!-- wp:list-item -->\n<li><a href="/live/">残す</a></li>\n<!-- /wp:list-item --></ul>\n<!-- /wp:list -->'
        result = module.transform(source)
        self.assertNotIn("fishingpage", result.updated)
        self.assertIn('/live/', result.updated)


if __name__ == "__main__":
    unittest.main()
