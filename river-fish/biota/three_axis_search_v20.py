#!/usr/bin/env python3
"""Research-only three-axis watershed / organism search over v1.9 SQLite.

Uses only independently validated fish and benthic *watershed/year* sources.
Never joins a literal observation label to a 2025 taxon code, a prefecture,
an individual river, or a current presence claim. Read-only and localhost only.
"""
import argparse
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import quote, parse_qs
from wsgiref.simple_server import make_server

REGIONS = ("hokkaido", "tohoku", "kanto", "hokuriku", "chubu",
           "kinki", "chugoku", "shikoku", "kyushu")
DIRECTIONS = ("organism_to_watershed", "watershed_to_organism", "region_explore")
GROUPS = ("fish", "benthic_animals", "both")
NOTICE = ("過去の国交省調査に掲載された「地方×水系×年度×当時の生物名」の記録です。"
          "特定の支流・都道府県での確認や現在の生息を示しません。"
          "2025年分類名簿との同定も未審査です。未掲載は不在の証明ではありません。")

FISH_SQL = """SELECT 'fish' AS survey_group, region, watershed_name,
    survey_year, literal_recorded_name AS recorded_name, source_url
    FROM watershed_year_fish_evidence"""
BENTHIC_SQL = """SELECT 'benthic_animals' AS survey_group, region,
    watershed_name, survey_year, literal_recorded_name AS recorded_name,
    official_source_url AS source_url FROM watershed_year_benthic_evidence"""

def like(value):
    return "%" + value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"

def validated(direction, group, region, watershed, organism, year, page, per_page):
    if direction not in DIRECTIONS:
        raise ValueError("検索方向が不正です")
    if group not in GROUPS:
        raise ValueError("生物調査区分が不正です")
    if region and region not in REGIONS:
        raise ValueError("地域は公式の9地方から選んでください")
    for label, val in (("水系名", watershed), ("生物名", organism)):
        if not isinstance(val, str) or len(val) > 100 or any(ord(c) < 32 for c in val):
            raise ValueError(label + "が長すぎるか不正です")
    if year and not re.fullmatch(r"(?:19|20)\d{2}", year):
        raise ValueError("調査年度は西暦4桁で指定してください")
    if not isinstance(page, int) or not 1 <= page <= 2000 or not isinstance(per_page, int) or not 1 <= per_page <= 25:
        raise ValueError("ページ指定が不正です")
    if direction == "organism_to_watershed" and not organism.strip():
        raise ValueError("生物名を入力してください")
    if direction == "watershed_to_organism" and not watershed.strip():
        raise ValueError("水系名を入力してください")
    if direction == "region_explore" and not region:
        raise ValueError("地域を選択してください")

def search(db, direction, group="both", region="", watershed="", organism="",
           year="", page=1, per_page=25):
    validated(direction, group, region, watershed, organism, year, page, per_page)
    db = Path(db).resolve()
    if not db.is_file():
        raise FileNotFoundError("研究用DBを先に生成してください")
    tables = [FISH_SQL] if group == "fish" else (
        [BENTHIC_SQL] if group == "benthic_animals" else [FISH_SQL, BENTHIC_SQL])
    union = " UNION ALL ".join(tables)
    where, args = [], []
    if region:
        where.append("region = ?")
        args.append(region)
    if watershed.strip():
        where.append("watershed_name LIKE ? ESCAPE '\\'")
        args.append(like(watershed.strip()))
    if organism.strip():
        where.append("recorded_name LIKE ? ESCAPE '\\'")
        args.append(like(organism.strip()))
    if year:
        where.append("survey_year = ?")
        args.append(year)
    predicate = " WHERE " + " AND ".join(where)
    # The only SQL fragments are fixed literals above; all user input is bound.
    src = "(" + union + ")"
    uri = "file:" + quote(str(db), safe="/") + "?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    con.row_factory = sqlite3.Row
    try:
        con.execute("PRAGMA query_only=ON")
        # If called with an earlier DB version, fail closed rather than hiding it.
        required = ["watershed_year_fish_evidence"] + (
            ["watershed_year_benthic_evidence"] if group != "fish" else [])
        found = {row[0] for row in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        if not set(required).issubset(found):
            raise ValueError("DBに必要な公式調査テーブルがありません")
        total = con.execute("SELECT COUNT(*) FROM " + src + predicate, args).fetchone()[0]
        records = [dict(r) for r in con.execute(
            "SELECT survey_group,region,watershed_name,survey_year,"
            "recorded_name,source_url FROM " + src + predicate +
            " ORDER BY region, watershed_name, survey_year, recorded_name,"
            "survey_group LIMIT ? OFFSET ?",
            (*args, per_page, (page-1)*per_page))]
        for r in records:
            r["verified_individual_river"] = None
            r["verified_prefecture"] = None
            r["approved_2025_taxon_code"] = None
            r["geographic_scope"] = "region_watershed_year_only"
        return {"direction": direction, "group": group, "total": total,
                "page": page, "per_page": per_page,
                "results": records, "evidence_type": "historical_survey_labels",
                "specific_river_presence_verified": False,
                "prefecture_presence_verified": False,
                "taxonomy_identity_verified": False,
                "wordpress_modified": False, "notice": NOTICE}
    finally:
        con.close()

def create_app(db):
    html = (Path(__file__).with_name("three_axis_frontend_v20.html")).read_bytes()
    def app(environ, start_response):
        path = environ.get("PATH_INFO", "")
        if environ.get("REQUEST_METHOD") != "GET":
            start_response("405 Method Not Allowed", [("Allow", "GET")])
            return [b""]
        if path == "/":
            start_response("200 OK", [("Content-Type", "text/html; charset=utf-8"),
                                      ("X-Content-Type-Options", "nosniff"),
                                      ("Cache-Control", "no-store")])
            return [html]
        if path != "/api/search":
            start_response("404 Not Found", [])
            return [b""]
        try:
            params = parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=True,
                              max_num_fields=10)
            if any(len(v) != 1 for v in params.values()):
                raise ValueError("同じパラメータが重複しています")
            if set(params) - {"direction", "group", "region", "watershed", "organism",
                              "year", "page", "per_page"}:
                raise ValueError("未知の検索項目")
            value = lambda k, default="": params.get(k, [default])[0]
            result = search(db, direction=value("direction"),
                            group=value("group", "both"), region=value("region"),
                            watershed=value("watershed"), organism=value("organism"),
                            year=value("year"), page=int(value("page", "1")),
                            per_page=int(value("per_page", "25")))
            status = "200 OK"
        except (ValueError, FileNotFoundError, sqlite3.DatabaseError) as e:
            result = {"error": str(e), "results": [], "total": 0}
            status = "400 Bad Request"
        body = json.dumps(result, ensure_ascii=False).encode("utf-8")
        start_response(status, [("Content-Type", "application/json; charset=utf-8"),
                                ("Cache-Control", "no-store"),
                                ("X-Content-Type-Options", "nosniff")])
        return [body]
    return app

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--direction", choices=DIRECTIONS, default="region_explore")
    parser.add_argument("--group", choices=GROUPS, default="both")
    parser.add_argument("--region", default="")
    parser.add_argument("--watershed", default="")
    parser.add_argument("--organism", default="")
    parser.add_argument("--year", default="")
    parser.add_argument("--page", type=int, default=1)
    args = parser.parse_args()
    if args.serve:
        with make_server("127.0.0.1", 8765, create_app(args.db)) as server:
            print("Research preview only: http://127.0.0.1:8765/")
            server.serve_forever()
    else:
        print(json.dumps(search(args.db,args.direction,args.group,args.region,
                                args.watershed,args.organism,args.year,args.page),
                         ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
