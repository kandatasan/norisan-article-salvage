#!/usr/bin/env python3
"""Research-only 5-prefecture Chugoku watershed + river source mentions.

Ground rules:
* A prefectural source mentioning a watershed is NOT proof of the location of
  any individual 10-digit national river code.
* Municipalities named in 2026 flood-inundation-plan tables are NOT full river
  routes and do not constitute direct ecology observations.
* Historical 2021 Hiroshima watershed groups remain distinct from second-class
  water-system registers in the four other prefectures.
* Never reuse national fish observations as tributary fish occurrences.
"""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import re
import sqlite3
import unicodedata

from national_registry_v06 import build as build_old_national

ROOT=Path(__file__).resolve().parent
WATERSHED_FILE="chugoku_second_class_watersheds_v10.csv"
RIVER_FILE="yamaguchi_river_municipality_mentions_v10.csv"
WATERSHED_HEADERS=["record_id","prefecture","jis_prefecture_code","watershed_label_as_written",
                   "source_classification","source_coverage","source_page_url",
                   "source_page_updated_date_if_verified","primary_source_type",
                   "river_code","geographic_identity_status","fish_occurrence_status","site_status"]
RIVER_HEADERS=["evidence_id","prefecture","watershed_label_as_written",
               "municipality_in_source","river_name_as_written","source_document_context",
               "source_url","page_last_updated","source_floodmap_publication_date",
               "official_river_code","code_identity_status","biological_observation_status",
               "public_website_status"]
PREF_CODES={"鳥取県":"31","島根県":"32","岡山県":"33","広島県":"34","山口県":"35"}
OFFICIAL_SOURCES={
 "岡山県":"https://www.pref.okayama.jp/page/detail-3301.html",
 "山口県":"https://www.pref.yamaguchi.lg.jp/press/136686.html",
 "島根県":"https://www.pref.shimane.lg.jp/infra/river/kasen/hoshin/",
 "鳥取県":"https://www.pref.tottori.lg.jp/item/219859.htm"
}
YAMAGUCHI_RIVERS_SOURCE="https://www.pref.yamaguchi.lg.jp/soshiki/132/277948.html"

def read_table(path,headers):
    with Path(path).open(encoding="utf-8-sig",newline="") as f:
        reader=csv.DictReader(f)
        if reader.fieldnames!=headers:
            raise ValueError("Unexpected source table columns: "+str(path))
        return list(reader)

def load_sources(root=ROOT):
    root=Path(root)
    waters=read_table(root/WATERSHED_FILE,WATERSHED_HEADERS)
    river=read_table(root/RIVER_FILE,RIVER_HEADERS)
    if len(waters)!=72 or len(river)!=81:
        raise ValueError("Official source extraction changed; rerun manual provenance review")
    names=set()
    bypref=Counter()
    for w in waters:
        if w["record_id"] in names:raise ValueError("Duplicate watershed row identity")
        names.add(w["record_id"])
        bypref[w["prefecture"]]+=1
        if (PREF_CODES.get(w["prefecture"])!=w["jis_prefecture_code"]
            or w["source_page_url"]!=OFFICIAL_SOURCES.get(w["prefecture"])
            or w["source_classification"]!="二級水系"
            or w["primary_source_type"]!="prefecture_official_html"
            or w["river_code"] or w["geographic_identity_status"]!="source_mentions_prefecture_and_watershed_only"
            or w["fish_occurrence_status"]!="not_derived"
            or w["site_status"]!="research_only"
            or not w["watershed_label_as_written"]
            or w["watershed_label_as_written"][0] in "=+-@"):
            raise ValueError("Watershed source row cannot be promoted to approved geography")
    if dict(bypref)!={"岡山県":22,"山口県":26,"島根県":17,"鳥取県":7}:
        raise ValueError("Expected official watershed source groups changed")
    ids=set()
    for r in river:
        key=(r["prefecture"],r["watershed_label_as_written"],r["municipality_in_source"],r["river_name_as_written"])
        if r["evidence_id"] in ids:raise ValueError("Duplicate river source row identity")
        ids.add(r["evidence_id"])
        if (r["prefecture"]!="山口県"
            or r["watershed_label_as_written"] not in {"佐波川","小瀬川","錦川"}
            or not r["municipality_in_source"] or not r["river_name_as_written"]
            or r["river_name_as_written"][0] in "=+-@"
            or r["source_document_context"]!="flood_inundation_map_river_municipality_listing_partial"
            or r["source_url"]!=YAMAGUCHI_RIVERS_SOURCE
            or r["page_last_updated"]!="2026-05-29"
            or r["source_floodmap_publication_date"] not in ("2026-03-24","2025-06-03")
            or r["official_river_code"]
            or r["code_identity_status"]!="unlinked_name_and_watershed"
            or r["biological_observation_status"]!="not_examined"
            or r["public_website_status"]!="research_only"):
            raise ValueError("River listing must remain source-scoped and unlinked")
    # Repeated names *across municipalities* are expected; do not deduplicate.
    return waters,river

def load_existing_hiroshima(root):
    src=Path(root)/"river_registry_hiroshima_v01.csv"
    with src.open(encoding="utf-8-sig",newline="") as f:
        records=list(csv.DictReader(f))
    if len(records)!=66:raise ValueError("Unexpected Hiroshima v0.1 archive size")
    result={}
    for r in records:
        key=r["watershed"]
        if key not in result:
            result[key]=r["source_url"]
    if len(result)!=15:raise ValueError("Hiroshima river/watershed identities changed")
    return result

def build(path,root=ROOT):
    path=Path(path)
    if path.exists():raise FileExistsError("No overwriting already audited DB")
    root=Path(root)
    waters,rivers=load_sources(root)
    earlier=build_old_national(path,root)
    conn=sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        conn.executescript("""
            CREATE TABLE prefecture_watershed_source_mentions (
              mention_id TEXT PRIMARY KEY,
              prefecture TEXT NOT NULL,
              prefecture_code TEXT NOT NULL REFERENCES prefectures(code),
              watershed_label TEXT NOT NULL,
              classification_as_published TEXT NOT NULL,
              scope TEXT NOT NULL,
              source_url TEXT NOT NULL,
              source_page_date TEXT,
              code_identity_status TEXT NOT NULL,
              geographic_review_status TEXT NOT NULL,
              species_status TEXT NOT NULL,
              site_status TEXT NOT NULL
            );
            CREATE TABLE municipality_river_source_mentions (
              mention_id TEXT PRIMARY KEY,
              prefecture TEXT NOT NULL,
              watershed_label TEXT NOT NULL,
              municipality_in_source TEXT NOT NULL,
              river_name TEXT NOT NULL,
              document_scope TEXT NOT NULL,
              source_url TEXT NOT NULL,
              source_page_date TEXT,
              document_publication_date TEXT,
              river_code TEXT,
              identity_status TEXT NOT NULL,
              species_status TEXT NOT NULL,
              site_status TEXT NOT NULL
            );
            CREATE INDEX idx_watershed_prefecture ON prefecture_watershed_source_mentions(prefecture);
            CREATE INDEX idx_river_municipality ON municipality_river_source_mentions(municipality_in_source);
            CREATE INDEX idx_river_name ON municipality_river_source_mentions(river_name);
        """)
        hs=load_existing_hiroshima(root)
        inswaters=[]
        for i,(name,url) in enumerate(sorted(hs.items()),1):
            inswaters.append((f"HS-{i:04d}","広島県","34",name,
                "existing_2021_maintenance_plan_group","river_maintenance_plan_v01_not_all_watersheds",
                url,"2021","unlinked","source_named_watershed_not_full_geography",
                "not_assigned","research_only"))
        for w in waters:
            inswaters.append((
                w["record_id"],w["prefecture"],w["jis_prefecture_code"],
                w["watershed_label_as_written"],w["source_classification"],
                w["source_coverage"],w["source_page_url"],
                w["source_page_updated_date_if_verified"] or None,
                "unlinked","source_named_watershed_not_full_geography",
                "not_assigned","research_only"
            ))
        conn.executemany("INSERT INTO prefecture_watershed_source_mentions VALUES ("+",".join("?" for _ in range(12))+")",inswaters)
        conn.executemany("INSERT INTO municipality_river_source_mentions VALUES ("+",".join("?" for _ in range(13))+")",[
            (r["evidence_id"],r["prefecture"],r["watershed_label_as_written"],
             r["municipality_in_source"],r["river_name_as_written"],
             r["source_document_context"],r["source_url"],r["page_last_updated"],
             r["source_floodmap_publication_date"],None,r["code_identity_status"],
             r["biological_observation_status"],r["public_website_status"])
            for r in rivers
        ])
        conn.commit()
        if conn.execute("PRAGMA integrity_check").fetchone()[0]!="ok" or conn.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("River source cache foreign key or integrity issue")
        totals={r[0]:r[1] for r in conn.execute(
            "SELECT prefecture,COUNT(*) FROM prefecture_watershed_source_mentions GROUP BY prefecture")}
        if totals!={"広島県":15,"岡山県":22,"山口県":26,"島根県":17,"鳥取県":7}:
            raise ValueError("Unexpected nationwide/watershed source totals")
        return {
            "prefecture_keys":earlier["prefectures"],
            "chugoku_prefecture_watershed_mentions":len(inswaters),
            "new_watershed_source_mentions":len(waters),
            "new_yamaguchi_river_municipality_mentions":len(rivers),
            "by_prefecture":totals,
            "existing_hiroshima_verified_rivers":earlier["existing_verified_river_names"],
            "existing_hiroshima_unreviewed_mentions":earlier["additional_unreviewed_river_mentions"],
            "approved_river_code_to_prefecture_links":0,
            "approved_river_fish_occurrences":0,
            "website_publication":False
        }
    finally:
        conn.close()

def search(path,prefecture="",watershed="",river="",municipality="",limit=50,offset=0):
    if not (1<=limit<=200 and offset>=0):
        raise ValueError("Invalid pagination")
    conn=sqlite3.connect(str(path));conn.row_factory=sqlite3.Row
    try:
        systems=[dict(r) for r in conn.execute("SELECT * FROM prefecture_watershed_source_mentions ORDER BY mention_id")]
        mentions=[dict(r) for r in conn.execute("SELECT * FROM municipality_river_source_mentions ORDER BY mention_id")]
        def same(x,y):
            return unicodedata.normalize("NFKC",str(x or ""))==unicodedata.normalize("NFKC",str(y or ""))
        systems=[x for x in systems if (not prefecture or same(x["prefecture"],prefecture))
                 and (not watershed or watershed in x["watershed_label"])]
        mentions=[x for x in mentions if (not prefecture or same(x["prefecture"],prefecture))
                  and (not watershed or watershed in x["watershed_label"])
                  and (not river or river in x["river_name"])
                  and (not municipality or municipality in x["municipality_in_source"])]
        return {
            "watershed_source_mentions_total":len(systems),
            "river_municipality_source_mentions_total":len(mentions),
            "watershed_mentions":systems[offset:offset+limit] if not river and not municipality else [],
            "river_mentions":mentions[offset:offset+limit],
            "limit":limit,"offset":offset,
            "notice":"各県の水系・河川名の資料掲載事実のみ。山口県の関係市町は川の全流路ではありません。水系名は全国河川コードと未照合。支流ごとの魚の生息を推測しません。"
        }
    finally:conn.close()

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--db",default="river-fish/chugoku_5pref_registry_v10.sqlite")
    p.add_argument("--build",action="store_true")
    p.add_argument("--prefecture",default="")
    p.add_argument("--watershed",default="")
    p.add_argument("--river",default="")
    p.add_argument("--municipality",default="")
    p.add_argument("--limit",type=int,default=40)
    p.add_argument("--offset",type=int,default=0)
    args=p.parse_args()
    result=build(args.db) if args.build else search(args.db,args.prefecture,args.watershed,args.river,args.municipality,args.limit,args.offset)
    print(json.dumps(result,ensure_ascii=False,indent=2))
