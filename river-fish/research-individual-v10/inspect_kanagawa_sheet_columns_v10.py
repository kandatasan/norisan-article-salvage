#!/usr/bin/env python3
"""Safely inspect column meanings in official Kanagawa 2025 eDNA spreadsheet.

This is an external source identification/provenance audit, NOT direct capture
or a claimed river match. Do not store sampling coordinates or participant data.
Sheet OOXML is inspected without editing the original workbook.
"""
from __future__ import annotations
import argparse,hashlib,json,re,urllib.request
from pathlib import Path
from io import BytesIO
from xml.etree import ElementTree as ET
from zipfile import ZipFile
N="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
S="https://www.pref.kanagawa.jp/documents/97797/r7_project_kekka.xlsx"
EXPECTED="ca92efc511d26a02a48ca44d6660d8fbc0fa681b594b334003527b54ed159211"
def clean(v):
    v=re.sub(r"[\r\n\t]+"," ",str(v)).strip()
    if re.search(r"(?:\d{2,3}\.\d{4,}|緯度|経度|latit|longit|調査者|参加者|住所|電話)",v,re.I):
        return "[site-or-person-metadata-held]"
    return v[:75]
def main(out):
    request=urllib.request.Request(S,headers={"User-Agent":"Tsurikue-river-research/1.0"})
    with urllib.request.urlopen(request,timeout=95) as f:raw=f.read(3_000_000)
    if hashlib.sha256(raw).hexdigest()!=EXPECTED:
        raise ValueError("The public Kanagawa workbook changed. Inspect before reuse.")
    with ZipFile(BytesIO(raw)) as z:
        strings=[]
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall(f"{{{N}}}si"):
                strings.append("".join(t.text or "" for t in si.iter(f"{{{N}}}t")))
        root=ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
        rows={}
        for row in root.findall(f".//{{{N}}}sheetData/{{{N}}}row"):
            vals={}
            for cell in row.findall(f"{{{N}}}c"):
                v=cell.find(f"{{{N}}}v")
                value=v.text if v is not None else ""
                typ=cell.attrib.get("t")
                if typ=="s" and value.isdigit():value=strings[int(value)]
                elif typ=="inlineStr":
                    value="".join(t.text or "" for t in cell.iter(f"{{{N}}}t"))
                if value!="":vals[re.sub(r"\d","",cell.attrib.get("r",""))]=clean(value)
            rows[int(row.attrib["r"])]=vals
        head=[]
        for i in range(1,9):
            vals=rows.get(i,{})
            head.append({"row":i,"A_through_Q":{k:v for k,v in vals.items() if len(k)==1 and k<="Q"},
                         "named_water_or_group_labels":[{"column":k,"text":v}
                           for k,v in vals.items() if k not in list("ABCDEFGHIJKLMNOPQ")
                           and re.search(r"[川沢渓水系]|河川|調査区間|魚類|底生",v)][:24],
                         "nonempty_cells":len(vals)})
        hits=[]
        for i,vals in list(rows.items())[:70]:
            for col,value in vals.items():
                if re.search(r"河川名|水系名|[一-龥]{1,7}川|[一-龥]{1,6}沢",value) and "[site-" not in value:
                    hits.append({"row":i,"col":col,"possible_river_label":value})
        source={"input_source_url":S,"input_sha256":EXPECTED,
            "method":"environmental DNA, not confirmed physical catch",
            "worksheet_rows":len(rows),"head_structure":head,
            "possible_river_names_in_first_70_rows":hits[:40],
            "river_locations_not_confirmed":True,
            "site_coordinates_and_personal_data_not_exported":True,
            "label_source_has_not_been_imported_into_main_catalog":True}
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(source,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"rows":len(rows),"top_rows":head,"possible_river_names":hits[:20]},ensure_ascii=False))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",required=True);main(p.parse_args().out)
