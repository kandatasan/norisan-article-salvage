import importlib.util
import pathlib
import sys
import unittest

MODULE_PATH = pathlib.Path(__file__).parents[1] / "scripts" / "tsurikue_internal_link_cleanup.py"
spec = importlib.util.spec_from_file_location("tsurikue_cleanup", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
assert spec.loader
spec.loader.exec_module(module)


class OrphanLabelCleanupTests(unittest.TestCase):
    def test_known_orphan_labels_are_removed(self):
        for label in module.ORPHAN_LABELS:
            source = (
                '<!-- wp:paragraph -->\n'
                f'<p><strong>{label}</strong></p>\n'
                '<!-- /wp:paragraph -->'
            )
            self.assertEqual(module.remove_orphan_labels(source).strip(), "")

    def test_other_strong_paragraph_is_preserved(self):
        source = (
            '<!-- wp:paragraph -->\n'
            '<p><strong>これは残す本文見出し</strong></p>\n'
            '<!-- /wp:paragraph -->'
        )
        self.assertEqual(module.remove_orphan_labels(source), source)

    def test_target_link_and_its_orphan_label_are_both_removed(self):
        source = (
            '<!-- wp:paragraph -->\n'
            '<p><strong>華火の詳しい体験はこちら</strong></p>\n'
            '<!-- /wp:paragraph -->\n\n'
            '<!-- wp:paragraph -->\n'
            '<p>魚介醤油ラーメンの感想は、 <a href="/hanabiramenn/">華火の個別記事</a> で紹介しています。</p>\n'
            '<!-- /wp:paragraph -->'
        )
        result = module.transform(source)
        self.assertNotIn("華火の詳しい体験はこちら", result.updated)
        self.assertNotIn("hanabiramenn", result.updated)


if __name__ == "__main__":
    unittest.main()
