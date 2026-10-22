"""Tests for bounded, non-approving Yamaguchi fish-source page review."""
import hashlib
import unittest
from pathlib import Path
from unittest.mock import patch

from audit_yamaguchi_fish_pages_v10 import (
    PDFS, REQUIRED_RECORD_TERMS, SCHEMA, SOURCE_PDF_PAGE, SPECIES_TERM, STATUS,
    build_review, extract_pdf_page_text, extract_target_excerpt,
)


class YamaguchiFishPageReviewTests(unittest.TestCase):
    def setUp(self):
        self.excerpt = (
            "ヌマムツは山口県では既往文献に記録がある。本調査では"
            "2005年佐波川水系小島川と2007年に山口湾に流入する長沢川水系で確認した。"
        )

    def test_exact_target_scope_and_years_are_isolated(self):
        result = extract_target_excerpt("前の説明。\n" + self.excerpt + "\n別の種の説明。")
        self.assertTrue(all(term in result for term in REQUIRED_RECORD_TERMS))
        self.assertNotIn("別の種", result)
        self.assertLessEqual(len(result), 500)

    def test_missing_required_scope_fails_closed(self):
        with self.assertRaises(ValueError):
            extract_target_excerpt("ヌマムツは2005年に佐波川で確認。小島川の記録。")

    def test_coordinates_are_not_emitted(self):
        text = (
            self.excerpt
            + " 北緯34°00′東経131°00′"
        )
        result = extract_target_excerpt(text)
        self.assertNotIn("北緯", result)
        self.assertNotIn("東経", result)

    def test_review_never_approves_or_changes_rows(self):
        raw = b"%PDF-test"
        with patch.dict(PDFS["YA07"], {"sha256": hashlib.sha256(raw).hexdigest()}):
            result = build_review(raw, self.excerpt, 87)
        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(result["status"], STATUS)
        self.assertEqual(result["pdf_page_number"], SOURCE_PDF_PAGE)
        self.assertEqual(result["species_term_on_same_page"], SPECIES_TERM)
        self.assertTrue(result["human_review_required"])
        self.assertEqual(result["source_rows_changed"], 0)
        self.assertFalse(result["approved_for_publication"])
        self.assertFalse(result["site_updated"])

    def test_page_extractor_rejects_out_of_range_page(self):
        with self.assertRaises(ValueError):
            extract_pdf_page_text(Path("/missing.pdf"), 0)


if __name__ == "__main__":
    unittest.main()
