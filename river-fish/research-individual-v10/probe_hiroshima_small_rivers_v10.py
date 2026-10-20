#!/usr/bin/env python3
"""Fetch TWO Hiroshima City official PDFs to verify uncollected small river evidence.

(1) Hiroshima municipal environmental assessment fish survey 2002.
(2) Hiroshima city study-area environment: all four rivers belong to Otagawa
watershed. This study is NOT the MLIT national 36-archive input.

Use only river name and taxon name, survey year, public report URL and page
numbers. Never collect exact survey point/coordinates.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import urllib.request
from tempfile import TemporaryDirectory

SOURCES={
  "fish":"https://www.city.hiroshima.lg.jp/uploaded/attachment/43905.pdf",
  "basin":"https://www.city.hiroshima.lg.jp/uploaded/attachment/43900.pdf",
}
STREAMS=["細坂川","椎原川","奥畑川","安川"]
TAXA=["アマゴ","タカハヤ","オイカワ","カワムツ","カマツカ","カワヨシノボリ"]
def get(name,url,out):
    req=urllib.request.Request(url,headers={"User-Agent":"Tsurikue-evidence-research/1.0"})
    with urllib.request.urlopen(req,timeout=95) as response:
        if response.status!=200 or response.url!=url:raise ValueError("Municipal PDF redirect/change")
        pdf=response.read(18_000_001)
        if len(pdf)>18_000_000 or not pdf.startswith(b"%PDF"):raise ValueError("Invalid/oversized municipal PDF")
    path=out/(name+".pdf");path.write_bytes(pdf)
    text=subprocess.check_output(["pdftotext","-layout",str(path),"-"],text=True)
    pages=text.split("\f")
    info={"url":url,"sha256":hashlib.sha256(pdf).hexdigest(),"bytes":len(pdf),
          "pages":len([p for p in pages if p.strip()]),
          "river_mentions":{s:len(re.findall(s,text)) for s in STREAMS},
          "taxonomy_name_mentions":{s:len(re.findall(s,text)) for s in TAXA},
          "evidence_pages":[]}
    for i,page in enumerate(pages,1):
        if len([x for x in STREAMS if x in page])>=2 and (
            name=="basin" or ("アマゴ" in page and "カワムツ" in page)):
            chunks=page.splitlines()
            keywords=[(n,line.strip()) for n,line in enumerate(chunks)
                      if any(word in line for word in STREAMS+TAXA)]
            info["evidence_pages"].append({"pdf_page":i,"matching_lines":len(keywords),
                          "abbreviated_nonlocation_text":[v[:220] for _,v in keywords[:15]]})
    return info

def run(dest):
    dest=Path(dest);dest.parent.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory() as d:
        out=Path(d)
        infos={kind:get(kind,url,out) for kind,url in SOURCES.items()}
    if not all(v["river_mentions"][s]>0 for v in infos.values() for s in STREAMS):
        raise ValueError("Municipal report not clear about all source river names")
    if not infos["fish"]["evidence_pages"] or not infos["basin"]["evidence_pages"]:
        raise ValueError("No standalone fish/basin documentation found")
    report={"sources":infos,
       "river_identity_source":"Hiroshima City official site, explicitly all four source river names belong to Otagawa water system",
       "biology_method":"capture/visual river-fish survey from municipal EIA, not eDNA",
       "survey_year_candidate":2002,
       "four_named_rivers_not_yet_in_existing_428":True,
       "promoted_biology_records":0,
       "rights_review_before_publication":True,
       "raw_pdfs_not_committed":True,
       "exact_sites_not_stored":True}
    dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:{"sha256":v["sha256"],"pages":v["pages"],"evidence_pages":v["evidence_pages"]} for k,v in infos.items()},ensure_ascii=False))
    return report

if __name__=="__main__":
    a=argparse.ArgumentParser();a.add_argument("--out",required=True)
    run(a.parse_args().out)
