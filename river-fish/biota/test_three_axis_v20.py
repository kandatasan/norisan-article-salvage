"""Read-only v2.0 watershed survey search regression tests, without live MLIT access."""
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from urllib.parse import urlencode

from three_axis_search_v20 import search, create_app

class ThreeAxisResearchV20(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.db=Path(self.temp.name)/"research.sqlite"
        with sqlite3.connect(self.db) as c:
            c.executescript("""
                CREATE TABLE watershed_year_fish_evidence(
                  region TEXT, watershed_name TEXT, survey_year TEXT,
                  literal_recorded_name TEXT, source_url TEXT);
                CREATE TABLE watershed_year_benthic_evidence(
                  region TEXT, watershed_name TEXT, survey_year TEXT,
                  literal_recorded_name TEXT, official_source_url TEXT);
            """)
            c.executemany("INSERT INTO watershed_year_fish_evidence VALUES (?,?,?,?,?)",[
                ("chugoku","太田川","2020","アユ","https://www.nilim.go.jp/fish.zip"),
                ("chugoku","江の川","2019","アユ","https://www.nilim.go.jp/fish.zip"),
                ("kinki","淀川","2019","オイカワ","https://www.nilim.go.jp/fish.zip")])
            c.executemany("INSERT INTO watershed_year_benthic_evidence VALUES (?,?,?,?,?)",[
                ("chugoku","太田川","2020","モクズガニ","https://www.nilim.go.jp/benthic.zip"),
                ("tohoku","阿武隈川","2015","カワゲラ","https://www.nilim.go.jp/benthic.zip")])
    def tearDown(self):
        self.temp.cleanup()

    def test_organism_to_watershed(self):
        x=search(self.db,"organism_to_watershed",organism="アユ")
        self.assertEqual(x["total"],2)
        self.assertEqual({r["watershed_name"] for r in x["results"]},{"太田川","江の川"})
        self.assertEqual({r["survey_group"] for r in x["results"]},{"fish"})
    def test_watershed_to_organism_across_groups(self):
        x=search(self.db,"watershed_to_organism",watershed="太田川")
        self.assertEqual(x["total"],2)
        self.assertEqual({r["recorded_name"] for r in x["results"]},{"アユ","モクズガニ"})
        for r in x["results"]:
            self.assertIsNone(r["verified_individual_river"])
            self.assertIsNone(r["verified_prefecture"])
            self.assertIsNone(r["approved_2025_taxon_code"])
        self.assertFalse(x["taxonomy_identity_verified"])
        self.assertFalse(x["wordpress_modified"])
    def test_region_and_source_filter(self):
        x=search(self.db,"region_explore",region="chugoku",group="benthic_animals")
        self.assertEqual(x["total"],1)
        self.assertEqual(x["results"][0]["recorded_name"],"モクズガニ")
        self.assertTrue(x["results"][0]["source_url"].endswith("benthic.zip"))
    def test_cross_region_not_prefecture_assignment(self):
        x=search(self.db,"organism_to_watershed",organism="カワゲラ",region="chugoku")
        self.assertEqual(x["total"],0)
        self.assertFalse(x["prefecture_presence_verified"])
    def test_year_is_exact(self):
        self.assertEqual(search(self.db,"organism_to_watershed",organism="アユ",year="2019")["total"],1)
    def test_paging(self):
        x=search(self.db,"region_explore",region="chugoku",page=2,per_page=1)
        self.assertEqual(x["total"],3)
        self.assertEqual(len(x["results"]),1)
    def test_wildcards_and_sql_injection_are_literals(self):
        for q in ["%", "_", "' OR 1=1 --"]:
            self.assertEqual(search(self.db,"organism_to_watershed",organism=q)["total"],0)
        self.assertEqual(search(self.db,"watershed_to_organism",watershed="%")["total"],0)
    def test_user_must_pick_direction_filter(self):
        with self.assertRaises(ValueError):search(self.db,"organism_to_watershed")
        with self.assertRaises(ValueError):search(self.db,"watershed_to_organism")
        with self.assertRaises(ValueError):search(self.db,"region_explore")
    def test_invalid_input_rejected(self):
        for opts in [
            {"region":"広島県","organism":"アユ"},
            {"year":"2020 OR 1=1","organism":"アユ"},
            {"organism":"アユ","page":2001},
            {"organism":"アユ","per_page":26},
            {"organism":"アユ","group":"amphibians"},
            {"organism":"アユ","watershed":"a"*101}
        ]:
            with self.assertRaises(ValueError):
                search(self.db,"organism_to_watershed",**opts)
    def test_nonexistent_db_not_created(self):
        missing=Path(self.temp.name)/"missing.sqlite"
        with self.assertRaises(FileNotFoundError):
            search(missing,"organism_to_watershed",organism="アユ")
        self.assertFalse(missing.exists())
    def test_real_sqlite_unchanged(self):
        original=self.db.read_bytes()
        search(self.db,"region_explore",region="chugoku")
        self.assertEqual(original,self.db.read_bytes())
    def test_http_api_and_no_duplicate_params(self):
        app=create_app(self.db)
        def req(path,params="",method="GET"):
            received={}
            def start(status,headers):
                received["status"]=status
                received["headers"]=dict(headers)
            raw=b"".join(app({"PATH_INFO":path,"QUERY_STRING":params,
                              "REQUEST_METHOD":method},start))
            return received,json.loads(raw) if raw.startswith(b"{") else raw
        a,x=req("/api/search",urlencode({"direction":"organism_to_watershed","organism":"アユ"}))
        self.assertEqual(a["status"],"200 OK")
        self.assertEqual(x["total"],2)
        self.assertEqual(a["headers"]["Cache-Control"],"no-store")
        a,x=req("/api/search","direction=organism_to_watershed&organism=%25")
        self.assertEqual(x["total"],0)
        a,x=req("/api/search","direction=organism_to_watershed&organism=A&organism=B")
        self.assertEqual(a["status"],"400 Bad Request")
        a,x=req("/api/search","direction=region_explore&region=chugoku&prefecture=hiroshima")
        self.assertEqual(a["status"],"400 Bad Request")
        a,x=req("/",method="POST")
        self.assertEqual(a["status"],"405 Method Not Allowed")
        a,x=req("/")
        self.assertEqual(a["status"],"200 OK")
        self.assertIn(b"<!doctype html>",x)

if __name__ == "__main__":
    unittest.main()
