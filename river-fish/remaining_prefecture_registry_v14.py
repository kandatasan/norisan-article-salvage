#!/usr/bin/env python3
"""Add source-limited river/river-basin names for remaining 32 prefectures.

Reuses v1.3 national SQLite with official 35,449 river names, 18,814
watershed-year fish names, and 15 prefectures' independent local sources.
The new 439 name mentions are split by river, watershed and planning_region.

Do NOT promote any source mention to a located 10-digit RiverCodeCd record.
Do NOT associate nationwide watershed fish observations with any tributary.
This is an offline, research-only stage; never modifies WordPress.
"""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import sqlite3
from urllib.parse import urlparse
import unicodedata

from multi_prefecture_registry_v13 import build as build_v13, unified_search as search_v13

ROOT=Path(__file__).resolve().parent
MENTIONS="remaining_32pref_source_mentions_v14.csv"
MANIFEST="remaining_32pref_manifest_v14.json"
FIELDS=["mention_id","prefecture","label_type","name_as_written",
        "watershed_explicit_in_source","source_context","source_document_scope",
        "source_page_url","page_date_if_available","individual_river_code",
        "source_review_status","national_code_geography_status",
        "individual_fish_evidence_status","public_website_status"]
TYPES=("river","watershed","planning_region")
SOURCE_STATUS="official_page_name_mention_checked_code_identity_unreviewed"

def norm(s):
    return unicodedata.normalize("NFKC",str(s or "")).casefold().strip()

def read_sources(root=ROOT):
    root=Path(root)
    with (root/MENTIONS).open(encoding="utf-8-sig",newline="") as f:
        reader=csv.DictReader(f)
        if reader.fieldnames!=FIELDS:raise ValueError("Unexpected 32-pref source schema")
        rows=list(reader)
    m=json.loads((root/MANIFEST).read_text(encoding="utf-8"))
    if (m["source_mention_count"]!=len(rows) or len(rows)!=439 or
        m["new_prefecture_count"]!=32 or
        not m["public_site_status"]=="research_only" or
        m["direct_fish_observations_created"]!=0 or
        m["code_to_prefecture_identity_approvals"]!=0):
        raise ValueError("National source manifest count/permissions changed")
    ids=set()
    counts=Counter(); kindcounts=Counter(); sources=Counter()
    for x in rows:
        name=x["name_as_written"]
        if x["mention_id"] in ids:raise ValueError("Duplicate source mention ID")
        ids.add(x["mention_id"])
        counts[x["prefecture"]]+=1
        kindcounts[x["label_type"]]+=1
        sources[(x["prefecture"],x["source_document_scope"],x["source_page_url"],x["label_type"])]+=1
        u=urlparse(x["source_page_url"])
        if (x["label_type"] not in TYPES
            or not x["source_context"] and x["label_type"]=="planning_region"
            or not x["source_document_scope"]
            or not name or name[0] in "=+-@"
            or u.scheme!="https"
            or not (u.hostname and (
                u.hostname.startswith("www.pref.") and u.hostname.endswith(".jp")
                or u.hostname=="www.kensetsu.metro.tokyo.lg.jp"
                or u.hostname=="web.pref.hyogo.lg.jp"
              ))
            or x["source_review_status"]!=SOURCE_STATUS
            or x["individual_river_code"]!=""
            or x["national_code_geography_status"]!="unlinked"
            or x["individual_fish_evidence_status"]!="not_observed_in_this_source"
            or x["public_website_status"]!="research_only_not_wordpress"):
            raise ValueError("Source-restricted evidence failed: "+x["mention_id"])
        if x["label_type"]=="watershed" and x["watershed_explicit_in_source"]!=name:
            raise ValueError("Watershed source name isn't the explicitly listed basin")
        if x["label_type"]=="planning_region" and x["watershed_explicit_in_source"]:
            raise ValueError("Planning region is not evidence for an exact watershed")
    if (len(counts)!=32 or
        counts.keys()!=set(m["prefectures"]) or
        kindcounts!=Counter(m["by_kind"])):
        raise ValueError("Missing official source jurisdictions")
    groups=Counter((x["prefecture"],x["source_document_scope"],x["source_page_url"],x["label_type"]) for x in rows)
    for g in m["source_groups"]:
        key=(g["prefecture"],g["scope"],g["url"],g["kind"])
        if groups.get(key,0)!=g["rows"]:
            raise ValueError("Actual source group not matching reviewed manifest")
    if len(m["source_groups"])!=len(groups):
        raise ValueError("Unknown/duplicate official source groups")
    return rows,m

def build(db,root=ROOT):
    db=Path(db)
    if db.exists():raise FileExistsError("No overwriting previous national research database")
    previous=build_v13(db,root)
    rows,manifest=read_sources(root)
    conn=sqlite3.connect(db)
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        conn.executescript("""
            CREATE TABLE new_prefecture_official_mentions (
              mention_id TEXT PRIMARY KEY,
              prefecture TEXT NOT NULL,
              prefecture_code TEXT NOT NULL REFERENCES prefectures(code),
              source_label_type TEXT NOT NULL CHECK (source_label_type IN ('river','watershed','planning_region')),
              literal_name TEXT NOT NULL,
              explicit_watershed TEXT,
              source_context TEXT,
              source_scope TEXT NOT NULL,
              source_url TEXT NOT NULL,
              page_date TEXT,
              review_status TEXT NOT NULL,
              national_river_code TEXT,
              code_identity_status TEXT NOT NULL CHECK (code_identity_status='unlinked'),
              direct_fish_status TEXT NOT NULL CHECK (direct_fish_status='not_observed_in_this_source'),
              publication_status TEXT NOT NULL CHECK (publication_status='research_only_not_wordpress')
            );
            CREATE INDEX idx_new_pref ON new_prefecture_official_mentions(prefecture);
            CREATE INDEX idx_new_label ON new_prefecture_official_mentions(literal_name);
            CREATE INDEX idx_new_type ON new_prefecture_official_mentions(source_label_type);
        """)
        codes=dict(conn.execute("SELECT prefecture_name,code FROM prefectures"))
        if any(x["prefecture"] not in codes for x in rows):
            raise ValueError("Invalid prefecture code")
        conn.executemany("INSERT INTO new_prefecture_official_mentions VALUES ("+",".join(["?"]*15)+")",[
            (r["mention_id"],r["prefecture"],codes[r["prefecture"]],r["label_type"],
             r["name_as_written"],r["watershed_explicit_in_source"] or None,
             r["source_context"] or None,r["source_document_scope"],
             r["source_page_url"],r["page_date_if_available"] or None,
             r["source_review_status"],None,r["national_code_geography_status"],
             r["individual_fish_evidence_status"],r["public_website_status"])
            for r in rows
        ])
        conn.commit()
        if (conn.execute("PRAGMA integrity_check").fetchone()[0]!="ok"
            or conn.execute("PRAGMA foreign_key_check").fetchall()):
            raise ValueError("Failed national research DB integrity QA")
        with_sources=conn.execute("""
            SELECT COUNT(DISTINCT prefecture) FROM (
              SELECT prefecture FROM prefecture_watershed_source_mentions
              UNION SELECT prefecture FROM other_prefecture_official_source_mentions
              UNION SELECT prefecture FROM new_prefecture_official_mentions
            )""").fetchone()[0]
        if with_sources!=47:raise ValueError("There must be source evidence for each of the 47 prefectures")
        return {
          "prefecture_directory":previous["directory_prefectures"],
          "prefecture_source_coverage":with_sources,
          "new_source_mentions":len(rows),
          "new_source_types":manifest["by_kind"],
          "old_ten_pref_source_mentions":previous["source_mentions_added"],
          "national_code_name_rows":previous["national_code_river_name_count"],
          "national_watershed_year_fish_rows":previous["national_water_system_fish_name_count"],
          "code_to_prefecture_identity_links_approved":0,
          "direct_tributary_fish_confirmations":0,
          "all_prefecture_rivers_exhaustively_catalogued":False,
          "website_published":False
        }
    finally:
        conn.close()

def source_search(db,prefecture="",name="",kind="",limit=35,offset=0):
    if not (1<=limit<=200 and offset>=0):raise ValueError("Invalid page size")
    if kind and kind not in TYPES:raise ValueError("Invalid source label type")
    conn=sqlite3.connect(str(db));conn.row_factory=sqlite3.Row
    try:
        valid={r["prefecture_name"] for r in conn.execute("SELECT prefecture_name FROM prefectures")}
        if prefecture and prefecture not in valid:raise ValueError("Unknown prefecture")
        all_rows=[dict(r) for r in conn.execute(
          "SELECT * FROM new_prefecture_official_mentions ORDER BY mention_id"
        )]
        found=[r for r in all_rows if
          (not prefecture or r["prefecture"]==prefecture)
          and (not name or norm(name) in norm(r["literal_name"]))
          and (not kind or r["source_label_type"]==kind)]
        for r in found:
            r["current_river_code"]=None
            r["verified_full_river_course"]=False
            r["fish_observation_in_specific_river"]=None
        return {"source_matches_total":len(found),
                "source_matches":found[offset:offset+limit],
                "review_status":"research_only",
                "scope_notice":"県公式資料に川名・水系名・整備圏域名が登場することの資料証拠のみ。県の全河川網羅・現行河川区分・10桁コードと所在地・個別の生息魚は未承認。"}

    finally:
        conn.close()

def unified_search(db,prefecture="",name="",limit=35,offset=0):
    old=search_v13(db,prefecture=prefecture,name=name,limit=limit,offset=offset)
    extra=source_search(db,prefecture=prefecture,name=name,limit=limit,offset=offset)
    old["remaining_prefecture_official_mentions_total"]=extra["source_matches_total"]
    old["remaining_prefecture_official_mentions"]=extra["source_matches"]
    old["remaining_source_notice"]=extra["scope_notice"]
    old["all_47_prefectures_have_at_least_one_official_page_source"]=True
    old["all_47_prefecture_rivers_exhaustively_covered"]=False
    old["national_code_to_prefecture_link_approved"]=0
    old["individual_fish_site_from_this_update"]=None
    if prefecture and extra["source_matches_total"] and old["prefecture_local_river_source_status"]=="no_local_river_source_loaded":
        old["prefecture_local_river_source_status"]="partial_official_source_mentions_only"
    return old

if __name__=="__main__":
    p=argparse.ArgumentParser(description="つりくえ！全国47県・公式掲載資料名の研究版")
    p.add_argument("--db",default="river-fish/47pref_sources_v14.sqlite")
    p.add_argument("--build",action="store_true")
    p.add_argument("--prefecture",default="")
    p.add_argument("--name",default="")
    p.add_argument("--kind",default="")
    p.add_argument("--limit",type=int,default=30)
    p.add_argument("--offset",type=int,default=0)
    a=p.parse_args()
    result=(build(a.db) if a.build else
       source_search(a.db,a.prefecture,a.name,a.kind,a.limit,a.offset) if a.kind
       else unified_search(a.db,a.prefecture,a.name,a.limit,a.offset))
    print(json.dumps(result,ensure_ascii=False,indent=2))
