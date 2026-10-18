#!/usr/bin/env python3
"""National verified river-edition PLANT name evidence, 9 regions, no station data.

The source ZIPs, workbook names and counts are pinned from independently
successful audit v2.4, and must match exactly. Outputs historical
(region, watershed, survey year, original plant label) only. Never treats a
watershed listing as an individual tributary location, species ID, or current
presence claim. Research-only artifact staging; no WordPress writes.
"""
import argparse
import csv
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
from zipfile import ZipFile

from audit_plant_sources_v26 import (
    audit, BASE, EXPECTED_CATEGORY, REGION_NUMBERS
)
from import_national_benthic_v19 import (
    excel_rows_benthic,source_verified_in_official_index,fetch,MAX_ZIP
)
from build_dataset_v23 import CSV_COLS,sha256_file

ROOT=Path(__file__).resolve().parent
PINS=ROOT/"plant_sources_v27.json"
STAGED=ROOT/"plants-staged"
REGIONS=tuple(REGION_NUMBERS)
HEX=re.compile(r"[0-9a-f]{64}\Z")
EXPECTED={"C":"生物項目","F":"水系","G":"調査年度","J":"種名"}

def pin(region,registry=PINS):
    config=json.loads(Path(registry).read_text(encoding="utf-8"))
    if config["publication_status"]!="research_only" or config["wordpress_modified"] is not False:
        raise ValueError("Unapproved published dataset")
    if config["checked_schema"]!=EXPECTED or config["original_category"]!="植物":
        raise ValueError("Unexpected plant original data category or columns")
    if len(config["regions"])!=9 or config["total_expected_unique_records"]!=270180:
        raise ValueError("Nine-region approved audit totals changed")
    entries={r["region"]:r for r in config["regions"]}
    if set(entries)!=set(REGIONS) or len(config["regions"])!=len(entries) or region not in entries:
        raise ValueError("Incomplete national plant archive registry")
    item=entries[region]
    expected_url=f"{BASE}RT{REGION_NUMBERS[region]}_B03.zip"
    if (item["source_url"]!=expected_url or not HEX.fullmatch(item["checksum_sha256"]) or
        not item["xlsx_member"].startswith(f"RT{REGION_NUMBERS[region]}_B03/") or
        not item["xlsx_member"].endswith(".xlsx") or
        item["expected_aggregated_records"]<100 or item["audited_source_rows"]<100):
        raise ValueError("Unapproved source reference")
    if sum(e["expected_aggregated_records"] for e in config["regions"])!=270180:
        raise ValueError("Original plant source audit totals do not reconcile")
    return item,config

def transform(region,raw,output=STAGED,registry=PINS):
    item,config=pin(region,registry)
    digest=hashlib.sha256(raw).hexdigest()
    if digest!=item["checksum_sha256"]:
        raise ValueError("Plant official ZIP changed; require new source audit and approval")
    actual=audit(region,raw)
    for key,expected in (
        ("source_sha256",digest),("xlsx_member",item["xlsx_member"]),
        ("official_category","植物"),
        ("original_source_rows",item["audited_source_rows"]),
        ("unique_watershed_year_literal_name_records",item["expected_aggregated_records"])):
        if actual[key]!=expected:
            raise ValueError("Plant original source audit mismatch: "+key)
    with ZipFile(BytesIO(raw)) as z:
        members=[m.filename for m in z.infolist() if not m.is_dir()]
        if members!=[item["xlsx_member"]]:
            raise ValueError("Workbook member changed")
    # Second pass reads only C/F/G/J, never site or coordinate columns.
    unique=set()
    for r in excel_rows_benthic(raw,item["xlsx_member"]):
        if r.get("C")!="植物":
            continue
        name=r.get("J","").strip();watershed=r.get("F","").strip()
        year=r.get("G","").strip()
        if (not name or not watershed or len(name)>150 or len(watershed)>80 or
            any(v[0] in "=+-@" for v in (name,watershed)) or
            not re.fullmatch(r"(?:19|20)[0-9]{2}",year) or year>"2026"):
            continue
        unique.add((watershed,year,name))
    if len(unique)!=item["expected_aggregated_records"]:
        raise ValueError("Imported plant tuples inconsistent with original audit")
    dest=Path(output)/region
    if dest.exists():
        raise FileExistsError("Never overwrite previous plant staged artifact")
    dest.mkdir(parents=True)
    csvpath=dest/"watershed_year_plants.csv"
    with csvpath.open("w",encoding="utf-8",newline="") as f:
        writer=csv.writer(f,lineterminator="\n")
        writer.writerow(CSV_COLS)
        for watershed,year,name in sorted(unique):
            writer.writerow((region,watershed,year,name,item["source_url"],digest))
    manifest={
        "region":region,"source_url":item["source_url"],
        "source_sha256":digest,"xlsx_member":item["xlsx_member"],
        "original_category":"植物",
        "source_rows":item["audited_source_rows"],
        "aggregated_records":len(unique),
        "staged_csv_sha256":sha256_file(csvpath),
        "source_index":config["verified_index_url"],
        "scope":"region_watershed_year_only",
        "stations_or_coordinates_extracted":False,
        "precise_important_species_locations_extracted":False,
        "approved_taxon_identity":False,
        "wordpress_modified":False,
        "status":"research_staged_only"
    }
    (dest/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return manifest

def read_stage(region,root=STAGED,registry=PINS):
    item,_=pin(region,registry)
    source=Path(root)/region
    manifest=json.loads((source/"manifest.json").read_text(encoding="utf-8"))
    file=source/"watershed_year_plants.csv"
    if (manifest["region"]!=region or manifest["source_url"]!=item["source_url"]
        or manifest["source_sha256"]!=item["checksum_sha256"]
        or manifest["xlsx_member"]!=item["xlsx_member"]
        or manifest["original_category"]!="植物"
        or manifest["status"]!="research_staged_only"
        or manifest["wordpress_modified"] is not False
        or manifest["stations_or_coordinates_extracted"] is not False
        or manifest["precise_important_species_locations_extracted"] is not False
        or manifest["approved_taxon_identity"] is not False
        or manifest["aggregated_records"]!=item["expected_aggregated_records"]
        or manifest["staged_csv_sha256"]!=sha256_file(file)):
        raise ValueError("Plant stage provenance mismatch")
    with file.open("r",encoding="utf-8",newline="") as f:
        reader=csv.DictReader(f)
        if tuple(reader.fieldnames or ())!=CSV_COLS:
            raise ValueError("Changed historical plant data schema")
        rows=list(reader)
    if len(rows)!=item["expected_aggregated_records"]:
        raise ValueError("Plant stage count mismatch")
    keys=set()
    for r in rows:
        if (r["region"]!=region or r["source_url"]!=item["source_url"] or
            r["source_sha256"]!=item["checksum_sha256"] or
            not r["watershed"] or not r["recorded_name"] or
            not re.fullmatch(r"(?:19|20)[0-9]{2}",r["survey_year"])):
            raise ValueError("Plant stage content inconsistent with pinned source")
        key=(r["watershed"],r["survey_year"],r["recorded_name"])
        if key in keys:raise ValueError("Duplicate water system/year/plant name")
        keys.add(key)
    return rows,manifest

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--region",required=True,choices=REGIONS)
    p.add_argument("--out",required=True)
    opts=p.parse_args()
    item,config=pin(opts.region)
    if not source_verified_in_official_index(item["source_url"],config["verified_index_url"]):
        raise ValueError("Pinned original plant archive removed from MLIT index")
    raw=fetch(item["source_url"],MAX_ZIP)
    manifest=transform(opts.region,raw,opts.out)
    rows,_=read_stage(opts.region,opts.out)
    print("PLANTS_STAGED_VERIFIED "+json.dumps({
        "region":opts.region,"unique_watershed_year_names":len(rows),
        "sha256":manifest["source_sha256"],"published":False
    },ensure_ascii=False))
if __name__=="__main__":
    main()
