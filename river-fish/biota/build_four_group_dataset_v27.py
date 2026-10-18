#!/usr/bin/env python3
"""v2.7: add audited national PLANTS to verified fish, benthic and bird data.

All additional groups arrive as verified CSV files in an immutable dataset.
The v2.3 generic search engine and frontend are UNCHANGED.
"""
import argparse
import csv
import json
from pathlib import Path

from build_dataset_v23 import build as build_dataset, sha256_file, CSV_COLS, REGISTRY
from import_national_birds_v25 import REGIONS, read_stage as read_bird, pin as bird_pin, PINS as BIRD_PINS
from import_national_plants_v27 import read_stage as read_plant, pin as plant_pin, PINS as PLANT_PINS

BIRDS=44093
PLANTS=270180
TOTAL=408036

def stage_collection(regions, reader, checker, root, staged_path, expected):
    records=[]
    for region in regions:
        part,manifest=reader(region,root,checker)
        original,_=checker_for(region,checker,checker_kind="birds" if expected==BIRDS else "plants")
        if (manifest["aggregated_records"]!=original["expected_aggregated_records"]
            or manifest["source_sha256"]!=original["checksum_sha256"]):
            raise ValueError("Official survey stage diverges from pinned archive")
        records.extend(part)
    if len(records)!=expected:
        raise ValueError("Nationwide biological category has missing staged rows")
    keyset={(r["region"],r["watershed"],r["survey_year"],r["recorded_name"]) for r in records}
    if len(keyset)!=expected:
        raise ValueError("Duplicate official watershed/year/name research tuples")
    with Path(staged_path).open("w",encoding="utf-8",newline="") as handle:
        writer=csv.writer(handle,lineterminator="\n")
        writer.writerow(CSV_COLS)
        for record in records:
            writer.writerow([record[x] for x in CSV_COLS])
    return sha256_file(staged_path)

def checker_for(region,path,checker_kind):
    return bird_pin(region,path) if checker_kind=="birds" else plant_pin(region,path)

def build(legacy_db,birds_root,plants_root,output_db,output_manifest,
          generated_dir,source_registry=REGISTRY,birds_pins=BIRD_PINS,plants_pins=PLANT_PINS):
    generated_dir=Path(generated_dir).resolve()
    if generated_dir.exists():
        raise FileExistsError("Never overwrite previously generated survey data files")
    if any(Path(x).resolve().is_relative_to(generated_dir) for x in (legacy_db, birds_root, plants_root)):
        raise ValueError("Source input cannot be inside the output folder")
    config=json.loads(Path(source_registry).read_text(encoding="utf-8"))
    if (config["publication_status"]!="research_only_not_wordpress" or
        config["taxonomy_identity_verified"] is not False or
        {g["id"] for g in config["source_groups"]}!={"fish","benthic_animals"} or
        len(config["source_groups"])!=2):
        raise ValueError("Unexpected baseline survey registry or publication boundary")
    generated_dir.mkdir(parents=True)
    for item,root,reader,pins,count,label,note in (
        ("birds",birds_root,read_bird,birds_pins,BIRDS,"鳥類","監査済み河川版鳥類・水系×年度×当時の掲載名"),
        ("plants",plants_root,read_plant,plants_pins,PLANTS,"植物","監査済み河川版植物・水系×年度×当時の掲載名")
    ):
        file=generated_dir/(item+"-audited.csv")
        source_hash=stage_collection(REGIONS,reader,pins,root,file,count)
        if item in config["unavailable_separate_groups"]:
            config["unavailable_separate_groups"].pop(item)
        config["source_groups"].append({
            "id":item,"label":label,"note":note,
            "kind":"verified_csv","expected_rows":count,"file":file.name,
            "sha256":source_hash,"reviewed_original_category":label
        })
    registry=generated_dir/"registry-four-groups.json"
    registry.write_text(json.dumps(config,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    result=build_dataset(legacy_db,output_db,output_manifest,registry,generated_dir)
    required={"fish":18814,"benthic_animals":74949,"birds":BIRDS,"plants":PLANTS}
    if (result["group_counts"]!=required or result["total_survey_rows"]!=TOTAL or
        result["wordpress_modified"] is not False or result["individual_river_verified"] is not False
        or result["taxonomy_identity_verified"] is not False):
        raise ValueError("Independent nationwide group counts or safety boundary changed")
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--legacy-db",required=True)
    p.add_argument("--birds-staged",required=True)
    p.add_argument("--plants-staged",required=True)
    p.add_argument("--db",required=True)
    p.add_argument("--manifest",required=True)
    p.add_argument("--generated-dir",required=True)
    a=p.parse_args()
    print(json.dumps(build(a.legacy_db,a.birds_staged,a.plants_staged,a.db,a.manifest,a.generated_dir),
                     ensure_ascii=False,indent=2))
if __name__=="__main__":
    main()
