import importlib.util
import pathlib
import unittest

P = pathlib.Path(__file__).parents[1] / "scripts" / "apply_category_reorg_once.py"
spec = importlib.util.spec_from_file_location("m", P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class CategoryReorgTests(unittest.TestCase):
    def resolved(self):
        return {
            "sightseeing-leisure": {"id": 7, "slug": "sightseeing-leisure", "name": "おでかけ", "parent": 0},
            "drive": {"id": 8, "slug": "drive", "name": "旅行・モデルコース", "parent": 7},
            "fishing": {"id": 1, "slug": "fishing", "name": "釣り", "parent": 0},
            "wild-food-fish-cooking": {"id": 5, "slug": "wild-food-fish-cooking", "name": "野食・魚料理", "parent": 1},
            "car": {"id": 10, "slug": "car", "name": "クルマ", "parent": 0},
            "car-goods-wash": {"id": 11, "slug": "car-goods-wash", "name": "カー用品・洗車", "parent": 10},
        }

    def post(self, categories):
        return {
            "id": 100,
            "slug": "spot",
            "status": "publish",
            "link": "https://tsurikue.com/spot/",
            "title": {"raw": "Spot"},
            "content": {"raw": "<p>body</p>"},
            "excerpt": {"raw": ""},
            "featured_media": 12,
            "categories": categories,
        }

    def manifest(self):
        return {
            "operations": [
                {
                    "post_id": 100,
                    "slug": "spot",
                    "from_category_slugs": ["drive"],
                    "to_category_slugs": ["sightseeing-leisure"],
                }
            ]
        }

    def test_category_slug_resolution(self):
        self.assertEqual(
            m.category_slugs([8], self.resolved()),
            ["drive"],
        )

    def test_unknown_category_is_blocked(self):
        with self.assertRaises(RuntimeError):
            m.category_slugs([999], self.resolved())

    def test_preflight_allows_exact_expected_source(self):
        original = m.fetch_post
        m.fetch_post = lambda post_id, auth: self.post([8])
        try:
            plans = m.preflight(self.manifest(), self.resolved(), "auth")
        finally:
            m.fetch_post = original
        self.assertEqual(plans[0]["action"], "UPDATE")
        self.assertEqual(plans[0]["desired_category_ids"], [7])

    def test_preflight_accepts_already_done(self):
        original = m.fetch_post
        m.fetch_post = lambda post_id, auth: self.post([7])
        try:
            plans = m.preflight(self.manifest(), self.resolved(), "auth")
        finally:
            m.fetch_post = original
        self.assertEqual(plans[0]["action"], "ALREADY_DONE")

    def test_preflight_blocks_unexpected_current_categories(self):
        original = m.fetch_post
        m.fetch_post = lambda post_id, auth: self.post([1])
        try:
            with self.assertRaises(RuntimeError):
                m.preflight(self.manifest(), self.resolved(), "auth")
        finally:
            m.fetch_post = original

    def test_verify_after_blocks_non_category_changes(self):
        before = self.post([8])
        plan = {
            "slug": "spot",
            "before_snapshot": m.protected_snapshot(before),
            "desired_category_slugs": ["sightseeing-leisure"],
        }
        after = self.post([7])
        after["content"] = {"raw": "changed"}
        with self.assertRaises(RuntimeError):
            m.verify_after(plan, after, self.resolved())

    def test_verify_after_accepts_category_only_change(self):
        before = self.post([8])
        plan = {
            "slug": "spot",
            "before_snapshot": m.protected_snapshot(before),
            "desired_category_slugs": ["sightseeing-leisure"],
        }
        after = self.post([7])
        m.verify_after(plan, after, self.resolved())


if __name__ == "__main__":
    unittest.main()
