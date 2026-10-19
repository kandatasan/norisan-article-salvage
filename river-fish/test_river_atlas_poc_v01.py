"""Isolated offline atlas prototype regression tests. Never touch live systems."""
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from build_river_atlas_poc_v01 import collect, build

class TestAtlasPrototype(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=collect()

    def test_real_code_membership_and_identity(self):
        w=self.data["watershed"]
        self.assertEqual((w["code"],w["name"]),("870709","太田川"))
        self.assertGreater(len(self.data["rivers"]),20)
        codes=[x["riverCode"] for x in self.data["rivers"]]
        self.assertEqual(len(codes),len(set(codes)))
        self.assertTrue(all(c.startswith("870709") and len(c)==10 for c in codes))
        self.assertIn({"riverCode":"8707090023","riverName":"諸木川"},self.data["rivers"])

    def test_data_scope_remains_separate(self):
        self.assertEqual(self.data["riverPrefectureStatus"],"not_verified")
        self.assertEqual(self.data["directRiverSpeciesStatus"],"not_available")
        self.assertEqual(self.data["parentRiverStatus"],"not_available")
        self.assertEqual(self.data["fishJoinStatus"],
                         "name_and_region_context_only_not_official_code_identity")
        self.assertEqual(set(self.data["rivers"][0]),{"riverCode","riverName"})
        self.assertGreater(len(self.data["fishSurvey"]),0)
        self.assertTrue(all(f["region"]=="chugoku" and f["watershedLabel"]=="太田川"
                            for f in self.data["fishSurvey"]))
        self.assertNotIn("fish",self.data["rivers"][0])
        self.assertGreater(self.data["prefectureEvidence"]["localMentions"],0)

    def test_offline_zip_without_secrets_or_server_write(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)
            m=build(p/"output",p/"preview.zip")
            self.assertEqual(m["status"],"research_preview_only_no_server_or_wordpress_changes")
            self.assertEqual(m["riverCodes"],len(self.data["rivers"]))
            self.assertEqual(m["fishSurveyRecords"],len(self.data["fishSurvey"]))
            page=(p/"output/index.html").read_text(encoding="utf-8")
            js=(p/"output/data.js").read_text(encoding="utf-8")
            self.assertIn('id="tsu-river-atlas"',page)
            self.assertNotIn("<iframe",page.lower())
            self.assertNotIn("innerHTML",page)
            self.assertNotIn("wp-json",page)
            self.assertNotIn("fetch(",page)
            self.assertIn("window.TSURI_ATLAS_POC",js)
            one=(p/"output/standalone.html").read_text(encoding="utf-8")
            self.assertIn("window.TSURI_ATLAS_POC",one)
            self.assertNotIn('<script src="data.js"></script>',one)
            self.assertNotIn('"prefecture":"広島県"',js)
            with zipfile.ZipFile(p/"preview.zip") as z:
                self.assertIsNone(z.testzip())
                self.assertEqual(len(z.namelist()),4)
            with self.assertRaises(FileExistsError):
                build(p/"output")

if __name__=="__main__":
    unittest.main()
