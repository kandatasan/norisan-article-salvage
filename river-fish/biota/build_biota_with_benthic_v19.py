#!/usr/bin/env python3
"""Add nationwide historical BENTHIC survey context to v1.8 taxonomy + fish.

The 9 official sources are NOT living-species location evidence for a specific
river or prefecture. Three deliberately independent data concepts remain:
  official taxon reference, fish watershed/year labels, benthic watershed/year
  labels. Literal-name matching in the UI is NOT taxon-ID determination.

All data are research-only, not pushed to WordPress. Dataset CSVs come from
separately verified GitHub Actions artifacts rather than checked-in raw ZIPs.
"""
import argparse
import json
from pathlib import Path
import sqlite3

from build_biota_catalog_v18 import build as build_v18, search as search_v18
from import_national_benthic_v19 import read_stage,VALID_REGIONS,BASE

NOTICE=("底生動物の名称は国交省の過去の水系・調査年度別の確認種掲載記録です。"
        "特定の支流や都道府県への帰属、現在の生息、和名と2025分類コードの厳密な一致、"
        "エビ・カニか水生昆虫かの分類まで、この資料だけで確定したものではありません。")

def build(db,root=BASE):
    db=Path(db)
    if db.exists():
        raise FileExistsError("Research biota DB already exists: no overwrite")
    base=build_v18(db)
    conn=sqlite3.connect(str(db))
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        conn.executescript("""
            CREATE TABLE watershed_year_benthic_evidence (
              source_row_id INTEGER PRIMARY KEY,
              region TEXT NOT NULL,
              watershed_name TEXT NOT NULL,
              survey_year TEXT NOT NULL,
              literal_recorded_name TEXT NOT NULL,
              official_source_url TEXT NOT NULL,
              source_zip_sha256 TEXT NOT NULL,
              scope TEXT NOT NULL CHECK(scope='regional_watershed_year_only'),
              approved_prefecture TEXT CHECK(approved_prefecture IS NULL),
              approved_individual_river_code TEXT CHECK(approved_individual_river_code IS NULL),
              approved_taxon_code TEXT CHECK(approved_taxon_code IS NULL)
            );
            CREATE UNIQUE INDEX uq_benthic_unique_source
                ON watershed_year_benthic_evidence(region,watershed_name,survey_year,literal_recorded_name);
            CREATE INDEX idx_benthic_region ON watershed_year_benthic_evidence(region);
            CREATE INDEX idx_benthic_name ON watershed_year_benthic_evidence(literal_recorded_name);
            CREATE INDEX idx_benthic_watershed ON watershed_year_benthic_evidence(watershed_name);
            CREATE INDEX idx_benthic_year ON watershed_year_benthic_evidence(survey_year);
        """)
        count=0;waters=set();labels=set();manifest=[]
        for region in VALID_REGIONS:
            rows,m=read_stage(region,root)
            if not rows:raise ValueError("Empty regional benthic source")
            payload=[]
            for r in rows:
                count+=1
                payload.append((
                  count,r["region"],r["watershed"],r["survey_year"],
                  r["recorded_name"],r["source_url"],r["source_sha256"],
                  "regional_watershed_year_only",None,None,None
                ))
                waters.add((region,r["watershed"]))
                labels.add(r["recorded_name"])
            conn.executemany("""
                INSERT INTO watershed_year_benthic_evidence VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,payload)
            manifest.append({"region":region,"rows":len(rows),"source_sha256":m["source_sha256"],
                             "watersheds":m["unique_watersheds"]})
        conn.commit()
        if count!=conn.execute("SELECT COUNT(*) FROM watershed_year_benthic_evidence").fetchone()[0]:
            raise ValueError("Partial benthic research database insert")
        if conn.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
            raise ValueError("Benthic database integrity error")
        if conn.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("Benthic database referential integrity error")
        return {
          "benthic_regions":len(VALID_REGIONS),
          "benthic_watershed_year_name_records":count,
          "benthic_region_watershed_pairs":len(waters),
          "benthic_distinct_literal_labels_not_species_count":len(labels),
          "regions":manifest,
          "national_taxonomic_reference_names":base["official_taxon_reference_rows"],
          "existing_national_fish_watershed_records":base["national_watershed_year_fish_evidence"],
          "verified_individual_river_locations":0,
          "taxon_benthic_identity_links_approved":0,
          "wordpress_updated":False,
          "published":False,
          "warning":NOTICE
        }
    finally:
        conn.close()

def contains(text):
    return "%"+str(text).replace("\\","\\\\").replace("%","\\%").replace("_","\\_")+"%"

def search_benthic(db,benthic_name="",region="",watershed="",year="",limit=25,offset=0):
    if region and region not in VALID_REGIONS:
        raise ValueError("Region must be one of the nine official source regions")
    if not 1<=limit<=100 or offset<0:raise ValueError("Pagination out of bounds")
    if year and (len(year)!=4 or not year.isdigit()):raise ValueError("Survey year must have four digits")
    if not any((benthic_name,region,watershed,year)):
        return {"total_benthic_survey_records":0,"benthic_survey_records":[],"warning":NOTICE}
    where=[];args=[]
    if benthic_name:
        where.append("literal_recorded_name LIKE ? ESCAPE '\\'")
        args.append(contains(benthic_name))
    if region:
        where.append("region=?")
        args.append(region)
    if watershed:
        where.append("watershed_name LIKE ? ESCAPE '\\'")
        args.append(contains(watershed))
    if year:
        where.append("survey_year=?")
        args.append(year)
    w=" AND ".join(where)
    c=sqlite3.connect(str(db));c.row_factory=sqlite3.Row
    try:
        n=c.execute("SELECT COUNT(*) FROM watershed_year_benthic_evidence WHERE "+w,args).fetchone()[0]
        data=[dict(x) for x in c.execute("""
            SELECT source_row_id,region,watershed_name,survey_year,literal_recorded_name,
                   official_source_url,source_zip_sha256,scope
            FROM watershed_year_benthic_evidence WHERE """+w+
            " ORDER BY region,watershed_name,survey_year,literal_recorded_name LIMIT ? OFFSET ?",
            (*args,limit,offset))]
        for row in data:
            row["verified_individual_river"]=None
            row["verified_prefecture"]=None
            row["accepted_taxon_code"]=None
        return {
           "total_benthic_survey_records":n,
           "benthic_survey_records":data,
           "results_are_historical_water_system_context_only":True,
           "warning":NOTICE
        }
    finally:c.close()

def search(db,name="",scientific="",group="",region="",watershed="",
           survey_name="",benthic_name="",year="",limit=25,offset=0):
    # Independently query the v1.8 name reference and old fish evidence.
    v18=search_v18(db,name,scientific,group,region,watershed,survey_name,limit,offset)
    new=search_benthic(db,benthic_name or name,region,watershed,year,limit,offset)
    v18.update(new)
    v18["biological_taxonomy_river_fish_and_benthic_are_not_auto_joined"]=True
    return v18

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--db",default="river-fish/biota/v19_benthic_research.sqlite")
    p.add_argument("--build",action="store_true")
    p.add_argument("--staged-dir",default=str(BASE))
    p.add_argument("--name",default="")
    p.add_argument("--benthic-name",default="")
    p.add_argument("--scientific",default="")
    p.add_argument("--group",default="")
    p.add_argument("--region",default="")
    p.add_argument("--watershed",default="")
    p.add_argument("--survey-name",default="")
    p.add_argument("--year",default="")
    p.add_argument("--limit",type=int,default=25)
    p.add_argument("--offset",type=int,default=0)
    a=p.parse_args()
    if a.build:
        result=build(a.db,a.staged_dir)
    else:
        result=search(a.db,a.name,a.scientific,a.group,a.region,a.watershed,
                      a.survey_name,a.benthic_name,a.year,a.limit,a.offset)
    print(json.dumps(result,ensure_ascii=False,indent=2))
