#!/usr/bin/env python3
"""Bridge dated MLIT river-code evidence to a newer prefectural municipality list.

All relations remain document-scoped: no full river geometry, direct parent,
fish observation or current 10-digit code reuse is auto-inferred.
"""
import argparse
import csv
import json
from pathlib import Path
import sqlite3
from historical_ledger_crosscheck_v09 import build as build_historical, search as historical_search

ROOT=Path(__file__).resolve().parent
CSVNAME="ota_municipality_evidence_v09.csv"
URL="https://www.pref.hiroshima.lg.jp/uploaded/attachment/634919.pdf"
FIELDS=["local_evidence_id","river_name","water_system_name","municipality_from_document",
        "document_listing_type","designation_date_if_given","pdf_page_1based",
        "document_url","checked_on","evidence_status","entire_river_course_status","fish_site_status"]

def evidence(root=ROOT):
    with (Path(root)/CSVNAME).open(encoding="utf-8-sig",newline="") as f:
        d=csv.DictReader(f)
        if d.fieldnames!=FIELDS:raise ValueError("Unexpected municipality evidence schema")
        rows=list(d)
    if len(rows)!=12:raise ValueError("The 12 source excerpts changed; review before import")
    ids=set()
    for r in rows:
        key=(r["local_evidence_id"],r["municipality_from_document"],
             r["document_listing_type"])
        if key in ids:raise ValueError("Duplicate document municipality evidence")
        ids.add(key)
        k=r["document_listing_type"]
        if (k not in ("flood_risk_related_municipality","prefectural_river_camera_municipality")
          or (k=="flood_risk_related_municipality" and (not r["designation_date_if_given"] or r["pdf_page_1based"]!="145"))
          or (k=="prefectural_river_camera_municipality" and (r["designation_date_if_given"] or r["pdf_page_1based"]!="33"))
          or not r["municipality_from_document"]
          or r["water_system_name"]!="太田川"
          or r["document_url"]!=URL
          or r["checked_on"]!="2026-10-18"
          or r["evidence_status"]!="prefectural_document_named_river_and_municipality"
          or r["entire_river_course_status"]!="not_exhaustively_verified"
          or r["fish_site_status"]!="not_assigned"):
            raise ValueError("Municipality source claim not supported by reviewed document")
    return rows

def build(path,root=ROOT):
    path=Path(path)
    if path.exists():raise FileExistsError("Do not overwrite the evidence cache")
    history=build_historical(path,root)
    conn=sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        conn.executescript("""
            CREATE TABLE municipal_document_evidence (
              local_id TEXT NOT NULL REFERENCES official_historical_code_crosschecks(local_id),
              river_name TEXT NOT NULL,
              watershed_name TEXT NOT NULL,
              municipality_in_document TEXT NOT NULL,
              source_listing_type TEXT NOT NULL,
              designation_date TEXT,
              pdf_page TEXT NOT NULL,
              source_url TEXT NOT NULL,
              checked_on TEXT NOT NULL,
              evidence_status TEXT NOT NULL,
              complete_geography_status TEXT NOT NULL,
              species_status TEXT NOT NULL,
              PRIMARY KEY (local_id,municipality_in_document,source_listing_type)
            );
        """)
        rows=evidence(root)
        official={
            x[0]:(x[1],x[2]) for x in conn.execute(
                "SELECT local_id,river_name,watershed_name FROM official_historical_code_crosschecks")
        }
        for r in rows:
            if official.get(r["local_evidence_id"])!=(r["river_name"],r["water_system_name"]):
                raise ValueError("Local municipality excerpt cannot join historical code source")
        conn.executemany("INSERT INTO municipal_document_evidence VALUES ("+",".join("?" for _ in range(12))+")",[
            (r["local_evidence_id"],r["river_name"],r["water_system_name"],
             r["municipality_from_document"],r["document_listing_type"],
             r["designation_date_if_given"] or None,r["pdf_page_1based"],
             r["document_url"],r["checked_on"],r["evidence_status"],
             r["entire_river_course_status"],r["fish_site_status"])
            for r in rows
        ])
        conn.commit()
        if conn.execute("PRAGMA integrity_check").fetchone()[0]!="ok" or conn.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("Integrity check failed")
        return dict(history,
                    newer_prefectural_document_municipality_mentions=12,
                    historically_crosschecked_rivers_with_additional_municipal_evidence=10,
                    current_complete_geography_approvals=0,
                    direct_river_fish_approvals=0)
    finally:conn.close()

def search(path,river=""):
    earlier=historical_search(path,name=river)
    conn=sqlite3.connect(path);conn.row_factory=sqlite3.Row
    try:
        for record in earlier["historical_ledger_matches"]:
            rows=conn.execute("""SELECT municipality_in_document,source_listing_type,designation_date,
                               pdf_page,source_url,checked_on,evidence_status
                               FROM municipal_document_evidence WHERE local_id=?
                               ORDER BY municipality_in_document""",(record["local_id"],)).fetchall()
            record["municipalities_in_newer_prefectural_document"]=[dict(x) for x in rows]
            record["complete_river_course_verified"]=False
            record["individual_river_fish_evidence"]=None
        earlier["notice"]="2016年河川コードとの照合＋広島県資料に掲載された関係市町（または河川監視施設の所在市）を表示。川の全流路や現在の管理区分、魚の生息は確定していません。"
        return earlier
    finally:conn.close()

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--db",default="river-fish/river_evidence_v09.sqlite")
    p.add_argument("--build",action="store_true")
    p.add_argument("--river",default="")
    a=p.parse_args()
    result=build(a.db) if a.build else search(a.db,a.river)
    print(json.dumps(result,ensure_ascii=False,indent=2))
