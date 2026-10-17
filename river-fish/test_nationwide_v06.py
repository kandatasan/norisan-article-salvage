"""Offline source-integrity tests for the nationwide river-fish aggregator."""
import csv
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile,ZIP_DEFLATED

from aggregate_nationwide_region_v06 import (compute_one_region,audit_output,
                                             FISH_HEADER,LEGACY_HEADER,get_region)

M="http://schemas.openxmlformats.org/spreadsheetml/2006/main"

def sample_zip():
    # Minimal XLSX without unneeded shared strings: only approved columns.
    cell=lambda col,row,text:f'<c r="{col}{row}" t="inlineStr"><is><t>{text}</t></is></c>'
    rows=[
        '<row r="1">'+''.join(cell(col,1,name) for col,name in
            [("C","生物項目"),("F","水系"),("G","調査年度"),("J","種名")])+'</row>'
    ]
    for i in range(2,123):
        cat="魚類" if i<116 else "魚介類"
        name="アユ" if i<=119 else "スジエビ"
        rows.append(f'<row r="{i}">'+
                    cell("C",i,cat)+cell("F",i,"試験水系")+
                    cell("G",i,"2020")+cell("J",i,name)+'</row>')
    sheet=f'<worksheet xmlns="{M}"><sheetData>{"".join(rows)}</sheetData></worksheet>'
    b=io.BytesIO()
    with ZipFile(b,"w",compression=ZIP_DEFLATED) as z:
        z.writestr("xl/worksheets/sheet1.xml",sheet.encode("utf-8"))
        z.writestr("xl/sharedStrings.xml",f'<sst xmlns="{M}"></sst>'.encode())
    outer=io.BytesIO()
    with ZipFile(outer,"w",compression=ZIP_DEFLATED) as z:
        z.writestr("RTTEST/魚類_テスト.xlsx",b.getvalue())
    return outer.getvalue()

class NationalSourceImportTests(unittest.TestCase):
    def test_source_registry_all_nine_pinned(self):
        config=json.loads((Path(__file__).resolve().parent/"nationwide_sources_v06.json").read_text())
        self.assertEqual(len(config["region_sources"]),9)
        self.assertEqual(len({x["region_id"] for x in config["region_sources"]}),9)
        self.assertTrue(all(len(x["checksum_sha256"])==64 for x in config["region_sources"]))
        self.assertTrue(all(x["checked_schema"]=={"C":"生物項目","F":"水系","G":"調査年度","J":"種名"} for x in config["region_sources"]))
        self.assertEqual(config["uncovered"][0]["region"],"沖縄")

    def test_names_are_not_prefectures(self):
        with self.assertRaises(ValueError):
            get_region("東京")
        with self.assertRaises(ValueError):
            get_region("okinawa")

    def test_safe_staging_retains_no_site_or_invertebrate(self):
        data=sample_zip()
        info={"region_id":"test","official_region":"試験","checksum_sha256":hashlib.sha256(data).hexdigest(),
              "xlsx_member":"RTTEST/魚類_テスト.xlsx",
              "source_url":"https://www.nilim.go.jp/test.zip"}
        with tempfile.TemporaryDirectory() as td:
            result=compute_one_region("test",td,data,info)
            out=audit_output(td,"test")
            self.assertEqual(out["verified_fish_rows"],1)
            self.assertEqual(out["held_for_review"],1)
            self.assertEqual(result["manifest"]["source_rows"],121)
            csv_path=Path(td)/"test/watershed_year_fish.csv"
            with csv_path.open(encoding="utf-8",newline="") as f:
                r=csv.DictReader(f)
                self.assertEqual(r.fieldnames,FISH_HEADER)
                self.assertEqual([x["recorded_name"] for x in r],["アユ"])
            csv_path=Path(td)/"test/legacy_mixed_category_candidates.csv"
            with csv_path.open(encoding="utf-8",newline="") as f:
                r=csv.DictReader(f)
                self.assertEqual(r.fieldnames,LEGACY_HEADER)
                self.assertEqual([x["recorded_name"] for x in r],["アユ"])
            self.assertNotIn("district",(Path(td)/"test/watershed_year_fish.csv").read_text())

    def test_source_hash_mismatch_rejected(self):
        d=sample_zip()
        info={"official_region":"試験","checksum_sha256":"0"*64,
              "xlsx_member":"RTTEST/魚類_テスト.xlsx","source_url":"https://www.nilim.go.jp/test.zip"}
        with tempfile.TemporaryDirectory() as td, self.assertRaises(ValueError):
            compute_one_region("test",td,d,info)

    def test_source_member_mismatch_rejected(self):
        d=sample_zip()
        info={"official_region":"試験","checksum_sha256":hashlib.sha256(d).hexdigest(),
              "xlsx_member":"not-the-source.xlsx","source_url":"https://www.nilim.go.jp/test.zip"}
        with tempfile.TemporaryDirectory() as td, self.assertRaises(ValueError):
            compute_one_region("test",td,d,info)

    def test_all_47_prefectures_are_keys_not_coverage_claims(self):
        from csv import DictReader
        with (Path(__file__).resolve().parent/"japan_prefectures_v06.csv").open(encoding="utf-8") as f:
            prefectures=list(DictReader(f))
        self.assertEqual(len(prefectures),47)
        self.assertEqual({p["jis_prefecture_code"] for p in prefectures},{f"{i:02d}" for i in range(1,48)})
        hiroshima=[p for p in prefectures if p["prefecture_name"]=="広島県"][0]
        self.assertIn("hiroshima",hiroshima["river_registry_status"])
        self.assertTrue(all(p["fish_survey_crosswalk_status"]=="unassigned" for p in prefectures))

if __name__=="__main__":
    unittest.main()
