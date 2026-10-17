"""Official national river code list and non-inference regression tests."""
import csv
import json
import tempfile
from pathlib import Path
import unittest
from import_national_river_codes_v07 import (parse_list,decode,stage,RIVERS,WATERSHEDS,
                                           RIVER_HEADER,WATER_HEADER)

def html(rows):
    return "<html><body><table><tr><th>河川コード</th><th>河川名</th></tr>"+\
      "".join(f'<tr><td>{code}</td><td>{name}</td></tr>' for code,name in rows)+\
      "</table></body></html>"

class NationalCodes(unittest.TestCase):
    def test_html_two_column_extraction(self):
        r,d=parse_list(html([("8707090023","諸木川"),("8707090021","矢口川")]),"river",min_count=2)
        self.assertEqual(len(r),2)
        self.assertEqual(r["8707090023"],"諸木川")

    def test_water_code_extraction(self):
        r,d=parse_list(html([("870709","太田川"),("470047","浦内川")]),"watershed",min_count=2)
        self.assertEqual(r["470047"],"浦内川")

    def test_same_name_different_code_kept(self):
        r,d=parse_list(html([("8707090003","八幡川"),("8707090015","八幡川")]),"river",min_count=2)
        self.assertEqual(len(r),2)
        self.assertEqual(list(r.values()),["八幡川","八幡川"])

    def test_different_name_same_code_refused(self):
        with self.assertRaises(ValueError):
            parse_list(html([("8707090023","諸木川"),("8707090023","別の川")]),"river",min_count=1)

    def test_no_guess_for_unknown_watershed(self):
        rivers={"8707090023":"諸木川","9900000001":"試験河川"}
        waters={"870709":"太田川"}
        with tempfile.TemporaryDirectory() as t:
            m=stage(t,rivers,waters,{"example":"abc"})
            with (Path(t)/"river_codes_national_v07.csv").open(encoding="utf-8") as f:
                data=list(csv.DictReader(f))
            moroki=[x for x in data if x["river_code"]=="8707090023"][0]
            unknown=[x for x in data if x["river_code"]=="9900000001"][0]
            self.assertEqual(moroki["watershed_code"],"870709")
            self.assertEqual(moroki["watershed_name"],"太田川")
            self.assertEqual(moroki["code_region_prefix"],"87")
            self.assertEqual(unknown["watershed_name"],"")
            self.assertEqual(m["river_rows_without_matching_watershed_code"],1)
            self.assertEqual(m["prefecture_mapping"],"not_inferred")
            self.assertEqual(m["direct_parent_river"],"not_inferred")
            self.assertEqual(m["direct_species"],"not_inferred")
            self.assertTrue(m["no_W05_geometries"])

    def test_no_name_only_identity(self):
        with tempfile.TemporaryDirectory() as t:
            m=stage(t,{"8707090003":"八幡川","8707090015":"八幡川"},{"870709":"太田川"},{})
            self.assertEqual(m["river_code_rows"],2)
            self.assertEqual(m["distinct_literal_river_names"],1)

    def test_bounded_source_schema(self):
        with self.assertRaises(ValueError):
            parse_list("<html><body></body></html>","river")

    def test_cp932_html_support(self):
        content='<html><meta charset="Shift_JIS"><table><tr><td>8707090023</td><td>諸木川</td></tr></table></html>'
        decoded,enc=decode(content.encode("cp932"))
        self.assertEqual(enc,"cp932")
        self.assertIn("諸木川",decoded)

    def test_reject_unexpected_code_width(self):
        a,_=parse_list(html([("8707090023","諸木川")]),"river",min_count=1)
        self.assertEqual(len(a),1)
        with self.assertRaises(ValueError):
            parse_list(html([("8707090023","諸木川")]),"watershed",min_count=1)

if __name__=="__main__":
    unittest.main()
