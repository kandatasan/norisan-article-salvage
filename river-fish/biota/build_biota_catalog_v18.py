#!/usr/bin/env python3
"""National biology reference + historic WATER-SYSTEM fish evidence.

Two independent dimensions:
  reference rows: MLIT's 2025 taxonomy list for seven survey groups;
  fish survey: published 9-region × watershed × year × name observations.

NO JOIN creating a claim about an individual river, municipality, prefecture,
current species presence, exact taxonomic identity, or fishing suitability.
A literal-name match is a search convenience, NOT verified taxon synonymy.

Offline-only research build: never touches WordPress or external APIs.
"""
import argparse
from collections import Counter,defaultdict
import csv
import hashlib
import json
from pathlib import Path
import sqlite3
import unicodedata

from build_river_beta_v15 import census_fish

ROOT=Path(__file__).resolve().parents[1]
BIO=Path(__file__).resolve().parent
TAXA_CSV="official_biota_reference_2025_v18.csv"
MANIFEST="official_biota_manifest_2025_v18.json"
CATEGORIES=("fish","benthic_animals","plants","birds",
            "amphibians_reptiles_mammals","terrestrial_insects","plankton")
TAXA_FIELDS=[
    "source_row","official_taxon_code","japanese_name","scientific_name",
    "phylum_japanese","phylum_scientific","class_japanese","class_scientific",
    "order_japanese","order_scientific","family_japanese","family_scientific",
    "genus_japanese","genus_scientific",
    *CATEGORIES,"evidence_kind"
]
NOTICE=("この一覧は生物分類の基準資料であり、生息場所を示しません。"
        "魚類調査データは水系・地域・年度単位で、都道府県別や個々の川の生息魚には変換しません。"
        "同じ和名でも分類コードが複数の場合、未確認のまま個別表示します。")

def normalize(value):
    return unicodedata.normalize("NFKC",str(value or "")).casefold().strip()

def read_reference(root=BIO):
    root=Path(root)
    m=json.loads((root/MANIFEST).read_text(encoding="utf-8"))
    csv_file=root/TAXA_CSV
    if (m["publication_status"]!="research_only_not_wordpress"
        or m["contains_species_occurrence_or_river_presence"] is not False
        or m["sensitive_locations_in_data"] is not False
        or m["source_workbook_data_rows_including_structural"]!=37812
        or m["reference_rows"] + m["excluded_structural_rows_without_taxon_code"]!=37812
        or hashlib.sha256(csv_file.read_bytes()).hexdigest()!=m["staged_csv_sha256"]):
        raise ValueError("Official biota reference manifest must be reviewed")
    with csv_file.open(encoding="utf-8-sig",newline="") as f:
        reader=csv.DictReader(f)
        if reader.fieldnames!=TAXA_FIELDS:
            raise ValueError("Taxonomy column scheme changed")
        result=list(reader)
    if len(result)!=m["reference_rows"]:raise ValueError("Official taxon references inconsistent with manifest")
    counts=Counter()
    last_row=1
    for r in result:
        if (r["evidence_kind"]!="2025_official_taxon_reference_not_observation"
            or int(r["source_row"])<=last_row or int(r["source_row"])>37813
            or not (r["japanese_name"] or r["scientific_name"])
            or not r["official_taxon_code"]):
            raise ValueError("Invalid original taxon code/name or source row: "+r["source_row"])
        last_row=int(r["source_row"])
        for group in CATEGORIES:
            if r[group] not in ("0","1"):raise ValueError("Non-boolean list membership")
            if r[group]=="1":counts[group]+=1
    if dict(counts)!=m["category_membership_counts_not_distinct_species"]:
        raise ValueError("Biology survey-group membership validation failed")
    if len({x["japanese_name"] for x in result})!=m["distinct_japanese_labels_not_species_count"]:
        raise ValueError("Unexpected literal Japanese name labels")
    return result,m

def build(db, root=BIO):
    db=Path(db)
    if db.exists():raise FileExistsError("Do not overwrite existing biodiversity DB")
    taxon_rows,m=read_reference(root)
    fish=census_fish()
    if len(fish)!=18814:raise ValueError("National fish census must remain provenance checked")
    db.parent.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(str(db))
    try:
        c.executescript("""
          CREATE TABLE taxon_name_reference (
            source_row INTEGER PRIMARY KEY,
            official_taxon_code TEXT NOT NULL,
            japanese_name TEXT NOT NULL,
            scientific_name TEXT NOT NULL,
            phylum_japanese TEXT NOT NULL,
            phylum_scientific TEXT NOT NULL,
            class_japanese TEXT NOT NULL,
            class_scientific TEXT NOT NULL,
            order_japanese TEXT NOT NULL,
            order_scientific TEXT NOT NULL,
            family_japanese TEXT NOT NULL,
            family_scientific TEXT NOT NULL,
            genus_japanese TEXT NOT NULL,
            genus_scientific TEXT NOT NULL,
            evidence_status TEXT NOT NULL CHECK(evidence_status='name_reference_not_observation'),
            source_url TEXT NOT NULL,
            source_version TEXT NOT NULL
          );
          CREATE TABLE taxon_survey_groups (
            source_row INTEGER NOT NULL REFERENCES taxon_name_reference(source_row),
            survey_group TEXT NOT NULL,
            PRIMARY KEY(source_row,survey_group)
          );
          CREATE INDEX idx_taxa_name ON taxon_name_reference(japanese_name);
          CREATE INDEX idx_taxa_scientific ON taxon_name_reference(scientific_name);
          CREATE INDEX idx_group ON taxon_survey_groups(survey_group);
          CREATE TABLE watershed_year_fish_evidence (
            evidence_id INTEGER PRIMARY KEY,
            region TEXT NOT NULL,
            watershed_name TEXT NOT NULL,
            survey_year TEXT NOT NULL,
            literal_recorded_name TEXT NOT NULL,
            source_url TEXT NOT NULL,
            geographic_scope TEXT NOT NULL CHECK(geographic_scope='regional_watershed_year_only'),
            direct_tributary_river_id TEXT,
            prefecture TEXT,
            approved_taxon_code TEXT,
            CHECK(direct_tributary_river_id IS NULL),
            CHECK(prefecture IS NULL),
            CHECK(approved_taxon_code IS NULL)
          );
          CREATE INDEX idx_fish_literal_name ON watershed_year_fish_evidence(literal_recorded_name);
          CREATE INDEX idx_fish_watershed ON watershed_year_fish_evidence(watershed_name);
          CREATE INDEX idx_fish_region ON watershed_year_fish_evidence(region);
        """)
        c.executemany("""
          INSERT INTO taxon_name_reference VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,[
            (int(r["source_row"]),r["official_taxon_code"],r["japanese_name"],
             r["scientific_name"],r["phylum_japanese"],r["phylum_scientific"],
             r["class_japanese"],r["class_scientific"],r["order_japanese"],
             r["order_scientific"],r["family_japanese"],r["family_scientific"],
             r["genus_japanese"],r["genus_scientific"],
             "name_reference_not_observation",m["source_url"],"2025_R07")
            for r in taxon_rows
        ])
        c.executemany("INSERT INTO taxon_survey_groups VALUES (?,?)",[
            (int(r["source_row"]),group)
            for r in taxon_rows for group in CATEGORIES if r[group]=="1"
        ])
        c.executemany("INSERT INTO watershed_year_fish_evidence VALUES (?,?,?,?,?,?,?,?,?,?)",[
            (i+1,*row,"regional_watershed_year_only",None,None,None)
            for i,row in enumerate(fish)
        ])
        c.commit()
        if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
            raise ValueError("Biological catalog SQL consistency failed")
        if c.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("Biological catalog has invalid parent identifiers")
        result={
            "official_taxon_reference_rows":len(taxon_rows),
            "distinct_literal_japanese_names_not_species_count":m["distinct_japanese_labels_not_species_count"],
            "official_taxon_group_memberships":dict(m["category_membership_counts_not_distinct_species"]),
            "national_watershed_year_fish_evidence":len(fish),
            "taxon_survey_rows_assigned_to_individual_river":0,
            "taxon_survey_rows_assigned_to_prefecture":0,
            "survey_label_matched_to_verified_taxonomic_identity":0,
            "sources":{"taxonomy":m["source_url"],
                       "fish":"https://www.nilim.go.jp/lab/fbg/ksnkankyo/dl_00_index.html"},
            "wordpress_modified":False,
            "warning":NOTICE
        }
        return result
    finally:c.close()

def search(db, name="", scientific="", group="", region="", watershed="",
           survey_name="", limit=25,offset=0):
    if group and group not in CATEGORIES:raise ValueError("Not an official survey group")
    if region and region not in ("hokkaido","tohoku","kanto","hokuriku","chubu",
                                 "kinki","chugoku","shikoku","kyushu"):
        raise ValueError("Invalid river census region")
    if not 1<=limit<=100 or offset<0:raise ValueError("Bad page size")
    if not any((name,scientific,group,region,watershed,survey_name)):
        return {"total_reference_names":0,"reference_names":[],
                "total_fish_survey_records":0,"fish_survey_records":[],
                "warning":NOTICE}
    c=sqlite3.connect(str(db));c.row_factory=sqlite3.Row
    try:
        def contains_sql(value):
            return "%"+str(value).replace("\\","\\\\").replace("%","\\%").replace("_","\\_")+"%"
        w=[];args=[]
        if name:
            w.append("t.japanese_name LIKE ? ESCAPE '\\'")
            args.append(contains_sql(name))
        if scientific:
            w.append("t.scientific_name LIKE ? ESCAPE '\\'")
            args.append(contains_sql(scientific))
        if group:
            w.append("EXISTS (SELECT 1 FROM taxon_survey_groups g WHERE g.source_row=t.source_row AND g.survey_group=?)")
            args.append(group)
        where=" AND ".join(w) if w else "1=0"
        count=c.execute("SELECT COUNT(*) FROM taxon_name_reference t WHERE "+where,args).fetchone()[0]
        rows=[dict(x) for x in c.execute(
            "SELECT t.* FROM taxon_name_reference t WHERE "+where+" ORDER BY t.source_row LIMIT ? OFFSET ?",
            (*args,limit,offset))]
        for r in rows:
            r["official_survey_groups"]=[x[0] for x in c.execute(
                "SELECT survey_group FROM taxon_survey_groups WHERE source_row=? ORDER BY survey_group",
                (r["source_row"],))]
            r["confirmed_river_presence"]=None
            r["confirmed_prefecture_presence"]=None
        fw=[];fa=[]
        if survey_name:
            fw.append("literal_recorded_name LIKE ? ESCAPE '\\'");fa.append(contains_sql(survey_name))
        elif name:
            fw.append("literal_recorded_name LIKE ? ESCAPE '\\'");fa.append(contains_sql(name))
        if region:fw.append("region=?");fa.append(region)
        if watershed:fw.append("watershed_name LIKE ? ESCAPE '\\'");fa.append(contains_sql(watershed))
        fish_where=" AND ".join(fw) if fw else "1=0"
        survey_count=c.execute(
            "SELECT COUNT(*) FROM watershed_year_fish_evidence WHERE "+fish_where,fa).fetchone()[0]
        surveys=[dict(x) for x in c.execute(
            "SELECT evidence_id,region,watershed_name,survey_year,literal_recorded_name,source_url,"
            "geographic_scope FROM watershed_year_fish_evidence WHERE "+fish_where+
            " ORDER BY region,watershed_name,survey_year,literal_recorded_name LIMIT ? OFFSET ?",
            (*fa,limit,offset))]
        return {
            "total_reference_names":count,"reference_names":rows,
            "total_fish_survey_records":survey_count,"fish_survey_records":surveys,
            "taxonomy_and_fish_data_separate":True,
            "exact_name_is_not_verified_taxonomic_or_geographical_join":True,
            "warning":NOTICE
        }
    finally:c.close()

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--db",default="river-fish/biota/biota_v18.sqlite")
    p.add_argument("--build",action="store_true")
    p.add_argument("--name",default="")
    p.add_argument("--scientific",default="")
    p.add_argument("--group",default="")
    p.add_argument("--region",default="")
    p.add_argument("--watershed",default="")
    p.add_argument("--survey-name",default="")
    p.add_argument("--limit",type=int,default=25)
    p.add_argument("--offset",type=int,default=0)
    a=p.parse_args()
    result=build(a.db) if a.build else search(
        a.db,a.name,a.scientific,a.group,a.region,a.watershed,
        a.survey_name,a.limit,a.offset)
    print(json.dumps(result,ensure_ascii=False,indent=2))
