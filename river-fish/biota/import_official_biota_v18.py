#!/usr/bin/env python3
"""Import MLIT 2025 all-organism reference list as literal TAXON NAME ROWS.

This is a TAXONOMY REFERENCE, not evidence of organism presence in a river,
prefecture or even Japan. The workbook includes named taxa above species rank,
historical names and identification entries. Do not call every row "a species".

Source: 令和7年度 河川水辺の国勢調査 全生物種 (2025-10-10;
2025-11-27 fish amendment), URL in SOURCE_URL below.
2026 plankton-only list is a separate reference, NOT substituted silently.

No biological observation sites, coordinates, protected species localities,
photos or maps are downloaded. Uses standard-library XLSX XML to extract
only explicit literal classification columns with minimal dependencies.
"""
from collections import Counter
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import unicodedata
from urllib.request import Request,urlopen
import xml.etree.ElementTree as ET
from zipfile import ZipFile

SOURCE_URL=("https://www.nilim.go.jp/lab/fbg/ksnkankyo/"
            "mizukokuweb/system/DownLoad/List/R07List/R07zenseibutsu.xlsx")
SOURCE_INDEX="https://www.nilim.go.jp/lab/fbg/ksnkankyo/mizukokuweb/system/seibutsuListfile.htm"
SOURCE_TERMS="https://www.nilim.go.jp/lab/fbg/ksnkankyo/Mokj_chui.htm"
NS="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
M="{"+NS+"}"
CATEGORIES={
    "AC":"fish", "AD":"benthic_animals", "AE":"plants",
    "AF":"birds", "AG":"amphibians_reptiles_mammals",
    "AH":"terrestrial_insects", "AI":"plankton",
}
FIELDS=[
    "source_row","official_taxon_code","japanese_name","scientific_name",
    "phylum_japanese","phylum_scientific",
    "class_japanese","class_scientific",
    "order_japanese","order_scientific",
    "family_japanese","family_scientific",
    "genus_japanese","genus_scientific",
    "fish","benthic_animals","plants","birds",
    "amphibians_reptiles_mammals","terrestrial_insects","plankton",
    "evidence_kind"
]
EXPECTED_HEADER={
    "B":"門和名","C":"門","H":"綱和名","I":"綱",
    "N":"目和名","O":"目","Q":"科和名","R":"科",
    "W":"属和名","X":"属","Y":"種コード","Z":"学名",
    "AA":"種和名","AC":"魚類","AD":"底生","AE":"植物",
    "AF":"鳥類","AG":"両爬哺","AH":"昆虫","AI":"プランクトン",
}
FIELDS_FROM_CELLS={
    "official_taxon_code":"Y","japanese_name":"AA","scientific_name":"Z",
    "phylum_japanese":"B","phylum_scientific":"C",
    "class_japanese":"H","class_scientific":"I",
    "order_japanese":"N","order_scientific":"O",
    "family_japanese":"Q","family_scientific":"R",
    "genus_japanese":"W","genus_scientific":"X"
}

def fetch_official(timeout=80):
    req=Request(SOURCE_URL,headers={"User-Agent":"TsurikueBiotaResearch/1.0"})
    with urlopen(req,timeout=timeout) as resp:
        data=resp.read(16*1024*1024)
    if len(data)<100_000 or len(data)>=16*1024*1024:
        raise ValueError("Unexpected official taxonomy workbook size")
    return data

def xlsx_rows(raw):
    """Read literal Excel cells, preserve sparse A1 column positions."""
    z=ZipFile(io.BytesIO(raw))
    names=z.namelist()
    if ("xl/worksheets/sheet1.xml" not in names or
        any(name.endswith("externalLinks/externalLink1.xml") for name in names)):
        raise ValueError("Unexpected or externally linked taxonomy workbook")
    shared=[]
    if "xl/sharedStrings.xml" in names:
        root=ET.fromstring(z.read("xl/sharedStrings.xml"))
        shared=["".join(t.text or "" for t in e.iter(M+"t")) for e in root.findall(M+"si")]
    with z.open("xl/worksheets/sheet1.xml") as stream:
        for event,row in ET.iterparse(stream,events=("end",)):
            if row.tag!=M+"row":
                continue
            out={}
            for cell in row.findall(M+"c"):
                m=re.match(r"^([A-Z]{1,3})([0-9]+)$",cell.get("r",""))
                if not m:continue
                col=m.group(1)
                value=cell.find(M+"v")
                inline=cell.find(M+"is")
                if value is not None and value.text is not None:
                    txt=value.text
                    if cell.get("t")=="s":
                        txt=shared[int(txt)]
                elif inline is not None:
                    txt="".join(t.text or "" for t in inline.iter(M+"t"))
                else:
                    txt=""
                out[col]=str(txt).strip()
            yield int(row.get("r")),out
            row.clear()

def import_workbook(raw):
    seen=set();records=[];cats=Counter();structural_rows=0
    for rowno,cells in xlsx_rows(raw):
        if rowno==1:
            for col,title in EXPECTED_HEADER.items():
                if cells.get(col)!=title:
                    raise ValueError(f"Official taxonomy header {col} changed: {cells.get(col)} != {title}")
            continue
        if rowno<2:continue
        if rowno in seen:raise ValueError("Duplicate row index")
        seen.add(rowno)
        if not cells.get("Y"):
            # The official all-organism workbook includes structural grouping
            # rows. They show higher taxonomy but no individual taxon ID/name.
            # Do not invent a species entry for those separators.
            if cells.get("AA") or cells.get("Z"):
                raise ValueError(f"Uncoded organism label requires human review: row {rowno}")
            structural_rows+=1
            continue
        if not (cells.get("AA") or cells.get("Z")):
            raise ValueError(f"Taxon code without either literal scientific or Japanese name: row {rowno}")
        flags={label:1 if cells.get(col)=="●" else 0 for col,label in CATEGORIES.items()}
        for col,label in CATEGORIES.items():
            if cells.get(col,"") not in ("","●"):
                raise ValueError(f"Unexpected label in {label}/{rowno}: {cells.get(col)}")
        info={"source_row":rowno,"evidence_kind":"2025_official_taxon_reference_not_observation"}
        info.update({out:cells.get(col,"") for out,col in FIELDS_FROM_CELLS.items()})
        info.update(flags)
        records.append(info)
        cats.update({name:1 for name,has in flags.items() if has})
    if len(records)+structural_rows!=37812 or len(seen)!=37812:
        raise ValueError("Official 2025 taxonomy source changed; re-audit before ingest")
    return records,cats,structural_rows

def write_staged(raw,output,manifest_path):
    rows,category_count,structural=import_workbook(raw)
    output=Path(output);manifest_path=Path(manifest_path)
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS,lineterminator="\n",quoting=csv.QUOTE_MINIMAL)
        writer.writeheader();writer.writerows(rows)
    reference_names=len(set(x["japanese_name"] for x in rows))
    id_pairs=len(set((x["official_taxon_code"],x["japanese_name"]) for x in rows))
    manifest={
        "edition":"2025_reference_only",
        "source_url":SOURCE_URL,
        "source_index":SOURCE_INDEX,
        "usage_terms":SOURCE_TERMS,
        "official_version_note":"2025-10-10 list; fish list revised 2025-11-27. 2026 plankton revision not yet applied",
        "source_workbook_sha256":hashlib.sha256(raw).hexdigest(),
        "staged_csv_sha256":hashlib.sha256(output.read_bytes()).hexdigest(),
        "source_workbook_data_rows_including_structural":37812,
        "excluded_structural_rows_without_taxon_code":structural,
        "reference_rows":len(rows),
        "distinct_japanese_labels_not_species_count":reference_names,
        "distinct_taxon_code_and_literal_name_pairs":id_pairs,
        "category_membership_counts_not_distinct_species":dict(category_count),
        "sensitive_locations_in_data":False,
        "contains_species_occurrence_or_river_presence":False,
        "publication_status":"research_only_not_wordpress",
        "note":"Official list rows may include genus/complex/higher-rank entries; some organisms occur in multiple survey groups. Empty species observation is not absence."
    }
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return manifest

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--download",action="store_true")
    p.add_argument("--xlsx",default="")
    p.add_argument("--output",required=True)
    p.add_argument("--manifest",required=True)
    args=p.parse_args()
    if args.download==bool(args.xlsx):
        raise ValueError("Select exactly --download or --xlsx")
    raw=fetch_official() if args.download else Path(args.xlsx).read_bytes()
    stats=write_staged(raw,args.output,args.manifest)
    print(json.dumps(stats,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
