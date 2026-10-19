#!/usr/bin/env python3
"""Strict Tohoku-only independent code ledger crosswalk for research.

No database modification. Only promote recovered B contexts if the official
2010/2011 regional code ledger + national river code CSV agree exactly,
the watershed label occurs in the page HEADER, and the pair is unique.
"""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
from inspect_tohoku_code_ledger import analyze, OFFICIAL_URL, ROOT

PINNED_SOURCE_SHA256="cde06431d9f50fbccf9ac4606544a595168d86ea44b1864a9c47ccbf8e5111f8"
CROSSWALK_FIELDS=["region","source_authority","watershed_name","river_name","river_code",
                  "watershed_code","code_source_url","code_source_page","source_sha256","approval_basis"]
PROMOTED_FIELDS=["region","watershed_name","river_name","river_code","watershed_code",
                 "group","recovered_records","distinct_literal_names_not_species","year_min","year_max",
                 "code_source_url","code_source_page","approval_basis"]

def page_watersheds(pdf):
    pages=subprocess.check_output(["pdftotext","-layout",str(pdf),"-"],text=True).split("\f")
    code_re=re.compile(r"^\s*\d{1,6}\s+\d{10}\s+\d{1,2}\s+\S+",re.M)
    mapping={}
    for number,page in enumerate(pages,1):
        match=code_re.search(page)
        if not match:continue
        header=page[:match.start()]
        labels=set(re.findall(r"(?m)^\s*東北地方整備局\s+([^\s]+)\s*$",header))
        if len(labels)==1 and re.search(r"水\\s*系\\s*名",header):
            mapping[number]=next(iter(labels))
    return mapping

def verify(pdf,out):
    pdf=Path(pdf);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    sha=hashlib.sha256(pdf.read_bytes()).hexdigest()
    if sha!=PINNED_SOURCE_SHA256:
        raise ValueError("Official Tohoku PDF changed; do not automatically approve")
    info,matched=analyze(pdf)
    headers=page_watersheds(pdf)
    # Some official pages place the authority and watershed on separate header
    # lines; allow an EXACT watershed token only before the first code row.
    # Never infer watershed using a river name or a code prefix alone.
    pages=subprocess.check_output(["pdftotext","-layout",str(pdf),"-"],text=True).split("\f")
    code_start=re.compile(r"^\s*\d{1,6}\s+\d{10}\s+\d{1,2}\s+\S+",re.M)
    for pg in {r["source_page"] for r in matched}:
        if pg in headers:continue
        page=pages[pg-1]
        m=code_start.search(page)
        if not m:continue
        header=page[:m.start()]
        if "東北地方整備局" not in header or not re.search(r"水\\s*系\\s*名",header):continue
        claimed={r["national_watershed"] for r in matched if r["source_page"]==pg}
        if len(claimed)!=1:continue
        name=next(iter(claimed))
        if name in header.split():headers[pg]=name
    if len(set(headers.values()))!=12 or len(headers)<50:
        raise ValueError(f"Too few unambiguous watershed page headers: count={len(headers)} names={sorted(set(headers.values()))} sample={list(headers.items())[:5]}")
    correct=[r for r in matched if headers.get(r["source_page"])==r["national_watershed"]]
    pairs=Counter((r["national_watershed"],r["ledger_river_name"]) for r in correct)
    # Even same name on two separate river codes must stay B.
    unique=[r for r in correct if pairs[(r["national_watershed"],r["ledger_river_name"])]==1]
    if len({r["river_code"] for r in unique})!=len(unique):
        raise ValueError("Duplicate codes in verified ledger")
    approved=[]
    for r in unique:
        approved.append({
            "region":"tohoku","source_authority":"東北地方整備局",
            "watershed_name":r["national_watershed"],"river_name":r["ledger_river_name"],
            "river_code":r["river_code"],"watershed_code":r["national_watershed_code"],
            "code_source_url":OFFICIAL_URL,"code_source_page":r["source_page"],
            "source_sha256":sha,
            "approval_basis":"exact regional page-header watershed and 10-digit code/name; national registry agrees; unique pair in pinned ledger"
        })
    with (ROOT/"research-individual-v01/outputs/river_counts.csv").open(encoding="utf-8",newline="") as f:
        groups=list(csv.DictReader(f))
    B=[r for r in groups if r["region"]=="tohoku" and r["match_class"]=="B"]
    if not B:raise ValueError("No unresolved Tohoku B records found")
    mapping={(r["watershed_name"],r["river_name"]):r for r in approved}
    promoted=[]
    for row in B:
        found=mapping.get((row["watershed"],row["river"]))
        if not found:continue
        promoted.append({
            "region":"tohoku","watershed_name":row["watershed"],"river_name":row["river"],
            "river_code":found["river_code"],"watershed_code":found["watershed_code"],
            "group":row["group"],"recovered_records":row["recovered_records"],
            "distinct_literal_names_not_species":row["distinct_literal_names_not_species"],
            "year_min":row["year_min"],"year_max":row["year_max"],
            "code_source_url":OFFICIAL_URL,"code_source_page":found["code_source_page"],
            "approval_basis":found["approval_basis"]
        })
    for name,fields,rows in [
        ("tohoku_independent_crosswalk.csv",CROSSWALK_FIELDS,approved),
        ("tohoku_B_to_A_candidate_counts.csv",PROMOTED_FIELDS,promoted)
    ]:
        with (out/name).open("w",encoding="utf-8",newline="") as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    newcodes={r["river_code"] for r in promoted}
    n=sum(int(r["recovered_records"]) for r in promoted)
    all_b=sum(int(r["recovered_records"]) for r in B)
    summary={
        "source_url":OFFICIAL_URL,"pinned_sha256":sha,
        "watershed_headers_verified":len(headers),
        "independent_ledger_exact_matches":len(correct),
        "unique_regional_code_name_pairs":len(approved),
        "ambiguous_ledger_code_name_rows_excluded":len(correct)-len(approved),
        "tohoku_B_grouped_records_before":all_b,
        "candidate_B_records_supported_by_ledger":n,
        "remaining_B_grouped_records":all_b-n,
        "candidate_rivers_with_records":len(newcodes),
        "candidate_watersheds_with_records":len({r["watershed_name"] for r in promoted}),
        "candidate_group_rows":len(promoted),
        "new_A_records_NOT_YET_loaded_into_SQLite":True,
        "production_changed":False,
        "counts_are_restored_river_contexts_not_new_observations":True
    }
    if n>all_b or len(approved)>info["ledger_rows_regex_matched"]:
        raise ValueError("Counts inconsistent")
    (out/"tohoku_crosswalk_review.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return summary

def main():
    p=argparse.ArgumentParser();p.add_argument("--pdf",required=True);p.add_argument("--out",required=True)
    a=p.parse_args()
    print(json.dumps(verify(Path(a.pdf),Path(a.out)),ensure_ascii=False))
if __name__=="__main__":main()
