"""Benthic national source verification and biology+fish query regression."""
from collections import Counter
from pathlib import Path
import sqlite3
import tempfile
import unittest

from import_national_benthic_v19 import VALID_REGIONS,read_stage,pin,aggregate_benthic
from build_biota_with_benthic_v19 import build,search,search_benthic

class BenthicNineRegionsV19(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.all={region:read_stage(region) for region in VALID_REGIONS}
        cls.tmp=tempfile.TemporaryDirectory()
        cls.db=Path(cls.tmp.name)/"full_biota.sqlite"
        cls.stats=build(cls.db)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_all_nine_pinned_official_archives_available(self):
        self.assertEqual(len(self.all),9)
        for name,(rows,m) in self.all.items():
            source,index=pin(name)
            self.assertEqual(m["source_url"],source["source_url"])
            self.assertEqual(m["source_sha256"],source["checksum_sha256"])
            self.assertGreater(len(rows),100)
            self.assertEqual(len(rows),m["aggregated_records"])
            self.assertEqual(m["source_taxon_group"],"benthic_animals_not_individually_classified_as_crab_or_shrimp")

    def test_benthic_name_count_not_independent_species(self):
        self.assertGreater(self.stats["benthic_watershed_year_name_records"],20000)
        self.assertGreater(self.stats["benthic_distinct_literal_labels_not_species_count"],100)
        self.assertEqual(self.stats["benthic_regions"],9)
        self.assertGreater(self.stats["benthic_region_watershed_pairs"],9)

    def test_2025_taxonomic_reference_and_old_fish_unmodified(self):
        self.assertEqual(self.stats["national_taxonomic_reference_names"],37648)
        self.assertEqual(self.stats["existing_national_fish_watershed_records"],18814)
        self.assertFalse(self.stats["wordpress_updated"])
        self.assertFalse(self.stats["published"])

    def test_no_specific_river_or_prefecture_or_taxon_identity(self):
        c=sqlite3.connect(self.db)
        self.assertEqual(c.execute(
            "SELECT COUNT(*) FROM watershed_year_benthic_evidence WHERE "
            "approved_prefecture IS NOT NULL OR approved_individual_river_code IS NOT NULL OR "
            "approved_taxon_code IS NOT NULL").fetchone()[0],0)
        self.assertEqual(c.execute("PRAGMA integrity_check").fetchone()[0],"ok")
        self.assertEqual(c.execute("PRAGMA foreign_key_check").fetchall(),[])
        c.close()
        self.assertEqual(self.stats["verified_individual_river_locations"],0)
        self.assertEqual(self.stats["taxon_benthic_identity_links_approved"],0)

    def test_chugoku_benthic_record_scoped_to_region_and_watershed(self):
        x=search_benthic(self.db,region="chugoku",limit=15)
        self.assertGreater(x["total_benthic_survey_records"],1000)
        self.assertTrue(all(r["region"]=="chugoku" for r in x["benthic_survey_records"]))
        self.assertTrue(all(r["scope"]=="regional_watershed_year_only" for r in x["benthic_survey_records"]))
        self.assertTrue(all(r["verified_individual_river"] is None and
                            r["verified_prefecture"] is None and
                            r["accepted_taxon_code"] is None
                            for r in x["benthic_survey_records"]))

    def test_name_filtered_benthic_survey_not_alleged_location(self):
        x=search_benthic(self.db,benthic_name="カワゲラ",limit=10)
        self.assertGreater(x["total_benthic_survey_records"],0)
        self.assertTrue(all("カワゲラ" in r["literal_recorded_name"] for r in x["benthic_survey_records"]))

    def test_taxonomy_and_benthic_source_names_separate(self):
        x=search(self.db,name="カワゲラ",group="benthic_animals",limit=15)
        self.assertGreater(x["total_reference_names"],0)
        self.assertGreater(x["total_benthic_survey_records"],0)
        self.assertTrue(x["biological_taxonomy_river_fish_and_benthic_are_not_auto_joined"])
        self.assertTrue(all(r["confirmed_river_presence"] is None for r in x["reference_names"]))

    def test_no_reinterpretation_of_original_taxon_species(self):
        x=search(self.db,group="benthic_animals",limit=2)
        self.assertGreater(x["total_reference_names"],0)
        self.assertEqual(x["total_benthic_survey_records"],0)
        self.assertEqual(x["total_fish_survey_records"],0)

    def test_new_benthic_source_does_not_delete_old_fish(self):
        x=search(self.db,survey_name="アユ",region="chugoku",limit=20)
        self.assertGreater(x["total_fish_survey_records"],0)
        self.assertEqual(x["total_benthic_survey_records"],0)
        self.assertTrue(all(r["region"]=="chugoku" for r in x["fish_survey_records"]))

    def test_query_safe_literals(self):
        result=search_benthic(self.db,benthic_name="' OR 1=1 --")
        self.assertEqual(result["total_benthic_survey_records"],0)
        result=search_benthic(self.db,benthic_name="%")
        self.assertEqual(result["total_benthic_survey_records"],0)
        with self.assertRaises(ValueError):
            search_benthic(self.db,region="広島県")
        with self.assertRaises(ValueError):
            search_benthic(self.db,limit=2000)

    def test_aggregator_rejects_mixed_legacy_species_and_incomplete(self):
        samples=[
            {"C":"底生動物","F":"太田川","G":"2020","J":"モクズガニ"},
            {"C":"底生動物","F":"太田川","G":"2020","J":"モクズガニ"},
            {"C":"魚介類","F":"太田川","G":"2010","J":"モクズガニ"},
            {"C":"底生動物","F":"","G":"2020","J":"モクズガニ"},
            {"C":"魚類","F":"太田川","G":"2020","J":"アユ"},
        ]
        with self.assertRaises(ValueError):
            aggregate_benthic(samples)
        long=samples[:2]*75+samples[2:]
        rows,meta=aggregate_benthic(long)
        self.assertEqual(rows,[("太田川","2020","モクズガニ")])
        self.assertGreater(meta["excluded_by_reason"]["not_explicit_benthic_category"],0)
        self.assertGreater(meta["excluded_by_reason"]["no_watershed_or_name"],0)

    def test_no_sqlite_overwrite(self):
        with self.assertRaises(FileExistsError):
            build(self.db)

if __name__=="__main__":
    unittest.main()
