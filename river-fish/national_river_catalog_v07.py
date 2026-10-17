#!/usr/bin/env python3
"""Offline national river-code SQLite catalog and safe search.

Code identity is NOT geographic location proof. The two-digit prefix is the
issuing-code region, NOT the actual prefecture crossed by a river. Never make
fish occurrence claims for a tributary based on watershed survey records.
"""
import argparse
import csv
import json
from pathlib import Path
import sqlite3
import unicodedata

HERE=Path(__file__).resolve().parent
RIVER_HEADERS=["river_code","river_name","watershed_code","watershed_name",
               "code_region_prefix","source_url","identity_status","site_status"]
WATER_HEADERS=["watershed_code","watershed_name","code_region_prefix",
               "source_url","identity_status"]
CODE_DIR="national-codes-staged"

def norm(v):
    return unicodedata.normalize("NFKC",str(v or "")).casefold().strip()

def load(path,headers):
    with Path(path).open(encoding="utf-8-sig",newline="") as fd:
        r=csv.DictReader(fd)
        if r.fieldnames!=headers:raise ValueError("Unexpected official code CSV schema: "+str(path))
        return list(r)

def build_catalog(db_path,source_root=HERE):
    db_path=Path(db_path)
    if db_path.exists():raise FileExistsError("Do not overwrite an existing national code catalog")
    root=Path(source_root)/CODE_DIR
    rivers=load(root/"river_codes_national_v07.csv",RIVER_HEADERS)
    waters=load(root/"watershed_codes_national_v07.csv",WATER_HEADERS)
    manifest=json.loads((root/"river_code_manifest_v07.json").read_text(encoding="utf-8"))
    if (len(rivers)!=manifest["river_code_rows"] or len(waters)!=manifest["watershed_code_rows"]
        or len(rivers)<20000 or len(waters)<3000
        or manifest["prefecture_mapping"]!="not_inferred"
        or manifest["direct_species"]!="not_inferred"
        or manifest["no_W05_geometries"] is not True):
        raise ValueError("Official code catalog not QA-approved for database construction")
    source_names=set(w["watershed_code"] for w in waters)
    if len(source_names)!=len(waters) or len({r["river_code"] for r in rivers})!=len(rivers):
        raise ValueError("Duplicate official code")
    for r in rivers:
        if (len(r["river_code"])!=10 or not r["river_code"].isdigit()
            or r["watershed_code"]!=r["river_code"][:6]
            or r["code_region_prefix"]!=r["river_code"][:2]
            or r["identity_status"]!="coded_name_only_not_geographically_verified"
            or r["site_status"]!="research_only"):
            raise ValueError("Unexpected river-code record")
        if r["watershed_code"] not in source_names and r["watershed_name"]:
            raise ValueError("Unverified water-system name added")
    # Never write directly to the public WordPress site.
    conn=sqlite3.connect(db_path)
    try:
        conn.executescript("""
            PRAGMA foreign_keys=ON;
            CREATE TABLE watersheds (
              code TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              source_url TEXT NOT NULL,
              identity_status TEXT NOT NULL
            );
            CREATE TABLE rivers (
              code TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              watershed_code TEXT NOT NULL,
              code_prefix TEXT NOT NULL,
              source_url TEXT NOT NULL,
              identity_status TEXT NOT NULL,
              site_status TEXT NOT NULL
            );
            CREATE INDEX idx_river_name ON rivers(name);
            CREATE INDEX idx_river_watershed ON rivers(watershed_code);
            CREATE INDEX idx_river_prefix ON rivers(code_prefix);
            CREATE TABLE local_river_evidence (
              record_id TEXT PRIMARY KEY,
              prefecture_name TEXT NOT NULL,
              river_name TEXT NOT NULL,
              watershed_name TEXT NOT NULL,
              source_url TEXT NOT NULL,
              matched_official_code TEXT,
              approval_status TEXT NOT NULL CHECK (approval_status='unmatched_needs_review')
            );
        """)
        conn.executemany("INSERT INTO watersheds VALUES (?,?,?,?)", [
            (w["watershed_code"],w["watershed_name"],w["source_url"],w["identity_status"]) for w in waters
        ])
        conn.executemany("INSERT INTO rivers VALUES (?,?,?,?,?,?,?)", [
            (r["river_code"],r["river_name"],r["watershed_code"],
             r["code_region_prefix"],r["source_url"],r["identity_status"],r["site_status"])
            for r in rivers
        ])
        # Legacy prefecture-level evidence remains separate, and no code match
        # is approved without validating river location / watershed identity.
        old=Path(source_root)/"river_registry_hiroshima_v01.csv"
        if old.exists():
            with old.open(encoding="utf-8-sig",newline="") as f:
                legacy=list(csv.DictReader(f))
            conn.executemany("INSERT INTO local_river_evidence VALUES (?,?,?,?,?,?,?)", [
                (r["river_id"],r["prefecture"],r["river_name"],r["watershed"],
                 r["source_url"],None,"unmatched_needs_review")
                for r in legacy
            ])
        conn.commit()
        if conn.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
            raise ValueError("SQLite integrity check failed")
        return {
            "river_code_rows":conn.execute("SELECT COUNT(*) FROM rivers").fetchone()[0],
            "watershed_code_rows":conn.execute("SELECT COUNT(*) FROM watersheds").fetchone()[0],
            "local_evidence_unmatched":conn.execute("SELECT COUNT(*) FROM local_river_evidence").fetchone()[0],
            "official_codes_approved_for_hiroshima_local_evidence":0,
            "river_fish_direct_observations":0,
            "publication_status":"research_only",
        }
    finally:conn.close()

def search(db_path,name="",watershed="",code_prefix="",river_code="",limit=30,offset=0):
    if not (1<=limit<=100 and offset>=0):raise ValueError("Invalid pagination")
    if code_prefix and (len(code_prefix)!=2 or not code_prefix.isdigit()):
        raise ValueError("Code prefix must be two digits")
    conn=sqlite3.connect(str(db_path))
    conn.row_factory=sqlite3.Row
    try:
        sql="""SELECT r.code, r.name, r.watershed_code,
                      w.name AS watershed_name, r.code_prefix,r.source_url
               FROM rivers AS r LEFT JOIN watersheds AS w
               ON r.watershed_code=w.code ORDER BY r.code"""
        found=[]
        for rr in conn.execute(sql):
            r=dict(rr)
            if name and norm(name) not in norm(r["name"]):continue
            if watershed and norm(watershed) not in norm(r["watershed_name"]):continue
            if code_prefix and r["code_prefix"]!=code_prefix:continue
            if river_code and river_code!=r["code"]:continue
            found.append({
                "river_code":r["code"],"river_name":r["name"],
                "watershed_code":r["watershed_code"],"watershed_name":r["watershed_name"],
                "code_region_prefix":r["code_prefix"],
                "prefecture_of_location":None,
                "direct_parent_river":None,
                "river_fish_occurrences":None,
                "identity":"official_code_name_not_location_verified",
                "source_url":r["source_url"],
            })
        count=len(found)
        page=found[offset:offset+limit]
        for r in page:
            p=conn.execute(
                """SELECT record_id,prefecture_name,river_name,watershed_name,source_url
                   FROM local_river_evidence WHERE river_name=? AND watershed_name=?""",
                (r["river_name"],r["watershed_name"])).fetchall()
            r["potential_local_evidence_matches_unapproved"]=[dict(x) for x in p]
        return {
            "total_code_records":count,"rivers":page,"limit":limit,"offset":offset,
            "notice":"河川コードは河川名の識別に使います。都道府県・直接の親河川・支流の魚類生息地は、この表だけでは特定できません。コード先頭2桁は所在地の県名とは限りません。"
        }
    finally:conn.close()

if __name__=="__main__":
    p=argparse.ArgumentParser(description="つりくえ！全国河川コード名検索")
    p.add_argument("--db",default="river-fish/national_codes_v07.sqlite")
    p.add_argument("--build",action="store_true")
    p.add_argument("--name",default="")
    p.add_argument("--watershed",default="")
    p.add_argument("--code-prefix",default="")
    p.add_argument("--river-code",default="")
    p.add_argument("--limit",type=int,default=30)
    p.add_argument("--offset",type=int,default=0)
    opt=p.parse_args()
    result=build_catalog(opt.db) if opt.build else search(
       opt.db,opt.name,opt.watershed,opt.code_prefix,opt.river_code,opt.limit,opt.offset)
    print(json.dumps(result,ensure_ascii=False,indent=2))
