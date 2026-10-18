"""Offline beta artifact QA: real source counts, no cross-table assignments, ZIP."""
import csv
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from build_river_beta_v15 import build,create_payload,official_river_codes,local_mentions,census_fish

class OfflineBetaV15(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload=create_payload()
        cls.tmp=tempfile.TemporaryDirectory()
        cls.base=Path(cls.tmp.name)
        cls.out=cls.base/"preview"
        cls.zip=cls.base/"preview.zip"
        cls.manifest=build(cls.out,cls.zip)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_all_official_counts(self):
        self.assertEqual(len(self.payload["riverCodes"]),35449)
        self.assertEqual(len(self.payload["localEvidence"]),1449)
        self.assertEqual(len(self.payload["fishCensus"]),18814)
        self.assertEqual(len(self.payload["prefectures"]),47)

    def test_source_categories_separate(self):
        sources=self.payload["localEvidence"]
        self.assertEqual(len([s for s in sources if s[2]=="river"]),996)
        self.assertEqual(len([s for s in sources if s[2]=="watershed"]),443)
        self.assertEqual(len([s for s in sources if s[2]=="planning_region"]),10)
        self.assertEqual(len({s[6] for s in sources}),1449)

    def test_moroki_is_not_joined_to_prefecture(self):
        codes=[c for c in self.payload["riverCodes"] if c[0]=="8707090023"]
        self.assertEqual(len(codes),1)
        self.assertEqual(codes[0][1],"諸木川")
        self.assertEqual(codes[0][2],"太田川")
        self.assertEqual(len(codes[0]),4)
        local=[s for s in self.payload["localEvidence"] if s[1]=="諸木川"]
        self.assertTrue(any(s[0]=="広島県" for s in local))
        self.assertTrue(all(len(s)==9 and s[6].startswith(("HR-","HM-","TP-","YR-","CW-","NP-","AP-")) for s in local))

    def test_no_species_attached_to_a_particular_river(self):
        self.assertTrue(all(len(c)==4 for c in self.payload["riverCodes"]))
        self.assertTrue(all(len(s)==9 for s in self.payload["localEvidence"]))
        self.assertTrue(all(len(f)==5 for f in self.payload["fishCensus"]))
        self.assertIn("not_tributary",self.payload["meta"]["censusScope"])

    def test_nine_survey_regions_no_prefecture_or_river(self):
        fish=self.payload["fishCensus"]
        self.assertEqual(len(set(r[0] for r in fish)),9)
        self.assertTrue(all(r[0] in self.payload["regionLabels"] for r in fish))

    def test_ui_files_are_portable(self):
        for name in ("index.html","style.css","search-core.js","app.js","data.js","manifest.json"):
            self.assertTrue((self.out/name).is_file())
        html=(self.out/"index.html").read_text(encoding="utf-8")
        self.assertIn('src="data.js"',html)
        self.assertNotIn('src="https:',html)
        self.assertNotIn("<iframe",html)
        self.assertNotIn("fetch(",(self.out/"app.js").read_text(encoding="utf-8"))
        self.assertNotIn("innerHTML",(self.out/"app.js").read_text(encoding="utf-8"))

    def test_zip_has_exact_portable_assets(self):
        with zipfile.ZipFile(self.zip) as z:
            names=z.namelist()
        self.assertEqual(len(names),6)
        self.assertTrue(all(x.startswith("tsurikue-river-beta/") for x in names))

    def test_manifest_non_public_and_source_count(self):
        self.assertEqual(self.manifest["counts"]["rivers"],35449)
        self.assertEqual(self.manifest["counts"]["sourceMentions"],1449)
        self.assertEqual(self.manifest["counts"]["fishCensus"],18814)
        self.assertEqual(self.manifest["status"],"offline_preview_only_not_WordPress_published")
        self.assertFalse(self.manifest["requires_network"])

    def test_source_prefectures_all_47_not_completeness(self):
        self.assertEqual({r[0] for r in self.payload["localEvidence"]},set(self.payload["prefectures"]))
        self.assertTrue(self.payload["meta"]["websitePublished"] is False)

    def test_generator_refuses_existing_nonempty_folder(self):
        with self.assertRaises(FileExistsError):
            build(self.out)

if __name__=="__main__":unittest.main()
