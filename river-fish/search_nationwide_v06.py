#!/usr/bin/env python3
"""Search safely aggregated nine-region fish census records, never exact rivers.

Search by region, watershed, fiscal year or fish name / vetted local name.
Results represent WATER-SYSTEM observations; a tributary may be unobserved.
No assumption that a record belongs to any individual prefecture.
"""
import argparse
import csv
import json
from pathlib import Path
import unicodedata

HERE=Path(__file__).resolve().parent
HEADERS=["region","watershed","survey_year","recorded_name","source_url","source_sha256"]

def normalize(s):
    return unicodedata.normalize("NFKC",str(s or "")).casefold().strip()

def local_aliases(root):
    result={}
    with (Path(root)/"akaza_local_names_v03.csv").open(encoding="utf-8-sig",newline="") as f:
        for r in csv.DictReader(f):
            result.setdefault(r["standard_name"],set()).add(r["alias"])
    return result

def search(root=HERE,region="",watershed="",year="",name="",offset=0,limit=30):
    if not (1<=limit<=200 and offset>=0):raise ValueError("Invalid pagination")
    if year and (not year.isdigit() or len(year)!=4):raise ValueError("Invalid year")
    root=Path(root)
    index=json.loads((root/"nationwide_sources_v06.json").read_text(encoding="utf-8"))
    known={s["region_id"] for s in index["region_sources"]}
    if region and region not in known:raise ValueError("Region not present in official river-fish index")
    required=[region] if region else sorted(known)
    alias=local_aliases(root)
    law={}
    with (root/"legal_designations_v04.csv").open(encoding="utf-8-sig",newline="") as f:
        law={x["recorded_name"]:x["legal_status"] for x in csv.DictReader(f)}
    rows=[]
    for rid in required:
        p=root/"nationwide-staged"/rid
        if not (p/"watershed_year_fish.csv").is_file() or not (p/"manifest.json").is_file():
            raise FileNotFoundError("Regional data is not loaded or verified: "+rid)
        m=json.loads((p/"manifest.json").read_text(encoding="utf-8"))
        if (m["status"]!="staged_not_published" or m["region"]!=rid
            or m["prefecture_mapping"]!="not_inferred"):
            raise RuntimeError("Region survey manifest is not safe")
        with (p/"watershed_year_fish.csv").open(encoding="utf-8-sig",newline="") as f:
            reader=csv.DictReader(f)
            if reader.fieldnames != HEADERS:raise ValueError("Unexpected regional CSV")
            for record in reader:
                if record["region"]!=rid or record["source_sha256"]!=m["source_sha256"]:
                    raise ValueError("Region provenance mismatch")
                fish=record["recorded_name"]
                if name and not any(normalize(name) in normalize(t) for t in [fish]+sorted(alias.get(fish,[]))):
                    continue
                if watershed and normalize(watershed) not in normalize(record["watershed"]):continue
                if year and year != record["survey_year"]:continue
                rows.append({
                    "source_region":rid,"watershed":record["watershed"],
                    "survey_year":record["survey_year"],"fish_name_as_recorded":fish,
                    "prefecture":None,"river_name":None,
                    "direct_tributary_evidence":False,
                    "local_name_match":name if name and normalize(name) not in normalize(fish) else None,
                    "legal_status":law.get(fish,"unreviewed"),
                    "origin_status":"unreviewed",
                    "source_url":record["source_url"],
                    "source_sha256":record["source_sha256"]
                })
    rows.sort(key=lambda x:(x["source_region"],x["watershed"],x["survey_year"],x["fish_name_as_recorded"]))
    return {"total":len(rows),"records":rows[offset:offset+limit],
            "loaded_regions":required,"offset":offset,"limit":limit,
            "evidence_scope":"watershed_year_fish_name",
            "notice":"水系の記録を個別の支流・都道府県の生息魚とみなしません。未掲載は不在の証拠ではありません。旧『魚介類』区分の候補は審査待ちで含めません。"}

if __name__=="__main__":
    p=argparse.ArgumentParser(description="全国の国交省魚類記録：水系×調査年度の検索")
    p.add_argument("--region",default="")
    p.add_argument("--watershed",default="")
    p.add_argument("--year",default="")
    p.add_argument("--name",default="")
    p.add_argument("--limit",type=int,default=30)
    p.add_argument("--offset",type=int,default=0)
    a=p.parse_args()
    print(json.dumps(search(region=a.region,watershed=a.watershed,year=a.year,
                            name=a.name,limit=a.limit,offset=a.offset),ensure_ascii=False,indent=2))
