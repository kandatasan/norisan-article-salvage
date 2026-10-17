#!/usr/bin/env python3
"""Conservative official-name source registry for 10 additional prefectures.

Add separate official-mention rows to unified v1.2 SQLite. The batch contains
river NAMES and basin NAMES with different scopes; neither is a 10-digit river
code identity assignment. River-fish links and exact observation locations
remain absent. No network; no site writes.
"""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import sqlite3
import unicodedata

from japan_unified_registry_v12 import build as build_national

ROOT=Path(__file__).resolve().parent
DATA="multi_prefecture_source_mentions_v13.csv"
HEAD=["evidence_id","prefecture","jis_prefecture_code","evidence_kind",
      "literal_name","watershed_explicit_in_source","source_subarea","source_scope",
      "source_url","source_as_of_if_stated","prefecture_relation",
      "national_river_code_status","direct_fish_observation_status","website_status"]
PREFS={"北海道":"01","青森県":"02","宮城県":"04","埼玉県":"11","新潟県":"15",
       "長野県":"20","静岡県":"22","奈良県":"29","愛媛県":"38","福岡県":"40"}
EXPECTED={"北海道":13,"青森県":49,"宮城県":50,"埼玉県":29,"新潟県":65,
          "長野県":17,"静岡県":71,"奈良県":4,"愛媛県":5,"福岡県":13}
COUNTRYWIDE_REGION="prefecture_location_from_named_public_source_only"

def norm(s):
    return unicodedata.normalize("NFKC",str(s or "")).strip().casefold()

def read_source_rows(root=ROOT):
    root=Path(root)
    with (root/DATA).open(encoding="utf-8-sig",newline="") as f:
        reader=csv.DictReader(f)
        if reader.fieldnames!=HEAD:raise ValueError("Official source mention schema changed")
        rows=list(reader)
    if len(rows)!=316:raise ValueError("Not all 316 independently reviewed source rows are present")
    ids=set();count=Counter();sources=Counter()
    for r in rows:
        if r["evidence_id"] in ids:raise ValueError("Duplicate evidence ID")
        ids.add(r["evidence_id"]);count[r["prefecture"]]+=1
        sources[r["source_url"]]+=1
        if (PREFS.get(r["prefecture"])!=r["jis_prefecture_code"]
            or r["evidence_kind"] not in ("river","watershed")
            or not r["literal_name"] or not r["source_subarea"]
            or not r["source_scope"] or not r["source_url"].startswith("https://")
            or r["literal_name"][0] in "=+-@"
            or r["prefecture_relation"]!="mentioned_in_prefecture_or_city_official_source_only"
            or r["national_river_code_status"]!="not_linked"
            or r["direct_fish_observation_status"]!="none_from_this_document"
            or r["website_status"]!="research_only"):
            raise ValueError("Claim exceeds explicit prefectural source scope: "+r["evidence_id"])
        if r["evidence_kind"]=="watershed" and r["literal_name"]!=r["watershed_explicit_in_source"]:
            raise ValueError("Basin name was inferred rather than quoted from source")
        if r["evidence_kind"]=="river" and "basin_plans" in r["source_scope"]:
            raise ValueError("Basin plans cannot be treated as individual river survey")
    if dict(count)!=EXPECTED:raise ValueError("Selected province coverage changed; review sources")
    if len(sources)!=10:
        # 10 source documents are not assumed to cover 47 prefectures.
        # Actually distinct URLs include Nagano PDF and Nagano City => 11.
        if len(sources)!=11:raise ValueError("Unexpected set of official source URLs")
    return rows

def build(path,root=ROOT):
    path=Path(path)
    if path.exists():raise FileExistsError("Cannot overwrite a previously generated research DB")
    prior=build_national(path,root)
    rows=read_source_rows(root)
    conn=sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        conn.executescript("""
          CREATE TABLE other_prefecture_official_source_mentions (
             evidence_id TEXT PRIMARY KEY,
             prefecture TEXT NOT NULL,
             prefecture_code TEXT NOT NULL REFERENCES prefectures(code),
             evidence_kind TEXT NOT NULL CHECK(evidence_kind IN ('river','watershed')),
             literal_name TEXT NOT NULL,
             watershed_in_source TEXT,
             source_subarea TEXT NOT NULL,
             source_scope TEXT NOT NULL,
             source_url TEXT NOT NULL,
             source_as_of TEXT,
             relation_status TEXT NOT NULL,
             national_code_status TEXT NOT NULL CHECK(national_code_status='not_linked'),
             direct_fish_status TEXT NOT NULL CHECK(direct_fish_status='none_from_this_document'),
             publication_status TEXT NOT NULL CHECK(publication_status='research_only')
          );
          CREATE INDEX idx_other_prefecture ON other_prefecture_official_source_mentions(prefecture);
          CREATE INDEX idx_other_river_name ON other_prefecture_official_source_mentions(literal_name);
          CREATE INDEX idx_other_watershed ON other_prefecture_official_source_mentions(watershed_in_source);
        """)
        conn.executemany("INSERT INTO other_prefecture_official_source_mentions VALUES ("+",",".join(["?"]*14)+")",[
            (r["evidence_id"],r["prefecture"],r["jis_prefecture_code"],
             r["evidence_kind"],r["literal_name"],
             r["watershed_explicit_in_source"] or None,r["source_subarea"],
             r["source_scope"],r["source_url"],
             r["source_as_of_if_stated"] or None,r["prefecture_relation"],
             r["national_river_code_status"],
             r["direct_fish_observation_status"],r["website_status"])
            for r in rows
        ])
        conn.commit()
        if conn.execute("PRAGMA integrity_check").fetchone()[0]!="ok" or conn.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("National-source SQL integrity failed")
        scope_counts=dict(conn.execute("SELECT evidence_kind,COUNT(*) FROM other_prefecture_official_source_mentions GROUP BY evidence_kind").fetchall())
        counts=dict(conn.execute("SELECT prefecture,COUNT(*) FROM other_prefecture_official_source_mentions GROUP BY prefecture").fetchall())
        statuses={
          "source_mentions_added":len(rows),
          "source_mention_counts_by_prefecture":counts,
          "source_types":scope_counts,
          "prefectures_with_source_data_before":5,
          "prefectures_with_source_data_after":15,
          "directory_prefectures":prior["prefecture_directory"],
          "national_code_river_name_count":prior["nationwide_official_river_code_names"],
          "national_water_system_fish_name_count":prior["nationwide_census_watershed_year_fish_name_records"],
          "new_approved_prefecture_to_10_digit_code_links":0,
          "new_direct_river_fish_observations":0,
          "wordpress_updated":False,
        }
        return statuses
    finally:
        conn.close()

def query(path,prefecture="",name="",kind="",limit=40,offset=0):
    if not 1<=limit<=200 or offset<0:raise ValueError("Invalid pagination")
    if kind and kind not in ("river","watershed"):raise ValueError("Invalid source type")
    conn=sqlite3.connect(str(path));conn.row_factory=sqlite3.Row
    try:
        if prefecture and prefecture not in {p["prefecture_name"] for p in conn.execute("SELECT prefecture_name FROM prefectures")}:
            raise ValueError("Not a Japanese prefecture")
        source_rows=[dict(x) for x in conn.execute("SELECT * FROM other_prefecture_official_source_mentions ORDER BY evidence_id")]
        hits=[x for x in source_rows if (not prefecture or x["prefecture"]==prefecture)
               and (not name or norm(name) in norm(x["literal_name"]))
               and (not kind or x["evidence_kind"]==kind)]
        for x in hits:
            x["10_digit_river_code"]=None
            x["verified_full_course"]=False
            x["direct_fish_occurrence"]=None
        return {
          "total_source_mentions":len(hits),
          "source_mentions":hits[offset:offset+limit],
          "prefecture":prefecture or None,"query":name,
          "site_status":"research_only",
          "warning":"これは県・市の公式ページに現れた名称の掲載行で、全国10桁コードや川の全流路、魚種の生息は未照合。水系名と川名は区別して表示しています。"
        }
    finally:
        conn.close()

if __name__=="__main__":
    p=argparse.ArgumentParser(description="全国版：新たな10道県の河川・水系公式掲載行を検索")
    p.add_argument("--db",default="river-fish/japan_15pref_source_v13.sqlite")
    p.add_argument("--build",action="store_true")
    p.add_argument("--prefecture",default="")
    p.add_argument("--name",default="")
    p.add_argument("--kind",default="")
    p.add_argument("--limit",type=int,default=30)
    p.add_argument("--offset",type=int,default=0)
    a=p.parse_args()
    answer=build(a.db) if a.build else query(a.db,a.prefecture,a.name,a.kind,a.limit,a.offset)
    print(json.dumps(answer,ensure_ascii=False,indent=2))
