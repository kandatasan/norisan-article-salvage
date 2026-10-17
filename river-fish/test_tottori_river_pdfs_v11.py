"""Fail-closed tests for 2023 Tottori official PDF river-name staging."""
import csv
import tempfile
from pathlib import Path
import unittest
from import_tottori_river_pdfs_v11 import parse_text,build,CSV_HEAD,PDFS

DOC="""鳥取県　河川一覧　令和５年４月１日時点
●東部圏域
○１級河川
千代川水系 1 千代川 52,100
2 湖山川 19,100
3 晩稲川 2,000
○２級河川
蒲生川 403 蒲生川
404 日比野川
○準用河川
千代川 601 旧野坂川
塩見川 668 江川
"""

class TottoriPdfExtractorTests(unittest.TestCase):
    def test_source_urls_are_only_prefecture_official(self):
        self.assertEqual(set(PDFS),{"east","central","west"})
        self.assertTrue(all(x.startswith("https://www.pref.tottori.lg.jp/secure/1313532/") for x in PDFS.values()))

    def test_three_classes_and_source_date_from_fixture(self):
        rows,_=parse_text("east",DOC)
        self.assertEqual(len(rows),7)
        self.assertEqual({r["river_class_page_heading"] for r in rows},{"一級河川","二級河川","準用河川"})
        self.assertEqual(rows[0]["source_as_of"],"2023-04-01")
        self.assertEqual(rows[0]["watershed_printed_on_same_line"],"千代川水系")
        self.assertEqual(rows[1]["watershed_printed_on_same_line"],"")

    def test_no_inferred_prefecture_code_or_fish(self):
        rows,_=parse_text("east",DOC)
        self.assertTrue(all(r["prefecture"]=="鳥取県" and
                            r["ten_digit_code_status"]=="unlinked" and
                            r["specific_river_ecology_status"]=="not_examined"
                            for r in rows))

    def test_source_serial_is_not_mlit_code(self):
        rows,_=parse_text("east",DOC)
        self.assertEqual(rows[0]["printed_local_serial"],"1")
        self.assertEqual(rows[0]["document_mention_id"],"TP-east-001")
        self.assertNotIn("river_code",rows[0])

    def test_ambiguous_same_name_has_distinct_local_ids(self):
        data=DOC.replace("2 湖山川","2 千代川")
        rows,_=parse_text("east",data)
        matching=[r for r in rows if r["river_name_as_pdf_text"]=="千代川"]
        self.assertEqual(len(matching),2)
        self.assertNotEqual(matching[0]["document_mention_id"],matching[1]["document_mention_id"])

    def test_date_change_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_text("east",DOC.replace("令和５年４月１日","令和６年４月１日"))

    def test_no_class_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_text("east","鳥取県　河川一覧　令和５年４月１日時点\n1 千代川\n")

    def test_duplicate_serial_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_text("east",DOC+"601 別の川\n")

    def test_fake_pdf_source_cannot_claim_complete_inventory(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                build(td,downloader=lambda url:b"%PDF-1.5\nmock",extractor=lambda b:DOC)
            self.assertFalse((Path(td)/"tottori_river_pdf_mentions_v11.csv").exists())

    def test_names_can_include_kanji_radicals(self):
        doc=DOC+"669 ⻄ノ川\n"
        r,_=parse_text("east",doc)
        self.assertTrue(any(x["river_name_as_pdf_text"]=="⻄ノ川" for x in r))

if __name__=="__main__":
    unittest.main()
