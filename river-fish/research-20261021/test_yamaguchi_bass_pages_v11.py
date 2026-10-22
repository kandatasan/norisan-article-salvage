import hashlib
import unittest
from unittest.mock import patch

from audit_yamaguchi_bass_pages_v11 import (
    EXPECTED_PAGES, REVIEW_PAGES, review_pdf, validate_source,
)

class YamaguchiBassTableReviewTests(unittest.TestCase):
    def setUp(self):
        self.raw = b"%PDF-1.7 pinned test bytes"

    def test_review_is_page_scoped_and_non_publishing(self):
        with patch("audit_yamaguchi_bass_pages_v11.SOURCE_SHA256",
                   hashlib.sha256(self.raw).hexdigest()):
            result = review_pdf(self.raw, EXPECTED_PAGES)
        self.assertEqual(result["reviewed_pdf_pages"], list(REVIEW_PAGES))
        self.assertEqual(result["page_image_files"], ["YA04-125.png", "YA04-126.png"])
        self.assertEqual(result["source_rows_changed"], 0)
        self.assertFalse(result["approved_for_publication"])
        self.assertFalse(result["site_updated"])
        self.assertTrue(result["human_review_required"])

    def test_wrong_hash_and_page_count_stop(self):
        with self.assertRaises(ValueError):
            review_pdf(self.raw, EXPECTED_PAGES - 1)
        with self.assertRaises(ValueError):
            review_pdf(b"%PDF-1.7 different content", EXPECTED_PAGES)

    def test_only_fixed_official_url_is_allowed(self):
        validate_source()
        for url in ("http://www.pref.yamaguchi.lg.jp/uploaded/attachment/197775.pdf",
                    "https://evil.example/uploaded/attachment/197775.pdf",
                    "https://www.pref.yamaguchi.lg.jp/uploaded/attachment/197775.pdf?x=1"):
            with self.assertRaises(ValueError):
                validate_source(url)

if __name__ == "__main__":
    unittest.main()
