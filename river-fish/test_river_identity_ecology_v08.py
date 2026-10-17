"""Verify official-code matching is review-only and narrative fish stay source-scoped."""
import csv
from pathlib import Path
import sqlite3
import tempfile
import unittest

from review_hiroshima_code_links_v08 import compute_candidates, export, FIELDS, local_evidence
from river_review_catalog_v08 import build_database,query,verify_narratives

class RiverIdentityAndEcologyV08(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidates,cls.manifest=compute_candidates()
        cls.tmp=tempfile.TemporaryDirectory()
        cls.db=Path(cls.tmp.name)/"review.sqlite"
        cls.stats=build_database(cls.db)
    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_164_source_records(self):
        src=local_evidence()
        self.assertEqual(len(src),164)
        self.assertEqual(len({x["id"] for x in src}),164)
        self.assertEqual(self.manifest["base_registry_evidence"],66)
        self.assertEqual(self.manifest["municipality_mention_evidence"],98)

    def test_each_source_has_one_or_more_review_rows(self):
        self.assertEqual(len({x["local_evidence_id"] for x in self.candidates}),164)
        self.assertGreaterEqual(len(self.candidates),164)

    def test_no_identity_or_prefecture_auto_approved(self):
        self.assertTrue(all(c["identity_approved"]=="false" and
                            c["prefecture_attribution_approved"]=="false" and
                            c["fish_attribution_approved"]=="false"
                            for c in self.candidates))
        self.assertEqual(self.stats["approved_code_links"],0)

    def test_moroki_official_code_is_candidate_not_approval(self):
        moroki=[x for x in self.candidates if x["river_name_in_source"]=="諸木川"]
        self.assertGreaterEqual(len(moroki),1)
        self.assertIn("8707090023",{x["candidate_river_code"] for x in moroki})
        self.assertTrue(all(x["review_status"]!="approved" for x in moroki))
        self.assertTrue(all(x["match_basis"]=="exact_name_and_source_watershed" for x in moroki))

    def test_same_name_without_watershed_remains_ambiguous(self):
        mij=[x for x in self.candidates if x["local_evidence_type"]=="municipality_listing"]
        self.assertTrue(all(x["watershed_in_source"]=="" for x in mij))
        self.assertTrue(all(x["match_basis"] in
                            ("exact_name_only_no_source_watershed","no_match_with_current_scope")
                            for x in mij))
        self.assertTrue(any(x["candidate_count_for_evidence"]>1 for x in mij))

    def test_source_review_manifest_totals(self):
        d=self.manifest["candidate_counts_by_evidence_and_status"]
        base=sum(v for k,v in d.items() if k.startswith("river_register_2021__"))
        mentions=sum(v for k,v in d.items() if k.startswith("municipality_listing__"))
        self.assertEqual(base,66)
        self.assertEqual(mentions,98)

    def test_nine_narrative_fish_labels(self):
        fish=verify_narratives()
        self.assertEqual(len(fish),9)
        self.assertIn("アユ",{r["fish_label_as_written"] for r in fish})
        self.assertIn("ブルーギル",{r["fish_label_as_written"] for r in fish})
        self.assertIn("スナヤツメ",{r["fish_label_as_written"] for r in fish})

    def test_narrative_not_field_survey(self):
        for r in verify_narratives():
            self.assertEqual(r["survey_year"],"")
            self.assertEqual(r["national_river_code"],"")
            self.assertEqual(r["evidence_scope"],"named_river_general_no_specific_site")
            self.assertEqual(r["publication_status"],"research_only_not_website_published")

    def test_sensitive_species_not_located(self):
        fish=[x for x in verify_narratives() if x["sensitive_species_flag"]=="true"]
        self.assertGreaterEqual(len(fish),2)
        self.assertTrue(all(x["survey_year"]=="" and x["national_river_code"]==""
                            for x in fish))

    def test_review_search_moroki_and_kurose(self):
        moroki=query(self.db,river_name="諸木川")
        self.assertGreaterEqual(moroki["candidate_total"],1)
        self.assertEqual(moroki["narrative_total"],0)
        kurose=query(self.db,river_name="黒瀬川",prefecture="広島県")
        self.assertGreaterEqual(kurose["candidate_total"],1)
        self.assertEqual(kurose["narrative_total"],9)
        self.assertEqual(kurose["approved_fish_to_official_code_links"],0)

    def test_sqlite_species_review_never_approves(self):
        c=sqlite3.connect(self.db)
        self.assertEqual(c.execute("select count(*) from narrative_fish_mentions where national_river_code!=''").fetchone()[0],0)
        self.assertEqual(c.execute("select count(*) from identity_candidates where identity_approved!='false'").fetchone()[0],0)
        self.assertEqual(c.execute("pragma integrity_check").fetchone()[0],"ok")
        c.close()

    def test_export_headers_and_empty_are_safe(self):
        with tempfile.TemporaryDirectory() as td:
            export(td,self.candidates,self.manifest)
            with (Path(td)/"hiroshima_river_code_candidates_v08.csv").open(encoding="utf-8",newline="") as f:
                r=csv.DictReader(f)
                self.assertEqual(r.fieldnames,FIELDS)
                self.assertEqual(sum(1 for _ in r),len(self.candidates))

    def test_no_overwrite(self):
        with self.assertRaises(FileExistsError):
            build_database(self.db)

if __name__=="__main__":unittest.main()
