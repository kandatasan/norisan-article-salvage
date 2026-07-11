import importlib.util
import pathlib
import sys
import unittest

MODULE_PATH = pathlib.Path(__file__).parents[1] / "scripts" / "tsurikue_replace_yokakunin.py"
spec = importlib.util.spec_from_file_location("tsurikue_replace_yokakunin", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
assert spec.loader
spec.loader.exec_module(module)


class YokakuninReplacementTests(unittest.TestCase):
    def test_each_exact_source_is_replaced_without_touching_other_text(self):
        original_target = module.TARGETS[1887]
        try:
            for before, after, _label in module.REPLACEMENTS:
                module.TARGETS[1887] = (original_target[0], original_target[1], 1)
                content = f"<!-- wp:table --><figure>{before}</figure><!-- /wp:table --><p>本文はそのまま</p>"
                doc = module.Document(1887, "posts", "テスト", original_target[1], content)
                result = module.transform(doc)
                self.assertEqual(len(result.changes), 1)
                self.assertNotIn("要確認", result.updated)
                self.assertIn(after, result.updated)
                self.assertIn("<p>本文はそのまま</p>", result.updated)
        finally:
            module.TARGETS[1887] = original_target

    def test_unexpected_count_stops(self):
        doc = module.Document(
            1887,
            "posts",
            "テスト",
            module.TARGETS[1887][1],
            "<p>要確認</p>",
        )
        with self.assertRaises(ValueError):
            module.transform(doc)

    def test_expected_total_is_24(self):
        self.assertEqual(module.EXPECTED_TOTAL, 24)
        self.assertEqual(sum(module.EXPECTED_PATTERN_COUNTS.values()), 24)
        self.assertEqual(sum(value[2] for value in module.TARGETS.values()), 24)

    def test_apply_confirmation_is_fixed(self):
        self.assertEqual(module.APPLY_CONFIRMATION, "APPLY-YOKAKUNIN-20260711")


if __name__ == "__main__":
    unittest.main()
