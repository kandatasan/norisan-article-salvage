"""Synthetic plant workbook audit tests, no MLIT network access."""
from io import BytesIO
from zipfile import ZipFile,ZIP_DEFLATED
import unittest
from audit_plant_sources_v24 import audit

M="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
def bundle(region="chugoku",category="植物",header="種名",rows=60):
    sheet=['<?xml version="1.0" encoding="UTF-8"?>',
           '<worksheet xmlns="'+M+'"><sheetData>']
    def c(ref,text):
        return '<c r="'+ref+'" t="inlineStr"><is><t>'+text+'</t></is></c>'
    sheet.append('<row r="1">'+c("C1","生物項目")+c("F1","水系")+
                 c("G1","調査年度")+c("J1",header)+"</row>")
    for i in range(rows):
        n=i+2
        sheet.append('<row r="'+str(n)+'">'+c("C"+str(n),category)+
                     c("F"+str(n),"太田川")+c("G"+str(n),"2020")+
                     c("J"+str(n),"草"+str(i))+"</row>")
    sheet.append('</sheetData></worksheet>')
    wb=BytesIO()
    with ZipFile(wb,"w",ZIP_DEFLATED) as z:
        z.writestr("xl/sharedStrings.xml",'<?xml version="1.0"?><sst xmlns="'+M+'"></sst>')
        z.writestr("xl/worksheets/sheet1.xml","".join(sheet))
    rnum={"chugoku":"87","kanto":"83"}[region]
    outer=BytesIO()
    with ZipFile(outer,"w",ZIP_DEFLATED) as z:
        z.writestr("RT"+rnum+"_B03/植物_架空.xlsx",wb.getvalue())
    return outer.getvalue()

class PlantSourceAuditV24(unittest.TestCase):
    def test_only_plant_category_accepted(self):
        meta=audit("chugoku",bundle())
        self.assertEqual(meta["original_source_rows"],60)
        self.assertEqual(meta["unique_watershed_year_literal_name_records"],60)
        self.assertEqual(meta["original_categories"],{"植物":60})
        self.assertIn("RT87_B03.zip",meta["source_url"])
        self.assertFalse(meta["survey_station_columns_read"])
        self.assertFalse(meta["wordpress_modified"])
        self.assertEqual(meta["status"],"audit_only_not_approved_for_import")
    def test_wrong_original_biological_category_is_not_imported(self):
        with self.assertRaises(ValueError):audit("chugoku",bundle(category="魚類"))
    def test_header_replacement_rejected(self):
        with self.assertRaises(ValueError):audit("chugoku",bundle(header="生物名"))
    def test_mismatched_region_archive_rejected(self):
        with self.assertRaises(ValueError):audit("kanto",bundle())
    def test_underfilled_category_fails_closed(self):
        with self.assertRaises(ValueError):audit("chugoku",bundle(rows=5))

if __name__=="__main__":
    unittest.main()
