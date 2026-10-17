#!/usr/bin/env python3
"""Offline search for locally sourced river-code candidates and fish narratives.

NEVER joins a fish narrative to a 10-digit river code or a prefectural fish
observation without an independently approved source-to-code identity review.
"""
import argparse
import csv
import json
from pathlib import Path
import sqlite3
import unicodedata
from review_hiroshima_code_links_v08 import compute_candidates,export,FIELDS

ROOT=Path(__file__).resolve().parent
ECOLOGY_FIELDS=["record_id","prefecture","river_name","watershed_name",
                "fish_label_as_written","evidence_scope","source_kind","survey_year",
                "source_page_date","source_url","source_uncertainty",
                "sensitive_species_flag","national_river_code",
                "identity_review_status","publication_status"]

def read_rows(path,headers):
    with Path(path).open(encoding="utf-8-sig",newline="") as f:
        reader=csv.DictReader(f)
        if reader.fieldnames != headers:raise ValueError("Unexpected reviewed evidence schema")
        return list(reader)

def verify_narratives(root=ROOT):
    fish=read_rows(Path(root)/"hiroshima_river_fish_narratives_v08.csv",ECOLOGY_FIELDS)
    ids=set()
    for r in fish:
        if r["record_id"] in ids:raise ValueError("Duplicate fish narrative ID")
        ids.add(r["record_id"])
        if not all(r[x] for x in ["prefecture","river_name","watershed_name","fish_label_as_written","source_url"]):
            raise ValueError("Missing source fish evidence")
        if (r["source_kind"]!="prefectural_environment_narrative" or
            r["evidence_scope"]!="named_river_general_no_specific_site" or
            r["survey_year"]!="" or
            r["national_river_code"]!="" or
            r["identity_review_status"]!="unlinked_river_code_pending_review" or
            r["publication_status"]!="research_only_not_website_published" or
            r["sensitive_species_flag"] not in ("true","false")):
            raise ValueError("Unreviewed ecology record claims survey year, species site or official river-code assignment")
        if not r["source_url"].startswith("https://www.pref.hiroshima.lg.jp/"):
            raise ValueError("Unsupported ecology source host")
    return fish

def build_database(path,root=ROOT):
    path=Path(path)
    if path.exists():raise FileExistsError("Refuse to overwrite an existing review database")
    candidates,manifest=compute_candidates(root)
    if not candidates or any(c["identity_approved"]!="false" or
                             c["prefecture_attribution_approved"]!="false" or
                             c["fish_attribution_approved"]!="false"
                             for c in candidates):
        raise ValueError("An unreviewed identity candidate was marked approved")
    fish=verify_narratives(root)
    conn=sqlite3.connect(path)
    try:
        conn.executescript("""
            PRAGMA foreign_keys=ON;
            CREATE TABLE identity_candidates (
                local_id TEXT NOT NULL, local_type TEXT NOT NULL,
                prefecture_in_source TEXT NOT NULL, municipality_in_source TEXT NOT NULL,
                river_name_in_source TEXT NOT NULL, watershed_in_source TEXT,
                source_url TEXT NOT NULL, code_candidate TEXT,
                candidate_watershed TEXT, match_basis TEXT NOT NULL,
                candidate_count INTEGER NOT NULL, review_status TEXT NOT NULL,
                identity_approved TEXT NOT NULL CHECK(identity_approved='false'),
                prefecture_approved TEXT NOT NULL CHECK(prefecture_approved='false'),
                fish_approved TEXT NOT NULL CHECK(fish_approved='false'),
                PRIMARY KEY(local_id,code_candidate)
            );
            CREATE INDEX idx_candidates_name ON identity_candidates(river_name_in_source);
            CREATE INDEX idx_candidates_review ON identity_candidates(review_status);
            CREATE TABLE narrative_fish_mentions (
                record_id TEXT PRIMARY KEY, prefecture TEXT NOT NULL,
                river_name TEXT NOT NULL, watershed_name TEXT NOT NULL,
                fish_label TEXT NOT NULL, evidence_scope TEXT NOT NULL,
                source_kind TEXT NOT NULL, survey_year TEXT,
                source_page_date TEXT NOT NULL, source_url TEXT NOT NULL,
                source_uncertainty TEXT NOT NULL, sensitive_flag TEXT NOT NULL,
                national_river_code TEXT, identity_review_status TEXT NOT NULL,
                publication_status TEXT NOT NULL
            );
        """)
        conn.executemany("INSERT INTO identity_candidates VALUES ("+",".join(["?"]*15)+")",[
            (c["local_evidence_id"],c["local_evidence_type"],c["prefecture_in_source"],
             c["municipality_in_source"],c["river_name_in_source"],
             c["watershed_in_source"],c["source_url"],c["candidate_river_code"],
             c["candidate_watershed_name"],c["match_basis"],c["candidate_count_for_evidence"],
             c["review_status"],c["identity_approved"],c["prefecture_attribution_approved"],
             c["fish_attribution_approved"])
            for c in candidates
        ])
        conn.executemany("INSERT INTO narrative_fish_mentions VALUES ("+",".join(["?"]*15)+")",[
            tuple(row[key] for key in ECOLOGY_FIELDS) for row in fish
        ])
        conn.commit()
        assert conn.execute("PRAGMA integrity_check").fetchone()[0]=="ok"
        return {
            "local_sources":manifest["total_local_evidence"],
            "unapproved_code_candidate_rows":conn.execute("SELECT COUNT(*) FROM identity_candidates").fetchone()[0],
            "new_narrative_fish_name_mentions":conn.execute("SELECT COUNT(*) FROM narrative_fish_mentions").fetchone()[0],
            "approved_code_links":0,"new_census_observations":0,"site_published":False
        }
    finally:
        conn.close()

def norm(x):
    return unicodedata.normalize("NFKC",str(x or "")).strip().casefold()

def query(db,river_name="",prefecture="",municipality="",limit=40):
    if not 1<=limit<=200:raise ValueError("Invalid page size")
    conn=sqlite3.connect(str(db));conn.row_factory=sqlite3.Row
    try:
        all_candidates=[dict(c) for c in conn.execute("SELECT * FROM identity_candidates ORDER BY local_id,code_candidate")]
        candidates=[c for c in all_candidates
                    if (not river_name or norm(river_name) in norm(c["river_name_in_source"]))
                    and (not prefecture or norm(prefecture) in norm(c["prefecture_in_source"]))
                    and (not municipality or norm(municipality) in norm(c["municipality_in_source"]))]
        all_ecology=[dict(e) for e in conn.execute("SELECT * FROM narrative_fish_mentions ORDER BY record_id")]
        ecology=[e for e in all_ecology
                 if (not river_name or norm(river_name) in norm(e["river_name"]))
                 and (not prefecture or norm(prefecture) in norm(e["prefecture"]))]
        # Do not attempt to tie narratives to any candidate river-code.
        return {
            "candidate_total":len(candidates),"candidate_rows":candidates[:limit],
            "narrative_total":len(ecology),
            "river_named_fish_narratives":ecology[:limit],
            "approved_prefecture_to_code_links":0,
            "approved_fish_to_official_code_links":0,
            "warning":"全国コードとの名称一致は同一河川の証明ではありません。魚は県の説明資料に登場した名称で、現在の生息・現地調査年・希少種の詳細位置は確定していません。"
        }
    finally:conn.close()

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--db",default="river-fish/hiroshima_identity_review_v08.sqlite")
    p.add_argument("--build",action="store_true")
    p.add_argument("--river",default="")
    p.add_argument("--prefecture",default="")
    p.add_argument("--municipality",default="")
    p.add_argument("--limit",type=int,default=40)
    x=p.parse_args()
    result=build_database(x.db) if x.build else query(x.db,x.river,x.prefecture,x.municipality,x.limit)
    print(json.dumps(result,ensure_ascii=False,indent=2))
