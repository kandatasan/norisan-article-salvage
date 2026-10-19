#!/usr/bin/env python3
"""Inspect independently published Tohoku river code ledger (research only).

No new 'A'/approved matches are emitted by this initial inspection. Raw PDF
is never committed or redistributed. No WordPress/API/MySQL access.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
OFFICIAL_URL="https://www.thr.mlit.go.jp/bumon/b00037/k00290/river-hp/kasen/code/data/ikkyuusuikei/0200_ikkatu.pdf"

def analyze(pdf:Path):
    pdf=Path(pdf)
    data=pdf.read_bytes()
    if len(data)>35_000_000 or not data.startswith(b"%PDF-"):
        raise ValueError("Unexpected PDF")
    pages=subprocess.check_output(["pdftotext","-layout",str(pdf),"-"],text=True).split("\f")
    with (ROOT/"national-codes-staged/river_codes_national_v07.csv").open(encoding="utf-8-sig",newline="") as f:
        national={r["river_code"]:r for r in csv.DictReader(f)}
    code_re=re.compile(r"^\s*(\d{1,6})\s+(\d{10})\s+(\d{1,2})\s+(\S+)",re.M)
    valid=[]
    candidate=[]
    samples=[]
    for pg,page in enumerate(pages,1):
        if not page.strip():continue
        matched=list(code_re.finditer(page))
        if matched and len(samples)<8:
            samples.append({"page":pg,"header_lines":[s.strip() for s in page[:matched[0].start()].splitlines() if s.strip()][:12],"sample_rows":[m.group(0).strip()[:145] for m in matched[:2]]})
        header=page[:matched[0].start()] if matched else page
        for m in matched:
            row_number,code,order,name=m.groups()
            nat=national.get(code)
            obj={"source_page":pg,"river_code":code,"ledger_river_name":name,"ledger_order":order,
                 "national_river_name":nat["river_name"] if nat else "",
                 "national_watershed":nat["watershed_name"] if nat else "",
                 "national_watershed_code":nat["watershed_code"] if nat else ""}
            candidate.append(obj)
            if nat and nat["river_name"]==name and ("東北地方整備局" in header) and nat["watershed_name"] in header:
                valid.append(obj)
    return {"source_url":OFFICIAL_URL,"source_sha256":hashlib.sha256(data).hexdigest(),
            "pdf_pages":len(pages),"ledger_rows_regex_matched":len(candidate),
            "strict_page_and_national_matches":len(valid),
            "distinct_strict_codes":len({r["river_code"] for r in valid}),
            "distinct_strict_watersheds":len({r["national_watershed_code"] for r in valid}),
            "inspection_only_no_new_A_approved":True,
            "header_samples":samples},valid

def main():
    p=argparse.ArgumentParser();p.add_argument("--pdf");p.add_argument("--out",required=True)
    a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    pdf=Path(a.pdf) if a.pdf else out/"tohoku-source.pdf"
    if not a.pdf:
        req=urllib.request.Request(OFFICIAL_URL,headers={"User-Agent":"tsurikue-river-evidence-research/1.0"})
        with urllib.request.urlopen(req,timeout=120) as res:
            if res.status!=200 or res.url!=OFFICIAL_URL:raise ValueError("Official download redirected")
            content=res.read(35_000_001)
        if len(content)>35_000_000:raise ValueError("PDF too large")
        pdf.write_bytes(content)
    summary,rows=analyze(pdf)
    (out/"tohoku_ledger_inspection.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    with (out/"tohoku_unapproved_evidence.csv").open("w",encoding="utf-8",newline="") as fd:
        fields=["source_page","river_code","ledger_river_name","ledger_order","national_river_name","national_watershed","national_watershed_code"]
        w=csv.DictWriter(fd,fieldnames=fields);w.writeheader();w.writerows(rows)
    print(json.dumps(summary,ensure_ascii=False))
if __name__=="__main__":main()
