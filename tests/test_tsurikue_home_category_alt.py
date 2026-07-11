import importlib.util
import pathlib
import sys
import unittest

MODULE_PATH = pathlib.Path(__file__).parents[1] / "scripts" / "tsurikue_home_category_alt.py"
spec = importlib.util.spec_from_file_location("tsurikue_home_category_alt", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
assert spec.loader
spec.loader.exec_module(module)


SAMPLE = '''<!-- wp:image -->
<figure><img src="hero.jpg" alt="" class="wp-image-2269"/></figure>
<!-- /wp:image -->
<figure><a href="https://tsurikue.com/category/fishing/"><img src="1.jpg" alt="" class="wp-image-2298"/></a></figure>
<figure><a href="https://tsurikue.com/category/sightseeing-leisure/"><img src="2.jpg" alt="" class="wp-image-2297"/></a></figure>
<figure><a href="https://tsurikue.com/category/gourmet/"><img src="3.jpg" alt="" class="wp-image-2299"/></a></figure>
<figure><a href="https://tsurikue.com/category/car/"><img src="4.jpg" alt="" class="wp-image-2300"/></a></figure>'''


class HomepageCategoryAltTests(unittest.TestCase):
    def test_only_four_category_images_change(self):
        result = module.transform(SAMPLE)
        self.assertEqual(len(result.actions), 4)
        self.assertEqual(result.blank_alts_before, 5)
        self.assertEqual(result.blank_alts_after, 1)
        self.assertIn('alt="" class="wp-image-2269"', result.updated)
        self.assertIn('alt="釣りカテゴリー"', result.updated)
        self.assertIn('alt="レジャー・観光カテゴリー"', result.updated)
        self.assertIn('alt="グルメカテゴリー"', result.updated)
        self.assertIn('alt="車カテゴリー"', result.updated)
        self.assertTrue(module.transform_after_apply(result.updated))

    def test_rejects_nonblank_target_alt(self):
        broken = SAMPLE.replace('alt="" class="wp-image-2298"', 'alt="既存" class="wp-image-2298"')
        with self.assertRaises(ValueError):
            module.transform(broken)

    def test_confirmation_string_is_fixed(self):
        self.assertEqual(module.APPLY_CONFIRMATION, "APPLY-HOME-CATEGORY-ALT-20260711")


if __name__ == "__main__":
    unittest.main()
