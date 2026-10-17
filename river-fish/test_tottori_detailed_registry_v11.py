"""Cross-file test of 377 actual river-name rows from three 2023 Tottori PDFs."""
import sqlite3
import tempfile
from pathlib import Path
import unittest
from tottori_detailed_registry_v11 import build,load,search

class TottoriDetailedInventory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.db=Path(cls.temp.name)/"tottori.sqlite"
        cls.stats=build(cls.db)
    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_official_source_counts(self):
        self.assertEqual(self.stats["tottori_pdf_mention_rows"],377)
        self.assertEqual(self.stats["source_distinct_river_labels"],335)
        self.assertEqual(self.stats["chugoku_watershed_source_mentions_previous"],87)
        self.assertEqual(self.stats["yamaguchi_municipality_source_mentions_previous"],81)

    def test_real_three_classes(self):
        self.assertEqual(search(self.db,river_class="一級河川")["source_mention_count"],183)
        self.assertEqual(search(self.db,river_class="二級河川")["source_mention_count"],114)
        self.assertEqual(search(self.db,river_class="準用河川")["source_mention_count"],80)

    def test_east_central_west(self):
        self.assertEqual(search(self.db,district="東部")["source_mention_count"],141)
        self.assertEqual(search(self.db,district="中部")["source_mention_count"],114)
        self.assertEqual(search(self.db,district="西部")["source_mention_count"],122)

    def test_small_east_river_comes_from_real_pdf(self):
        data=search(self.db,name="皆込谷川")
        self.assertGreaterEqual(data["source_mention_count"],1)
        self.assertTrue(any(r["district"]=="東部圏域" for r in data["records"]))

    def test_limited_source_watershed_not_automatic(self):
        rows=search(self.db,name="湖山川")["records"]
        self.assertTrue(any(x["watershed_printed_same_line"] is None for x in rows))
        self.assertTrue(all(not x["watershed_inferred_from_other_rows"] for x in rows))

    def test_2023_snapshot_not_current(self):
        data=search(self.db,name="千代川")
        self.assertEqual(data["source_as_of"],"2023-04-01")
        self.assertIn("2023年4月1日",data["notice"])

    def test_no_mlit_10_digit_code_from_pdf_local_serial(self):
        data=search(self.db,district="東部")
        self.assertTrue(all(r["national_river_code"] is None for r in data["records"]))
        self.assertTrue(all(r["ten_digit_code_status"]=="unlinked" for r in data["records"]))

    def test_no_tributary_species_assigned(self):
        data=search(self.db,name="三谷川")
        self.assertGreaterEqual(data["source_mention_count"],1)
        self.assertTrue(all(r["specific_river_fish_occurrence"] is None for r in data["records"]))
        self.assertEqual(self.stats["tottori_direct_fish_occurrences"],0)

    def test_duplicate_label_not_collapsed(self):
        rows=search(self.db,name="清水川",limit=100)
        self.assertGreaterEqual(rows["source_mention_count"],2)
        self.assertEqual(len({r["document_mention_id"] for r in rows["records"]}),len(rows["records"]))

    def test_source_review_not_deployed(self):
        rows,manifest=load()
        self.assertEqual(manifest["publication_status"],"research_only_pending_visual_review")
        self.assertTrue(all(r["text_extraction_review_status"]=="pdf_text_machine_extracted_requires_visual_review" for r in rows))
        self.assertFalse(self.stats["website_published"])

    def test_integrity_and_prior_data_stays(self):
        conn=sqlite3.connect(self.db)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM prefectures").fetchone()[0],47)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM river_name_mentions").fetchone()[0],98)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM municipality_river_source_mentions").fetchone()[0],81)
        self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0],"ok")
        conn.close()

    def test_invalid_class_or_pagination(self):
        with self.assertRaises(ValueError): search(self.db,river_class="普通河川")
        with self.assertRaises(ValueError): search(self.db,limit=0)

    def test_does_not_overwrite(self):
        with self.assertRaises(FileExistsError):build(self.db)

if __name__=="__main__":
    unittest.main()
