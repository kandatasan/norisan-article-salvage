from io import BytesIO
from pathlib import Path
import sqlite3
import tempfile
import unittest
from zipfile import ZipFile
from audit_individual_rivers import classify,source_rows,SCHEMA,valid,code_catalog,load_approvals

class IdentityTests(unittest.TestCase):
    def test_names_alone_never_approve(self):
        candidates={('太田川','太田川'):['8707090001','0700110001']}
        self.assertEqual(classify('chugoku','太田川','太田川','中国地方整備局',{},candidates)[0],'B')
    def test_authority_and_region_required(self):
        a={('chugoku','太田川','三篠川'):{'source_authority':'中国地方整備局','river_code':'8707090029'}}
        self.assertEqual(classify('chugoku','太田川','三篠川','中国地方整備局',a,{})[0],'A')
        self.assertEqual(classify('chugoku','太田川','三篠川','別事務所',a,{})[0],'B')
        self.assertEqual(classify('kanto','太田川','三篠川','中国地方整備局',a,{})[0],'B')
    def test_watershed_does_not_imply_tributary(self):
        a={('chugoku','太田川','三篠川'):{'source_authority':'中国地方整備局'}}
        self.assertEqual(classify('chugoku','太田川','','中国地方整備局',a,{})[0],'C')
        self.assertEqual(classify('chugoku','','三篠川','中国地方整備局',a,{})[0],'D')
    def test_code_constraints(self):
        c=sqlite3.connect(':memory:');c.executescript(SCHEMA)
        row=['fish','chugoku','太田川','2023','アユ','三篠川','中国地方整備局','8707090029','870709','B','individual_river','','','',1,'','','']
        with self.assertRaises(sqlite3.IntegrityError):c.execute('INSERT INTO evidence VALUES ('+','.join('?'*18)+')',row)
        row[9]='A';row[8]='000000'
        with self.assertRaises(sqlite3.IntegrityError):c.execute('INSERT INTO evidence VALUES ('+','.join('?'*18)+')',row)
    def test_literal_names_and_year_preserved(self):
        for name in ['ヨシノボリ類','トウヨシノボリ（型不明）','アユ']:
            self.assertTrue(valid({'watershed':'太田川','name':name,'year':'2009'}))
        self.assertFalse(valid({'watershed':'太田川','name':'アユ','year':'不明'}))
    def test_plant_river_column_found_by_header_not_M(self):
        ns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
        headers={'C':'生物項目','D':'地整','F':'水系','G':'調査年度','J':'種名','L':'河川名','M':'ダム名','P':'地区名'}
        data={'C':'植物','D':'中国地方整備局','F':'太田川','G':'2016','J':'ヨシ','L':'三篠川','P':'DO_NOT_EXPORT_STATION'}
        def row(n,values):
            return '<row r="'+str(n)+'">'+''.join(f'<c r="{col}{n}" t="inlineStr"><is><t>{v}</t></is></c>' for col,v in values.items())+'</row>'
        inner=BytesIO()
        with ZipFile(inner,'w') as z:z.writestr('xl/worksheets/sheet1.xml',f'<worksheet xmlns="{ns}"><sheetData>{row(1,headers)}{row(2,data)}</sheetData></worksheet>')
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'test.zip'
            with ZipFile(path,'w') as z:z.writestr('test.xlsx',inner.getvalue())
            rows=list(source_rows(path,'test.xlsx'))
        self.assertEqual(rows[1]['river'],'三篠川');self.assertNotIn('DO_NOT_EXPORT_STATION',str(rows[1]))
    def test_approvals_match_full_catalog(self):
        rows=load_approvals(Path(__file__).with_name('approved_river_crosswalk.csv'),code_catalog())
        self.assertEqual(rows[('chugoku','太田川','三篠川')]['river_code'],'8707090029')

if __name__=='__main__':unittest.main()
