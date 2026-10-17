"""Offline tests for nationwide fish search (no geographic attribution)."""
import csv
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from search_nationwide_v06 import search,HEADERS,HERE

class NationwideFishSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.root=Path(cls.tmp.name)
        for name in ("nationwide_sources_v06.json","akaza_local_names_v03.csv","legal_designations_v04.csv"):
            shutil.copyfile(HERE/name,cls.root/name)
        stage=cls.root/"nationwide-staged"/"chugoku"
        stage.mkdir(parents=True)
        with (stage/"watershed_year_fish.csv").open("w",encoding="utf-8",newline="") as f:
            w=csv.writer(f)
            w.writerow(HEADERS)
            for water,year,fish in [
                ("太田川","2020","アカザ"),("太田川","2021","アユ"),
                ("高梁川","2022","ブルーギル")]:
                w.writerow(["chugoku",water,year,fish,"https://www.nilim.go.jp/fish.zip","a"*64])
        (stage/"manifest.json").write_text(json.dumps({
            "region":"chugoku","source_sha256":"a"*64,
            "status":"staged_not_published",
            "prefecture_mapping":"not_inferred"
        },ensure_ascii=False),encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_alias(self):
        r=search(root=self.root,region="chugoku",name="てんきり")
        self.assertEqual(r["total"],1)
        self.assertEqual(r["records"][0]["fish_name_as_recorded"],"アカザ")

    def test_year_and_water(self):
        r=search(root=self.root,region="chugoku",year="2021",watershed="太田川")
        self.assertEqual(r["total"],1)
        self.assertEqual(r["records"][0]["fish_name_as_recorded"],"アユ")

    def test_region_not_prefecture_or_tributary(self):
        r=search(root=self.root,region="chugoku")
        self.assertEqual(r["total"],3)
        self.assertTrue(all(row["prefecture"] is None for row in r["records"]))
        self.assertTrue(all(row["river_name"] is None for row in r["records"]))
        self.assertTrue(all(row["direct_tributary_evidence"] is False for row in r["records"]))

    def test_legislation_does_not_infer_origin(self):
        r=search(root=self.root,region="chugoku",name="ブルーギル")
        self.assertEqual(r["total"],1)
        self.assertEqual(r["records"][0]["legal_status"],"specified_alien")
        self.assertEqual(r["records"][0]["origin_status"],"unreviewed")

    def test_unknown_region_rejected(self):
        with self.assertRaises(ValueError):
            search(root=self.root,region="tokyo")

    def test_all_requires_all_sources(self):
        with self.assertRaises(FileNotFoundError):
            search(root=self.root)

    def test_empty_is_not_absence(self):
        r=search(root=self.root,region="chugoku",name="存在しない名前")
        self.assertEqual(r["total"],0)
        self.assertIn("不在の証拠ではありません",r["notice"])

if __name__=="__main__":
    unittest.main()
