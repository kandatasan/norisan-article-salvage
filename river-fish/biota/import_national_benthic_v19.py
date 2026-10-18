#!/usr/bin/env python3
"""National MLIT river-version BENTHIC ANIMAL regional survey importer, v1.9.

Source-scope ONLY: region × watershed × year × literal recorded name.
No station, river section, location, taxon-ID, latitude, abundance, individual
river or prefecture are read or exported. Reject ambiguous biological labels.

Source ZIP and workbook member must exactly match separately audited official
download index and SHA256 (biota/benthic_sources_v19.json). All accepted rows
are biological category "底生動物" ONLY; do not merge historical mixed "魚介類".
"""
import argparse
from collections import Counter
import csv
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parent
RIVER_ROOT=ROOT.parent
import sys
sys.path.insert(0,str(RIVER_ROOT))
import xml.etree.ElementTree as ET

M="{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
APPROVED_COLUMNS={"C":"生物項目","F":"水系","G":"調査年度","J":"種名"}
MAX_UNCOMPRESSED_SHEET=1_800_000_000

def excel_rows_benthic(zip_bytes, member):
    """Bounded streaming parser for large approved official bottom-animal XML.

    The existing fish parser deliberately retains a 300MB max sheet limit;
    DO NOT alter it. All ZIP hashes are pinned separately before this call.
    """
    with ZipFile(BytesIO(zip_bytes)) as outer:
        meta=outer.getinfo(member)
        if meta.file_size<=0 or meta.file_size>220_000_000:
            raise ValueError("Unexpected source workbook size")
        raw=outer.read(member)
    with ZipFile(BytesIO(raw)) as workbook:
        sh=workbook.getinfo("xl/worksheets/sheet1.xml")
        if sh.file_size>MAX_UNCOMPRESSED_SHEET:
            raise ValueError("Large XML sheet exceeds reviewed stream bound: "+str(sh.file_size))
        shared=[]
        with workbook.open("xl/sharedStrings.xml") as f:
            context=ET.iterparse(f,events=("start","end"))
            _,root=next(context)
            for ev,e in context:
                if ev=="end" and e.tag==M+"si":
                    shared.append("".join(t.text or "" for t in e.iter(M+"t")))
                    e.clear()
                    root.clear()
        first=True
        with workbook.open("xl/worksheets/sheet1.xml") as stream:
            context=ET.iterparse(stream,events=("start","end"))
            _,root=next(context)
            for ev,row in context:
                if ev!="end" or row.tag!=M+"row":continue
                values={}
                for c in row.findall(M+"c"):
                    ref=c.get("r","")
                    col=re.match(r"^([A-Z]+)",ref)
                    name=col.group(1) if col else ""
                    if name not in APPROVED_COLUMNS:continue
                    txt=c.findtext(M+"v") or ""
                    if c.get("t")=="s" and txt.isdecimal():
                        index=int(txt)
                        if index>=len(shared):raise ValueError("Unknown shared-string index")
                        txt=shared[index]
                    elif c.get("t")=="inlineStr":
                        txt="".join(t.text or "" for t in c.iter(M+"t"))
                    values[name]=txt.strip()
                if first:
                    if values!=APPROVED_COLUMNS:
                        raise ValueError("Bottom-animal schema changed; stop source import")
                    first=False
                else:
                    yield values
                row.clear()
                root.clear()
        if first:raise ValueError("Empty biological observation sheet")

from inspect_nationwide_source_v06 import fetch,source_verified_in_official_index,MAX_ZIP

PINS=ROOT/"benthic_sources_v19.json"
BASE=ROOT/"benthic-staged"
CSV_NAME="watershed_year_benthic.csv"
CSV_HEADER=["region","watershed","survey_year","recorded_name","source_url","source_sha256"]
VALID_REGIONS=("hokkaido","tohoku","kanto","hokuriku","chubu","kinki","chugoku","shikoku","kyushu")

def pin(region,registry=PINS):
    p=json.loads(Path(registry).read_text(encoding="utf-8"))
    if not p["public_site_status"]=="research_only" or p["wordpress_modified"] is not False:
        raise ValueError("Research stage must not publish")
    if len(p["regions"])!=9:
        raise ValueError("Missing regional benthic sources")
    if len({x["region"] for x in p["regions"]})!=9:
        raise ValueError("Duplicate region labels")
    items={x["region"]:x for x in p["regions"]}
    if region not in VALID_REGIONS or region not in items:
        raise ValueError("Unsupported source region")
    entry=items[region]
    if entry["checked_schema"]!={"C":"生物項目","F":"水系","G":"調査年度","J":"種名"}:
        raise ValueError("Review original workbook headers again")
    if (not re.fullmatch(r"[0-9a-f]{64}",entry["checksum_sha256"])
        or not re.fullmatch(r"https://www\.nilim\.go\.jp/lab/fbg/ksnkankyo/download/slist/RT8[1-9]_B02\.zip",entry["source_url"])
        or "底生_" not in entry["xlsx_member"]):
        raise ValueError("Source URL/member/hash unverified")
    return entry,p

def aggregate_benthic(rows,max_source_rows=1_500_000):
    unique=set();discard=Counter();labels=Counter()
    source_rows=0;accepted_source_rows=0
    for r in rows:
        source_rows+=1
        if source_rows>max_source_rows:raise ValueError("Large unexpected source: review required")
        cat=r.get("C","")
        if cat!="底生動物":
            labels[cat or "<empty>"]+=1
            discard["not_explicit_benthic_category"]+=1
            continue
        watershed=r.get("F","").strip()
        year=r.get("G","").strip()
        literal=r.get("J","").strip()
        if not watershed or not literal:
            discard["no_watershed_or_name"]+=1;continue
        if (len(watershed)>80 or len(literal)>150 or
            any(x[0] in "=+-@" for x in (watershed,literal))):
            discard["unsafe_or_oversize_label"]+=1;continue
        if not re.fullmatch(r"(?:19|20)[0-9]{2}",year) or year>"2026":
            discard["invalid_survey_year"]+=1;continue
        accepted_source_rows+=1
        unique.add((watershed,year,literal))
    if source_rows<100 or accepted_source_rows<100 or not unique:
        raise ValueError("Official benthic data unexpectedly empty")
    return sorted(unique),{
        "source_rows":source_rows,"accepted_raw_benthic_source_rows":accepted_source_rows,
        "unique_watersheds":len({r[0] for r in unique}),
        "distinct_literal_names_not_species":len({r[2] for r in unique}),
        "survey_years":sorted({r[1] for r in unique}),
        "aggregated_records":len(unique),
        "excluded_source_rows":sum(discard.values()),
        "excluded_by_reason":dict(discard),
        "other_biological_category_labels_not_imported":dict(labels)
    }

def transform(region,raw,output=BASE):
    info,index=pin(region)
    digest=hashlib.sha256(raw).hexdigest()
    if digest!=info["checksum_sha256"]:raise ValueError("Official source has changed; re-audit")
    with ZipFile(BytesIO(raw)) as z:
        members=[o.filename for o in z.infolist() if not o.is_dir()]
        if members!=[info["xlsx_member"]]:raise ValueError("Official workbook member changed")
    aggregate,stats=aggregate_benthic(excel_rows_benthic(raw,member=info["xlsx_member"]))
    output=Path(output)/region
    output.mkdir(parents=True,exist_ok=True)
    file=output/CSV_NAME
    with file.open("w",encoding="utf-8",newline="") as f:
        writer=csv.writer(f,lineterminator="\n")
        writer.writerow(CSV_HEADER)
        for watershed,year,name in aggregate:
            writer.writerow([region,watershed,year,name,info["source_url"],digest])
    stats.update({
      "region":region,"official_region":info["official_region"],
      "biological_item":"底生動物","source_url":info["source_url"],
      "source_sha256":digest,"source_xlsx_member":info["xlsx_member"],
      "source_index":index["verified_index_url"],
      "staged_csv_sha256":hashlib.sha256(file.read_bytes()).hexdigest(),
      "geographic_scope":"regional_watershed_year_not_specific_river_or_prefecture",
      "taxon_name_identity":"literal_name_only_not_verified_current_taxonomy",
      "source_taxon_group":"benthic_animals_not_individually_classified_as_crab_or_shrimp",
      "direct_individual_river_observations":0,
      "precise_observation_locations":0,
      "historical_legacy_mixed_records_included":0,
      "wordpress_modified":False,"status":"staged_research_only"
    })
    (output/"manifest.json").write_text(json.dumps(stats,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return stats

def read_stage(region,root=BASE):
    info,_=pin(region)
    p=Path(root)/region
    m=json.loads((p/"manifest.json").read_text(encoding="utf-8"))
    file=p/CSV_NAME
    if (m["region"]!=region or m["source_url"]!=info["source_url"]
        or m["source_sha256"]!=info["checksum_sha256"]
        or m["status"]!="staged_research_only"
        or m["wordpress_modified"] is not False
        or m["precise_observation_locations"]!=0
        or m["direct_individual_river_observations"]!=0
        or hashlib.sha256(file.read_bytes()).hexdigest()!=m["staged_csv_sha256"]):
        raise ValueError("Stage provenance or privacy contract changed")
    with file.open(encoding="utf-8",newline="") as f:
        rd=csv.DictReader(f)
        if rd.fieldnames!=CSV_HEADER:raise ValueError("Unexpected staged bottom-fauna schema")
        rows=list(rd)
    keys=set()
    for r in rows:
        if (r["region"]!=region or r["source_url"]!=m["source_url"]
            or r["source_sha256"]!=m["source_sha256"]
            or not r["recorded_name"] or not r["watershed"]
            or not re.fullmatch(r"(?:19|20)\d{2}",r["survey_year"])):
            raise ValueError("Invalid benthic regional source stage")
        key=(r["watershed"],r["survey_year"],r["recorded_name"])
        if key in keys:raise ValueError("Duplicated regional watershed-year-name")
        keys.add(key)
    if len(rows)!=m["aggregated_records"] or len(keys)!=len(rows):
        raise ValueError("Benthic manifest does not match actual data")
    return rows,m

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--region",required=True,choices=VALID_REGIONS)
    p.add_argument("--out",default=str(BASE))
    a=p.parse_args()
    info,index=pin(a.region)
    if not source_verified_in_official_index(info["source_url"],index["verified_index_url"]):
        raise ValueError("MLIT download index no longer provides this file")
    raw=fetch(info["source_url"],MAX_ZIP)
    m=transform(a.region,raw,a.out)
    rows,_=read_stage(a.region,a.out)
    if len(rows)!=m["aggregated_records"]:raise ValueError("Import verification failed")
    print("BENTHIC_STAGED "+json.dumps({"region":a.region,"source_rows":m["source_rows"],
       "records":len(rows),"unique_names":m["distinct_literal_names_not_species"],
       "watersheds":m["unique_watersheds"],"not_imported":m["excluded_by_reason"]},ensure_ascii=False))

if __name__=="__main__":
    main()
