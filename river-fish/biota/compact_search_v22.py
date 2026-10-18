#!/usr/bin/env python3
"""v2.2: Compact historical watershed survey results without asserting species.

Research-only localhost service on the official v1.9 fish + benthic SQLite.
For directions "organism_to_watershed" / "watershed_to_organism", repeated
survey years are collapsed by (region, watershed, source group, literal name).
For "region_explore", return one card per (region, watershed), with separate
counts of distinct *literal labels* in fish and benthic records.

This is NOT taxonomic synonym resolution, individual-river presence, or
historical records converted into current distribution. No WordPress writes.
"""
import argparse
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import parse_qs, quote
from wsgiref.simple_server import make_server

from three_axis_search_v20 import REGIONS, DIRECTIONS, FISH_SQL, BENTHIC_SQL, NOTICE, like

GROUPS = ("fish", "benthic_animals")
FRONTEND = "compact_frontend_v22.html"
SOURCE_SELECT = {"fish": FISH_SQL, "benthic_animals": BENTHIC_SQL}
MAX_PAGE = 20000
MAX_PAGE_SIZE = 25

def validate(direction, groups, region, watershed, organism, year, page, per_page, watershed_match):
    if watershed_match not in ('contains','exact'):
        raise ValueError('水系名の一致条件が不正です')
    if direction not in DIRECTIONS:
        raise ValueError("検索方向が不正です")
    if not isinstance(groups, (tuple, list)) or not groups or len(groups) > 2:
        raise ValueError("利用可能な調査区分を1つ以上選択してください")
    if len(set(groups)) != len(groups) or any(g not in GROUPS for g in groups):
        raise ValueError("未検証または重複した調査区分です")
    if region and region not in REGIONS:
        raise ValueError("地域は公式9地方から選んでください")
    for label, val in (("水系", watershed), ("生物", organism)):
        if not isinstance(val, str) or len(val) > 100 or any(ord(ch) < 32 for ch in val):
            raise ValueError(label+"名が不正です")
    if year and (not isinstance(year, str) or not re.fullmatch(r"(?:19|20)\d{2}",year)):
        raise ValueError("調査年度は西暦4桁で指定してください")
    if isinstance(page,bool) or not isinstance(page,int) or not 1<=page<=MAX_PAGE:
        raise ValueError("ページ番号が不正です")
    if isinstance(per_page,bool) or not isinstance(per_page,int) or not 1<=per_page<=MAX_PAGE_SIZE:
        raise ValueError("ページ件数が不正です")
    if direction=="organism_to_watershed" and not organism.strip():
        raise ValueError("生物名を入力してください")
    if direction=="watershed_to_organism" and not watershed.strip():
        raise ValueError("水系名を入力してください")
    if direction=="region_explore" and not region:
        raise ValueError("地域を選択してください")

def search(db, direction, groups=("fish","benthic_animals"), region="",
           watershed="", organism="", year="", page=1, per_page=20, watershed_match="contains"):
    validate(direction,groups,region,watershed,organism,year,page,per_page,watershed_match)
    path=Path(db).resolve()
    if not path.is_file():
        raise FileNotFoundError("研究用データベースが見つかりません")
    # All source selection and SQL expressions are fixed constants.
    source=" UNION ALL ".join(SOURCE_SELECT[g] for g in GROUPS if g in groups)
    sql_from="("+source+")"
    conditions=[]
    params=[]
    if region:
        conditions.append("region=?");params.append(region)
    if watershed.strip():
        if watershed_match=="exact":
            conditions.append("watershed_name=?")
            params.append(watershed.strip())
        else:
            conditions.append("watershed_name LIKE ? ESCAPE '\\'")
            params.append(like(watershed.strip()))
    if organism.strip():
        conditions.append("recorded_name LIKE ? ESCAPE '\\'")
        params.append(like(organism.strip()))
    if year:
        conditions.append("survey_year=?");params.append(year)
    where=" WHERE "+" AND ".join(conditions) if conditions else ""
    filtered="SELECT * FROM "+sql_from+where
    uri="file:"+quote(str(path),safe="/")+"?mode=ro"
    c=sqlite3.connect(uri,uri=True)
    c.row_factory=sqlite3.Row
    try:
        c.execute("PRAGMA query_only=ON")
        required=({"watershed_year_fish_evidence"} if "fish" in groups else set()) | (
            {"watershed_year_benthic_evidence"} if "benthic_animals" in groups else set())
        existing={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not required.issubset(existing):
            raise ValueError("選択した調査区分の検証済みテーブルがありません")
        if direction=="region_explore":
            groupcols="region, watershed_name"
            aggregate=(
                "SELECT region,watershed_name,"
                " COUNT(DISTINCT CASE WHEN survey_group='fish' THEN recorded_name END) AS fish_labels,"
                " COUNT(DISTINCT CASE WHEN survey_group='benthic_animals' THEN recorded_name END) AS benthic_labels,"
                " COUNT(*) AS historical_records,"
                " MIN(survey_year) AS first_year, MAX(survey_year) AS last_year"
                " FROM ("+filtered+") GROUP BY "+groupcols
            )
            order=" ORDER BY region,watershed_name"
            result_type="watershed_summary"
        else:
            groupcols="survey_group, region, watershed_name, recorded_name"
            aggregate=(
                "SELECT survey_group,region,watershed_name,recorded_name,"
                " COUNT(*) AS historical_records,"
                " GROUP_CONCAT(DISTINCT survey_year) AS survey_years,"
                " MIN(source_url) AS source_url"
                " FROM ("+filtered+") GROUP BY "+groupcols
            )
            order=" ORDER BY region,watershed_name,survey_group,recorded_name"
            result_type="distinct_source_labels_by_watershed"
        # Paginate *after* aggregating; LIMIT on raw rows would split
        # the same organism's survey years across multiple pages.
        total=c.execute("SELECT COUNT(*) FROM ("+aggregate+")",params).fetchone()[0]
        rows=[dict(r) for r in c.execute(
            "SELECT * FROM ("+aggregate+")"+order+" LIMIT ? OFFSET ?",
            (*params,per_page,(page-1)*per_page))]
        for r in rows:
            if direction!="region_explore":
                r["survey_years"]=sorted(set((r["survey_years"] or "").split(",")))
                r["survey_year_count"]=len(r["survey_years"])
            r["geographic_scope"]="region_watershed_year_only"
            r["verified_individual_river"]=None
            r["verified_prefecture"]=None
            r["approved_2025_taxon_code"]=None
        return {
            "direction":direction,
            "watershed_match":watershed_match,
            "selected_groups":[g for g in GROUPS if g in groups],
            "result_type":result_type,
            "total":total,
            "page":page,"per_page":per_page,"results":rows,
            "count_unit":"watersheds" if direction=="region_explore" else "literal_survey_names_per_watershed",
            "historical_observations_are_not_distinct_species":True,
            "aquatic_insect_subgroup_available":False,
            "birds_survey_records_available":False,
            "individual_river_verified":False,
            "prefecture_presence_verified":False,
            "current_distribution_verified":False,
            "taxonomy_identity_verified":False,
            "wordpress_modified":False,
            "notice":NOTICE
        }
    finally:
        c.close()

def create_app(db):
    html=Path(__file__).with_name(FRONTEND).read_bytes()
    def app(environ,start_response):
        path=environ.get("PATH_INFO","")
        if environ.get("REQUEST_METHOD")!="GET":
            start_response("405 Method Not Allowed",[("Allow","GET")])
            return [b""]
        if path=="/":
            start_response("200 OK",[
                ("Content-Type","text/html; charset=utf-8"),
                ("Cache-Control","no-store"),("X-Content-Type-Options","nosniff")])
            return [html]
        if path!="/api/compact":
            start_response("404 Not Found",[])
            return [b""]
        try:
            items=parse_qs(environ.get("QUERY_STRING",""),keep_blank_values=True,max_num_fields=12)
            allowed={"direction","group","region","watershed","organism","year","page","per_page","watershed_match"}
            if set(items)-allowed:
                raise ValueError("未対応の検索項目です")
            if any(len(v)!=1 for k,v in items.items() if k!="group"):
                raise ValueError("検索条件が重複しています")
            if len(items.get("group",[]))>2:
                raise ValueError("調査区分の数が不正です")
            single=lambda name,default="":items.get(name,[default])[0]
            groups=tuple(items.get("group",[]))
            result=search(db,direction=single("direction"),groups=groups,
                          region=single("region"),watershed=single("watershed"),
                          organism=single("organism"),year=single("year"),
                          page=int(single("page","1")),per_page=int(single("per_page","20")),
                          watershed_match=single("watershed_match","contains"))
            status="200 OK"
        except (ValueError,FileNotFoundError,sqlite3.DatabaseError) as err:
            result={"error":str(err),"results":[],"total":0}
            status="400 Bad Request"
        body=json.dumps(result,ensure_ascii=False).encode("utf-8")
        start_response(status,[
            ("Content-Type","application/json; charset=utf-8"),
            ("Cache-Control","no-store"),("X-Content-Type-Options","nosniff")])
        return [body]
    return app

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--db",required=True)
    p.add_argument("--serve",action="store_true")
    p.add_argument("--direction",choices=DIRECTIONS,default="region_explore")
    p.add_argument("--group",choices=GROUPS,action="append")
    p.add_argument("--region",default="")
    p.add_argument("--watershed",default="")
    p.add_argument("--organism",default="")
    p.add_argument("--year",default="")
    p.add_argument("--watershed-match",choices=("contains","exact"),default="contains")
    p.add_argument("--page",type=int,default=1)
    args=p.parse_args()
    if args.serve:
        with make_server("127.0.0.1",8765,create_app(args.db)) as server:
            print("Research-only preview: http://127.0.0.1:8765/")
            server.serve_forever()
    else:
        print(json.dumps(search(args.db,args.direction,tuple(args.group or GROUPS),
                                args.region,args.watershed,args.organism,args.year,
                                args.page,watershed_match=args.watershed_match),ensure_ascii=False,indent=2))
if __name__=="__main__":
    main()
