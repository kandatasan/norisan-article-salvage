#!/usr/bin/env python3
"""River-name register for Tsurikue. Separate river identity from fish occurrence.

Source register: river_registry_hiroshima_v01.csv, curated name-level evidence.
The NILIM fish census CSV records WATERSHEDS, not tributary observations.
Under no circumstances should these become direct river-fish claims.
"""
import argparse
import csv
import json
import re
import sqlite3
import unicodedata
from pathlib import Path

ROOT=Path(__file__).resolve().parent
RIVER_CSV="river_registry_hiroshima_v01.csv"
FISH_CSV="official_chugoku_watershed_year_fish_v05.csv"
RIVER_FIELDS=["river_id","prefecture","watershed","river_name","municipality_example",
              "legal_class","direct_parent_river","record_status","source_url",
              "source_document_year","source_kind","publication_status"]
FISH_FIELDS=["watershed","survey_year","recorded_name","source_url","source_sha256"]

def normalize(s):
    return unicodedata.normalize("NFKC",str(s or "")).strip().casefold()

def load_csv(file,headers):
    with Path(file).open(encoding="utf-8-sig",newline="") as f:
        r=csv.DictReader(f)
        if r.fieldnames != headers:
            raise ValueError(f"Unexpected CSV schema: {file}: {r.fieldnames}")
        return list(r)

def create_database(destination,source_dir=ROOT):
    """Build an offline SQLite cache. Return QA stats; no web or WordPress calls."""
    source_dir=Path(source_dir)
    river_rows=load_csv(source_dir/RIVER_CSV,RIVER_FIELDS)
    survey_rows=load_csv(source_dir/FISH_CSV,FISH_FIELDS)
    seen_ids=set()
    seen_rivers=set()
    for r in river_rows:
        rid=r["river_id"]
        key=(r["prefecture"],r["watershed"],r["river_name"])
        if (not re.fullmatch(r"HR-[0-9]{4}",rid) or
            not all(r[k].strip() for k in ("prefecture","watershed","river_name","source_url","source_document_year"))):
            raise ValueError(f"Incomplete river evidence {rid}")
        if rid in seen_ids or key in seen_rivers:
            raise ValueError(f"Duplicate river identity {rid} {key}")
        if r["record_status"]!="source_name_confirmed":
            raise ValueError("River not name-confirmed")
        if r["publication_status"]!="registry_staged":
            raise ValueError("Publication not approved")
        if r["direct_parent_river"]:
            raise ValueError("Direct-parent field must have independent proof")
        if r["legal_class"]!="unverified":
            raise ValueError("Administrative class requires extra provenance")
        if not r["source_url"].startswith("https://www.pref.hiroshima.lg.jp/"):
            raise ValueError("Unapproved raw evidence host")
        seen_ids.add(rid);seen_rivers.add(key)
    seen_fish=set()
    for r in survey_rows:
        k=(r["watershed"],r["survey_year"],r["recorded_name"])
        if not all(k) or k in seen_fish or not re.fullmatch(r"(?:19|20)\d{2}",r["survey_year"]):
            raise ValueError(f"Invalid official survey aggregation {k}")
        seen_fish.add(k)
    db=sqlite3.connect(str(destination))
    try:
        db.executescript("""
        PRAGMA foreign_keys=ON;
        CREATE TABLE rivers (
           river_id TEXT PRIMARY KEY, prefecture TEXT NOT NULL,
           watershed TEXT NOT NULL, river_name TEXT NOT NULL,
           municipality_example TEXT, legal_class TEXT NOT NULL,
           direct_parent_river TEXT,
           record_status TEXT NOT NULL, source_url TEXT NOT NULL,
           source_document_year TEXT NOT NULL, source_kind TEXT NOT NULL,
           publication_status TEXT NOT NULL,
           UNIQUE(prefecture,watershed,river_name)
        );
        CREATE TABLE river_aliases (
           river_id TEXT NOT NULL REFERENCES rivers(river_id),
           alias TEXT NOT NULL, evidence_url TEXT NOT NULL,
           PRIMARY KEY (river_id,alias)
        );
        CREATE TABLE watershed_fish_context (
           watershed TEXT NOT NULL, survey_year TEXT NOT NULL,
           recorded_name TEXT NOT NULL, source_url TEXT NOT NULL,
           source_sha256 TEXT NOT NULL,
           PRIMARY KEY (watershed,survey_year,recorded_name)
        );
        CREATE TABLE direct_river_fish_evidence (
           id TEXT PRIMARY KEY, river_id TEXT NOT NULL REFERENCES rivers(river_id),
           recorded_name TEXT NOT NULL, survey_year TEXT, source_url TEXT NOT NULL,
           source_record_type TEXT NOT NULL, publication_review_status TEXT NOT NULL
        );
        CREATE INDEX river_name_idx ON rivers(river_name);
        CREATE INDEX river_watershed_idx ON rivers(watershed);
        CREATE INDEX context_water_idx ON watershed_fish_context(watershed);
        """)
        db.executemany(
            "INSERT INTO rivers VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            [tuple(r.get(k,"") or None for k in RIVER_FIELDS) for r in river_rows])
        db.executemany(
            "INSERT INTO watershed_fish_context VALUES (?,?,?,?,?)",
            [tuple(r[k] for k in FISH_FIELDS) for r in survey_rows])
        db.commit()
        integrity=db.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity!="ok": raise ValueError("SQLite integrity failure: "+integrity)
        result={
          "rivers":db.execute("SELECT COUNT(*) FROM rivers").fetchone()[0],
          "watersheds":db.execute("SELECT COUNT(DISTINCT watershed) FROM rivers").fetchone()[0],
          "official_watershed_year_name_records":db.execute("SELECT COUNT(*) FROM watershed_fish_context").fetchone()[0],
          "direct_species_evidence":db.execute("SELECT COUNT(*) FROM direct_river_fish_evidence").fetchone()[0],
          "publication":"unpublished_research",
        }
        return result
    finally:
        db.close()

def find_rivers(db,name="",prefecture="",watershed="",municipality="",limit=50):
    if not (1<=limit<=200):raise ValueError("Limit must be from 1 to 200")
    where=[];args=[]
    for col,value in (("river_name",name),("prefecture",prefecture),("watershed",watershed),
                      ("municipality_example",municipality)):
        if value:
            # Compare normalized names inside Python rather than trust LIKE
            # escaping/collation for Japanese; small register is intentional.
            pass
    conn=sqlite3.connect(str(db))
    conn.row_factory=sqlite3.Row
    try:
        all_rivers=conn.execute("SELECT * FROM rivers ORDER BY river_id").fetchall()
        result=[]
        for row in all_rivers:
            r=dict(row)
            if (name and normalize(name) not in normalize(r["river_name"])):continue
            if (prefecture and normalize(prefecture) not in normalize(r["prefecture"])):continue
            if (watershed and normalize(watershed) not in normalize(r["watershed"])):continue
            if (municipality and normalize(municipality) not in normalize(r["municipality_example"])):continue
            ctx=conn.execute("SELECT COUNT(*) FROM watershed_fish_context WHERE watershed=?",
                             (r["watershed"],)).fetchone()[0]
            direct=conn.execute("SELECT COUNT(*) FROM direct_river_fish_evidence WHERE river_id=? AND publication_review_status='approved'",
                             (r["river_id"],)).fetchone()[0]
            result.append({
                "river_id":r["river_id"],"name":r["river_name"],
                "prefecture":r["prefecture"],"watershed":r["watershed"],
                "municipality_example_not_full_coverage":r["municipality_example"],
                "parent_river":r["direct_parent_river"],"parent_link_status":"not_reviewed",
                "legal_class":r["legal_class"],"source_url":r["source_url"],
                "direct_species_records":direct,
                "same_watershed_survey_records_context_only":ctx,
                "watershed_context_is_direct_river_evidence":False,
                "status":"河川名登録済み／この川固有の魚種記録は未確認" if not direct else "河川固有の魚種資料あり",
                "publication_status":r["publication_status"]
            })
        return {
            "total_rivers":len(result), "rivers":result[:limit],
            "notice":"水系の魚類調査記録を支流の生息記録に流用しません。情報なしは魚の不在ではありません。県と市町村は完全な流域範囲を示しません。",
        }
    finally:
        conn.close()

def main():
    p=argparse.ArgumentParser(description="つりくえ！河川マスター検索／魚類水系データ安全分離")
    p.add_argument("--db",default="river-fish/hiroshima_river_registry_v01.sqlite")
    p.add_argument("--build",action="store_true")
    p.add_argument("--name",default="")
    p.add_argument("--prefecture",default="")
    p.add_argument("--watershed",default="")
    p.add_argument("--municipality",default="")
    p.add_argument("--limit",type=int,default=40)
    args=p.parse_args()
    path=Path(args.db)
    if args.build:
        path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists():path.unlink()  # Deterministic local cache regeneration
        print(json.dumps(create_database(path),ensure_ascii=False,indent=2))
    else:
        if not path.exists():p.error("DB not found: first use --build")
        print(json.dumps(find_rivers(path,args.name,args.prefecture,args.watershed,args.municipality,args.limit),
                         ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
