import unittest
from scripts.apply_en_travel_20261113 import _build, _same_metadata

class TravelEditTests(unittest.TestCase):
    def test_insert_after(self):
        out = _build("before A after", [{"mode": "insert_after", "anchor": "A", "fragment": "new"}])
        self.assertEqual(out, "before A\n\nnew after")

    def test_insert_before(self):
        out = _build("before A after", [{"mode": "insert_before", "anchor": "A", "fragment": "new"}])
        self.assertEqual(out, "before new\n\nA after")

    def test_exact_replace(self):
        out = _build("before A after", [{"mode": "replace", "anchor": "A", "fragment": "new"}])
        self.assertEqual(out, "before new after")

    def test_refuse_ambiguous_anchor(self):
        with self.assertRaisesRegex(RuntimeError, "ANCHOR_MISMATCH"):
            _build("A A", [{"mode": "insert_after", "anchor": "A", "fragment": "new"}])

    def test_preserve_post_identity(self):
        row = {"id": 1, "slug": "a-english", "status": "publish",
               "featured_media": 5, "categories": [49], "author": 3}
        self.assertTrue(_same_metadata(row, dict(row, content="changed")))
        self.assertFalse(_same_metadata(row, dict(row, status="draft")))

if __name__ == "__main__":
    unittest.main()
