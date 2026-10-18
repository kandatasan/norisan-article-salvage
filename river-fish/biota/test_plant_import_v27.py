"""Official plant archive pin regression and safe import using synthetic XLSX only."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_plant_source_audit_v26 import bundle
from import_national_plants_v27 import REGIONS, pin, transform, read_stage

class NationalPlantImportV25(unittest.TestCase):
    def test_all_nine_sha_pins_and_source_counts(self):
        self.assertEqual(len(REGIONS),9)
        count=0
        for i,region in enumerate(REGIONS,81):
            entry,registry=pin(region)
            self.assertEqual(entry["source_url"].split("/")[-1],f"RT{i}_B03.zip")
            self.assertEqual(len(entry["checksum_sha256"]),64)
            self.assertIn("植物_",entry["xlsx_member"])
            self.assertEqual(registry["original_category"],"植物")
            count+=entry["expected_aggregated_records"]
        self.assertEqual(count,270180)

    def test_synthetic_checked_zip_to_read_only_staged_csv(self):
        raw=bundle()
        item={
            "source_url":"https://www.nilim.go.jp/lab/fbg/ksnkankyo/download/slist/RT87_B03.zip",
            "checksum_sha256":hashlib.sha256(raw).hexdigest(),
            "xlsx_member":"RT87_B03/植物_架空.xlsx",
            "audited_source_rows":60,
            "expected_aggregated_records":60
        }
        config={"verified_index_url":"https://www.nilim.go.jp/lab/fbg/ksnkankyo/dl_00_index.html"}
        with tempfile.TemporaryDirectory() as tmp:
            with patch("import_national_plants_v27.pin",return_value=(item,config)):
                manifest=transform("chugoku",raw,tmp)
                rows,m=read_stage("chugoku",tmp)
                self.assertEqual(len(rows),60)
                self.assertEqual(manifest["aggregated_records"],60)
                self.assertEqual(manifest["source_sha256"],item["checksum_sha256"])
                self.assertTrue(all(r["region"]=="chugoku" for r in rows))
                self.assertEqual(m["scope"],"region_watershed_year_only")
                self.assertFalse(m["stations_or_coordinates_extracted"])
                self.assertFalse(m["wordpress_modified"])
                with self.assertRaises(FileExistsError):
                    transform("chugoku",raw,tmp)

    def test_forged_original_sha_rejected(self):
        raw=bundle()
        item={
            "source_url":"https://www.nilim.go.jp/lab/fbg/ksnkankyo/download/slist/RT87_B03.zip",
            "checksum_sha256":"0"*64,
            "xlsx_member":"RT87_B03/植物_架空.xlsx",
            "audited_source_rows":60,
            "expected_aggregated_records":60
        }
        with tempfile.TemporaryDirectory() as tmp:
            with patch("import_national_plants_v27.pin",return_value=(item,{})):
                with self.assertRaises(ValueError):
                    transform("chugoku",raw,tmp)
                self.assertFalse((Path(tmp)/"chugoku").exists())

if __name__=="__main__":
    unittest.main()
