import importlib.util
import json
import pathlib
import tempfile
import unittest

P = pathlib.Path(__file__).parents[1] / "scripts" / "create_experimental_page_once.py"
spec = importlib.util.spec_from_file_location("m", P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class T(unittest.TestCase):
    def package(self):
        td = tempfile.TemporaryDirectory()
        d = pathlib.Path(td.name)
        (d / "content.html").write_text("<p>Hello</p>", encoding="utf-8")
        cfg = {
            "slug": "top-design-lab",
            "title": "Design Lab",
            "marker": "<!-- tsurikue-experimental-page:v1 -->",
            "content_file": "content.html",
        }
        p = d / "config.json"
        p.write_text(json.dumps(cfg), encoding="utf-8")
        return td, p, cfg

    def test_package_adds_marker(self):
        td, p, cfg = self.package()
        loaded, full = m.load_package(p)
        self.assertTrue(full.startswith(cfg["marker"] + "\n"))
        self.assertIn("<p>Hello</p>", full)
        td.cleanup()

    def test_create_when_slug_absent(self):
        td, p, cfg = self.package()
        _, full = m.load_package(p)
        self.assertEqual(m.validate_existing([], cfg, full), ("CREATE", None))
        td.cleanup()

    def test_idempotent_exact_draft(self):
        td, p, cfg = self.package()
        _, full = m.load_package(p)
        row = {
            "id": 10,
            "slug": cfg["slug"],
            "status": "draft",
            "title": {"raw": cfg["title"]},
            "content": {"raw": full},
        }
        action, existing = m.validate_existing([row], cfg, full)
        self.assertEqual(action, "ALREADY_EXISTS")
        self.assertEqual(existing["id"], 10)
        td.cleanup()

    def test_reject_published_same_slug(self):
        td, p, cfg = self.package()
        _, full = m.load_package(p)
        row = {
            "id": 10,
            "slug": cfg["slug"],
            "status": "publish",
            "title": {"raw": cfg["title"]},
            "content": {"raw": full},
        }
        with self.assertRaises(RuntimeError):
            m.validate_existing([row], cfg, full)
        td.cleanup()

    def test_reject_edited_draft_same_slug(self):
        td, p, cfg = self.package()
        _, full = m.load_package(p)
        row = {
            "id": 10,
            "slug": cfg["slug"],
            "status": "draft",
            "title": {"raw": cfg["title"]},
            "content": {"raw": full + "human edit"},
        }
        with self.assertRaises(RuntimeError):
            m.validate_existing([row], cfg, full)
        td.cleanup()

    def test_reject_multiple_matches(self):
        td, p, cfg = self.package()
        _, full = m.load_package(p)
        with self.assertRaises(RuntimeError):
            m.validate_existing([{"id": 1}, {"id": 2}], cfg, full)
        td.cleanup()


if __name__ == "__main__":
    unittest.main()
