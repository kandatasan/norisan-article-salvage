#!/usr/bin/env python3
"""Make compact 428-river x 4-category FULL original-label index from v05.

SOURCE: read-only historical MLIT survey SQLite (428 named river identities).
NO new biological observation, prefecture allocation, coordinates, web calls,
WordPress, MySQL, taxonomic species assertion, or modification of v05.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sqlite3
from urllib.parse import quote

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
PINNED_SOURCE_SHA="dfa193bc882dfbc1dc3c30dc226bf81bc2e3754007069fed1b25e3007f4c1dd1"
EXPECTED_RIVERS=428
EXPECTED_CONTEXTS=553351
EXPECTED_OLD_CODED_RIVERS=115
GROUPS=("fish","benthic_animals","birds","plants")
GROUP_DISPLAY={"fish":"魚類","benthic_animals":"底生動物","birds":"鳥類","plants":"植物"}

def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1048576),b""):h.update(chunk)
    return h.hexdigest()

def safe_db_read(path):
    p=Path(path).resolve()
    c=sqlite3.connect("file:"+quote(str(p),safe="/")+"?mode=ro",uri=True)
    c.execute("PRAGMA query_only=ON")
    return c

def build(source,out,report_dir):
    source,out,report_dir=Path(source).resolve(),Path(out).resolve(),Path(report_dir)
    if out.exists():raise FileExistsError(out)
    if sha(source)!=PINNED_SOURCE_SHA:raise ValueError("Source v05 research DB SHA256 changed")
    s=safe_db_read(source)
    d=sqlite3.connect(out)
    try:
        if s.execute("PRAGMA integrity_check").fetchone()[0]!="ok":raise ValueError("Original read-only SQLite corrupt")
        source_rivers=s.execute("SELECT COUNT(*) FROM name_first_rivers WHERE review_status='eligible'").fetchone()[0]
        source_contexts=s.execute("SELECT COUNT(*) FROM name_first_evidence").fetchone()[0]
        if source_rivers!=EXPECTED_RIVERS or source_contexts!=EXPECTED_CONTEXTS:
            raise ValueError("Unexpected code-optional base survey counts")
        d.execute("PRAGMA foreign_keys=ON")
        d.executescript("""
        CREATE TABLE river (
          identity_key TEXT PRIMARY KEY,
          source_region TEXT NOT NULL,
          source_authority TEXT NOT NULL,
          watershed_name TEXT NOT NULL,
          river_name TEXT NOT NULL,
          river_code TEXT,
          survey_contexts INTEGER NOT NULL,
          evidence_confidence TEXT NOT NULL CHECK(evidence_confidence IN
             ('approved_10digit','source_river_name_only')),
          UNIQUE(source_region,source_authority,watershed_name,river_name)
        );
        CREATE INDEX idx_river_name ON river(source_region,watershed_name,river_name);
        CREATE TABLE category_summary (
          identity_key TEXT NOT NULL REFERENCES river(identity_key),
          category TEXT NOT NULL,
          historical_contexts INTEGER NOT NULL,
          literal_name_count INTEGER NOT NULL,
          first_survey_year INTEGER,
          last_survey_year INTEGER,
          PRIMARY KEY(identity_key,category)
        );
        CREATE TABLE literal_taxon_label (
          taxon_key INTEGER PRIMARY KEY,
          identity_key TEXT NOT NULL REFERENCES river(identity_key),
          category TEXT NOT NULL,
          recorded_name TEXT NOT NULL,
          historical_contexts INTEGER NOT NULL,
          first_survey_year INTEGER,
          last_survey_year INTEGER,
          cited_source_count INTEGER NOT NULL,
          UNIQUE(identity_key,category,recorded_name)
        );
        CREATE INDEX idx_taxon_category_record_count
            ON literal_taxon_label(identity_key,category,historical_contexts DESC,recorded_name);
        CREATE INDEX idx_taxon_reverse_name
            ON literal_taxon_label(recorded_name,category);
        CREATE TABLE source_catalog (
          source_id INTEGER PRIMARY KEY,
          source_category TEXT NOT NULL,
          source_url TEXT NOT NULL,
          source_sha256 TEXT NOT NULL
        );
        CREATE TABLE taxon_source_proof (
          taxon_key INTEGER NOT NULL REFERENCES literal_taxon_label(taxon_key),
          source_id INTEGER NOT NULL REFERENCES source_catalog(source_id),
          historical_contexts INTEGER NOT NULL,
          year_min INTEGER,
          year_max INTEGER,
          PRIMARY KEY(taxon_key,source_id)
        );
        """)
        rivers=list(s.execute("""
          SELECT identity_key,region,source_authority,watershed_name,river_name,
                 river_code,survey_record_contexts,code_confidence
          FROM name_first_rivers WHERE review_status='eligible'
          ORDER BY identity_key
        """))
        if sum(r[6] for r in rivers)!=EXPECTED_CONTEXTS:raise ValueError("River conservation failed")
        d.executemany("INSERT INTO river VALUES(?,?,?,?,?,?,?,?)",rivers)
        d.executemany("INSERT INTO source_catalog VALUES(?,?,?,?)",
                      s.execute("SELECT id,group_id,source_url,source_sha256 FROM sources"))
        # Retain EVERY literal classification label (not only two demo examples).
        # Grouping by exact label spelling does not assert scientific synonymy.
        count=0
        for key,cat,label,total,first,last,source_count in s.execute("""
          SELECT n.identity_key,src.group_id,l.recorded_name,
                 COUNT(*) contexts,MIN(e.survey_year),MAX(e.survey_year),
                 COUNT(DISTINCT e.source_id) document_count
          FROM river_evidence e
          JOIN river_context rc ON rc.id=e.river_context_id
          JOIN name_first_context_links k ON k.context_id=rc.id
          JOIN name_first_rivers n ON n.identity_key=k.identity_key
          JOIN sources src ON src.id=e.source_id
          JOIN labels l ON l.id=e.label_id
          WHERE n.review_status='eligible'
          GROUP BY n.identity_key,src.group_id,l.recorded_name
          ORDER BY n.identity_key,src.group_id,l.recorded_name
        """):
            if cat not in GROUPS or not label:
                raise ValueError("Unrecognized category or empty literal taxon label")
            d.execute("""
                INSERT INTO literal_taxon_label(
                    identity_key,category,recorded_name,historical_contexts,
                    first_survey_year,last_survey_year,cited_source_count
                ) VALUES(?,?,?,?,?,?,?)
            """,(key,cat,label,total,first,last,source_count))
            count+=1
        if not count:raise ValueError("No labels copied")
        # Source URLs are preserved PER literal label; not just a global one.
        count_proof=0
        for key,cat,label,sid,total,first,last in s.execute("""
          SELECT n.identity_key,src.group_id,l.recorded_name,e.source_id,
                 COUNT(*),MIN(e.survey_year),MAX(e.survey_year)
          FROM river_evidence e
          JOIN river_context rc ON rc.id=e.river_context_id
          JOIN name_first_context_links k ON k.context_id=rc.id
          JOIN name_first_rivers n ON n.identity_key=k.identity_key
          JOIN sources src ON src.id=e.source_id
          JOIN labels l ON l.id=e.label_id
          WHERE n.review_status='eligible'
          GROUP BY n.identity_key,src.group_id,l.recorded_name,e.source_id
          ORDER BY n.identity_key,src.group_id,l.recorded_name,e.source_id
        """):
            found=d.execute("""
              SELECT taxon_key FROM literal_taxon_label
              WHERE identity_key=? AND category=? AND recorded_name=?
            """,(key,cat,label)).fetchone()
            if not found:raise ValueError("Source proof has no literal taxon")
            d.execute("INSERT INTO taxon_source_proof VALUES(?,?,?,?,?)",
                      (found[0],sid,total,first,last))
            count_proof+=1
        if not count_proof:raise ValueError("No source evidence")
        sums=list(d.execute("""
          SELECT identity_key,category,SUM(historical_contexts),
                 COUNT(*),MIN(first_survey_year),MAX(last_survey_year)
          FROM literal_taxon_label GROUP BY identity_key,category
        """))
        d.executemany("""
          INSERT INTO category_summary(identity_key,category,historical_contexts,
                                      literal_name_count,first_survey_year,last_survey_year)
          VALUES(?,?,?,?,?,?)
        """,sums)
        # Add explicit zero categories: 0 means unconfirmed in these records,
        # not biological absence.
        for key,*_ in rivers:
            for cat in GROUPS:
                d.execute("""
                  INSERT OR IGNORE INTO category_summary
                  VALUES(?,?,0,0,NULL,NULL)
                """,(key,cat))
        d.commit()

        if d.execute("PRAGMA integrity_check").fetchone()[0]!="ok":raise ValueError("New index corrupt")
        if d.execute("PRAGMA foreign_key_check").fetchall():raise ValueError("New index foreign-key error")
        total_labels=d.execute("SELECT COUNT(*) FROM literal_taxon_label").fetchone()[0]
        total_proofs=d.execute("SELECT COUNT(*) FROM taxon_source_proof").fetchone()[0]
        if count!=total_labels or count_proof!=total_proofs:raise ValueError("Inserted row count wrong")
        if d.execute("SELECT SUM(historical_contexts) FROM literal_taxon_label").fetchone()[0]!=EXPECTED_CONTEXTS:
            raise ValueError("Survey contexts changed during grouping")
        if d.execute("SELECT SUM(historical_contexts) FROM taxon_source_proof").fetchone()[0]!=EXPECTED_CONTEXTS:
            raise ValueError("Survey source proofs fail conservation")
        if d.execute("SELECT SUM(historical_contexts) FROM category_summary").fetchone()[0]!=EXPECTED_CONTEXTS:
            raise ValueError("Category rollup fails conservation")
        if d.execute("SELECT COUNT(*) FROM category_summary").fetchone()[0]!=EXPECTED_RIVERS*4:
            raise ValueError("Every river must have four independent category windows")
        # Regression: named-river index is NOT a reclassification of physical
        # species/river status; the old 115 code-confirmed rivers remain tagged.
        if d.execute("SELECT COUNT(*) FROM river WHERE evidence_confidence='approved_10digit'").fetchone()[0]!=EXPECTED_OLD_CODED_RIVERS:
            raise ValueError("Confirmed code identity changed")
        # Explicitly keep unsurveyed category zeros and source-list labels.
        if d.execute("SELECT historical_contexts FROM category_summary WHERE identity_key=(SELECT identity_key FROM river WHERE watershed_name='太田川' AND river_name='根谷川') AND category='birds'").fetchone()[0]!=0:
            raise ValueError("Never promote watershed bird records into Neya")
        report_dir.mkdir(parents=True,exist_ok=True)
        with (report_dir/"river_biota_category_counts_v08.csv").open("w",encoding="utf-8",newline="") as f:
            writer=csv.writer(f)
            writer.writerow(["identity_key","region","watershed","river","category","historical_contexts","literal_names_not_species","year_min","year_max"])
            writer.writerows(d.execute("""
              SELECT r.identity_key,r.source_region,r.watershed_name,r.river_name,
                     c.category,c.historical_contexts,c.literal_name_count,
                     c.first_survey_year,c.last_survey_year
              FROM category_summary c JOIN river r ON c.identity_key=r.identity_key
              ORDER BY r.source_region,r.watershed_name,r.river_name,c.category
            """))
        bycat=[dict(zip(("category","historic_contexts","distinct_river_category_name_pairs","source_proof_rows"),r))
               for r in d.execute("""
               SELECT c.category,SUM(c.historical_contexts),SUM(c.literal_name_count),
                      (SELECT COUNT(*) FROM taxon_source_proof p
                       JOIN literal_taxon_label l ON l.taxon_key=p.taxon_key
                       WHERE l.category=c.category)
               FROM category_summary c GROUP BY c.category ORDER BY c.category
               """)]
        report={
           "version":"v08","input_sha256":PINNED_SOURCE_SHA,
           "named_rivers":EXPECTED_RIVERS,"historical_survey_contexts":EXPECTED_CONTEXTS,
           "category_windows":EXPECTED_RIVERS*4,
           "distinct_river_category_literal_label_rows":total_labels,
           "literal_taxon_source_evidence_rows":total_proofs,
           "source_documents":d.execute("SELECT COUNT(*) FROM source_catalog").fetchone()[0],
           "category_breakdown":bycat,
           "zero_record_windows":d.execute("SELECT COUNT(*) FROM category_summary WHERE historical_contexts=0").fetchone()[0],
           "unit":"historical river x category x year x literal name research contexts, not individuals or number of biological species",
           "taxonomic_synonyms_or_identification_not_normalized":True,
           "prefecture_location_not_inferred":True,
           "river_code_optional":True,
           "no_watershed_biota_promoted":True,
           "no_live_website_or_production_database_modified":True
        }
        (report_dir/"all_taxa_label_audit_v08.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(report,ensure_ascii=False))
        return report
    finally:
        s.close();d.close()

if __name__=="__main__":
    a=argparse.ArgumentParser();a.add_argument("--source",required=True)
    a.add_argument("--out",required=True);a.add_argument("--report-dir",required=True)
    args=a.parse_args();build(args.source,args.out,args.report_dir)
