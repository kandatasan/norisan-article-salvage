#!/usr/bin/env python3
"""Strict regional-code corroboration. Does not derive prefectures from codes.

Use pdftotext -layout on the official 2016-12 combined ledger first. Each approval
requires a complete row with exact code + name, a matching watershed page header,
agreement with the existing national registry, and a unique regional ledger pair.
Unmatched line wraps and duplicate names stay unapproved, even if plausible.
"""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
URL='https://www.cgr.mlit.go.jp/kasen/code/pdf/000ikkatu201612.pdf'

def build(pdf,out):
    pdf=Path(pdf);out=Path(out)
    text=subprocess.check_output(['pdftotext','-layout',str(pdf),'-'],text=True)
    with (ROOT/'national-codes-staged/river_codes_national_v07.csv').open(encoding='utf-8',newline='') as f:
        catalog={r['river_code']:r for r in csv.DictReader(f)}
    verified={}
    for page_no,page in enumerate(text.split('\f'),1):
        for line in page.splitlines():
            m=re.match(r'\s*\d+\s+(\d{10})\s+\d+\s+(\S+)',line)
            if not m:continue
            code,name=m.groups();v=catalog.get(code)
            if not v or v['river_name']!=name:continue
            if not re.search('中国地方整備局\\s+'+re.escape(v['watershed_name'])+r'(?:\s|$)',page):continue
            verified[code]=(v,page_no)
    pairs=defaultdict(list)
    for code,(v,pg) in verified.items():pairs[(v['watershed_name'],v['river_name'])].append(code)
    rows=[]
    for code,(v,pg) in sorted(verified.items()):
        if len(pairs[(v['watershed_name'],v['river_name'])])!=1:continue
        rows.append(['chugoku','中国地方整備局',v['watershed_name'],v['river_name'],code,v['watershed_code'],URL,pg,
                     'exact code/name on regional ledger page with matching watershed header; agrees with national CSV; unique within verified regional ledger'])
    with out.open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f);w.writerow(['region','source_authority','watershed_name','river_name','river_code','watershed_code','code_source_url','code_source_page','approval_basis']);w.writerows(rows)
    review={'source_url':URL,'sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'edition':'2016-12',
            'verified_ledger_rows':len(verified),'approved_exact_code_name_rows':len(rows),
            'ambiguous_pairs_within_verified_ledger':sum(len(v)>1 for v in pairs.values()),
            'watersheds':len({r[2] for r in rows}),'prefecture_inferred_from_prefix':False,
            'limitations':'historical regional ledger + national name/code corroboration; no independent proof of present-day river extent or direct confluence'}
    out.with_name('code_ledger_review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
    return review

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--pdf',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();print(json.dumps(build(a.pdf,a.out),ensure_ascii=False))
