#!/usr/bin/env python3
"""Generic search *engine* v2.3 for a signed, versioned biodiversity snapshot.

All available groups come from verified dataset metadata, not hardcoded UI/API
source adapters. Read-only local preview; never equate grouped labels with
independent species, individual rivers, current habitats or locations.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import parse_qs, quote
from wsgiref.simple_server import make_server

from build_dataset_v23 import sha256_file, VERSION, REGIONS
from three_axis_search_v20 import NOTICE, DIRECTIONS, like

FRONTEND="engine_frontend_v23.html"
MAX_PAGE=20000
MAX_PAGE_SIZE=25

class VerifiedSnapshot:
    def __init__(self, db, manifest):
        self.db=Path(db).resolve()
        self.manifest_file=Path(manifest).resolve()
        if not self.db.is_file() or not self.manifest_file.is_file():
            raise FileNotFoundError("検証済みの研究用データセットとマニフェストが必要です")
        data=json.loads(self.manifest_file.read_text(encoding="utf-8"))
        required={"contract_version","publication_status","database_filename",
                  "database_sha256","registry_sha256","group_counts","total_survey_rows",
                  "groups","unavailable_separate_groups","geographic_scope",
                  "taxonomy_identity_verified","individual_river_verified",
                  "prefecture_presence_verified","wordpress_modified"}
        if (set(data)!=required or data["contract_version"]!=VERSION or
            data["publication_status"]!="research_only_not_wordpress" or
            data["database_filename"]!=self.db.name or
            data["geographic_scope"]!="regional_watershed_year_only" or
            any(data[key] is not False for key in ("taxonomy_identity_verified",
                "individual_river_verified","prefecture_presence_verified","wordpress_modified")) or
            sha256_file(self.db)!=data["database_sha256"]):
            raise ValueError("データの版・内容・安全範囲が検証できません")
        self.metadata=data
        groups=data["groups"]
        self.groups={x["id"]:x for x in groups}
        if not groups or len(groups)>12 or len(self.groups)!=len(groups):
            raise ValueError("生物分類の構成に問題があります")
        if (data["group_counts"]!={x["id"]:x["source_rows"] for x in groups} or
            sum(data["group_counts"].values())!=data["total_survey_rows"] or
            any(not re.fullmatch(r"[a-z][a-z0-9_]{1,39}",x["id"]) for x in groups)):
            raise ValueError("データ分類の件数に不整合があります")
        with self.connect() as c:
            tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {"dataset_contract","available_groups","survey_evidence"}.issubset(tables):
                raise ValueError("非対応のデータ形式です")
            cv=c.execute("SELECT schema_version,geographic_scope,taxonomy_identity_verified FROM dataset_contract WHERE id=1").fetchone()
            if cv!=(VERSION,"regional_watershed_year_only",0):
                raise ValueError("データ構造の版が一致しません")
            actual=dict(c.execute("SELECT group_id,COUNT(*) FROM survey_evidence GROUP BY group_id").fetchall())
            if actual!=data["group_counts"]:
                raise ValueError("マニフェストと生物データの件数が異なります")
            if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
                raise ValueError("データファイルが破損しています")
            if c.execute("PRAGMA foreign_key_check").fetchall():
                raise ValueError("生物分類との参照整合性に問題があります")
            any_location=c.execute("""SELECT COUNT(*) FROM survey_evidence
                WHERE verified_prefecture IS NOT NULL OR verified_individual_river IS NOT NULL
                OR approved_taxon_code IS NOT NULL OR geographic_scope!='regional_watershed_year_only'""").fetchone()[0]
            if any_location:raise ValueError("未承認の生息場所・分類照合が含まれています")

    def connect(self):
        uri="file:"+quote(str(self.db),safe="/")+"?mode=ro"
        c=sqlite3.connect(uri,uri=True)
        c.execute("PRAGMA query_only=ON")
        c.execute("PRAGMA trusted_schema=OFF")
        return c

    def catalog(self):
        return {
            "contract_version":VERSION,
            "groups":self.metadata["groups"],
            "unavailable_groups":self.metadata["unavailable_separate_groups"],
            "geographic_scope":"regional_watershed_year_only",
            "dataset_sha256":self.metadata["database_sha256"],
            "data_rows":self.metadata["total_survey_rows"],
            "wordpress_modified":False,
            "notice":NOTICE
        }

    def search(self,direction,groups,region="",watershed="",organism="",year="",
               page=1,per_page=20,watershed_match="contains"):
        if direction not in DIRECTIONS:
            raise ValueError("検索方向が不正です")
        if watershed_match not in ("contains","exact"):
            raise ValueError("水系名の検索方式が不正です")
        if not isinstance(groups,(list,tuple)) or not groups or len(groups)>len(self.groups):
            raise ValueError("利用可能な生物区分を選んでください")
        if len(set(groups))!=len(groups) or any(x not in self.groups for x in groups):
            raise ValueError("データセットにない生物区分です")
        if region and region not in REGIONS:
            raise ValueError("調査地方が不正です")
        for label,val in (("水系名",watershed),("生物名",organism)):
            if not isinstance(val,str) or len(val)>100 or any(ord(ch)<32 for ch in val):
                raise ValueError(label+"に不正な文字があります")
        if year and (not isinstance(year,str) or not re.fullmatch(r"(?:19|20)\d{2}",year)):
            raise ValueError("調査年度は西暦4桁で指定してください")
        if type(page) is not int or not 1<=page<=MAX_PAGE or type(per_page) is not int or not 1<=per_page<=MAX_PAGE_SIZE:
            raise ValueError("ページ番号が不正です")
        if direction=="region_explore" and not region:
            raise ValueError("地方を選んでください")
        if direction=="watershed_to_organism" and not watershed.strip():
            raise ValueError("水系名を入力してください")
        if direction=="organism_to_watershed" and not organism.strip():
            raise ValueError("生物名を入力してください")
        placeholders=",".join("?" for _ in groups)
        where=["group_id IN ("+placeholders+")"]
        params=list(groups)
        if region:
            where.append("region=?");params.append(region)
        if watershed.strip():
            where.append("watershed_name=? " if watershed_match=="exact" else "watershed_name LIKE ? ESCAPE '\\'")
            params.append(watershed.strip() if watershed_match=="exact" else like(watershed.strip()))
        if organism.strip():
            where.append("recorded_name LIKE ? ESCAPE '\\'")
            params.append(like(organism.strip()))
        if year:
            where.append("survey_year=?");params.append(year)
        filtered="SELECT group_id,region,watershed_name,survey_year,recorded_name,source_url FROM survey_evidence WHERE "+" AND ".join(where)
        with self.connect() as c:
            c.row_factory=sqlite3.Row
            if direction=="region_explore":
                aggregated=("SELECT region,watershed_name,COUNT(*) AS historical_records,"
                    "MIN(survey_year) AS first_year,MAX(survey_year) AS last_year"
                    " FROM ("+filtered+") GROUP BY region,watershed_name")
                result_type="watershed_summary"
                order=" ORDER BY region,watershed_name"
            else:
                aggregated=("SELECT group_id AS survey_group,region,watershed_name,recorded_name,"
                    " COUNT(*) AS historical_records,"
                    " GROUP_CONCAT(DISTINCT survey_year) AS survey_years,"
                    " MIN(source_url) AS source_url, COUNT(DISTINCT source_url) AS source_count"
                    " FROM ("+filtered+") GROUP BY group_id,region,watershed_name,recorded_name")
                result_type="distinct_source_labels_by_watershed"
                order=" ORDER BY region,watershed_name,survey_group,recorded_name"
            total=c.execute("SELECT COUNT(*) FROM ("+aggregated+")",params).fetchone()[0]
            rows=[dict(r) for r in c.execute("SELECT * FROM ("+aggregated+")"+order+" LIMIT ? OFFSET ?",
                                             (*params,per_page,(page-1)*per_page))]
            if direction=="region_explore" and rows:
                pairs=[(r["region"],r["watershed_name"]) for r in rows]
                pairs_cond=" OR ".join("(region=? AND watershed_name=?)" for _ in pairs)
                count_query=(
                    "SELECT region,watershed_name,group_id,COUNT(DISTINCT recorded_name) AS count"
                    " FROM ("+filtered+") WHERE "+pairs_cond+
                    " GROUP BY region,watershed_name,group_id")
                pair_params=[z for pair in pairs for z in pair]
                raw=c.execute(count_query,(*params,*pair_params)).fetchall()
                mapping={(r["region"],r["watershed_name"]):{} for r in rows}
                for item in raw:
                    mapping[item["region"],item["watershed_name"]][item["group_id"]]=item["count"]
                for r in rows:
                    r["group_label_counts"]=mapping[r["region"],r["watershed_name"]]
                    # Kept for migration from v2.2; generic UI uses group_label_counts.
                    r["fish_labels"]=r["group_label_counts"].get("fish",0)
                    r["benthic_labels"]=r["group_label_counts"].get("benthic_animals",0)
            for r in rows:
                if direction!="region_explore":
                    r["survey_years"]=sorted(set((r["survey_years"] or "").split(",")))
                    r["survey_year_count"]=len(r["survey_years"])
                r["geographic_scope"]="regional_watershed_year_only"
                r["verified_individual_river"]=None
                r["verified_prefecture"]=None
                r["approved_2025_taxon_code"]=None
            return {
                "direction":direction,"watershed_match":watershed_match,
                "selected_groups":list(groups),"result_type":result_type,
                "total":total,"page":page,"per_page":per_page,"results":rows,
                "count_unit":"watersheds" if direction=="region_explore" else "literal_survey_names_per_watershed",
                "historical_observations_are_not_distinct_species":True,
                "individual_river_verified":False,"prefecture_presence_verified":False,
                "current_distribution_verified":False,"taxonomy_identity_verified":False,
                "wordpress_modified":False,"notice":NOTICE
            }

def create_app(dataset):
    frontend=Path(__file__).with_name(FRONTEND).read_bytes()
    def app(env,start_response):
        path=env.get("PATH_INFO","")
        if env.get("REQUEST_METHOD")!="GET":
            start_response("405 Method Not Allowed",[("Allow","GET")])
            return [b""]
        if path=="/":
            start_response("200 OK",[("Content-Type","text/html; charset=utf-8"),
                ("Cache-Control","no-store"),("X-Content-Type-Options","nosniff")])
            return [frontend]
        if path not in ("/api/catalog","/api/compact"):
            start_response("404 Not Found",[])
            return [b""]
        try:
            if path=="/api/catalog":
                if env.get("QUERY_STRING",""):
                    raise ValueError("カタログ検索は無効です")
                result=dataset.catalog()
            else:
                args=parse_qs(env.get("QUERY_STRING",""),keep_blank_values=True,max_num_fields=30)
                allowed={"direction","group","region","watershed","organism","year","page","per_page","watershed_match"}
                if set(args)-allowed or any(len(v)!=1 for k,v in args.items() if k!="group"):
                    raise ValueError("検索項目が不正か重複しています")
                val=lambda k,default="":args.get(k,[default])[0]
                result=dataset.search(
                    direction=val("direction"),groups=tuple(args.get("group",[])),
                    region=val("region"),watershed=val("watershed"),organism=val("organism"),
                    year=val("year"),page=int(val("page","1")),per_page=int(val("per_page","20")),
                    watershed_match=val("watershed_match","contains"))
            status="200 OK"
        except (ValueError,sqlite3.DatabaseError) as e:
            result={"error":str(e),"results":[],"total":0}
            status="400 Bad Request"
        body=json.dumps(result,ensure_ascii=False).encode("utf-8")
        start_response(status,[("Content-Type","application/json; charset=utf-8"),
             ("Cache-Control","no-store"),("X-Content-Type-Options","nosniff")])
        return [body]
    return app

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--db",required=True)
    p.add_argument("--manifest",required=True)
    p.add_argument("--serve",action="store_true")
    p.add_argument("--direction",choices=DIRECTIONS,default="region_explore")
    p.add_argument("--group",action="append")
    p.add_argument("--region",default="")
    p.add_argument("--watershed",default="")
    p.add_argument("--organism",default="")
    p.add_argument("--year",default="")
    p.add_argument("--watershed-match",choices=("contains","exact"),default="contains")
    p.add_argument("--page",type=int,default=1)
    a=p.parse_args()
    snapshot=VerifiedSnapshot(a.db,a.manifest)
    if a.serve:
        with make_server("127.0.0.1",8765,create_app(snapshot)) as server:
            print("Read-only research preview: http://127.0.0.1:8765/")
            server.serve_forever()
    else:
        print(json.dumps(snapshot.search(a.direction,tuple(a.group or snapshot.groups),
            a.region,a.watershed,a.organism,a.year,a.page,
            watershed_match=a.watershed_match),ensure_ascii=False,indent=2))
if __name__=="__main__":
    main()
