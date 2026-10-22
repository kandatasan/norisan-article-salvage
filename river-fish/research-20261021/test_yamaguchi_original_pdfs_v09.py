"""Original Yamaguchi PDF audit does not promote excerpt-only evidence."""
import unittest
from build_chugoku_source_crosscheck_v07 import read_rows, INPUT, PROVINCIAL_FIELDS
from audit_yamaguchi_original_pdfs_v09 import (
    PDFS, scan, text_page_hits, validate_url, SCHEMA, candidate_review_counts,
)


class YamaguchiPdfAuditTests(unittest.TestCase):
    def test_two_pinned_official_urls(self):
        self.assertEqual(set(PDFS), {"YA07", "YA04"})
        for source in PDFS.values():
            validate_url(source["url"])
            self.assertEqual(len(source["sha256"]), 64)
            self.assertGreater(source["expected_pages"], 50)
        with self.assertRaises(ValueError):
            validate_url("https://evil.example/attachment/197780.pdf")
        with self.assertRaises(ValueError):
            validate_url("https://www.pref.yamaguchi.lg.jp/uploaded/attachment/197780.pdf?fake=1")

    def test_pdf_page_number_is_not_sampling_site(self):
        hits, text_pages = text_page_hits(
            "ヌマムツが記載。小島川 2005\f長沢川 2007\f", PDFS["YA07"]["tokens"])
        self.assertEqual(hits["fish_term"], [1])
        self.assertEqual(hits["named_river_term"], [1])
        self.assertEqual(hits["watershed_term"], [2])
        self.assertEqual(hits["year_2005"], [1])
        self.assertEqual(hits["year_2007"], [2])
        self.assertEqual(text_pages, 2)

    def test_text_line_wrap_does_not_prevent_keyword(self):
        hits, pages = text_page_hits("ヌマ\nムツ\f", {"fish_term": "ヌマムツ"})
        self.assertEqual(hits["fish_term"], [1])

    def test_machine_scan_never_approves_or_exports_text(self):
        d = scan("YA07", b"%PDF-1.7 fake test", "ヌマムツ 小島川 2005\f長沢川 2007\f", 2)
        self.assertFalse(d["original_human_read_verified"])
        self.assertFalse(d["approved_for_publication"])
        self.assertEqual(d["staged_source_rows_promoted"], 0)
        self.assertNotIn("ヌマムツ", str(d))
        self.assertNotIn("小島川", str(d))
        self.assertIn("keyword_page_numbers_not_sampling_sites", d)

    def test_missing_tokens_stay_unverified(self):
        d = scan("YA04", b"%PDF-1.7 fake", "", 10)
        self.assertEqual(d["text_extraction_status"], "no_extractable_text")
        self.assertFalse(d["original_human_read_verified"])

    def test_ya04_and_ya07_rows_are_source_checked_but_staged(self):
        rows = read_rows(INPUT, PROVINCIAL_FIELDS)
        ya07 = [x for x in rows if x["source_id"] == "YA07"]
        ya04 = [x for x in rows if x["source_id"] == "YA04"]
        self.assertEqual((len(ya07), len(ya04)), (2, 18))
        self.assertTrue(all(x["verification_status"] == "source_text_checked"
                            and x["integration_status"] == "staged_only" for x in ya07))
        self.assertTrue(all(x["verification_status"] == "source_text_checked"
                            and "PDF p.126" in x["source_locator"]
                            and x["integration_status"] == "staged_only" for x in ya04))

    def test_all_twenty_yamaguchi_rows_are_page_checked_but_unapproved(self):
        self.assertEqual(candidate_review_counts(), {
            "source_records_pending_manual_review": 0,
            "source_records_source_text_checked_not_approved": 20,
            "source_records_automatically_approved": 0,
        })


if __name__ == "__main__":
    unittest.main()
