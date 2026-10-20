#!/usr/bin/env python3
"""Exploratory 2025 prefectural eDNA phenotype summary; code-free river labels.

Source is government-released read count matrix, NOT fish catch counts.
Use raw OOXML solely to read cell values without modifying workbook.
Do not copy sampling-point coordinates, participant data, or full stations.
"""
from collections import Counter,defaultdict
import hashlib,json,re,sys,urllib.request
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

URL="https://www.pref.kanagawa.jp/documents/97797/r7_project_kekka.xlsx"
PINNED="ca92efc511d26a02a48ca44d6660d8fbc0fa681b594b334003527b54ed159211"
N="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
def read_data():
    req=urllib.request.Request(URL,headers={"User-Agent":"Tsurikue-research/1.0"})
    with urllib.request.urlopen(req,timeout=90) as resp:b=resp.read(3000000)
    if hashlib.sha256(b).hexdigest()!=PINNED:raise ValueError("Workbook changed")
    with ZipFile(BytesIO(b)) as z:
        strings=[]
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall(f"{{{N}}}si"):
                strings.append("".join(t.text or "" for t in si.iter(f"{{{N}}}t")))
        root=ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
        out={}
        for row in root.findall(f".//{{{N}}}sheetData/{{{N}}}row"):
            data={}
            for cell in row.findall(f"{{{N}}}c"):
                v=cell.find(f"{{{N}}}v")
                val=(v.text or "") if v is not None else ""
                if cell.get("t")=="s" and val.isdigit():val=strings[int(val)]
                if cell.get("t")=="inlineStr":val="".join(t.text or "" for t in cell.iter(f"{{{N}}}t"))
                if val:data[re.sub(r"\d","",cell.get("r"))]=val
            out[int(row.get("r"))]=data
        return out

def clean_river_label(v):
    v=str(v).strip()
    # The official workbook appends reading in Katakana without separators,
    # e.g. 鶴見川ツルミガワ, 恩田川オンダカワ.
    stem=re.split(r"[\u30a1-\u30ff]",v,maxsplit=1)[0].strip()
    if re.fullmatch(r"[\u4e00-\u9fff々ヶぁ-んー]{1,15}",stem):
        return stem
    return None

def audit(out):
    data=read_data()
    basins=data[3];tributaries=data[4];dates=data[6]
    classcounts=Counter();confidence=Counter()
    column_positives=defaultdict(Counter)
    known_columns=set()
    for col,raw in tributaries.items():
        name=clean_river_label(raw)
        if name and re.search(r"(川|沢|谷|用水|水路|湧水)$",name):
            if clean_river_label(basins.get(col,"")):
                known_columns.add(col)
    for row in range(8,783):
        cells=data.get(row,{})
        classname=cells.get("A","")
        if not classname or not cells.get("F",""):continue
        confidence[cells.get("J","")]+=1
        classcounts[classname]+=1
        for col in known_columns:
            try:value=float(cells.get(col,"0"))
            except ValueError:continue
            if value>0:column_positives[(clean_river_label(basins[col]),clean_river_label(tributaries[col]))][classname]+=1
    report={
       "source_url":URL,"source_sha256":PINNED,
       "survey_method":"eDNA sequence reads; not capture and not a validated presence census",
       "workbook_data_rows":sum(bool(data.get(i,{}).get("F")) for i in range(8,783)),
       "survey_columns":len(basins)-1,
       "columns_with_explicit_tributary":len(known_columns),
       "unique_named_watershed_and_tributary_pairs":len(column_positives),
       "class_distribution_in_source_names":classcounts.most_common(25),
       "manual_name_confidence_field_distribution":confidence,
       "named_tributary_positive_counts_by_group":[{
          "watershed":a,"tributary":b,"groups":dict(v)
       } for (a,b),v in sorted(column_positives.items())][:120],
       "precise_locations_not_copied":True,
       "rivers_promoted_to_direct_observation":0
    }
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "records":report["workbook_data_rows"],
        "columns_with_explicit_tributary":report["columns_with_explicit_tributary"],
        "positive_pairs":len(column_positives),"major_classes":classcounts.most_common(16),
        "example_rivers":report["named_tributary_positive_counts_by_group"][:18]
    },ensure_ascii=False))
    return report

if __name__=="__main__":audit(sys.argv[1])
