#!/usr/bin/env python3
"""Fully local black-box API regression tests for code-free named river biota."""
from __future__ import annotations
import json
import os
from pathlib import Path
import threading
import unittest
from urllib.parse import urlencode,quote
from urllib.request import urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
from run_local_atlas_v09 import AtlasData,Handler

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent

class RiverAtlasHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db=os.environ.get("RIVER_V08_TEST_DB","/tmp/river_biota_literal_names_v08.sqlite")
        nav=ROOT/"research-individual-v07/outputs/river_atlas_navigation_v07.json"
        if not Path(db).exists():raise RuntimeError("Restore tested v08 research DB before running HTTP tests")
        app=AtlasData(db,nav,HERE/"index.html")
        class H(Handler):pass
        H.app=app
        cls.server=ThreadingHTTPServer(("127.0.0.1",0),H)
        cls.host="http://127.0.0.1:"+str(cls.server.server_address[1])
        cls.t=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.t.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.t.join(timeout=5)

    def request(self,path):
        with urlopen(self.host+path,timeout=10) as res:
            return json.loads(res.read()),res.headers

    def test_prefs_and_documentary_entrances(self):
        d,header=self.request("/api/v1/prefectures")
        self.assertEqual(len(d["items"]),47)
        self.assertEqual(header.get("X-Content-Type-Options"),"nosniff")
        self.assertNotIn("Access-Control-Allow-Origin",dict(header))
        d,_=self.request("/api/v1/watersheds?"+urlencode({"pref":"広島県"}))
        self.assertTrue({"太田川","芦田川"}.issubset({x["watershed"] for x in d["items"]}))
        self.assertTrue(all(x["no_claim_all_watershed_rivers_within_prefecture"] for x in d["items"]))
        self.assertTrue(all("biota" not in x for x in d["items"]))
        # Don't confuse locally named Oita/Kumamoto "大野川" river systems.
        d,_=self.request("/api/v1/watersheds?"+urlencode({"pref":"熊本県"}))
        self.assertNotIn("大野川",{x["watershed"] for x in d["items"]})
        d,_=self.request("/api/v1/watersheds?"+urlencode({"pref":"愛媛県"}))
        self.assertNotIn("渡川",{x["watershed"] for x in d["items"]})

    def test_hiroshima_misasa_full_fish_taxon_names_and_paging(self):
        d,_=self.request("/api/v1/rivers?"+urlencode({"pref":"広島県","watershed":"太田川"}))
        river=next(r for r in d["items"] if r["river_name"]=="三篠川")
        self.assertTrue(river["individual_river_prefecture_mention"])
        self.assertEqual(river["river_code_optional"],"8707090029")
        path="/api/v1/river/"+quote(river["identity_key"])
        page,_=self.request(path+"?"+urlencode({"category":"fish","limit":20}))
        self.assertEqual(page["total_literal_names_not_species"],25)
        self.assertEqual(page["four_categories"]["fish"]["historical_contexts"],67)
        self.assertEqual(page["selected_category"],"fish")
        self.assertEqual(len(page["items"]),20)
        self.assertTrue(page["has_more"])
        self.assertTrue(any(x["literal_recorded_name"]=="アユ" for x in page["items"]))
        for label in page["items"]:
            self.assertFalse(label["scientific_species_identity_verified"])
            self.assertTrue(label["sources"])
            self.assertTrue(all(s["source_url"].startswith("https://") for s in label["sources"]))
        second,_=self.request(path+"?"+urlencode({"category":"fish","limit":20,"offset":20}))
        self.assertEqual(len(second["items"]),5)
        self.assertFalse(second["has_more"])
        self.assertTrue({x["literal_recorded_name"] for x in page["items"]}.isdisjoint(
            {x["literal_recorded_name"] for x in second["items"]}))

    def test_kyushu_code_free_river_and_no_false_absence(self):
        d,_=self.request("/api/v1/rivers?"+urlencode({"pref":"佐賀県","watershed":"筑後川"}))
        river=next(r for r in d["items"] if r["river_name"]=="宝満川")
        self.assertIsNone(river["river_code_optional"])
        page,_=self.request("/api/v1/river/"+river["identity_key"]+"?category=benthic_animals&limit=25")
        self.assertEqual(page["total_literal_names_not_species"],94)
        self.assertEqual(page["four_categories"]["benthic_animals"]["historical_contexts"],124)
        self.assertEqual(page["four_categories"]["fish"]["historical_contexts"],0)
        self.assertFalse(page["prefecture"])
        self.assertEqual(page["source_scope"],"individual_named_river_only")

    def test_neyagawa_has_zero_birds_not_watershed_birds(self):
        d,_=self.request("/api/v1/rivers?"+urlencode({"pref":"広島県","watershed":"太田川"}))
        river=next(r for r in d["items"] if r["river_name"]=="根谷川")
        result,_=self.request("/api/v1/river/"+river["identity_key"]+"?category=birds")
        self.assertEqual(result["four_categories"]["birds"]["historical_contexts"],0)
        self.assertEqual(result["items"],[])
        self.assertFalse(result["has_more"])

    def test_malformed_or_unverified_inputs(self):
        for path in (
            "/api/v1/watersheds?pref=架空県",
            "/api/v1/rivers?"+urlencode({"pref":"佐賀県","watershed":"那珂川"}),
            "/api/v1/river/rn_fake?category=fish",
            "/api/v1/river/rn_123456789012345678901234?category=other",
            "/api/v1/river/rn_123456789012345678901234?category=fish&limit=10000"
        ):
            with self.subTest(path=path),self.assertRaises(HTTPError) as c:
                urlopen(self.host+path,timeout=5)
            self.assertIn(c.exception.code,(400,404))

    def test_frontend_is_tiny_and_no_embedded_taxon_dump(self):
        with urlopen(self.host+"/",timeout=10) as res:
            html=res.read().decode("utf-8")
        self.assertLess(len(html.encode("utf-8")),50_000)
        self.assertIn("魚類",html)
        self.assertIn("底生動物",html)
        self.assertIn("植物",html)
        self.assertNotIn("<iframe",html)
        self.assertNotIn("254574",html)
        self.assertIn("fetch(path",html)

if __name__=="__main__":unittest.main()
