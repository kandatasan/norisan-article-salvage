import unittest
from unittest.mock import patch

from audit_yamaguchi_bass_pages_v11 import (
    EXPECTED_PAGES, REVIEW_PAGES, SOURCE_SHA256, WATERSHEDS,
    extract_table_excerpt, review_pdf, validate_source,
)


class YamaguchiBassTableReviewTests(unittest.TestCase):
    def setUp(self):
        self.text = "表3 オオクチバス 確認された水系 " + " ".join(WATERSHEDS) + " 表4 次の表"
        self.raw = b"%PDF-1.7 pinned test bytes"

    def test_table_excerpt_is_bounded_by_next_table(self):
        excerpt = extract_table_excerpt(self.text)
        self.assertTrue(excerpt.startswith("表3"))
        self.assertNotIn("表4", excerpt)
        self.assertTrue(all(name in excerpt for name in WATERSHEDS))

    def test_missing_species_or_watershed_fails_closed(self):
        with self.assertRaises(ValueError):
            extract_table_excerpt(self.text.replace("オオクチバス", "外来魚"))
        with self.assertRaises(ValueError):
            extract_table_excerpt(self.text.replace("阿武川", ""))

    def test_review_is_non_publishing_and_page_scoped(self):
        with patch("audit_yamaguchi_bass_pages_v11.SOURCE_SHA256",
                   __import__("hashlib").sha256(self.raw).hexdigest()):
            result = review_pdf(self.raw, self.text, EXPECTED_PAGES)
        self.assertEqual(result["reviewed_pdf_pages"], list(REVIEW_PAGES))
        self.assertEqual(result["source_rows_changed"], 0)
        self.assertFalse(result["approved_for_publication"])
        self.assertFalse(result["site_updated"])
        self.assertTrue(result["human_review_required"])

    def test_wrong_hash_and_page_count_stop(self):
        with self.assertRaises(ValueError):
            review_pdf(self.raw, self.text, EXPECTED_PAGES - 1)
        with self.assertRaises(ValueError):
            review_pdf(self.raw, self.text, 172)

    def test_only_fixed_official_url_is_allowed(self):
        validate_source()
        for url in ("http://www.pref.yamaguchi.lg.jp/uploaded/attachment/197775.pdf",
                    "https://evil.example/uploaded/attachment/197775.pdf",
                    "https://www.pref.yamaguchi.lg.jp/uploaded/attachment/197775.pdf?x=1"):
            with self.assertRaises(ValueError):
                validate_source(url)


if __name__ == "__main__":
    unittest.main()
