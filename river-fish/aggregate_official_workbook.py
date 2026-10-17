#!/usr/bin/env python3
"""Aggregate NILIM fish observations safely: watershed × year × literal fish name.

NO station, coordinates, site, observation time, abundance, or prefecture inference.
The observed ZIP hash is pinned so a changed upstream file requires manual review.
"""
import csv
import hashlib
import json
import re
from io import BytesIO
from pathlib import Path
from urllib.request import Request,urlopen
from zipfile import ZipFile
import xml.etree.ElementTree as ET

SOURCE="https://www.nilim.go.jp/lab/fbg/ksnkankyo/download/slist/RT87_B01.zip"
EXPECTED_SHA256="1fd6a7201f3100164bc9921002b2723c04a9b6d1f55e0e773b957f6d97205f4e"
MEMBER="RT87_B01/魚類_中国.xlsx"
M="{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
HEADERS={"C":"生物項目","F":"水系","G":"調査年度","J":"種名"}
SOURCE_DESCRIPTION="国土交通省 河川水辺の国勢調査 中国地方・河川版・魚類"
OUTPUT="official_chugoku_watershed_year_fish_v05.csv"
MANIFEST="official_chugoku_manifest_v05.json"
LEGACY="official_chugoku_legacy_fish_candidates_v05.csv"

def get_official_zip():
    with urlopen(Request(SOURCE,headers={"User-Agent":"tsurikue-fish-database/0.5"}),timeout=90) as f:
        if f.status!=200 or f.url!=SOURCE:raise ValueError("Unexpected source or redirect")
        raw=f.read(75_000_001)
    if len(raw)>75_000_000:raise ValueError("ZIP too large")
    digest=hashlib.sha256(raw).hexdigest()
    if digest!=EXPECTED_SHA256:
        raise ValueError("Official ZIP changed. Reinspect source and update pinned hash with review.")
    return raw,digest

def excel_rows(zip_bytes):
    """Read ONLY the public book's specific columns using stdlib streaming XML."""
    with ZipFile(BytesIO(zip_bytes)) as outer:
        if MEMBER not in outer.namelist():raise ValueError("Unexpected workbook name")
        inner=outer.read(MEMBER)
    with ZipFile(BytesIO(inner)) as z:
        if "xl/sharedStrings.xml" not in z.namelist():raise ValueError("Missing string table")
        if z.getinfo("xl/worksheets/sheet1.xml").file_size>300_000_000:raise ValueError("Unexpected sheet size")
        strs=[]
        with z.open("xl/sharedStrings.xml") as f:
            for _,el in ET.iterparse(f,events=("end",)):
                if el.tag==M+"si":
                    strs.append("".join(x.text or "" for x in el.iter(M+"t")))
                    el.clear()
        first=True
        with z.open("xl/worksheets/sheet1.xml") as f:
            for _,row in ET.iterparse(f,events=("end",)):
                if row.tag!=M+"row":continue
                fields={}
                # Never even read location-specific columns into a Python record.
                for c in row.findall(M+"c"):
                    reference=c.get("r","")
                    col=re.match(r"^[A-Z]+",reference)
                    col=col.group(0) if col else ""
                    if col not in HEADERS:continue
                    val=c.findtext(M+"v") or ""
                    if c.get("t")=="s" and val.isdigit():
                        index=int(val)
                        val=strs[index] if index<len(strs) else ""
                    elif c.get("t")=="inlineStr":
                        val="".join(n.text or "" for n in c.iter(M+"t"))
                    fields[col]=val.strip()
                if first:
                    if fields!=HEADERS:
                        raise ValueError(f"Official schema changed; expected {HEADERS}, found {fields}")
                    first=False
                else:
                    yield fields
                row.clear()

def aggregate(records):
    unique=set()
    years=set()
    waters=set()
    names=set()
    input_rows=0
    skipped=0
    reasons={}
    def reject(reason):
        nonlocal skipped
        skipped+=1
        reasons[reason]=reasons.get(reason,0)+1
    for record in records:
        input_rows+=1
        if input_rows>1_000_000:raise ValueError("Unexpectedly large source")
        if record.get("C")=="魚介類":
            reject("mixed_fish_and_invertebrates_held_for_review");continue
        if record.get("C")!="魚類":
            reject("unrecognized_biological_category");continue
        water=record.get("F","").strip()
        year=record.get("G","").strip()
        name=record.get("J","").strip()
        if not water:
            reject("missing_watershed");continue
        if not name:
            reject("missing_species_name");continue
        if not re.fullmatch(r"(?:19|20)\d{2}",year):
            reject("invalid_or_missing_survey_year");continue
        if len(water)>80 or len(name)>150 or year>"2026":
            reject("unexpected_length_or_future_year");continue
        if any(x[0] in "=+-@" for x in (water,name)):
            reject("spreadsheet_formula_like_value");continue
        unique.add((water,year,name))
        waters.add(water);years.add(year);names.add(name)
    if input_rows<100 or not unique:raise ValueError("Source unexpectedly empty")
    ordered=sorted(unique,key=lambda x:(x[0],x[1],x[2]))
    return ordered,{"source_url":SOURCE,"source_title":SOURCE_DESCRIPTION,
        "source_sha256":EXPECTED_SHA256,"source_member":MEMBER,"source_sheet":"データ",
        "source_rows":input_rows,"unique_watersheds":len(waters),
        "distinct_name_labels":len(names),"years":sorted(years),
        "aggregated_records":len(ordered),"discarded_rows":skipped,
        "discarded_by_reason":reasons,
        "publication_status":"staged_not_published","prefecture_mapping":"not_inferred",
        "excluded_columns":"station, river section, distances, exact date/time, weather, abundance, site codes",
        "counting_rule":"one appearance per watershed x survey year x literal fish name",
        "important_species_note":"source provider excludes sensitive significant-species location records; absence is not absence in nature"}

def legacy_candidates(records,known_fish_labels):
    """Legacy '魚介類' label mixes fish and invertebrates; whitelist exact fish
    labels from unequivocal '魚類' records but keep separate, unapproved."""
    candidates=set()
    older_rows=0
    excluded=0
    for record in records:
        if record.get("C")!="魚介類":continue
        older_rows+=1
        water=record.get("F","").strip()
        name=record.get("J","").strip()
        year=record.get("G","").strip()
        if (not water or name not in known_fish_labels or
            not re.fullmatch(r"(?:19|20)\d{2}",year) or year>"2026" or
            len(water)>80 or len(name)>150 or
            any(x[0] in "=+-@" for x in (water,name))):
            excluded+=1
            continue
        candidates.add((water,year,name))
    return sorted(candidates),{
        "legacy_mixed_category_source_rows":older_rows,
        "legacy_name_matched_candidate_combinations":len(candidates),
        "legacy_rows_not_matched_or_invalid":excluded,
        "legacy_publication_status":"review_required_not_in_search",
        "legacy_criteria":"Exact name match against literal names already recorded with biological category 魚類"
    }


def export(folder,aggregated,manifest,legacy=()):
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    with (folder/OUTPUT).open("w",encoding="utf-8",newline="") as f:
        w=csv.writer(f)
        w.writerow(["watershed","survey_year","recorded_name","source_url","source_sha256"])
        for water,year,name in aggregated:
            w.writerow([water,year,name,SOURCE,EXPECTED_SHA256])
    with (folder/LEGACY).open("w",encoding="utf-8",newline="") as f:
        w=csv.writer(f)
        w.writerow(["watershed","survey_year","recorded_name","source_url","review_status"])
        for water,year,name in legacy:
            w.writerow([water,year,name,SOURCE,"unapproved_mixed_legacy_category"])
    (folder/MANIFEST).write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",default="river-fish")
    args=p.parse_args()
    raw,sha=get_official_zip()
    rows,manifest=aggregate(excel_rows(raw))
    legacy,legacy_stats=legacy_candidates(excel_rows(raw),{x[2] for x in rows})
    manifest.update(legacy_stats)
    export(args.output_dir,rows,manifest,legacy)
    print(json.dumps(manifest,ensure_ascii=False,indent=2))
