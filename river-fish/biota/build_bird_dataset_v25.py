#!/usr/bin/env python3
"""Merge approved bird staging into a NEW v2.3 immutable research dataset.

Existing 93,763 fish and benthic records are untouched. Birds are 44,093
official river-edition watershed/year/literal labels from nine SHA-locked ZIPs.
Creates a derived configuration and catalog, not a new hardcoded search engine.
"""
import argparse
import csv
import json
from pathlib import Path

from import_national_birds_v25 import REGIONS,read_stage,pin,PINS
from build_dataset_v23 import build as build_v23,sha256_file,CSV_COLS,REGISTRY

EXPECTED_TOTAL=44093
TOTAL_WITH_OLD=137856

def build(legacy_db,staged_dir,output_db,output_manifest,
          generated_dir,source_registry=REGISTRY,pins=PINS):
    generated_dir=Path(generated_dir).resolve()
    if generated_dir.exists():
        raise FileExistsError("Bird dataset build output must be new and isolated")
    if (Path(output_db).resolve()==generated_dir/"birds-audited.csv" or
        Path(output_manifest).resolve()==generated_dir/"registry-with-birds.json"):
        raise ValueError("Invalid output path")
    config=json.loads(Path(source_registry).read_text(encoding="utf-8"))
    if set(g["id"] for g in config["source_groups"])!={"fish","benthic_animals"}:
        raise ValueError("Unexpected previous vetted research survey groups")
    if config["publication_status"]!="research_only_not_wordpress":
        raise ValueError("No public dataset updates authorized")
    records=[]
    for region in REGIONS:
        rows,manifest=read_stage(region,staged_dir,pins)
        record,pin_config=pin(region,pins)
        if manifest["aggregated_records"]!=record["expected_aggregated_records"]:
            raise ValueError("Regional bird audit stage diverged")
        records.extend(rows)
    if len(records)!=EXPECTED_TOTAL:
        raise ValueError("Missing national bird regional staged surveys")
    keys={(r["region"],r["watershed"],r["survey_year"],r["recorded_name"]) for r in records}
    if len(keys)!=EXPECTED_TOTAL:
        raise ValueError("Duplicated national river bird survey entries")
    generated_dir.mkdir(parents=True)
    staged_csv=generated_dir/"birds-audited.csv"
    with staged_csv.open("w",encoding="utf-8",newline="") as f:
        writer=csv.writer(f,lineterminator="\n")
        writer.writerow(CSV_COLS)
        for r in records:
            writer.writerow(tuple(r[field] for field in CSV_COLS))
    if "birds" not in config["unavailable_separate_groups"]:
        raise ValueError("Bird group already enabled; migration requires manual review")
    config["unavailable_separate_groups"].pop("birds")
    config["source_groups"].append({
        "id":"birds","label":"鳥類",
        "note":"国土交通省河川水辺の国勢調査・河川版、地方×水系×年度×調査時点の鳥類掲載名",
        "kind":"verified_csv",
        "expected_rows":EXPECTED_TOTAL,
        "file":staged_csv.name,
        "sha256":sha256_file(staged_csv),
        "reviewed_original_category":"鳥類"
    })
    registry=generated_dir/"registry-with-birds.json"
    registry.write_text(json.dumps(config,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    status=build_v23(legacy_db,output_db,output_manifest,registry,generated_dir)
    if (status["group_counts"]!={"fish":18814,"benthic_animals":74949,"birds":EXPECTED_TOTAL}
        or status["total_survey_rows"]!=TOTAL_WITH_OLD):
        raise ValueError("Unexpected national data groups or counts after build")
    if status["wordpress_modified"] is not False:
        raise ValueError("Unexpected production change")
    return status

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--legacy-db",required=True)
    p.add_argument("--staged-dir",required=True)
    p.add_argument("--db",required=True)
    p.add_argument("--manifest",required=True)
    p.add_argument("--generated-dir",required=True)
    a=p.parse_args()
    print(json.dumps(build(a.legacy_db,a.staged_dir,a.db,a.manifest,a.generated_dir),
                     ensure_ascii=False,indent=2))
if __name__=="__main__":
    main()
