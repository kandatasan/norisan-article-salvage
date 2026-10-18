"""No biology category attribution is allowed from an URL suffix alone."""
import json
from pathlib import Path
import tempfile
import unittest

from audit_official_source_index_v21 import inventory, REGIONS, INDEX, PINS

class OfficialRegionalIndexV21(unittest.TestCase):
    @staticmethod
    def sample_html(missing=None):
        pins=json.loads(Path(PINS).read_text(encoding="utf-8"))
        known={r["region"]:r["source_url"] for r in pins["regions"]}
        lines=['<html><body><a href="https://evil.test/RT87_X02.zip">unsafe</a>']
        for code,region in REGIONS.items():
            if region!=missing:
                lines.append('<a href="'+known[region]+'"><img src="button.gif"></a>')
            lines.append('<a href="download/slist/RT'+code+'_P02.zip">unreviewed group</a>')
            lines.append('<a href="download/slist/RT'+code+'_T02.zip">unreviewed group</a>')
        lines.append('</body></html>')
        return "\n".join(lines)
    def test_all_regions_retain_benthic_source_pins(self):
        x=inventory(self.sample_html())
        self.assertEqual(x["candidate_url_count"],27)
        self.assertEqual(x["existing_v19_benthic_sources"],9)
        self.assertEqual(len(x["regions"]),9)
        for region in x["regions"]:
            self.assertEqual(region["candidate_count"],3)
            known=[c for c in region["candidates"] if c["verified_by_previous_v19"]]
            self.assertEqual(len(known),1)
            self.assertEqual(known[0]["survey_category"],"benthic_animals")
    def test_unreviewed_suffix_is_not_assumed_plant_or_bird(self):
        x=inventory(self.sample_html())
        self.assertEqual(x["new_survey_categories_approved"],0)
        for r in x["regions"]:
            for c in r["candidates"]:
                if not c["verified_by_previous_v19"]:
                    self.assertIsNone(c["survey_category"])
                    self.assertFalse(c["archive_sha256_checked"])
                    self.assertFalse(c["source_schema_checked"])
        self.assertFalse(x["raw_archive_downloaded"])
        self.assertFalse(x["wordpress_modified"])
        self.assertFalse(x["individual_river_or_prefecture_inferred"])
    def test_missing_previous_approved_official_link_is_fatal(self):
        with self.assertRaises(ValueError):
            inventory(self.sample_html(missing="chugoku"))
    def test_wrong_source_authority_is_fatal(self):
        with self.assertRaises(ValueError):
            inventory(self.sample_html(),index_url="https://example.com/")
    def test_other_hosts_not_accepted(self):
        x=inventory(self.sample_html())
        self.assertTrue(x["ignored_unrelated_or_unsafe_links"]>=1)
        for r in x["regions"]:
            for c in r["candidates"]:
                self.assertTrue(c["url"].startswith("https://www.nilim.go.jp/"))
    def test_no_region_source_is_silently_generated(self):
        html=self.sample_html().replace("RT85_P02.zip","RT85_ZZZZZ.dat")
        x=inventory(html)
        chubu=next(y for y in x["regions"] if y["region"]=="chubu")
        self.assertEqual(chubu["candidate_count"],2)

if __name__=="__main__":
    unittest.main()
