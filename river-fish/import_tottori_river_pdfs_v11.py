#!/usr/bin/env python3
"""Extract *candidate* names from Tottori Prefecture official river-list PDFs.

Official source: https://www.pref.tottori.lg.jp/307111.htm
Snapshot listed in each PDF: 2023-04-01. Three district PDF tables:
 eastern, central, western. Official printed serial is NOT MLIT 10-digit code.

pdftotext is used (not OCR); each proposed row keeps region, document page,
the exact river-name string printed, source URL and manual review status.
Do not assign missing watershed cells or river administrative class from
the national 10-digit river code. PDF text layout is untrusted until reviewed.
"""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.request

PDFS={
    "east":"https://www.pref.tottori.lg.jp/secure/1313532/toubu.pdf",
    "central":"https://www.pref.tottori.lg.jp/secure/1313532/230401chubu.pdf",
    "west":"https://www.pref.tottori.lg.jp/secure/1313532/230401seibu.pdf",
}
NAME_LABELS={"east":"東部圏域","central":"中部圏域","west":"西部圏域"}
CSV_HEAD=[
    "document_mention_id","prefecture","district_as_published",
    "river_name_as_pdf_text","printed_local_serial","river_class_page_heading",
    "watershed_printed_on_same_line","source_pdf_url","source_pdf_page_1based",
    "source_as_of","text_extraction_review_status","ten_digit_code_status",
    "specific_river_ecology_status","website_publication_status"
]
SOURCE_DATE="2023-04-01"
SOURCE_PAGE="https://www.pref.tottori.lg.jp/307111.htm"
MAX_BYTES=1_500_000
SERIAL=re.compile(r"(?<![0-9])(?P<serial>[0-9]{1,3})\s+(?P<name>[^\s,、。]{1,70})")
WATERSHED=re.compile(r"([\S]{1,40})水系")
CLASSES=[("準用河川",re.compile(r"準用\s*河川")),("一級河川",re.compile(r"[1１]\s*級\s*河川")),("二級河川",re.compile(r"[2２]\s*級\s*河川"))]

def download(url):
    if url not in PDFS.values():raise ValueError("Not a pinned official PDF URL")
    req=urllib.request.Request(url,headers={"User-Agent":"tsurikue-river-list-study/1.1"})
    with urllib.request.urlopen(req,timeout=45) as res:
        if res.status!=200 or res.url!=url:raise RuntimeError("Source redirected or unavailable")
        payload=res.read(MAX_BYTES+1)
    if len(payload)>MAX_BYTES or not payload.startswith(b"%PDF-"):
        raise RuntimeError("Unexpected PDF type or size; manual review")
    return payload

def extract_text(data):
    with tempfile.TemporaryDirectory() as td:
        pdf=Path(td)/"source.pdf"
        pdf.write_bytes(data)
        proc=subprocess.run(
            ["pdftotext","-raw","-enc","UTF-8",str(pdf),"-"],
            capture_output=True,timeout=35,check=True)
        return proc.stdout.decode("utf-8")

def looks_like_river_name(name):
    if not name or len(name)>45:return False
    if name.endswith(("川","池","水路","放水路","川派川","河川","水門")):
        if name in ("河川","水系名","河川名","準用河川","一級河川","二級河川"):
            return False
        if any(c.isdigit() for c in name):return False
        return True
    return False

def parse_text(region,text):
    if region not in PDFS:raise ValueError("Unrecognized district")
    if "令和５年４月１日" not in text and "令和5年4月1日" not in text:
        raise ValueError("Snapshot date not found. PDF revision must be re-audited")
    pages=text.split("\f")
    current_class=None
    seen=set()
    entries=[]
    rejected=Counter()
    for page_no,page in enumerate(pages,1):
        for line in page.splitlines():
            line=line.strip()
            if not line:continue
            for label,rx in CLASSES:
                if rx.search(line):current_class=label
            if "河川一覧" in line or "水系名" in line or "ページ" in line:
                continue
            for m in SERIAL.finditer(line):
                serial=m.group("serial")
                name=m.group("name").strip("　 \t,，")
                if not looks_like_river_name(name):
                    rejected["not_a_river_name"]+=1
                    continue
                if not current_class:
                    raise ValueError(f"No class heading for a number/name row: {region} {page_no} {line}")
                key=(region,serial)
                if key in seen:raise ValueError("Source serial repeated in same region: "+str(key))
                seen.add(key)
                prefix=line[:m.start()].strip()
                watershed=""
                if current_class!="準用河川":
                    match=WATERSHED.search(prefix)
                    if match:watershed=match.group(1)+"水系"
                # 3-digit number is a source-internal index, NOT a 10-digit code.
                entries.append({
                    "document_mention_id":f"TP-{region}-{int(serial):03d}",
                    "prefecture":"鳥取県",
                    "district_as_published":NAME_LABELS[region],
                    "river_name_as_pdf_text":name,
                    "printed_local_serial":serial,
                    "river_class_page_heading":current_class,
                    "watershed_printed_on_same_line":watershed,
                    "source_pdf_url":PDFS[region],
                    "source_pdf_page_1based":str(page_no),
                    "source_as_of":SOURCE_DATE,
                    "text_extraction_review_status":"pdf_text_machine_extracted_requires_visual_review",
                    "ten_digit_code_status":"unlinked",
                    "specific_river_ecology_status":"not_examined",
                    "website_publication_status":"research_only",
                })
    return entries,dict(rejected)

def build(out,downloader=download,extractor=extract_text):
    all_rows=[]
    source_provenance={}
    per_district={}
    for region,url in PDFS.items():
        raw=downloader(url)
        text=extractor(raw)
        rows,rejected=parse_text(region,text)
        if len(rows)<40:raise ValueError("Unusually few river rows extracted for "+region)
        if not all(c in {r["river_class_page_heading"] for r in rows} for c in ("一級河川","二級河川","準用河川")):
            raise ValueError("Missing river-class page; PDF classification extraction incomplete")
        all_rows.extend(rows)
        per_district[region]={
          "records":len(rows),
          "category_counts":dict(sorted(Counter(r["river_class_page_heading"] for r in rows).items())),
          "rejected_candidate_tokens":rejected,
          "source_url":url,"source_sha256":hashlib.sha256(raw).hexdigest(),
          "source_pages":max(int(r["source_pdf_page_1based"]) for r in rows),
        }
    ids=[r["document_mention_id"] for r in all_rows]
    if len(ids)!=len(set(ids)) or len(all_rows)<220:
        raise ValueError("Incomplete/duplicate list; do not publish or stage")
    output=Path(out)
    output.mkdir(parents=True,exist_ok=True)
    with (output/"tottori_river_pdf_mentions_v11.csv").open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=CSV_HEAD);w.writeheader()
        w.writerows(all_rows)
    manifest={
      "source_listing_page":SOURCE_PAGE,"source_as_of":SOURCE_DATE,
      "districts":per_district,
      "pdf_text_source_mention_rows":len(all_rows),
      "distinct_printed_name_labels":len({r["river_name_as_pdf_text"] for r in all_rows}),
      "by_page_heading":dict(sorted(Counter(r["river_class_page_heading"] for r in all_rows).items())),
      "all_codes_unlinked":True,
      "watershed_blank_means_not_on_same_row":True,
      "no_geolocation_or_species_inferred":True,
      "publication_status":"research_only_pending_visual_review",
      "source_republication":"Only extracted factual river names/metadata, no PDF pages or geometry copied."
    }
    (output/"tottori_river_pdf_manifest_v11.json").write_text(
        json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return manifest

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True)
    o=p.parse_args()
    print(json.dumps(build(o.out),ensure_ascii=False,indent=2))
