#!/usr/bin/env python3
"""Attach independently crosschecked 2016 official river-code ledger evidence.

A 2016 river administrator is NOT proof of full present-day geographic range.
Never infer an observation year, fish occurrence, station or river-parent edge.
The previous v0.8 identity candidates deliberately remain unapproved.
"""
import argparse
import csv
import json
from pathlib import Path
import re
import sqlite3
from river_review_catalog_v08 import build_database as build_v08

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/"ota_historical_code_crosschecks_v09.csv"
HEADER=[
  "local_evidence_id","river_name","watershed_name",
  "national_river_code","national_watershed_code",
  "ledger_administrator_as_of_2016","ledger_as_of","ledger_pdf_page_1based",
  "ledger_source_url","local_source_url","verification_status",
  "current_geography_status","individual_river_fish_status",
  "website_publication_status"
]
LEDGER_URL="https://www.cgr.mlit.go.jp/kasen/code/pdf/009oota201612.pdf"
LOCAL_URL="https://www.pref.hiroshima.lg.jp/uploaded/attachment/429109.pdf"
SCOPED_STATUS="historical_code_and_watershed_crosschecked"

def load_historical_rows(root=ROOT):
    with (Path(root)/SOURCE.name).open(encoding="utf-8-sig",newline="") as f:
        r=csv.DictReader(f)
        if r.fieldnames!=HEADER:raise ValueError("Unexpected historical ledger source schema")
        data=list(r)
    if len(data)!=10:raise ValueError("Unreviewed change to historical source row count")
    ids=set();codes=set()
    for x in data:
        local=x["local_evidence_id"];code=x["national_river_code"]
        if (local in ids or code in codes or not re.fullmatch(r"HR-\d{4}",local)
          or not re.fullmatch(r"\d{10}",code)
          or code[:6]!=x["national_watershed_code"]
          or x["watershed_name"]!="太田川"
          or x["national_watershed_code"]!="870709"
          or x["ledger_administrator_as_of_2016"]!="広島県"
          or x["ledger_as_of"]!="2016-12"
          or x["ledger_pdf_page_1based"] not in ("3","4")
          or x["ledger_source_url"]!=LEDGER_URL
          or x["local_source_url"]!=LOCAL_URL
          or x["verification_status"]!=SCOPED_STATUS
          or x["current_geography_status"]!="present_day_precise_location_unverified"
          or x["individual_river_fish_status"]!="not_assigned"
          or x["website_publication_status"]!="not_published"):
            raise ValueError("Bad/unsupported historical river record: "+local)
        ids.add(local);codes.add(code)
    return data

def audit_v08_candidates(rows,db):
    """All 10 must be independently unique source-name+watershed candidates."""
    for r in rows:
        hits=db.execute("""
          SELECT local_id,code_candidate,river_name_in_source,
                 watershed_in_source,source_url,candidate_count,
                 match_basis,identity_approved,prefecture_approved,fish_approved
          FROM identity_candidates
          WHERE local_id=?""",(r["local_evidence_id"],)).fetchall()
        if len(hits)!=1:raise ValueError("Not a single candidate for "+r["local_evidence_id"])
        h=hits[0]
        if (h["code_candidate"]!=r["national_river_code"] or
            h["river_name_in_source"]!=r["river_name"] or
            h["watershed_in_source"]!=r["watershed_name"] or
            h["source_url"]!=r["local_source_url"] or
            h["candidate_count"]!=1 or
            h["match_basis"]!="exact_name_and_source_watershed" or
            h["identity_approved"]!="false" or
            h["prefecture_approved"]!="false" or
            h["fish_approved"]!="false"):
            raise ValueError("Identity candidate does not match dated ledger and local source")
    return True

def build(path,root=ROOT):
    path=Path(path)
    if path.exists():raise FileExistsError("Refusing to overwrite an existing review database")
    stats=build_v08(path,root=root)
    conn=sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory=sqlite3.Row
    try:
        rows=load_historical_rows(root)
        audit_v08_candidates(rows,conn)
        conn.executescript("""
          CREATE TABLE official_historical_code_crosschecks (
             local_id TEXT PRIMARY KEY,
             river_name TEXT NOT NULL,
             watershed_name TEXT NOT NULL,
             river_code TEXT NOT NULL UNIQUE,
             watershed_code TEXT NOT NULL,
             2016_administrator TEXT NOT NULL,
             ledger_as_of TEXT NOT NULL,
             pdf_page TEXT NOT NULL,
             ledger_url TEXT NOT NULL,
             source_url TEXT NOT NULL,
             reviewed_ledger_scope TEXT NOT NULL,
             present_day_location_status TEXT NOT NULL,
             direct_river_fish_status TEXT NOT NULL,
             website_status TEXT NOT NULL,
             FOREIGN KEY (local_id, river_code)
               REFERENCES identity_candidates(local_id,code_candidate)
          );
        """)
        conn.executemany("""
          INSERT INTO official_historical_code_crosschecks VALUES
          (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,[
          (r["local_evidence_id"],r["river_name"],r["watershed_name"],
           r["national_river_code"],r["national_watershed_code"],
           r["ledger_administrator_as_of_2016"],r["ledger_as_of"],
           r["ledger_pdf_page_1based"],r["ledger_source_url"],r["local_source_url"],
           r["verification_status"],r["current_geography_status"],
           r["individual_river_fish_status"],r["website_publication_status"])
          for r in rows
        ])
        conn.commit()
        if conn.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
            raise ValueError("SQLite integrity failure")
        if conn.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("Historical-code references are not linked to v0.8 candidates")
        count=conn.execute("SELECT COUNT(*) FROM official_historical_code_crosschecks").fetchone()[0]
        pending=conn.execute("SELECT COUNT(*) FROM identity_candidates WHERE identity_approved='false'").fetchone()[0]
        if count!=10 or pending!=stats["unapproved_code_candidate_rows"]:
            raise ValueError("A previous review decision was overwritten")
        return {
          "historical_code_name_watershed_crosschecks":count,
          "review_candidates_remain_unapproved":pending,
          "direct_fish_records_created":0,
          "present_day_geo_approvals":0,
          "site_publication":"not_published",
        }
    finally:conn.close()

def search(db,name="",code=""):
    c=sqlite3.connect(str(db));c.row_factory=sqlite3.Row
    try:
        found=[dict(x) for x in c.execute(
          "SELECT * FROM official_historical_code_crosschecks ORDER BY river_code")]
        if name:found=[x for x in found if name in x["river_name"]]
        if code:found=[x for x in found if code==x["river_code"]]
        for x in found:
            x["present_day_prefecture_location_verified"]=False
            x["fish_observed_in_individual_river"]=None
            x["approved_current_local_to_code_link"]=False
        return {
          "total":len(found),"historical_ledger_matches":found,
          "warning":"2016年の国交省台帳で名前・水系・10桁コード・当時の管理者を照合済み。現在の川の所在地、親河川、魚類の生息は別資料で確認が必要です。"
        }
    finally:c.close()

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--db",default="river-fish/historical_crosschecks_v09.sqlite")
    p.add_argument("--build",action="store_true")
    p.add_argument("--river",default="")
    p.add_argument("--river-code",default="")
    args=p.parse_args()
    result=build(args.db) if args.build else search(args.db,args.river,args.river_code)
    print(json.dumps(result,ensure_ascii=False,indent=2))
