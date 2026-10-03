import importlib.util
import json
import pathlib
import tempfile
import unittest

P = pathlib.Path(__file__).parents[1] / "scripts" / "create_editorial_draft_once.py"
spec = importlib.util.spec_from_file_location("create_draft", P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class T(unittest.TestCase):
    def package(self):
        td = tempfile.TemporaryDirectory()
        d = pathlib.Path(td.name)
        (d / "content.html").write_text("<p>Hello</p>", encoding="utf-8")
        cfg = {
            "slug": "tanto-long-review",
            "title": "タント長期レビュー",
            "salvage_marker": "<!-- tsurikue-salvage:v1 -->",
            "editorial_marker": "<!-- tsurikue-editorial:tanto-long-review:v1 -->",
            "content_file": "content.html",
            "featured_media": 0,
            "expected_media": {},
        }
        p = d / "create.json"
        p.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
        return td, p, cfg

    def test_load_package_adds_markers(self):
        td, p, cfg = self.package()
        loaded, full = m.load_package(p)
        self.assertEqual(loaded["slug"], cfg["slug"])
        self.assertEqual(
            full,
            "<!-- tsurikue-salvage:v1 -->\n"
            "<!-- tsurikue-editorial:tanto-long-review:v1 -->\n"
            "<p>Hello</p>\n",
        )
        td.cleanup()

    def test_reject_post_id_in_create_package(self):
        td, p, cfg = self.package()
        cfg["post_id"] = 123
        p.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(RuntimeError):
            m.load_package(p)
        td.cleanup()

    def test_reject_unsafe_slug(self):
        td, p, cfg = self.package()
        cfg["slug"] = "Tanto Review"
        p.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(RuntimeError):
            m.load_package(p)
        td.cleanup()

    def test_reject_content_path_escape(self):
        td, p, cfg = self.package()
        cfg["content_file"] = "../outside.html"
        p.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(RuntimeError):
            m.load_package(p)
        td.cleanup()

    def test_reuse_exact_existing_draft(self):
        td, p, cfg = self.package()
        loaded, full = m.load_package(p)
        row = {
            "id": 42,
            "slug": loaded["slug"],
            "status": "draft",
            "title": {"raw": loaded["title"]},
            "content": {"raw": full},
            "featured_media": 0,
        }
        self.assertEqual(
            m.validate_existing_draft(row, loaded, full), "REUSE_EXISTING_DRAFT"
        )
        td.cleanup()

    def test_reject_existing_published_post(self):
        td, p, cfg = self.package()
        loaded, full = m.load_package(p)
        row = {
            "id": 42,
            "slug": loaded["slug"],
            "status": "publish",
            "title": {"raw": loaded["title"]},
            "content": {"raw": full},
            "featured_media": 0,
        }
        with self.assertRaises(RuntimeError):
            m.validate_existing_draft(row, loaded, full)
        td.cleanup()

    def test_reject_existing_draft_that_differs(self):
        td, p, cfg = self.package()
        loaded, full = m.load_package(p)
        row = {
            "id": 42,
            "slug": loaded["slug"],
            "status": "draft",
            "title": {"raw": loaded["title"]},
            "content": {"raw": full + "human edit"},
            "featured_media": 0,
        }
        with self.assertRaises(RuntimeError):
            m.validate_existing_draft(row, loaded, full)
        td.cleanup()

    def test_validate_created_requires_draft(self):
        td, p, cfg = self.package()
        loaded, full = m.load_package(p)
        row = {
            "id": 42,
            "slug": loaded["slug"],
            "status": "publish",
            "title": {"raw": loaded["title"]},
            "content": {"raw": full},
            "featured_media": 0,
        }
        with self.assertRaises(RuntimeError):
            m.validate_created(row, loaded, full)
        td.cleanup()


if __name__ == "__main__":
    unittest.main()
