#!/usr/bin/env python3
"""Unresolved small-river name mentions, separated from verified river identities.

Key design:
 - 98 source mentions are NOT 98 newly identified river objects.
 - A name-match to canonical rivers is only a possible identity match, not a join.
 - No fish species from the 2,285 watershed records are assigned to these rivers.
 - No network or WordPress changes; SQLite is an offline inspection cache.
"""
import argparse
import csv
import json
import sqlite3
import unicodedata
from pathlib import Path

from river_registry_v01 import create_database, find_rivers, ROOT as BASE_ROOT

ROOT=Path(__file__).resolve().parent
MENTIONS="river_name_mentions_hiroshima_v02.csv"
REQUIRED=["mention_id","prefecture","municipality_listing","river_name",
          "source_listing_class","watershed_review_status","watershed_name",
          "canonical_review_status","source_url","source_page_date",
          "source_page_section","public_site_status"]
PERMITTED_CLASSES={"一級河川","二級河川","単独河川","準用河川","普通河川"}
SOURCE_HOSTS={"www.pref.hiroshima.lg.jp","www.city.hiroshima.lg.jp"}

def norm(text):
    return unicodedata.normalize("NFKC",str(text or "")).casefold().strip()

def load_mentions(root=ROOT):
    from urllib.parse import urlparse
    with (Path(root)/MENTIONS).open(encoding="utf-8-sig",newline="") as fd:
        reader=csv.DictReader(fd)
        if reader.fieldnames != REQUIRED:raise ValueError("Source mention fields changed")
        results=list(reader)
    seen=set()
    for r in results:
        if r["mention_id"] in seen:raise ValueError("Duplicate mention ID")
        seen.add(r["mention_id"])
        if (not r["river_name"].strip() or not r["municipality_listing"].strip()
            or r["source_listing_class"] not in PERMITTED_CLASSES
            or r["watershed_review_status"]!="unverified"
            or r["watershed_name"]
            or r["canonical_review_status"]!="awaiting_identity_review"
            or r["public_site_status"]!="research_only"
            or urlparse(r["source_url"]).netloc not in SOURCE_HOSTS):
            raise ValueError("Mention has unsupported or inferred fields: "+r["mention_id"])
    return results

def create_catalog(db_path,source_dir=ROOT):
    db_path=Path(db_path)
    if db_path.exists():raise FileExistsError("Will not overwrite database. Build to a new path.")
    base=create_database(db_path,source_dir=source_dir)
    mentions=load_mentions(source_dir)
    conn=sqlite3.connect(db_path)
    try:
        conn.executescript("""
            CREATE TABLE river_name_mentions (
              mention_id TEXT PRIMARY KEY,
              prefecture TEXT NOT NULL,
              municipality_listing TEXT NOT NULL,
              river_name TEXT NOT NULL,
              source_listing_class TEXT NOT NULL,
              watershed_review_status TEXT NOT NULL,
              watershed_name TEXT,
              canonical_review_status TEXT NOT NULL,
              source_url TEXT NOT NULL,
              source_page_date TEXT NOT NULL,
              source_page_section TEXT NOT NULL,
              public_site_status TEXT NOT NULL
            );
            CREATE INDEX river_mentions_name_idx ON river_name_mentions(river_name);
            CREATE INDEX river_mentions_municipality_idx ON river_name_mentions(municipality_listing);
        """)
        conn.executemany(
            "INSERT INTO river_name_mentions VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            [tuple(r.get(k) or None for k in REQUIRED) for r in mentions]
        )
        conn.commit()
        assert conn.execute("PRAGMA integrity_check").fetchone()[0]=="ok"
        canon_names={norm(row[0]) for row in conn.execute("SELECT river_name FROM rivers")}
        names={norm(row["river_name"]) for row in mentions}
        return {
          "canonical_rivers":base["rivers"],
          "unresolved_name_mentions":len(mentions),
          "distinct_unresolved_name_labels":len(names),
          "name_labels_also_in_canonical":len(names & canon_names),
          "name_labels_not_in_canonical":len(names-canon_names),
          "all_new_mention_species_evidence":0,
          "site_publication":"not_deployed",
          "warning":"Name mentions are not unique river counts. No unreviewed name can inherit watershed fish observations."
        }
    finally:
        conn.close()

def search(db_path,name="",municipality="",kind="",limit=50):
    if not (1<=limit<=200):raise ValueError("invalid limit")
    if kind and kind not in PERMITTED_CLASSES:raise ValueError("invalid class")
    db_path=Path(db_path)
    if not db_path.is_file():raise FileNotFoundError("Build the offline database first")
    canonical=find_rivers(db_path,name=name,municipality=municipality,limit=200)
    conn=sqlite3.connect(db_path)
    conn.row_factory=sqlite3.Row
    try:
        all_mentions=conn.execute("SELECT * FROM river_name_mentions ORDER BY mention_id").fetchall()
        hits=[]
        for rec in all_mentions:
            r=dict(rec)
            if name and norm(name) not in norm(r["river_name"]):continue
            if municipality and norm(municipality) not in norm(r["municipality_listing"]):continue
            if kind and kind!=r["source_listing_class"]:continue
            possibles=conn.execute("SELECT river_id,watershed,prefecture FROM rivers WHERE river_name=?",
                                  (r["river_name"],)).fetchall()
            hits.append({
                "mention_id":r["mention_id"],
                "river_name":r["river_name"],
                "municipality_from_listing":r["municipality_listing"],
                "class_as_written_in_source":r["source_listing_class"],
                "source_url":r["source_url"],
                "source_page_date":r["source_page_date"],
                "watershed":None,
                "direct_parent":None,
                "fish_occurrences_for_this_river":None,
                "possible_same_name_canonical_rivers":[dict(c) for c in possibles],
                "possible_matches_are_verified":False,
                "review_status":"river_identity_unresolved",
            })
        # Kind-filtered candidate results do not imply a legal-class filter
        # on canonical rows: legal_class is unverified in v0.1.
        return {
            "canonical_total":canonical["total_rivers"] if not kind else 0,
            "canonical_rivers":canonical["rivers"][:limit] if not kind else [],
            "mention_total":len(hits),
            "unresolved_mentions":hits[:limit],
            "notice":"未照合の河川名候補は魚種・水系・親河川を確定していません。名称一致は同一河川の証明ではありません。"
        }
    finally:
        conn.close()

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--db",default="river-fish/hiroshima_river_catalog_v02.sqlite")
    p.add_argument("--build",action="store_true")
    p.add_argument("--name",default="")
    p.add_argument("--municipality",default="")
    p.add_argument("--class-name",dest="kind",default="")
    p.add_argument("--limit",type=int,default=40)
    x=p.parse_args()
    if x.build:
        result=create_catalog(x.db)
    else:
        result=search(x.db,x.name,x.municipality,x.kind,x.limit)
    print(json.dumps(result,ensure_ascii=False,indent=2))
