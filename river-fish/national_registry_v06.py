#!/usr/bin/env python3
"""Japan-wide 47-prefecture river registry skeleton with real coverage statuses.

Still only Hiroshima rivers are populated. Regional MLIT fish records are NOT
assigned to prefectures without separately verified geographic evidence.
"""
import argparse
import csv
import json
from pathlib import Path
import sqlite3
from river_mentions_v02 import create_catalog

ROOT=Path(__file__).resolve().parent
PREF_FILE=ROOT/"japan_prefectures_v06.csv"
SOURCE_FILE=ROOT/"nationwide_sources_v06.json"

def build(path,root=ROOT):
    root=Path(root)
    path=Path(path)
    if path.exists():raise FileExistsError("Never overwrite an existing DB without review")
    stats=create_catalog(path,source_dir=root)
    prefs=list(csv.DictReader((root/"japan_prefectures_v06.csv").open(encoding="utf-8-sig",newline="")))
    src=json.loads((root/"nationwide_sources_v06.json").read_text(encoding="utf-8"))
    if len(prefs)!=47 or len(src["region_sources"])!=9:
        raise ValueError("Prefecture or source inventory incomplete")
    c=sqlite3.connect(path)
    try:
        c.executescript("""
          CREATE TABLE prefectures (
            code TEXT PRIMARY KEY,prefecture_name TEXT NOT NULL UNIQUE,
            river_registry_status TEXT NOT NULL,
            fish_survey_crosswalk_status TEXT NOT NULL,
            notes TEXT NOT NULL
          );
          CREATE TABLE official_fish_regional_sources (
            region_id TEXT PRIMARY KEY,
            official_region TEXT NOT NULL,
            source_url TEXT NOT NULL,
            source_sha256 TEXT NOT NULL,
            import_status TEXT NOT NULL
          );
          CREATE TABLE verified_watershed_prefecture_links (
            watershed TEXT NOT NULL,
            prefecture_code TEXT NOT NULL REFERENCES prefectures(code),
            evidence_url TEXT NOT NULL,
            review_status TEXT NOT NULL,
            PRIMARY KEY(watershed,prefecture_code)
          );
        """)
        c.executemany("INSERT INTO prefectures VALUES (?,?,?,?,?)",[
          (r["jis_prefecture_code"],r["prefecture_name"],r["river_registry_status"],
           r["fish_survey_crosswalk_status"],r["notes"]) for r in prefs])
        c.executemany("INSERT INTO official_fish_regional_sources VALUES (?,?,?,?,?)",[
          (r["region_id"],r["official_region"],r["source_url"],
           r["checksum_sha256"],r["status"]) for r in src["region_sources"]])
        c.commit()
        assert c.execute("PRAGMA integrity_check").fetchone()[0]=="ok"
        return {"prefectures":47,"national_fish_source_regions":9,
                "existing_verified_river_names":stats["canonical_rivers"],
                "additional_unreviewed_river_mentions":stats["unresolved_name_mentions"],
                "water_system_year_species_context_existing":2285,
                "verified_prefecture_watershed_species_crosswalk_rows":
                    c.execute("SELECT COUNT(*) FROM verified_watershed_prefecture_links").fetchone()[0],
                "web_deployed":False}
    finally:
        c.close()

def coverage(db,prefecture=""):
    c=sqlite3.connect(str(db));c.row_factory=sqlite3.Row
    try:
        prefs=c.execute("SELECT * FROM prefectures ORDER BY code").fetchall()
        result=[]
        for row in prefs:
            p=dict(row)
            if prefecture and prefecture!=p["prefecture_name"]:continue
            canonical=c.execute("SELECT COUNT(*) FROM rivers WHERE prefecture=?",(p["prefecture_name"],)).fetchone()[0]
            mentions=c.execute("SELECT COUNT(*) FROM river_name_mentions WHERE prefecture=?",(p["prefecture_name"],)).fetchone()[0]
            p.update({"verified_river_count":canonical,
                      "unreviewed_name_mentions":mentions,
                      "national_fish_survey_prefecture_records":None,
                      "national_fish_survey_prefecture_status":"not_mapped",
                      "total_rivers_in_prefecture":None,
                      "site_status":"research_only"})
            result.append(p)
        return {"prefecture_records":result,
                "note":"全国47都道府県のキーを準備しただけ。河川名の網羅を意味しません。地域別魚類原本を県へ推測配賦しません。"}
    finally:
        c.close()

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--db",default="river-fish/japan_river_registry_v06.sqlite")
    p.add_argument("--build",action="store_true")
    p.add_argument("--prefecture",default="")
    args=p.parse_args()
    if args.build:
        print(json.dumps(build(args.db),ensure_ascii=False,indent=2))
    else:
        print(json.dumps(coverage(args.db,args.prefecture),ensure_ascii=False,indent=2))
