#!/usr/bin/env python3
"""Nationwide official fish survey import, one region at a time.

Input: verified MLIT regional fish ZIP containing one XLSX file.
Output: ONLY watershed × fiscal year × literal fish-name records and
      separately quarantined mixed-category candidates.
No detailed locations, coordinates, stations, distances, abundance or dates.
All 9 sources are checksum-pinned. Refuse unexpected schema and changed sources.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO

from aggregate_official_workbook import excel_rows, aggregate, legacy_candidates
from inspect_nationwide_source_v06 import fetch, source_verified_in_official_index, MAX_ZIP

HERE=Path(__file__).resolve().parent
CONF=HERE/"nationwide_sources_v06.json"
STAGED="nationwide-staged"
FISH_HEADER=["region","watershed","survey_year","recorded_name","source_url","source_sha256"]
LEGACY_HEADER=["region","watershed","survey_year","recorded_name","review_status"]

def get_region(region,registry=CONF):
    d=json.loads(Path(registry).read_text(encoding="utf-8"))
    regions={x["region_id"]:x for x in d["region_sources"]}
    if region not in regions:raise ValueError("Unrecognized official region")
    candidate=regions[region]
    if candidate.get("checked_schema")!={"C":"生物項目","F":"水系","G":"調査年度","J":"種名"}:
        raise RuntimeError("Column mapping not verified")
    if not candidate.get("checksum_sha256") or len(candidate["checksum_sha256"])!=64:
        raise RuntimeError("Source checksum not approved")
    return candidate,d["verified_index_url"]

def compute_one_region(region,output_root,zip_bytes,source_data):
    """Pure transformation of already verified source. No internet operations."""
    expected_hash=source_data["checksum_sha256"]
    observed_hash=hashlib.sha256(zip_bytes).hexdigest()
    if observed_hash!=expected_hash:raise ValueError("Official ZIP hash mismatch")
    with ZipFile(BytesIO(zip_bytes)) as z:
        xlsx=[x for x in z.namelist() if x.lower().endswith(".xlsx")]
        if xlsx!=[source_data["xlsx_member"]]:
            raise ValueError("Unexpected workbook member(s) in official archive")
    main_rows,base_manifest=aggregate(excel_rows(zip_bytes,member=source_data["xlsx_member"]))
    known_names={name for _,_,name in main_rows}
    held,held_report=legacy_candidates(excel_rows(zip_bytes,member=source_data["xlsx_member"]),known_names)
    base_manifest.update(held_report)
    base_manifest.update({
        "region":region,"official_region":source_data["official_region"],
        "source_url":source_data["source_url"],
        "source_sha256":observed_hash,
        "source_member":source_data["xlsx_member"],
        "counting_rule":"unique region x watershed x survey_year x literal recorded_name",
        "geography_scope":"nationally surveyed river segments; no specific observation location",
        "prefecture_mapping":"not_inferred",
        "direct_river_mapping":"not_inferred",
        "sensitive_fields_excluded":["site","station","river_name","district","subreach",
                                     "precise_survey_date","distance","coordinate","abundance"],
        "status":"staged_not_published",
    })
    root=Path(output_root)/region
    root.mkdir(parents=True,exist_ok=True)
    with (root/"watershed_year_fish.csv").open("w",encoding="utf-8",newline="") as f:
        w=csv.writer(f);w.writerow(FISH_HEADER)
        for water,year,name in main_rows:
            w.writerow([region,water,year,name,source_data["source_url"],observed_hash])
    with (root/"legacy_mixed_category_candidates.csv").open("w",encoding="utf-8",newline="") as f:
        w=csv.writer(f);w.writerow(LEGACY_HEADER)
        for water,year,name in held:
            w.writerow([region,water,year,name,"review_required_not_searchable"])
    (root/"manifest.json").write_text(json.dumps(base_manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return {"region":region,"manifest":base_manifest,"output_dir":str(root)}

def audit_output(out_root,region):
    path=Path(out_root)/region
    manifest=json.loads((path/"manifest.json").read_text(encoding="utf-8"))
    with (path/"watershed_year_fish.csv").open("r",encoding="utf-8",newline="") as fd:
        reader=csv.DictReader(fd)
        if reader.fieldnames!=FISH_HEADER:raise ValueError("Unexpected staged fish schema")
        rows=list(reader)
    with (path/"legacy_mixed_category_candidates.csv").open("r",encoding="utf-8",newline="") as fd:
        r=csv.DictReader(fd)
        if r.fieldnames!=LEGACY_HEADER:raise ValueError("Unexpected legacy schema")
        held=list(r)
    keys={(r["region"],r["watershed"],r["survey_year"],r["recorded_name"]) for r in rows}
    held_keys={(r["region"],r["watershed"],r["survey_year"],r["recorded_name"]) for r in held}
    if (not rows or len(rows)!=len(keys) or len(held)!=len(held_keys)
        or len(rows)!=manifest["aggregated_records"]
        or len(held)!=manifest["legacy_name_matched_candidate_combinations"]):
        raise ValueError("Staged row count or uniqueness mismatch")
    if not all(r["region"]==region and r["source_sha256"]==manifest["source_sha256"] for r in rows):
        raise ValueError("Incorrect source provenance or mixed region")
    if not all(r["review_status"]=="review_required_not_searchable" for r in held):
        raise ValueError("Legacy records not properly quarantined")
    if manifest["status"]!="staged_not_published" or manifest["prefecture_mapping"]!="not_inferred":
        raise ValueError("Unsafe public status or geography")
    if any("prefecture" in r or "district" in r or "station" in r for r in rows):
        raise ValueError("Sensitive or inferred per-record fields")
    return {"region":region,"verified_fish_rows":len(rows),"held_for_review":len(held),
            "watersheds":manifest["unique_watersheds"],"literal_fish_name_labels":manifest["distinct_name_labels"],
            "earliest_year":min(manifest["years"]),"latest_year":max(manifest["years"])}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--region",required=True)
    p.add_argument("--out",required=True)
    opts=p.parse_args()
    source,index=get_region(opts.region)
    if not source_verified_in_official_index(source["source_url"],index):
        raise RuntimeError("Official index no longer advertises this source")
    payload=fetch(source["source_url"],MAX_ZIP)
    result=compute_one_region(opts.region,opts.out,payload,source)
    summary=audit_output(opts.out,opts.region)
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return summary

if __name__=="__main__":
    main()
