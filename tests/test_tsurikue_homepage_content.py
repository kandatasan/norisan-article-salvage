import importlib.util
import pathlib
import sys
import unittest

MODULE_PATH = pathlib.Path(__file__).parents[1] / "scripts" / "tsurikue_homepage_content.py"
spec = importlib.util.spec_from_file_location("tsurikue_homepage_content", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
assert spec.loader
spec.loader.exec_module(module)

SAMPLE = '''<!-- wp:image -->
<figure><img src="hero.jpg" alt="" class="wp-image-2269"/></figure>
<a href="https://tsurikue.com/category/fishing/"><img alt="釣りカテゴリー"></a>
<a href="https://tsurikue.com/category/sightseeing-leisure/"><img alt="レジャー・観光カテゴリー"></a>
<a href="https://tsurikue.com/category/gourmet/"><img alt="グルメカテゴリー"></a>
<a href="https://tsurikue.com/category/car/"><img alt="車カテゴリー"></a>
<!-- wp:paragraph -->
<p></p>
<!-- /wp:paragraph -->'''


class HomepageContentTests(unittest.TestCase):
    def test_inserts_expected_sections(self):
        result = module.transform(SAMPLE)
        self.assertEqual(result.updated.count(module.MARKER), 1)
        self.assertNotIn(module.EMPTY_PARAGRAPH, result.updated)
        self.assertEqual(result.updated.count("<img "), SAMPLE.count("<img "))
        module.verify_applied(result.updated)

    def test_rejects_duplicate_run(self):
        result = module.transform(SAMPLE)
        with self.assertRaises(ValueError):
            module.transform(result.updated)

    def test_rejects_missing_button(self):
        with self.assertRaises(ValueError):
            module.transform(SAMPLE.replace('alt="車カテゴリー"', 'alt=""'))

    def test_confirmation_string_is_fixed(self):
        self.assertEqual(
            module.APPLY_CONFIRMATION,
            "APPLY-HOMEPAGE-CONTENT-20260711",
        )


if __name__ == "__main__":
    unittest.main()
