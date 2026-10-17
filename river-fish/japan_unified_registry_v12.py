#!/usr/bin/env python3
"""Build one research-only national river data catalog from v0.6–v1.1.

47 prefecture keys are a directory, NOT an assertion of 47-prefecture
per-river coverage. 35,449 official code/name pairs have NO prefecture links.
18,814 census fish records are watershed-only: NEVER attach them to a river,
or to a prefecture.  All listed local river evidence stays source scoped.

Source data live in this repository; this program uses no network, does no
WordPress writes, and builds a reproducible SQLite cache without overriding.
"""
import argparse
import csv
import json
from pathlib import Path
import sqlite3
import unicodedata

from tottori_detailed_registry_v11 import build as build_local
from national_river_catalog_v07 import load as read_codes, RIVER_HEADERS, WATER_HEADERS

HERE=Path(__file__).resolve().parent
OFFICIAL_CODE_DIR="national-codes-staged"
FISH_REGIONS=["hokkaido","tohoku","kanto","hokuriku","chubu","kinki","chugoku","shikoku","kyushu"]
FISH_FIELDS=["region","watershed","survey_year","recorded_name","source_url","source_sha256"]
NOTICE=("全国コードは所在県未確認。県別資料の掲載行と河川コードの名称一致は同じ川の証明ではありません。"
        "水系単位の魚類調査記録を個別の川や県の生息魚へ割り振りません。"
        "資料にない県・河川は不存在ではなく未収録です。")

def norm(s):
    return unicodedata.normalize("NFKC",str(s or "")).casefold().strip()

def load_national_records(root=HERE):
    root=Path(root)
    codes=read_codes(root/OFFICIAL_CODE_DIR/"river_codes_national_v07.csv",RIVER_HEADERS)
    waters=read_codes(root/OFFICIAL_CODE_DIR/"watershed_codes_national_v07.csv",WATER_HEADERS)
    manifest=json.loads((root/OFFICIAL_CODE_DIR/"river_code_manifest_v07.json").read_text(encoding="utf-8"))
    if (len(codes)!=35449 or len(waters)!=5475
        or manifest["river_code_rows"]!=len(codes)
        or manifest["watershed_code_rows"]!=len(waters)
        or manifest["prefecture_mapping"]!="not_inferred"
        or not manifest["no_W05_geometries"]):
        raise ValueError("Unaudited national river-code inputs")
    codes_by_id=set()
    for r in codes:
        if r["river_code"] in codes_by_id:raise ValueError("Duplicate nationwide river code")
        codes_by_id.add(r["river_code"])
        if r["identity_status"]!="coded_name_only_not_geographically_verified" or r["site_status"]!="research_only":
            raise ValueError("National code source incorrectly geography-approved")
    return codes,waters

def load_fish_regions(root=HERE):
    root=Path(root)
    for region in FISH_REGIONS:
        path=root/"nationwide-staged"/region
        manifest=json.loads((path/"manifest.json").read_text(encoding="utf-8"))
        if (manifest["region"]!=region or manifest["prefecture_mapping"]!="not_inferred"
            or manifest["direct_river_mapping"]!="not_inferred"
            or manifest["status"]!="staged_not_published"):
            raise ValueError("National census regional manifest could leak river geography")
        with (path/"watershed_year_fish.csv").open(encoding="utf-8-sig",newline="") as f:
            reader=csv.DictReader(f)
            if reader.fieldnames!=FISH_FIELDS:raise ValueError("National census schema unexpected")
            rows=list(reader)
        if len(rows)!=manifest["aggregated_records"]:
            raise ValueError("Fish region counts not verified")
        if not all(r["region"]==region and
                   r["source_sha256"]==manifest["source_sha256"]
                   for r in rows):
            raise ValueError("Fish source provenance inconsistent")
        yield region,rows

def build(path,root=HERE):
    path=Path(path)
    if path.exists():raise FileExistsError("Existing source DB must never be overwritten")
    root=Path(root)
    existing=build_local(path,root=root)
    conn=sqlite3.connect(path)
    try:
        conn.executescript("""
            CREATE TABLE national_named_river_codes (
              river_code TEXT PRIMARY KEY,
              river_name TEXT NOT NULL,
              watershed_code TEXT NOT NULL,
              watershed_name TEXT,
              source_url TEXT NOT NULL,
              official_name_status TEXT NOT NULL,
              prefecture_assignment_status TEXT NOT NULL CHECK(prefecture_assignment_status='not_mapped')
            );
            CREATE INDEX idx_national_code_name ON national_named_river_codes(river_name);
            CREATE INDEX idx_national_code_water ON national_named_river_codes(watershed_name);
            CREATE TABLE national_census_watershed_fish (
              region TEXT NOT NULL,
              watershed_name TEXT NOT NULL,
              survey_year TEXT NOT NULL,
              recorded_name TEXT NOT NULL,
              source_url TEXT NOT NULL,
              source_sha256 TEXT NOT NULL,
              geographic_scope TEXT NOT NULL CHECK(geographic_scope='watershed_not_river_not_prefecture'),
              PRIMARY KEY(region,watershed_name,survey_year,recorded_name)
            );
            CREATE INDEX idx_national_fish_name ON national_census_watershed_fish(recorded_name);
            CREATE INDEX idx_national_fish_watershed ON national_census_watershed_fish(watershed_name);
            CREATE TABLE official_station_localization_evidence (
              evidence_id TEXT PRIMARY KEY,
              prefecture_code TEXT NOT NULL REFERENCES prefectures(code),
              prefecture_name TEXT NOT NULL,
              river_name TEXT NOT NULL,
              watershed_name TEXT NOT NULL,
              site_source_url TEXT NOT NULL,
              reviewed_station_location_status TEXT NOT NULL,
              official_river_code TEXT,
              code_match_review_status TEXT NOT NULL,
              fish_evidence_status TEXT NOT NULL
            );
        """)
        codes,waters=load_national_records(root)
        conn.executemany(
          "INSERT INTO national_named_river_codes VALUES (?,?,?,?,?,?,?)",[
            (r["river_code"],r["river_name"],r["watershed_code"],
             r["watershed_name"] or None,r["source_url"],r["identity_status"],
             "not_mapped") for r in codes
        ])
        count_fish=0
        for region,rows in load_fish_regions(root):
            conn.executemany(
              "INSERT INTO national_census_watershed_fish VALUES (?,?,?,?,?,?,?)",[
               (r["region"],r["watershed"],r["survey_year"],r["recorded_name"],
                r["source_url"],r["source_sha256"],"watershed_not_river_not_prefecture")
               for r in rows
              ])
            count_fish+=len(rows)
        conn.commit()
        counts={
         "prefecture_directory":conn.execute("SELECT COUNT(*) FROM prefectures").fetchone()[0],
         "nationwide_official_river_code_names":conn.execute("SELECT COUNT(*) FROM national_named_river_codes").fetchone()[0],
         "nationwide_census_watershed_year_fish_name_records":conn.execute("SELECT COUNT(*) FROM national_census_watershed_fish").fetchone()[0],
         "hiroshima_local_river_register":conn.execute("SELECT COUNT(*) FROM rivers").fetchone()[0],
         "hiroshima_unreviewed_river_mentions":conn.execute("SELECT COUNT(*) FROM river_name_mentions").fetchone()[0],
         "yamaguchi_river_municipality_mentions":conn.execute("SELECT COUNT(*) FROM municipality_river_source_mentions").fetchone()[0],
         "tottori_pdf_river_mentions":conn.execute("SELECT COUNT(*) FROM tottori_pdf_river_mentions").fetchone()[0],
         "chugoku_5pref_watershed_mentions":conn.execute("SELECT COUNT(*) FROM prefecture_watershed_source_mentions").fetchone()[0],
         "source_verified_station_prefecture_links":0,
         "river_code_prefecture_links_approved":0,
         "direct_river_fish_observations":0,
         "publication_status":"research_only_no_WordPress_changes"
        }
        if (counts["prefecture_directory"]!=47 or
            counts["nationwide_official_river_code_names"]!=35449 or
            counts["nationwide_census_watershed_year_fish_name_records"]!=18814 or
            counts["hiroshima_local_river_register"]!=66 or
            counts["hiroshima_unreviewed_river_mentions"]!=98 or
            counts["yamaguchi_river_municipality_mentions"]!=81 or
            counts["tottori_pdf_river_mentions"]!=377 or
            counts["chugoku_5pref_watershed_mentions"]!=87 or
            count_fish!=18814 or
            conn.execute("PRAGMA integrity_check").fetchone()[0]!="ok" or
            conn.execute("PRAGMA foreign_key_check").fetchall()):
            raise ValueError("National integrated registry QA failed")
        return counts
    finally:conn.close()

def local_source_query(conn,name="",prefecture="",limit=30,offset=0):
    """Search all source-scoped local river data; do not collapse same names."""
    candidates=[]
    def accept(p,r):
        return ((not name or norm(name) in norm(r)) and (not prefecture or p==prefecture))
    for r in conn.execute("""
       SELECT river_id,prefecture,river_name,watershed,municipality_example,
              source_url FROM rivers ORDER BY river_id"""):
        if accept(r[1],r[2]):
            candidates.append(dict(source_id=r[0],prefecture=r[1],name=r[2],
                 watershed_in_source=r[3],municipality_in_source=r[4],
                 source_url=r[5],evidence_scope="hiroshima_2021_listing",
                 national_river_code=None,fish_direct_observation=None))
    for r in conn.execute("""
       SELECT mention_id,prefecture,river_name,watershed_name,municipality_listing,
              source_url FROM river_name_mentions ORDER BY mention_id"""):
        if accept(r[1],r[2]):
            candidates.append(dict(source_id=r[0],prefecture=r[1],name=r[2],
                 watershed_in_source=r[3] or None,municipality_in_source=r[4],
                 source_url=r[5],evidence_scope="hiroshima_unresolved_mention",
                 national_river_code=None,fish_direct_observation=None))
    for r in conn.execute("""
       SELECT mention_id,prefecture,river_name,watershed_label,municipality_in_source,
              source_url FROM municipality_river_source_mentions ORDER BY mention_id"""):
        if accept(r[1],r[2]):
            candidates.append(dict(source_id=r[0],prefecture=r[1],name=r[2],
                 watershed_in_source=r[3],municipality_in_source=r[4],
                 source_url=r[5],evidence_scope="yamaguchi_2026_floodmap_listing",
                 national_river_code=None,fish_direct_observation=None))
    for r in conn.execute("""
       SELECT document_mention_id,prefecture,river_name,watershed_printed_same_line,
              district,source_pdf_url,review_status FROM tottori_pdf_river_mentions
              ORDER BY document_mention_id"""):
        if accept(r[1],r[2]):
            candidates.append(dict(source_id=r[0],prefecture=r[1],name=r[2],
                 watershed_in_source=r[3],municipality_in_source=None,
                 district_in_document=r[4],source_url=r[5],
                 evidence_scope="tottori_2023_pdf_machine_extracted_review_pending",
                 review_status=r[6],
                 national_river_code=None,fish_direct_observation=None))
    return {"total_source_mentions":len(candidates),
            "source_mentions":candidates[offset:offset+limit]}

def search(path,name="",prefecture="",limit=30,offset=0,include_unassigned_codes=True):
    if not (1<=limit<=100 and offset>=0):raise ValueError("Invalid pagination")
    path=Path(path)
    if not path.is_file():raise FileNotFoundError("Build the national research catalog first")
    conn=sqlite3.connect(path);conn.row_factory=sqlite3.Row
    try:
        prefs=[dict(x) for x in conn.execute("SELECT code,prefecture_name FROM prefectures ORDER BY code")]
        valid={x["prefecture_name"] for x in prefs}
        if prefecture and prefecture not in valid:
            raise ValueError("Not a recognized Japanese prefecture")
        local=local_source_query(conn,name,prefecture,limit,offset)
        if not name and not prefecture:
            # A generic 35k return is unhelpful: return nationwide source summary.
            include_unassigned_codes=False
        codes=[]
        if include_unassigned_codes:
            for r in conn.execute("""
              SELECT river_code,river_name,watershed_code,watershed_name,source_url
              FROM national_named_river_codes ORDER BY river_code
            """):
                if name and norm(name) not in norm(r["river_name"]):continue
                codes.append(dict(code=r["river_code"],name=r["river_name"],
                   watershed_code=r["watershed_code"],watershed_name=r["watershed_name"],
                   prefecture=None,source_url=r["source_url"],
                   mapping_status="prefecture_not_verifiably_assigned",
                   fish_occurrences_at_this_river=None))
        if prefecture:
            selected=[x for x in prefs if x["prefecture_name"]==prefecture]
        else:selected=prefs
        if not prefecture:has_local=None
        else:has_local=prefecture in {"広島県","鳥取県","山口県"}
        status=("local_river_source_mentions_partial" if has_local else
                "only_watershed_source_mentions" if prefecture in ("島根県","岡山県") else
                "no_local_river_source_loaded" if prefecture else
                "prefecture_specific_river_data_incomplete")
        return {
          "prefectures_in_directory":len(prefs),
          "prefecture_selected":prefecture or None,
          "prefecture_local_river_source_status":status,
          "prefecture_selection":selected,
          **local,
          "national_name_code_candidates_total":len(codes) if include_unassigned_codes else None,
          "national_code_candidates":codes[offset:offset+limit] if include_unassigned_codes else [],
          "countrywide_code_name_inventory_total":35449,
          "countrywide_fish_census_watershed_year_name_inventory_total":18814,
          "national_river_codes_assigned_to_selected_prefecture":None,
          "river_species_confirmed_in_selected_prefecture":None,
          "notice":NOTICE
        }
    finally:conn.close()

def fish_context(path,name="",watershed="",region="",year="",limit=30,offset=0):
    """Explicit source-region/watershed search; can never accept prefecture."""
    if not (1<=limit<=100 and offset>=0):raise ValueError("Invalid pagination")
    if region and region not in FISH_REGIONS:raise ValueError("Unknown fish survey region")
    if year and (len(year)!=4 or not year.isdigit()):raise ValueError("Year must be YYYY")
    conn=sqlite3.connect(str(path));conn.row_factory=sqlite3.Row
    try:
        allrows=conn.execute("""
          SELECT region,watershed_name,survey_year,recorded_name,source_url
          FROM national_census_watershed_fish
          ORDER BY region,watershed_name,survey_year,recorded_name
        """)
        matches=[]
        for raw in allrows:
            r=dict(raw)
            if name and norm(name) not in norm(r["recorded_name"]):continue
            if watershed and norm(watershed) not in norm(r["watershed_name"]):continue
            if region and region!=r["region"]:continue
            if year and year!=r["survey_year"]:continue
            r["prefecture_of_observation"]=None
            r["specific_river_of_observation"]=None
            r["evidence_scope"]="watershed_year_name_only"
            matches.append(r)
        return {"total":len(matches),"records":matches[offset:offset+limit],
                "notice":"この公式記録は地域／水系／調査年の一覧。どの県・支流に生息するかの根拠ではありません。"}
    finally:conn.close()

def main():
    p=argparse.ArgumentParser(description="全国河川DB研究版：47都道府県の資料掲載状況・全国河川名・水系魚類記録を分離検索")
    p.add_argument("--db",default="river-fish/japan_unified_v12.sqlite")
    p.add_argument("--build",action="store_true")
    p.add_argument("--fish-context",action="store_true",help="Query only watershed-level fish data")
    p.add_argument("--name",default="")
    p.add_argument("--prefecture",default="")
    p.add_argument("--watershed",default="")
    p.add_argument("--region",default="")
    p.add_argument("--year",default="")
    p.add_argument("--limit",type=int,default=20)
    p.add_argument("--offset",type=int,default=0)
    a=p.parse_args()
    if a.build:result=build(a.db)
    elif a.fish_context:
        if a.prefecture:raise ValueError("Fish census cannot be filtered by prefecture")
        result=fish_context(a.db,a.name,a.watershed,a.region,a.year,a.limit,a.offset)
    else:result=search(a.db,a.name,a.prefecture,a.limit,a.offset)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
