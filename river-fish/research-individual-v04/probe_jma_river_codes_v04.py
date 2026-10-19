#!/usr/bin/env python3
"""Read official JMA flood-forecast table to inspect independent 10-digit river codes.

Research only; JMA forecast area titles may NOT equal literal river names.
Nothing is promoted from B to A without independent exact-name validation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import urllib.request

SOURCE="https://www.data.jma.go.jp/suishin/oshirase/pdf/20260422.pdf"
def inspect(output):
    req=urllib.request.Request(SOURCE,headers={"User-Agent":"tsurikue-kyushu-river-research/1.0"})
    with urllib.request.urlopen(req,timeout=45) as r:
        if r.status!=200 or r.url!=SOURCE:raise ValueError("Official PDF redirected")
        data=r.read(12_000_001)
        if len(data)>12_000_000 or not data.startswith(b"%PDF"):raise ValueError("Not an official PDF")
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    sourcepdf=output.with_suffix(".source.pdf")
    sourcepdf.write_bytes(data)
    txt=subprocess.check_output(["pdftotext","-layout",str(sourcepdf),"-"],text=True)
    sourcepdf.unlink()
    pages=txt.split("\f")
    hits=[]
    for pn,page in enumerate(pages,1):
        lines=page.splitlines()
        for i,line in enumerate(lines):
            codes=set(re.findall(r"(?<!\d)89\d{8}(?!\d)",line))
            for code in sorted(codes):
                hits.append({"page":pn,"code":code,
                             "line":line.strip()[:240],
                             "above":lines[i-1].strip()[:200] if i else "",
                             "below":lines[i+1].strip()[:200] if i+1<len(lines) else ""})
    result={"source_url":SOURCE,"source_sha256":hashlib.sha256(data).hexdigest(),
            "pdf_pages":len(pages),"kyushu_code_occurrences":len(hits),
            "distinct_kyushu_codes":len({h["code"] for h in hits}),
            "samples":hits[:65],
            "all_matching_codes":[c for c in sorted({h["code"] for h in hits})],
            "no_automatic_A_promotion":True}
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False))
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",required=True)
    a=p.parse_args();inspect(a.out)
