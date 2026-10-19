#!/usr/bin/env python3
"""Independently corroborate Kyushu ten-digit river codes via official JMA 2026 PDF.

A match requires:
 - JMA official '国' forecast item with a LITERAL river name (no 上流部/水系/etc),
 - JMA ten-digit code AND national MLIT ten-digit code/name/watershed agreement,
 - independent official MLIT watershed-river distribution-list pairing,
 - a unique national catalog code for this pair,
 - matching recovered Kyushu research B records.
No new species or survey observations are created.
"""
import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
V04=ROOT/"research-individual-v04"
SOURCES={
  "jma":"https://www.data.jma.go.jp/suishin/oshirase/pdf/20260422.pdf",
  "mlit":"https://www.mlit.go.jp/river/hourei_tsutatsu/riyou/kasen_riyou/oudan/kyuushuu.html"
}
SHA={"jma":"1fd72d7aaca4c42292249012de4dee03e0fa2e40554ac55b33ab12e306bb3275",
     "mlit":"36d0cfacef4c6fffbb0df7b2019aeadcdb0a5b3e554894a0c236263894077489"}
FIELDS=["region","source_authority","watershed_name","river_name","river_code",
        "watershed_code","jma_page","jma_source_url","jma_source_sha256",
        "mlit_independent_pair_url","mlit_pair_source_sha256","approval_basis"]

def read(path):
    with Path(path).open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))

def approve(jma_path,triage_path,pair_path,out_dir):
    jma=json.loads(Path(jma_path).read_text(encoding="utf-8"))
    if jma["source_url"]!=SOURCES["jma"] or jma["source_sha256"]!=SHA["jma"]:
        raise ValueError("JMA PDF proof not pinned or changed")
    if jma["kyushu_code_occurrences"]!=len(jma["samples"]):
        raise ValueError("Incomplete JMA extracted code samples: refuse automatic approval")
    pairs=read(pair_path);triage=read(triage_path)
    registry={r["river_code"]:r for r in read(ROOT/"national-codes-staged/river_codes_national_v07.csv")}
    official={(r["watershed_name"],r["river_name"]):r for r in pairs}
    B=defaultdict(list)
    for r in triage:
        if r["region"]!="kyushu" or r["match_class"]!="B" or r["is_approved_individual_river"]!="False":
            raise ValueError("Original B evidence changed")
        B[(r["watershed_name"],r["river_name"])].append(r)
    if len(B)!=92 or sum(int(r["recovered_records"]) for r in triage)!=115062:
        raise ValueError("Original Kyushu B totals changed")
    jurisdictions=("福岡管区気象台","佐賀地方気象台","長崎地方気象台","熊本地方気象台",
                   "大分地方気象台","宮崎地方気象台","鹿児島地方気象台")
    title_pattern=re.compile(r"^国\s+(.+?)\s+(?:"+"|".join(jurisdictions)+r")\s+(89\d{8})\s+\d{2}\s+")
    matches={}
    audit={"titles_reviewed":0,"not_literal_river_titles":[],"no_independent_pair":[],"missing_B":[],"catalog_disagreed":[]}
    for hit in jma["samples"]:
        match=title_pattern.match(hit["line"])
        if not match:continue
        name,code=match.groups();audit["titles_reviewed"]+=1
        national=registry.get(code)
        if not national or national["river_name"]!=name:
            audit["not_literal_river_titles"].append({"label":name,"code":code})
            continue
        key=national["watershed_name"],name
        row=official.get(key)
        if not row:
            audit["no_independent_pair"].append({"water":key[0],"name":name,"code":code})
            continue
        if (row["source_url"]!=SOURCES["mlit"] or row["catalog_matches"]!="1"
            or row["catalog_unique_code_candidate"]!=code):
            audit["catalog_disagreed"].append({"water":key[0],"name":name,"code":code})
            continue
        if key not in B:
            audit["missing_B"].append({"water":key[0],"name":name,"code":code})
            continue
        item={
            "region":"kyushu","source_authority":"九州地方整備局",
            "watershed_name":key[0],"river_name":name,"river_code":code,
            "watershed_code":national["watershed_code"],
            "jma_page":hit["page"],"jma_source_url":SOURCES["jma"],"jma_source_sha256":SHA["jma"],
            "mlit_independent_pair_url":SOURCES["mlit"],"mlit_pair_source_sha256":SHA["mlit"],
            "approval_basis":"JMA 2026 ten-digit river number directly pairs with literal river name; independent MLIT river-map distribution table confirms river under this watershed; national registry uniquely agrees"
        }
        if code in matches and (matches[code]["watershed_name"],matches[code]["river_name"])!=key:
            raise ValueError("Conflicting JMA river titles for the same code")
        matches[code]=item
    approved=sorted(matches.values(),key=lambda r:r["river_code"])
    bygroup=[]
    for item in approved:
        for old in B[(item["watershed_name"],item["river_name"])]:
            if old["unapproved_unique_catalog_code_candidate"]!=item["river_code"]:
                raise ValueError("Kyushu original B candidate disagrees with separate JMA proof")
            bygroup.append({"watershed_name":item["watershed_name"],
                            "river_name":item["river_name"],
                            "river_code":item["river_code"],
                            "category":old["category"],"recovered_records":old["recovered_records"],
                            "year_min":old["year_min"],"year_max":old["year_max"]})
    if not approved:raise ValueError("Zero strictly verified Kyushu records")
    out_dir=Path(out_dir);out_dir.mkdir(parents=True,exist_ok=True)
    with (out_dir/"kyushu_strict_independent_code_crosswalk_v04.csv").open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(approved)
    with (out_dir/"kyushu_jma_verified_group_counts_v04.csv").open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(bygroup[0]));w.writeheader();w.writerows(bygroup)
    report={
        "source_pages":[SOURCES["jma"],SOURCES["mlit"]],
        "source_sha256":SHA,
        "B_total_recovered_contexts":115062,
        "strict_matched_rivers":len(approved),
        "matched_old_B_recovered_contexts":sum(int(x["recovered_records"]) for x in bygroup),
        "independently_checked_jma_titles":audit["titles_reviewed"],
        "excluded":audit,
        "match_rules":"literal river name and JMA 10-digit code + MLIT independent watershed-river pairing + national catalog unique match; no forecast-zone suffix stripping",
        "no_prefecture_inference":True,
        "no_tributary_inference":True,
        "production_changed":False,
        "db_still_unchanged":True
    }
    (out_dir/"kyushu_jma_crosswalk_review_v04.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="excluded"},ensure_ascii=False))
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",required=True)
    a=p.parse_args()
    approve(V04/"outputs/jma_2026_river_numbers_probe.json",
            V04/"outputs/kyushu_B_triage_v04.csv",
            V04/"outputs/official_watershed_river_pairs_v04.csv",a.out)
