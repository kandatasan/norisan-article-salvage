import importlib.util
import pathlib
import sys
import unittest

MODULE_PATH = pathlib.Path(__file__).parents[1] / "scripts" / "tsurikue_adsense_cleanup_no_alt.py"
spec = importlib.util.spec_from_file_location("tsurikue_adsense_cleanup_no_alt", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
assert spec.loader
spec.loader.exec_module(module)


class NoAltCleanupTests(unittest.TestCase):
    def test_blank_alt_is_preserved(self):
        doc = module.base.Document(
            1883,
            "posts",
            "テスト記事",
            "https://tsurikue.com/aoriika-nikki/",
            '<!-- wp:image --><figure><img src="x.jpg" alt=""></figure><!-- /wp:image -->',
        )
        result = module.base.transform(doc)
        self.assertIn('alt=""', result.updated)
        self.assertFalse(any(action.kind == "add_alt" for action in result.actions))
        self.assertEqual(result.remaining_blank_alts, 1)

    def test_no_alt_expected_counts(self):
        self.assertEqual(module.base.EXPECTED_COUNTS["alt_additions"], 0)
        self.assertEqual(
            module.base.EXPECTED_COUNTS["remaining_blank_alts"],
            module.EXPECTED_BLANK_ALTS,
        )


if __name__ == "__main__":
    unittest.main()
