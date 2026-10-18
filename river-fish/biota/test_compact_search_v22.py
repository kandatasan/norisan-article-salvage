"""v2.2 compact display never confuses yearly rows with unique species."""
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest
from urllib.parse import urlencode

from compact_search_v22 import create_app, search

class CompactSearchV22(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=Path(self.tmp.name)/"study.sqlite"
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
                ("chugoku","太田川","2018","アユ","https://www.nilim.go.jp/fish.zip"),
                ("chugoku","太田川","2015","オイカワ","https://www.nilim.go.jp/fish.zip"),
                ("chugoku","太田川支流","2020","アユ","https://www.nilim.go.jp/fish.zip"),
                ("chugoku","江の川","2019","アユ","https://www.nilim.go.jp/fish.zip"),
                ("kinki","太田川","2019","アユ","https://www.nilim.go.jp/fish.zip")])
            c.executemany("INSERT INTO watershed_year_benthic_evidence VALUES (?,?,?,?,?)",[
                ("chugoku","太田川","2020","モクズガニ","https://www.nilim.go.jp/benthic.zip"),
                ("chugoku","太田川","2017","モクズガニ","https://www.nilim.go.jp/benthic.zip"),
                ("chugoku","太田川","2020","カワゲラ","https://www.nilim.go.jp/benthic.zip"),
                ("chugoku","江の川","2014","カワゲラ","https://www.nilim.go.jp/benthic.zip"),
                ("shikoku","太田川","2022","モクズガニ","https://www.nilim.go.jp/benthic.zip")])
    def tearDown(self):
        self.tmp.cleanup()

    def test_region_cards_aggregate_years_and_keep_group_counts(self):
        x=search(self.db,"region_explore",region="chugoku")
        self.assertEqual(x["total"],3)
        o=next(r for r in x["results"] if r["watershed_name"]=="太田川")
        self.assertEqual(o["fish_labels"],2)
        self.assertEqual(o["benthic_labels"],2)
        self.assertEqual(o["historical_records"],6)
        self.assertEqual((o["first_year"],o["last_year"]),("2015","2020"))
        self.assertTrue(x["historical_observations_are_not_distinct_species"])
        self.assertFalse(x["individual_river_verified"])
    def test_exact_drill_filters_out_similar_names(self):
        x=search(self.db,"watershed_to_organism",region="chugoku",
                 watershed="太田川",watershed_match="exact")
        self.assertEqual(x["total"],4)
        self.assertEqual({(r["survey_group"],r["recorded_name"]) for r in x["results"]},{
            ("fish","アユ"),("fish","オイカワ"),
            ("benthic_animals","モクズガニ"),("benthic_animals","カワゲラ")})
        ayu=next(r for r in x["results"] if r["recorded_name"]=="アユ")
        self.assertEqual(ayu["survey_years"],["2018","2020"])
        self.assertEqual(ayu["survey_year_count"],2)
        self.assertEqual(ayu["historical_records"],2)
        self.assertEqual(x["count_unit"],"literal_survey_names_per_watershed")
        for row in x["results"]:
            self.assertIsNone(row["verified_individual_river"])
            self.assertIsNone(row["verified_prefecture"])
            self.assertIsNone(row["approved_2025_taxon_code"])
    def test_contains_and_exact_are_not_interchangeable(self):
        x=search(self.db,"watershed_to_organism",region="chugoku",watershed="太田川")
        self.assertEqual(x["total"],5)
    def test_cross_region_kept_separate_even_with_identical_watershed_name(self):
        x=search(self.db,"organism_to_watershed",organism="アユ")
        self.assertEqual(x["total"],4)
        self.assertEqual(len([r for r in x["results"] if r["watershed_name"]=="太田川"]),2)
    def test_only_checked_groups_scanned(self):
        fish=search(self.db,"region_explore",region="chugoku",groups=("fish",))
        self.assertEqual(fish["total"],3)
        self.assertEqual(sum(r["benthic_labels"] for r in fish["results"]),0)
        benthic=search(self.db,"region_explore",region="chugoku",groups=("benthic_animals",))
        self.assertEqual(benthic["total"],2)
        self.assertEqual(sum(r["fish_labels"] for r in benthic["results"]),0)
    def test_year_filter_applies_before_grouping(self):
        x=search(self.db,"watershed_to_organism",region="chugoku",
                 watershed="太田川",watershed_match="exact",year="2020")
        self.assertEqual(x["total"],3)
        self.assertTrue(all(r["survey_years"]==["2020"] for r in x["results"]))
    def test_grouped_results_pagination_not_split_by_year(self):
        x=search(self.db,"watershed_to_organism",region="chugoku",watershed="太田川",
                 watershed_match="exact",page=2,per_page=1)
        self.assertEqual(x["total"],4)
        self.assertEqual(len(x["results"]),1)
        self.assertEqual(x["results"][0]["recorded_name"],"モクズガニ")
        self.assertEqual(x["results"][0]["survey_year_count"],2)
    def test_invalid_groups_and_filters_rejected(self):
        candidates=[
            {"groups":()},{"groups":("fish","fish")},
            {"groups":("aquatic_insects",)},{"groups":("birds",)},
            {"groups":("fish","benthic_animals","birds")},
            {"groups":("fish",),"watershed_match":"invalid"},
            {"region":"広島県"},{"year":"2019 OR TRUE"},
            {"page":20001},{"per_page":26},
            {"organism":"x"*101}
        ]
        for kwargs in candidates:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    search(self.db,"region_explore",**{
                        **{"region":"chugoku"},**kwargs})
    def test_wildcards_and_sql_injection_no_match(self):
        for name in ("%", "_", "' OR 1=1 --"):
            x=search(self.db,"organism_to_watershed",organism=name)
            self.assertEqual(x["total"],0)
        x=search(self.db,"watershed_to_organism",watershed="%")
        self.assertEqual(x["total"],0)
    def test_no_side_effect_or_created_database(self):
        before=self.db.read_bytes()
        x=search(self.db,"region_explore",region="chugoku")
        self.assertFalse(x["wordpress_modified"])
        self.assertFalse(x["birds_survey_records_available"])
        self.assertFalse(x["aquatic_insect_subgroup_available"])
        self.assertEqual(self.db.read_bytes(),before)
        missing=Path(self.tmp.name)/"absent.sqlite"
        with self.assertRaises(FileNotFoundError):
            search(missing,"region_explore",region="chugoku")
        self.assertFalse(missing.exists())
    def test_api_rejects_other_unknown_and_missing_inputs(self):
        api=create_app(self.db)
        def get(path,query="",method="GET"):
            response={}
            def start(status,headers):
                response.update(status=status,headers=dict(headers))
            raw=b"".join(api({"PATH_INFO":path,"QUERY_STRING":query,
                              "REQUEST_METHOD":method},start))
            data=json.loads(raw) if raw.startswith(b"{") else raw
            return response,data
        x,y=get("/api/compact",urlencode([("direction","watershed_to_organism"),
                                        ("region","chugoku"),("watershed","太田川"),
                                        ("watershed_match","exact"),("group","fish"),("group","benthic_animals")]))
        self.assertEqual(x["status"],"200 OK")
        self.assertEqual(y["total"],4)
        self.assertEqual(x["headers"]["Cache-Control"],"no-store")
        for query in [
            "direction=region_explore&region=chugoku",
            "direction=region_explore&region=chugoku&group=birds",
            "direction=region_explore&region=chugoku&group=fish&group=fish",
            "direction=region_explore&region=chugoku&group=fish&per_page=100000",
            "direction=region_explore&region=chugoku&group=fish&prefecture=hiroshima",
            "direction=region_explore&region=chugoku&group=fish&region=kinki",
        ]:
            x,y=get("/api/compact",query)
            self.assertEqual(x["status"],"400 Bad Request")
        x,y=get("/",method="POST")
        self.assertEqual(x["status"],"405 Method Not Allowed")
        x,raw=get("/")
        self.assertEqual(x["status"],"200 OK")
        self.assertIn(b"<!doctype html>",raw)
        self.assertIn(b'noindex,nofollow',raw)

if __name__=="__main__":
    unittest.main()
