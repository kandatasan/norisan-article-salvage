#!/usr/bin/env python3
"""Print workbook sheet layout and top rows from the NILIM RT87_B01 XLSX.
Only diagnostic output, no coordinates, no publication.
"""
from urllib.request import urlopen,Request
from io import BytesIO
from zipfile import ZipFile
import xml.etree.ElementTree as ET
from pathlib import PurePosixPath
import re

URL="https://www.nilim.go.jp/lab/fbg/ksnkankyo/download/slist/RT87_B01.zip"
M="{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL="{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PR="{http://schemas.openxmlformats.org/package/2006/relationships}"

def inspect_xlsx(data):
    with ZipFile(BytesIO(data)) as z:
        book=ET.fromstring(z.read("xl/workbook.xml"))
        relroot=ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        targets={el.get("Id"):el.get("Target") for el in relroot if el.tag==PR+"Relationship"}
        sheets=[(el.get("name"),el.get(REL+"id")) for el in book.iter(M+"sheet")]
        print("sheet_count:",len(sheets))
        print("sheets:",[name for name,_ in sheets][:70])
        strs=[]
        if "xl/sharedStrings.xml" in z.namelist():
            import io
            if z.getinfo("xl/sharedStrings.xml").file_size>100_000_000:raise ValueError("Shared strings too large")
            with z.open("xl/sharedStrings.xml") as fd:
                for event,el in ET.iterparse(fd,events=("end",)):
                    if el.tag==M+"si":
                        strs.append("".join((n.text or "") for n in el.iter(M+"t")))
                        el.clear()
            print("shared_string_count:",len(strs))
        for name,rid in sheets[:18]:
            target=targets.get(rid,"")
            if not target:continue
            path=target.lstrip("/") if target.startswith("/") else "xl/"+target
            path=str(PurePosixPath(path))
            if path not in z.namelist():
                print("missing sheet path",name,path);continue
            info=z.getinfo(path)
            print("SHEET",name,"xml_uncompressed:",info.file_size)
            if info.file_size>300_000_000:
                print("SKIP oversized sheet");continue
            shown=0
            with z.open(path) as fd:
                for event,el in ET.iterparse(fd,events=("end",)):
                    if el.tag!=M+"row":continue
                    i=int(el.get("r","0"))
                    cells=[]
                    for cell in el.iter(M+"c"):
                        label=cell.get("r");kind=cell.get("t","")
                        val=cell.findtext(M+"v")
                        if kind=="s" and val is not None and val.isdigit():
                            idx=int(val);val=strs[idx] if idx<len(strs) else f"(missing shared str {idx})"
                        if kind=="inlineStr":
                            val="".join(t.text or "" for t in cell.iter(M+"t"))
                        if val is None:continue
                        if i>5:
                            val="[masked]" # Preserve column positions, but avoid fine-grained occurrences
                        elif i>2 and (re.search("座標|緯度|経度|調査地点|詳細位置",str(val))):
                            val="[location header]"
                        cells.append(f"{label}:{str(val)[:35]}")
                    print("ROW",i,"|"," ".join(cells[:28])[:1500])
                    shown+=1
                    el.clear()
                    if shown>=7:break

def main():
    with urlopen(Request(URL,headers={"User-Agent":"tsurikue-research-probe/0.1"}),timeout=90) as f:
        outer=f.read(70_000_000)
    with ZipFile(BytesIO(outer)) as z:
        member=next((s for s in z.namelist() if s.lower().endswith(".xlsx")),None)
        if not member:raise ValueError("No xlsx in official ZIP")
        inner=z.read(member)
    print("official_xlsx_member:",member,"bytes:",len(inner))
    inspect_xlsx(inner)
if __name__=="__main__":main()
