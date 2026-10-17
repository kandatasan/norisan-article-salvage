"""Deterministic safety checks; no network access in unit tests."""
import csv
import tempfile
import unittest
from pathlib import Path
from aggregate_official_workbook import aggregate,export,legacy_candidates,OUTPUT,MANIFEST,LEGACY

def fixture(i,water="太田川",year="2020",name="アユ",biota="魚類"):
    return {"C":biota,"F":water,"G":year,"J":name}

class OfficialImportTests(unittest.TestCase):
    def test_repeated_sites_become_one_watershed_year_fish(self):
        data=[fixture(i) for i in range(105)]
        rows,m=aggregate(data)
        self.assertEqual(len(rows),1)
        self.assertEqual(m["source_rows"],105)
        self.assertEqual(m["aggregated_records"],1)

    def test_keep_years_separate(self):
        data=[fixture(i,year="2020" if i<60 else "2021") for i in range(120)]
        rows,_=aggregate(data)
        self.assertEqual(len(rows),2)

    def test_no_prefecture_or_station_in_export(self):
        data=[fixture(i) for i in range(105)]
        rows,m=aggregate(data)
        with tempfile.TemporaryDirectory() as tmp:
            export(tmp,rows,m)
            text=(Path(tmp)/OUTPUT).read_text(encoding="utf-8")
            self.assertEqual(len(list(csv.DictReader(text.splitlines()))),1)
            self.assertNotIn("prefecture",text)
            self.assertNotIn("site",text.lower())
            self.assertNotIn("distance",text.lower())
            self.assertTrue((Path(tmp)/MANIFEST).exists())

    def test_invalid_and_outside_group_are_discarded(self):
        data=[fixture(i) for i in range(103)]+[
            fixture(1,water="=HYPERLINK(1)",name="アユ"),
            fixture(1,biota="底生動物"),
            fixture(1,year="2030"),
            fixture(1,name=""),
            fixture(1,year="平成30"),
        ]
        rows,m=aggregate(data)
        self.assertEqual(len(rows),1)
        self.assertEqual(m["discarded_rows"],5)

    def test_literal_species_name_not_reclassified(self):
        data=[fixture(i,name="ヨシノボリ類") for i in range(101)]
        rows,_=aggregate(data)
        self.assertEqual(rows[0][2],"ヨシノボリ類")

    def test_mixed_legacy_never_enters_confirmed_output(self):
        trusted=[fixture(i,name="アユ") for i in range(110)]
        mixed=[fixture(i,name="アユ",biota="魚介類") for i in range(10)]
        mixed += [fixture(i,name="テナガエビ",biota="魚介類") for i in range(5)]
        trusted_rows,_=aggregate(trusted+mixed)
        self.assertEqual(len(trusted_rows),1)
        older,stats=legacy_candidates(trusted+mixed,{"アユ"})
        self.assertEqual(len(older),1)
        self.assertEqual(stats["legacy_rows_not_matched_or_invalid"],5)
        self.assertEqual(older[0][2],"アユ")
        with tempfile.TemporaryDirectory() as tmp:
            export(tmp,trusted_rows,{"scope":"staging"},older)
            txt=(Path(tmp)/LEGACY).read_text(encoding="utf-8")
            self.assertIn("unapproved_mixed_legacy_category",txt)
            self.assertNotIn("テナガエビ",txt)

    def test_no_pretend_empty_data(self):
        with self.assertRaises(ValueError):
            aggregate([fixture(i) for i in range(2)])

if __name__=="__main__":
    unittest.main()
