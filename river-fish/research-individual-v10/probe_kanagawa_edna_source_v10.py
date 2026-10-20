#!/usr/bin/env python3
"""Inventory a genuinely NEW prefectural biodiversity source, without importing it.

Kanagawa Environmental Research Center eDNA annual spreadsheets (2021-2025)
are methodologically NOT equivalent to capture/visual fish observations.
Commercial re-use rules explicitly permit reuse with attribution, modifications
labelled, and third-party rights safeguarded.
This probe downloads only official public files and stores abbreviated,
non-geolocating worksheet structure, SHA256 and exact source URLs. No biology
records are promoted until sheet columns have been independently validated.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import hashlib
from html.parser import HTMLParser
from io import BytesIO
import json
import posixpath
import re
import urllib.parse
import urllib.request
from xml.etree import ElementTree as ET
from zipfile import ZipFile

SOURCE="https://www.pref.kanagawa.jp/docs/b4f/suigen/edna.html"
LICENSE="https://www.pref.kanagawa.jp/documents/97797/riyo-kiyaku.pdf"
N="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
R="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
P="http://schemas.openxmlformats.org/package/2006/relationships"

class Links(HTMLParser):
    def __init__(self):
        super().__init__();self.links=[];self.href=None;self.current=[]
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            self.href=dict(attrs).get("href","");self.current=[]
    def handle_data(self,text):
        if self.href is not None:self.current.append(text)
    def handle_endtag(self,tag):
        if tag=="a" and self.href is not None:
            self.links.append((self.href,re.sub(r"\s+"," ","".join(self.current)).strip()))
            self.href=None;self.current=[]

def get(url,limit=5000000):
    request=urllib.request.Request(url,headers={"User-Agent":"Tsurikue-official-river-research/1.0 (noncommercial exploration of public source)"})
    with urllib.request.urlopen(request,timeout=85) as r:
        if r.status!=200:raise ValueError("Unexpected source HTTP status")
        if urllib.parse.urlsplit(r.url).netloc not in ("www.pref.kanagawa.jp","pref.kanagawa.jp"):
            raise ValueError("Official source redirected outside prefecture")
        content=r.read(limit+1)
        if len(content)>limit:raise ValueError("Exceeded source size cap")
        return content,r.url,r.headers.get_content_charset()

def plain_sheet_probe(data):
    """Minimal XLSX container STRUCTURE inspection, not a spreadsheet editor."""
    with ZipFile(BytesIO(data)) as z:
        files=set(z.namelist())
        if "[Content_Types].xml" not in files or "xl/workbook.xml" not in files:
            raise ValueError("Not OOXML workbook")
        wb=ET.fromstring(z.read("xl/workbook.xml"))
        rels=ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        link={r.attrib["Id"]:r.attrib["Target"] for r in rels if r.tag.endswith("Relationship")}
        shared=[]
        if "xl/sharedStrings.xml" in files:
            strings=ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in strings.findall(f"{{{N}}}si"):
                shared.append("".join(t.text or "" for t in si.iter(f"{{{N}}}t")))
        sheets=[]
        for sh in wb.findall(f".//{{{N}}}sheets/{{{N}}}sheet"):
            name=sh.attrib["name"]
            target=link.get(sh.attrib.get(f"{{{R}}}id"),"")
            path=target.lstrip("/") if target.startswith("/") else posixpath.normpath("xl/"+target)
            if path not in files:
                raise ValueError("Sheet relationship is missing: "+path)
            root=ET.fromstring(z.read(path))
            dim=root.find(f"{{{N}}}dimension")
            cellnames=[]
            samples=[]
            for row in root.findall(f".//{{{N}}}sheetData/{{{N}}}row")[:15]:
                vals=[]
                for c in row.findall(f"{{{N}}}c")[:12]:
                    v=c.find(f"{{{N}}}v")
                    raw=v.text or "" if v is not None else ""
                    if c.get("t")=="s" and raw.isdigit():raw=shared[int(raw)]
                    if c.get("t")=="inlineStr":raw="".join(t.text or "" for t in c.iter(f"{{{N}}}t"))
                    raw=str(raw).replace("\n"," ")
                    # Only preserve cell STRUCTURE / keywords, not precise locations,
                    # records, participant identities or sampling point coordinates.
                    if raw and (re.search(r"河川|水系|魚類|種名|学名|目名|検出|採水|年月|年|調査|地点|分類|生物|魚種",raw)):
                        vals.append({"col":re.sub(r"\d","",c.attrib.get("r","")),"keyword_label":raw[:85]})
                if vals:samples.append({"row":row.get("r"),"metadata_labels":vals[:8]})
            sheets.append({"name":name[:70],"dimension":dim.attrib.get("ref") if dim is not None else "unknown",
                           "column_metadata_examples":samples[:10]})
        return {"sheets":sheets,"shared_string_count":len(shared)}

def main(out):
    html,final,charset=get(SOURCE)
    text=html.decode(charset or "utf-8",errors="replace")
    l=Links();l.feed(text)
    links=[{"url":urllib.parse.urljoin(final,href),"description":label}
           for href,label in l.links
           if re.search(r"\.xlsx?(?:\?|$)",urllib.parse.urlsplit(href).path,re.I)]
    # URL path is often .xlsx for annual measurements. Page labels distinguish
    # fish-only vs vertebrates+insects; preserve method metadata separately.
    print("Official XLSX links",len(links))
    for a in links:print(json.dumps(a,ensure_ascii=False))
    if not links:raise ValueError("No publicly linked official XLSX")
    picks=[r for r in links if "脊椎動物" in r["description"]]
    if not picks:
        picks=[r for r in links if "魚類" in r["description"]]
    if not picks:raise ValueError("No biodiversity sheet recognized")
    # Prefer a later linked all-prefecture spreadsheet, but retain the actual
    # relationship in metadata: source PDF explains method is eDNA detection.
    chosen=picks[-1]
    content,url,_=get(chosen["url"],limit=3000000)
    if not content.startswith(b"PK"):raise ValueError("Not XLSX")
    probe=plain_sheet_probe(content)
    result={"source":"神奈川県環境科学センター：環境DNAのページ",
            "source_url":SOURCE,"source_html_sha256":hashlib.sha256(html).hexdigest(),
            "usage_policy_url":LICENSE,
            "license_interpretation":"commercial reuse with source attribution and modification notice; third-party rights must be checked; CC BY 4.0 compatible",
            "survey_method":"environmental_DNA_detection_not_capture_or_visual_sighting",
            "source_file_candidates":links,
            "inspected_excel_url":url,"inspected_excel_sha256":hashlib.sha256(content).hexdigest(),
            "inspected_excel_bytes":len(content),
            "sheet_structure":probe,
            "promoted_as_direct_fish_capture":False,
            "new_rivers_approved":0,
            "precise_sampling_locations_collected":False}
    out=__import__("pathlib").Path(out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k not in ("source_file_candidates","sheet_structure")},ensure_ascii=False))
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",required=True)
    a=p.parse_args();main(a.out)
