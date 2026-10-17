#!/usr/bin/env python3
"""Inventory one official MLIT nationwide fish source (metadata only).

- Verify the exact source is advertised by the official download index.
- Bound compressed/uncompressed sizes to prevent archive bombs.
- No raw observations, stations, or coordinates leave the runner.
- No writes to WordPress. Only source manifest JSON in an explicit output dir.
"""
import argparse
import hashlib
from html.parser import HTMLParser
from io import BytesIO
import json
from pathlib import Path
import re
import urllib.request
from zipfile import ZipFile
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
REGISTRY=HERE/"nationwide_sources_v06.json"
MAX_ZIP=260_000_000
MAX_WORKBOOK=220_000_000
M="{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
EXPECTED={"生物項目","水系","調査年度","種名"}
USER_AGENT="tsurikue-fish-source-audit/0.6 (+https://tsurikue.com)"

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls=set()
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            value=dict(attrs).get("href")
            if value:self.urls.add(value)

def fetch(url,cap):
    req=urllib.request.Request(url,headers={"User-Agent":USER_AGENT})
    with urllib.request.urlopen(req,timeout=100) as res:
        if res.url!=url or res.status!=200:
            raise RuntimeError("Official source unexpectedly redirected or did not return HTTP 200")
        data=res.read(cap+1)
    if len(data)>cap:raise RuntimeError("Official compressed source too large; manual review required")
    return data

def source_verified_in_official_index(source,index_url):
    raw=fetch(index_url,600_000)
    p=Links();p.feed(raw.decode("utf-8",errors="replace"))
    from urllib.parse import urljoin
    return any(urljoin(index_url,href)==source for href in p.urls)

def sheet_header(xlsx):
    """Return first sheet's top-row column headings only; never expose row 2+."""
    with ZipFile(BytesIO(xlsx)) as z:
        if "xl/worksheets/sheet1.xml" not in z.namelist():
            return {"sheet1_present":False,"headers":[],"required_headers_found":[]}
        strings=[]
        if "xl/sharedStrings.xml" in z.namelist():
            if z.getinfo("xl/sharedStrings.xml").file_size>35_000_000:
                raise RuntimeError("Unusually large string table")
            with z.open("xl/sharedStrings.xml") as fd:
                for _,el in ET.iterparse(fd,events=("end",)):
                    if el.tag==M+"si":
                        strings.append("".join(x.text or "" for x in el.iter(M+"t")))
                        el.clear()
        with z.open("xl/worksheets/sheet1.xml") as fd:
            for _,row in ET.iterparse(fd,events=("end",)):
                if row.tag!=M+"row":continue
                values={}
                for cell in row.findall(M+"c"):
                    match=re.match(r"^([A-Z]+)",cell.get("r",""))
                    if not match:continue
                    col=match.group(1)
                    value=cell.findtext(M+"v") or ""
                    if cell.get("t")=="s" and value.isdecimal():
                        index=int(value)
                        value=strings[index] if index<len(strings) else ""
                    elif cell.get("t")=="inlineStr":
                        value="".join(t.text or "" for t in cell.iter(M+"t"))
                    if value:values[col]=str(value).strip()[:70]
                found={col:title for col,title in values.items() if title in EXPECTED}
                return {"sheet1_present":True,"first_data_row_number":int(row.get("r","0")),
                        "header_columns":found,"required_headers_found":sorted(found.values()),
                        "header_count":len(values),"schema_compatible":set(found.values())==EXPECTED}
    return {"sheet1_present":True,"headers":[],"schema_compatible":False}

def inspect(region,output_dir,config=REGISTRY):
    conf=json.loads(Path(config).read_text(encoding="utf-8"))
    region_data={item["region_id"]:item for item in conf["region_sources"]}
    if region not in region_data:raise ValueError("Unknown region")
    item=region_data[region]
    source=item["source_url"]
    if not source_verified_in_official_index(source,conf["verified_index_url"]):
        raise RuntimeError("Source not listed at official MLIT index")
    payload=fetch(source,MAX_ZIP)
    digest=hashlib.sha256(payload).hexdigest()
    if item.get("checksum_sha256") and digest!=item["checksum_sha256"]:
        raise RuntimeError("Previously audited ZIP digest mismatch")
    infos=[]
    with ZipFile(BytesIO(payload)) as z:
        candidates=[]
        for mem in z.infolist():
            if mem.is_dir():continue
            if mem.file_size>MAX_WORKBOOK or mem.file_size<1:
                raise RuntimeError("Archive member size requires manual review")
            if mem.filename.startswith("/") or ".." in Path(mem.filename).parts:
                raise RuntimeError("Unsafe ZIP member path")
            info={"member_name":mem.filename,"bytes":mem.file_size,
                  "format":Path(mem.filename).suffix.lower()}
            infos.append(info)
            if mem.filename.lower().endswith(".xlsx"):
                candidates.append(mem)
        if len(candidates)!=1:
            header={"schema_compatible":False,"note":"Require exactly one XLSX member for automated import"}
        else:
            header=sheet_header(z.read(candidates[0]))
    result={"region_id":region,"official_region":item["official_region"],
            "source_url":source,"sha256":digest,"compressed_bytes":len(payload),
            "members":infos,"header_review":header,
            "publication_status":"research_metadata_only",
            "direct_river_species_mapping":"not_allowed",
            "prefecture_crosswalk":"not_inferred",
            "important_species_location_policy":"exact locations withheld"}
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    (out/f"{region}_source_inventory.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False))
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--region",required=True)
    p.add_argument("--output-dir",required=True)
    opts=p.parse_args()
    inspect(opts.region,opts.output_dir)
