#!/usr/bin/env python3
"""Stage nationwide river-name code lists WITHOUT geographic/species inference.

Official standalone CODE LISTS (not the W05 non-commercial geometry dataset):
  https://nlftp.mlit.go.jp/ksj/gml/codelist/RiverCodeCd.html
  https://nlftp.mlit.go.jp/ksj/gml/codelist/WaterSystemCodeCd.html

Source code metadata are historical/as-published. No official promise that every
modern/local stream is represented. Do not derive tributary fish or exact locations.
"""
import argparse
import csv
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.request
from urllib.parse import urlparse

RIVERS="https://nlftp.mlit.go.jp/ksj/gml/codelist/RiverCodeCd.html"
WATERSHEDS="https://nlftp.mlit.go.jp/ksj/gml/codelist/WaterSystemCodeCd.html"
TERMS="https://nlftp.mlit.go.jp/ksj/other/agreement.html"
MAX_BYTES=9_000_000
RIVER_HEADER=["river_code","river_name","watershed_code","watershed_name",
              "code_region_prefix","source_url","identity_status","site_status"]
WATER_HEADER=["watershed_code","watershed_name","code_region_prefix","source_url","identity_status"]

class TableRows(HTMLParser):
    """Only two-cell code/name table rows; no scraping of surrounding paragraphs."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows=[];self.in_row=False;self.in_cell=False
        self.cells=[];self.chunks=[]
    def handle_starttag(self,tag,attrs):
        tag=tag.lower()
        if tag=="tr":
            self.in_row=True;self.cells=[];self.in_cell=False;self.chunks=[]
        elif self.in_row and tag in ("td","th"):
            self.in_cell=True;self.chunks=[]
        elif self.in_cell and tag=="br":
            self.chunks.append(" ")
    def handle_data(self,data):
        if self.in_cell:self.chunks.append(data)
    def handle_endtag(self,tag):
        tag=tag.lower()
        if tag in ("td","th") and self.in_cell:
            self.cells.append(re.sub(r"\s+"," ","".join(self.chunks)).strip())
            self.chunks=[];self.in_cell=False
        elif tag=="tr" and self.in_row:
            if len(self.cells)>=2:self.rows.append(self.cells[:2])
            self.in_row=False;self.in_cell=False;self.cells=[];self.chunks=[]

def decode(raw):
    # Some old MLIT code list HTML documents are Shift-JIS or EUC-JP.
    meta=raw[:6000].lower()
    declared=re.search(rb'charset\s*=\s*["\x27]?\s*([a-z0-9_-]+)',meta)
    proposed=[]
    if raw.startswith(b'\xef\xbb\xbf'):proposed.append("utf-8-sig")
    if declared:
        charset=declared.group(1).decode("ascii",errors="ignore")
        if charset in ("shift_jis","shift-jis","sjis","x-sjis"):proposed.append("cp932")
        else:proposed.append(charset)
    proposed.extend(("utf-8","cp932","euc_jp"))
    for charset in dict.fromkeys(proposed):
        try:return raw.decode(charset),charset
        except (UnicodeDecodeError,LookupError):continue
    raise ValueError("Unknown HTML encoding; manual review required")

def parse_list(html,kind,min_count=None):
    if kind not in ("river","watershed"):raise ValueError("Unexpected list kind")
    parser=TableRows();parser.feed(html)
    width=10 if kind=="river" else 6
    matched={};dups=0
    for raw_code,raw_name in parser.rows:
        code=raw_code.strip()
        name=re.sub(r"\s+"," ",raw_name).strip()
        if not re.fullmatch(r"\d{"+str(width)+r"}",code):continue
        if not name or len(name)>140 or name[0] in "=+-@":
            raise ValueError("Unexpected river/watershed name in official list")
        if code in matched:
            if matched[code]!=name:raise ValueError("Conflicting names under one code: "+code)
            dups+=1
        matched[code]=name
    minimum=(20_000 if kind=="river" else 3_000) if min_count is None else min_count
    if len(matched)<minimum:
        raise ValueError(f"Too few {kind} records: {len(matched)}; source HTML may have changed")
    return matched,{"html_table_rows":len(parser.rows),"same_code_duplicate_rows":dups}

def download(url):
    if url not in (RIVERS,WATERSHEDS) or urlparse(url).hostname!="nlftp.mlit.go.jp":
        raise ValueError("Only allow specified official list source")
    with urllib.request.urlopen(
        urllib.request.Request(url,headers={"User-Agent":"tsurikue-river-code-research/0.7"}),timeout=90
    ) as res:
        if res.status!=200 or res.url!=url:raise RuntimeError("Official source redirect or non-200")
        raw=res.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES:raise RuntimeError("Official HTML unexpectedly oversized")
    return raw

def stage(output,rivers,watersheds,meta):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    missing=set()
    with (output/"river_codes_national_v07.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f);w.writerow(RIVER_HEADER)
        for code,name in sorted(rivers.items()):
            ws_code=code[:6]
            watershed_name=watersheds.get(ws_code,"")
            if not watershed_name:missing.add(ws_code)
            w.writerow([code,name,ws_code,watershed_name,code[:2],RIVERS,
                        "coded_name_only_not_geographically_verified","research_only"])
    with (output/"watershed_codes_national_v07.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f);w.writerow(WATER_HEADER)
        for code,name in sorted(watersheds.items()):
            w.writerow([code,name,code[:2],WATERSHEDS,"coded_watershed_name_only"])
    unique_names=len(set(rivers.values()))
    by_prefix={}
    for c in rivers:
        by_prefix[c[:2]]=by_prefix.get(c[:2],0)+1
    manifest={
      "source_pages":{"rivers":RIVERS,"watersheds":WATERSHEDS},
      "source_sha256":meta,
      "river_code_rows":len(rivers),"watershed_code_rows":len(watersheds),
      "distinct_literal_river_names":unique_names,
      "river_code_region_prefix_counts":dict(sorted(by_prefix.items())),
      "river_rows_without_matching_watershed_code":sum(1 for c in rivers if c[:6] not in watersheds),
      "unmatched_watershed_codes":sorted(missing),
      "river_key_rule":"10-digit river code, never name-only identity",
      "watershed_key_rule":"first six digits of river code; never parent river",
      "first_two_digits":"jurisdiction/code issuing prefix, NOT guaranteed actual prefecture location",
      "prefecture_mapping":"not_inferred",
      "direct_parent_river":"not_inferred",
      "direct_species":"not_inferred",
      "rights_review":"code lists separate from W05 geometries; commercial publication requires provenance and checking of exceptions",
      "source_recency":"as published, current administrative classification unverified",
      "publication_status":"research_only_not_website_deployed",
      "no_W05_geometries":True,
    }
    (output/"river_code_manifest_v07.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return manifest

def build(out):
    raw_r=download(RIVERS);raw_w=download(WATERSHEDS)
    river_html,enc_r=decode(raw_r);water_html,enc_w=decode(raw_w)
    rivers,rdiag=parse_list(river_html,"river")
    waters,wsdiag=parse_list(water_html,"watershed")
    if rivers.get("8707090023")!="諸木川":
        raise ValueError("Moroki (8707090023) is missing or renamed; manual verification required")
    if waters.get("870709")!="太田川":
        raise ValueError("Ota watershed code unexpectedly changed")
    result=stage(out,rivers,waters,{
        "river_html":hashlib.sha256(raw_r).hexdigest(),
        "watershed_html":hashlib.sha256(raw_w).hexdigest(),
        "river_encoding":enc_r,"watershed_encoding":enc_w,
        "river_parser":rdiag,"watershed_parser":wsdiag
    })
    print(json.dumps({k:v for k,v in result.items() if k not in ("river_code_region_prefix_counts","unmatched_watershed_codes")},ensure_ascii=False,indent=2))
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser(description="全国河川・水系コード台帳を公式HTMLから抽出")
    p.add_argument("--out",required=True)
    a=p.parse_args()
    build(a.out)
