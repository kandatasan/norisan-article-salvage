"""Real MLIT 2025 national biota taxonomy + historical watershed fish QA."""
import csv
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from build_biota_catalog_v18 import BIO,build,read_reference,search,CATEGORIES
from import_official_biota_v18 import FIELDS

class CompleteBiologicalNameBackboneV18(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.db=Path(cls.tmp.name)/"biota_v18.sqlite"
        cls.stats=build(cls.db)
        cls.m=json.loads((BIO/"official_biota_manifest_2025_v18.json").read_text(encoding="utf-8"))
    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_real_workbook_and_staged_name_row_counts(self):
        self.assertEqual(self.m["source_workbook_data_rows_including_structural"],37812)
        self.assertEqual(self.m["excluded_structural_rows_without_taxon_code"],164)
        self.assertEqual(self.stats["official_taxon_reference_rows"],37648)
        self.assertEqual(self.stats["distinct_literal_japanese_names_not_species_count"],37632)

    def test_all_seven_taxon_survey_memberships(self):
        target={
          "fish":1063,"benthic_animals":5642,"plants":5842,
          "birds":699,"amphibians_reptiles_mammals":372,
          "terrestrial_insects":27213,"plankton":365
        }
        self.assertEqual(self.stats["official_taxon_group_memberships"],target)
        self.assertEqual(set(target),set(CATEGORIES))
        c=sqlite3.connect(self.db)
        actual=dict(c.execute("SELECT survey_group,COUNT(*) FROM taxon_survey_groups GROUP BY survey_group"))
        self.assertEqual(actual,target);c.close()

    def test_not_37700_species_in_a_river(self):
        self.assertFalse(self.m["contains_species_occurrence_or_river_presence"])
        self.assertFalse(self.m["sensitive_locations_in_data"])
        self.assertEqual(self.m["publication_status"],"research_only_not_wordpress")
        self.assertEqual(self.stats["taxon_survey_rows_assigned_to_individual_river"],0)
        self.assertEqual(self.stats["taxon_survey_rows_assigned_to_prefecture"],0)
        self.assertEqual(self.stats["survey_label_matched_to_verified_taxonomic_identity"],0)

    def test_ayu_name_reference_and_yearly_fish_evidence_separated(self):
        r=search(self.db,name="アユ",group="fish",limit=100)
        self.assertGreater(r["total_reference_names"],0)
        self.assertGreater(r["total_fish_survey_records"],0)
        self.assertTrue(r["taxonomy_and_fish_data_separate"])
        self.assertTrue(all(t["confirmed_river_presence"] is None for t in r["reference_names"]))
        self.assertTrue(all(t["confirmed_prefecture_presence"] is None for t in r["reference_names"]))
        self.assertTrue(all(s["geographic_scope"]=="regional_watershed_year_only" for s in r["fish_survey_records"]))

    def test_nonfish_groups_do_not_acquire_fish_distribution(self):
        for g in ("birds","plants","terrestrial_insects","benthic_animals","plankton","amphibians_reptiles_mammals"):
            r=search(self.db,group=g,limit=2)
            self.assertGreater(r["total_reference_names"],0)
            self.assertEqual(r["total_fish_survey_records"],0)
            self.assertTrue(all(t["evidence_status"]=="name_reference_not_observation" for t in r["reference_names"]))

    def test_18814_fish_records_remain_waterbasin_only(self):
        self.assertEqual(self.stats["national_watershed_year_fish_evidence"],18814)
        c=sqlite3.connect(self.db)
        self.assertEqual(c.execute("SELECT COUNT(DISTINCT region) FROM watershed_year_fish_evidence").fetchone()[0],9)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM watershed_year_fish_evidence WHERE prefecture IS NOT NULL OR direct_tributary_river_id IS NOT NULL OR approved_taxon_code IS NOT NULL").fetchone()[0],0)
        self.assertEqual(c.execute("PRAGMA integrity_check").fetchone()[0],"ok")
        self.assertEqual(c.execute("PRAGMA foreign_key_check").fetchall(),[])
        c.close()

    def test_same_literal_name_distinct_codes_are_not_merged(self):
        c=sqlite3.connect(self.db)
        labels=c.execute("""
            SELECT japanese_name,COUNT(*) n FROM taxon_name_reference
            WHERE japanese_name!=''
            GROUP BY japanese_name HAVING n>1 LIMIT 1
        """).fetchone()
        self.assertIsNotNone(labels)
        label,n=labels
        r=search(self.db,name=label,limit=100)
        exact=[x for x in r["reference_names"] if x["japanese_name"]==label]
        self.assertEqual(len(exact),n)
        self.assertEqual(len({x["source_row"] for x in exact}),n)
        c.close()

    def test_taxonomy_search_by_scientific_name(self):
        r=search(self.db,scientific="Plecoglossus",limit=20)
        self.assertGreater(r["total_reference_names"],0)
        self.assertTrue(any("Plecoglossus" in x["scientific_name"] for x in r["reference_names"]))
        self.assertEqual(r["total_fish_survey_records"],0)

    def test_regional_fish_search_does_not_guess_prefecture(self):
        r=search(self.db,survey_name="アユ",region="chugoku",limit=60)
        self.assertEqual(r["total_reference_names"],0)
        self.assertGreater(r["total_fish_survey_records"],0)
        self.assertTrue(all(x["region"]=="chugoku" for x in r["fish_survey_records"]))

    def test_literal_query_wildcards_and_bad_group_rejected(self):
        with self.assertRaises(ValueError):search(self.db,group="all_life")
        with self.assertRaises(ValueError):search(self.db,region="沖縄県")
        with self.assertRaises(ValueError):search(self.db,limit=10000)
        empty=search(self.db,name="' OR 1=1 --")
        self.assertEqual(empty["total_reference_names"],0)
        self.assertEqual(search(self.db,name="%")["total_reference_names"],0)

    def test_csv_stored_raw_japanese_and_scientific_no_invented_id(self):
        with (BIO/"official_biota_reference_2025_v18.csv").open(encoding="utf-8",newline="") as f:
            rd=csv.DictReader(f)
            self.assertEqual(rd.fieldnames,FIELDS)
            first=next(rd)
            self.assertEqual(first["source_row"],"2")
            self.assertEqual(first["japanese_name"],"アルケラ属")
            self.assertEqual(first["scientific_name"],"Arcella")
            self.assertEqual(first["plankton"],"1")
        self.assertIn("2025",self.m["official_version_note"])
        self.assertIn("2026",self.m["official_version_note"])

    def test_refuses_db_overwrite(self):
        with self.assertRaises(FileExistsError):build(self.db)

if __name__=="__main__":
    unittest.main()
