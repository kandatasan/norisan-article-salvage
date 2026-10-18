"""v2.3 contract: data-only biological group addition and safe snapshots."""
import csv
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from urllib.parse import urlencode

from build_dataset_v23 import build, CSV_COLS
from engine_v23 import VerifiedSnapshot,create_app

ROOT_URL="https://www.nilim.go.jp/lab/fbg/ksnkankyo/download/slist/RT87_B01.zip"
BENTHIC_URL="https://www.nilim.go.jp/lab/fbg/ksnkankyo/download/slist/RT87_B02.zip"
BIRDS_URL="https://www.nilim.go.jp/lab/fbg/ksnkankyo/download/slist/RT87_B04.zip"

class V23DataEngineContract(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.legacy=self.root/"legacy.sqlite"
        with sqlite3.connect(self.legacy) as c:
            c.executescript("""
                CREATE TABLE watershed_year_fish_evidence(
                    region TEXT,watershed_name TEXT,survey_year TEXT,
                    literal_recorded_name TEXT,source_url TEXT);
                CREATE TABLE watershed_year_benthic_evidence(
                    region TEXT,watershed_name TEXT,survey_year TEXT,
                    literal_recorded_name TEXT,official_source_url TEXT,source_zip_sha256 TEXT);
            """)
            c.executemany("INSERT INTO watershed_year_fish_evidence VALUES (?,?,?,?,?)",[
                ("chugoku","太田川","2018","アユ",ROOT_URL),
                ("chugoku","太田川","2020","アユ",ROOT_URL),
                ("chugoku","江の川","2019","アユ",ROOT_URL),
                ("kinki","太田川支流","2020","オイカワ",ROOT_URL)])
            c.executemany("INSERT INTO watershed_year_benthic_evidence VALUES (?,?,?,?,?,?)",[
                ("chugoku","太田川","2020","モクズガニ",BENTHIC_URL,"a"*64),
                ("chugoku","太田川","2015","モクズガニ",BENTHIC_URL,"a"*64),
                ("chugoku","江の川","2016","カワゲラ",BENTHIC_URL,"a"*64)])
        self.base={
            "contract_version":1,
            "publication_status":"research_only_not_wordpress",
            "geographic_scope":"regional_watershed_year_only",
            "taxonomy_identity_verified":False,
            "source_groups":[
                {"id":"fish","label":"魚類","note":"魚類の過去記録","kind":"legacy_v19_fish","expected_rows":4},
                {"id":"benthic_animals","label":"底生動物","note":"底生動物の過去記録","kind":"legacy_v19_benthic","expected_rows":3}
            ],
            "unavailable_separate_groups":{"birds":"未審査","aquatic_insects":"分類未審査"},
            "note":"Fixture schema only"
        }
        self.registry=self.root/"registry.json"
        self.db=self.root/"dataset-v23.sqlite"
        self.manifest=self.root/"dataset-v23.json"

    def tearDown(self):
        self.temp.cleanup()

    def setup_birds(self):
        path=self.root/"birds-audited.csv"
        with path.open("w",encoding="utf-8",newline="") as f:
            writer=csv.writer(f)
            writer.writerow(CSV_COLS)
            writer.writerow(["chugoku","太田川","2019","カワセミ",BIRDS_URL,"b"*64])
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        new={
            "id":"birds","label":"鳥類","note":"監査済みの水系・年度別の鳥類調査記録",
            "kind":"verified_csv","expected_rows":1,"file":path.name,
            "sha256":digest,"reviewed_original_category":"鳥類"
        }
        self.base["source_groups"].append(new)
        self.base["unavailable_separate_groups"].pop("birds")
        return path

    def snapshot(self):
        self.registry.write_text(json.dumps(self.base,ensure_ascii=False),encoding="utf-8")
        manifest=build(self.legacy,self.db,self.manifest,self.registry,self.root)
        return manifest,VerifiedSnapshot(self.db,self.manifest)

    def test_v19_rows_are_repackaged_without_reinterpreting_taxonomy(self):
        meta,ds=self.snapshot()
        self.assertEqual(meta["group_counts"],{"fish":4,"benthic_animals":3})
        self.assertFalse(meta["wordpress_modified"])
        self.assertFalse(meta["individual_river_verified"])
        self.assertFalse(meta["taxonomy_identity_verified"])
        self.assertEqual(set(ds.groups),{"fish","benthic_animals"})
        self.assertIn("birds",ds.catalog()["unavailable_groups"])
        self.assertEqual(ds.catalog()["data_rows"],7)

    def test_year_dedup_exact_watershed_and_distinct_labels(self):
        _,ds=self.snapshot()
        x=ds.search("watershed_to_organism",("fish","benthic_animals"),
                    region="chugoku",watershed="太田川",watershed_match="exact")
        self.assertEqual(x["total"],2)
        self.assertEqual({r["recorded_name"] for r in x["results"]},{"アユ","モクズガニ"})
        ayu=next(r for r in x["results"] if r["recorded_name"]=="アユ")
        self.assertEqual(ayu["survey_years"],["2018","2020"])
        self.assertIsNone(ayu["approved_2025_taxon_code"])
        self.assertIsNone(ayu["verified_individual_river"])

    def test_region_cards_use_dynamic_group_counts(self):
        _,ds=self.snapshot()
        x=ds.search("region_explore",("fish","benthic_animals"),region="chugoku")
        self.assertEqual(x["total"],2)
        card=next(r for r in x["results"] if r["watershed_name"]=="太田川")
        self.assertEqual(card["group_label_counts"],{"fish":1,"benthic_animals":1})
        self.assertEqual(card["historical_records"],4)

    def test_new_group_is_data_only_no_engine_change(self):
        self.setup_birds()
        meta,ds=self.snapshot()
        self.assertEqual(meta["group_counts"]["birds"],1)
        self.assertEqual(set(ds.groups),{"fish","benthic_animals","birds"})
        self.assertNotIn("birds",ds.catalog()["unavailable_groups"])
        x=ds.search("region_explore",tuple(ds.groups),region="chugoku")
        card=next(r for r in x["results"] if r["watershed_name"]=="太田川")
        self.assertEqual(card["group_label_counts"]["birds"],1)
        result=ds.search("organism_to_watershed",("birds",),organism="カワセミ")
        self.assertEqual(result["total"],1)
        self.assertEqual(result["results"][0]["survey_group"],"birds")
        self.assertEqual(result["results"][0]["source_url"],BIRDS_URL)
        with self.assertRaises(ValueError):
            ds.search("organism_to_watershed",("aquatic_insects",),organism="カワゲラ")

    def test_read_only_inputs_and_immutability(self):
        before=self.legacy.read_bytes()
        self.snapshot()
        old_db=self.db.read_bytes()
        ds=VerifiedSnapshot(self.db,self.manifest)
        ds.search("region_explore",("fish",),region="chugoku")
        self.assertEqual(self.legacy.read_bytes(),before)
        self.assertEqual(self.db.read_bytes(),old_db)
        with self.assertRaises(FileExistsError):
            build(self.legacy,self.db,self.manifest,self.registry,self.root)

    def test_tampering_requires_sha_validation(self):
        self.snapshot()
        manifest_data=json.loads(self.manifest.read_text())
        manifest_data["database_sha256"]="f"*64
        self.manifest.write_text(json.dumps(manifest_data),encoding="utf-8")
        with self.assertRaises(ValueError):
            VerifiedSnapshot(self.db,self.manifest)

    def test_wrong_csv_checksum_fails_without_publishing_partial(self):
        self.setup_birds()
        self.base["source_groups"][-1]["sha256"]="f"*64
        self.registry.write_text(json.dumps(self.base,ensure_ascii=False),encoding="utf-8")
        with self.assertRaises(ValueError):
            build(self.legacy,self.db,self.manifest,self.registry,self.root)
        self.assertFalse(self.db.exists())
        self.assertFalse(self.manifest.exists())

    def test_unreviewed_categories_or_unsafe_url_rejected(self):
        self.base["source_groups"][0]["kind"]="legacy_v19_benthic"
        self.registry.write_text(json.dumps(self.base,ensure_ascii=False),encoding="utf-8")
        with self.assertRaises(ValueError):
            build(self.legacy,self.db,self.manifest,self.registry,self.root)
        self.base["source_groups"][0]["kind"]="legacy_v19_fish"
        with sqlite3.connect(self.legacy) as c:
            c.execute("UPDATE watershed_year_fish_evidence SET source_url='https://evil.example/species.csv'")
        self.registry.write_text(json.dumps(self.base,ensure_ascii=False),encoding="utf-8")
        with self.assertRaises(ValueError):
            build(self.legacy,self.db,self.manifest,self.registry,self.root)

    def test_injection_pagination_and_unavailable_group_rejected(self):
        _,ds=self.snapshot()
        for search_text in ("%", "_", "' OR 1=1 --"):
            self.assertEqual(ds.search("organism_to_watershed",("fish",),organism=search_text)["total"],0)
        for opts in (
            {"groups":("fish","fish"),"region":"chugoku"},
            {"groups":("birds",),"region":"chugoku"},
            {"groups":("fish",),"region":"広島県"},
            {"groups":("fish",),"region":"chugoku","page":20001},
            {"groups":("fish",),"region":"chugoku","per_page":1000},
        ):
            with self.assertRaises(ValueError):
                ds.search("region_explore",**opts)
        result=ds.search("region_explore",("fish","benthic_animals"),region="chugoku",per_page=1,page=2)
        self.assertEqual(result["total"],2)
        self.assertEqual(len(result["results"]),1)

    def test_http_catalog_dynamic_groups_and_get_only(self):
        self.setup_birds()
        _,ds=self.snapshot()
        api=create_app(ds)
        def request(path,query="",method="GET"):
            res={}
            def start(status,headers):
                res["status"]=status
                res["headers"]=dict(headers)
            body=b"".join(api({"PATH_INFO":path,"QUERY_STRING":query,
                               "REQUEST_METHOD":method},start))
            return res,json.loads(body) if body.startswith(b"{") else body
        status,catalog=request("/api/catalog")
        self.assertEqual(status["status"],"200 OK")
        self.assertEqual({g["id"] for g in catalog["groups"]},{"fish","benthic_animals","birds"})
        self.assertEqual(status["headers"]["Cache-Control"],"no-store")
        query=urlencode([("direction","organism_to_watershed"),("group","birds"),
                         ("organism","カワセミ")])
        status,result=request("/api/compact",query)
        self.assertEqual(status["status"],"200 OK")
        self.assertEqual(result["total"],1)
        for q in ("direction=region_explore&region=chugoku",
                  "direction=region_explore&region=chugoku&group=fish&group=fish",
                  "direction=region_explore&region=chugoku&group=fish&prefecture=広島県",
                  "direction=region_explore&region=chugoku&group=fish&year=abc"):
            status,result=request("/api/compact",q)
            self.assertEqual(status["status"],"400 Bad Request")
        status,_=request("/",method="POST")
        self.assertEqual(status["status"],"405 Method Not Allowed")
        status,html=request("/")
        self.assertEqual(status["status"],"200 OK")
        self.assertIn(b"<!doctype html>",html)

if __name__=="__main__":
    unittest.main()
