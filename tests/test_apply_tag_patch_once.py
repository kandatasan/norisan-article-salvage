import importlib.util
import pathlib
import unittest

P = pathlib.Path(__file__).parents[1] / "scripts" / "apply_tag_patch_once.py"
spec = importlib.util.spec_from_file_location("tag_patch", P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class TagPatchTests(unittest.TestCase):
    def test_normalize_string_and_object_tags(self):
        cfg = {
            "mode": "add_only",
            "tags": ["レクサスUX", {"name": "中古車", "slug": "used-car"}],
        }
        self.assertEqual(
            m.normalize_tag_specs(cfg),
            [
                {"name": "レクサスUX", "slug": ""},
                {"name": "中古車", "slug": "used-car"},
            ],
        )

    def test_reject_empty_tags(self):
        with self.assertRaises(RuntimeError):
            m.normalize_tag_specs({"tags": []})

    def test_reject_non_add_only_mode(self):
        with self.assertRaises(RuntimeError):
            m.normalize_tag_specs({"mode": "replace", "tags": ["x"]})

    def test_reject_duplicate_tag_name_case_insensitive(self):
        with self.assertRaises(RuntimeError):
            m.normalize_tag_specs({"tags": ["Lexus UX", "lexus ux"]})

    def test_reject_duplicate_explicit_slug(self):
        with self.assertRaises(RuntimeError):
            m.normalize_tag_specs(
                {
                    "tags": [
                        {"name": "A", "slug": "same"},
                        {"name": "B", "slug": "SAME"},
                    ]
                }
            )

    def test_validate_target_accepts_publish(self):
        cfg = {"post_id": 10, "slug": "x"}
        m.validate_target({"id": 10, "slug": "x", "status": "publish"}, cfg)

    def test_validate_target_accepts_draft(self):
        cfg = {"post_id": 10, "slug": "x"}
        m.validate_target({"id": 10, "slug": "x", "status": "draft"}, cfg)

    def test_validate_target_rejects_other_status(self):
        cfg = {"post_id": 10, "slug": "x"}
        with self.assertRaises(RuntimeError):
            m.validate_target({"id": 10, "slug": "x", "status": "private"}, cfg)

    def test_validate_target_rejects_id_slug_mismatch(self):
        cfg = {"post_id": 10, "slug": "x"}
        with self.assertRaises(RuntimeError):
            m.validate_target({"id": 11, "slug": "x", "status": "publish"}, cfg)

    def test_expected_status_guard(self):
        cfg = {"post_id": 10, "slug": "x", "expected_status": "draft"}
        with self.assertRaises(RuntimeError):
            m.validate_target({"id": 10, "slug": "x", "status": "publish"}, cfg)

    def test_validate_existing_tag_accepts_exact_name_and_slug(self):
        row = {"id": 3, "name": "レクサスUX", "slug": "lexus-ux"}
        spec = {"name": "レクサスUX", "slug": "lexus-ux"}
        self.assertEqual(m.validate_existing_tag(row, spec), row)

    def test_validate_existing_tag_rejects_name_mismatch(self):
        with self.assertRaises(RuntimeError):
            m.validate_existing_tag(
                {"id": 3, "name": "NX", "slug": "lexus-ux"},
                {"name": "レクサスUX", "slug": "lexus-ux"},
            )

    def test_validate_existing_tag_rejects_slug_mismatch(self):
        with self.assertRaises(RuntimeError):
            m.validate_existing_tag(
                {"id": 3, "name": "レクサスUX", "slug": "ux"},
                {"name": "レクサスUX", "slug": "lexus-ux"},
            )

    def test_stable_post_state_ignores_tags(self):
        base = {
            "id": 1,
            "slug": "x",
            "status": "publish",
            "title": {"raw": "Title"},
            "content": {"raw": "<p>Body</p>"},
            "featured_media": 4,
            "tags": [1],
        }
        other = dict(base)
        other["tags"] = [1, 2, 3]
        self.assertEqual(m.stable_post_state(base), m.stable_post_state(other))

    def test_stable_post_state_detects_content_change(self):
        base = {
            "id": 1,
            "slug": "x",
            "status": "publish",
            "title": {"raw": "Title"},
            "content": {"raw": "<p>Body</p>"},
            "featured_media": 4,
            "tags": [1],
        }
        other = dict(base)
        other["content"] = {"raw": "<p>Changed</p>"}
        self.assertNotEqual(m.stable_post_state(base), m.stable_post_state(other))


if __name__ == "__main__":
    unittest.main()
