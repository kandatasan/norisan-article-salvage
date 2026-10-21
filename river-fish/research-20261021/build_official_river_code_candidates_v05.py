#!/usr/bin/env python3
"""Triangulate source-named fish survey rivers against MLIT national river CODE LIST.

REVIEW ONLY. Exact source watershed+river name is a candidate, not verified
identity. Code prefix is NOT prefecture. Do not publish fish labels or locations.
"""
from __future__ import annotations
import argparse
import collections
import csv
import json
from pathlib import Path

from extract_official_named_river_fish_nationwide_v04 import (
    FIELDS as SOURCE_FIELDS, REGIONS, manifest_for, validate_manifest
)

ROOT = Path(__file__).resolve().parent.parent / "national-codes-staged"
RIVER_HEADER = ("river_code", "river_name", "watershed_code", "watershed_name",
                "code_region_prefix", "source_url", "identity_status", "site_status")
WATER_HEADER = ("watershed_code", "watershed_name", "code_region_prefix",
                "source_url", "identity_status")
SOURCE_RIVER_URL = "https://nlftp.mlit.go.jp/ksj/gml/codelist/RiverCodeCd.html"
SOURCE_WATER_URL = "https://nlftp.mlit.go.jp/ksj/gml/codelist/WaterSystemCodeCd.html"
SCHEMA = "tsurikue-official-direct-river-national-code-candidates-v05"


def basin(value):
    value = str(value or "").strip()
    return value[:-2] if value.endswith("水系") else value


def read_csv(path, header, max_rows):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if tuple(reader.fieldnames or ()) != tuple(header):
            raise ValueError(f"Unexpected header: {path}")
        rows = []
        for row in reader:
            if set(row) != set(header) or not all(isinstance(v, str) for v in row.values()):
                raise ValueError("Bad CSV record")
            rows.append(row)
            if len(rows) > max_rows:
                raise ValueError("Unexpectedly large input CSV")
        return rows


def load_codes(root=ROOT):
    meta = json.loads((root / "river_code_manifest_v07.json").read_text(encoding="utf-8"))
    if (meta.get("river_code_rows") != 35449 or
            meta.get("watershed_code_rows") != 5475 or
            meta.get("prefecture_mapping") != "not_inferred" or
            meta.get("direct_species") != "not_inferred" or
            meta.get("publication_status") != "research_only_not_website_deployed" or
            meta.get("no_W05_geometries") is not True):
        raise ValueError("National code manifest changed: manual audit required")
    rivers = read_csv(root / "river_codes_national_v07.csv", RIVER_HEADER, 35500)
    waters = read_csv(root / "watershed_codes_national_v07.csv", WATER_HEADER, 5500)
    if len(rivers) != meta["river_code_rows"] or len(waters) != meta["watershed_code_rows"]:
        raise ValueError("National code list count mismatch")
    by_ws = {}
    for w in waters:
        code = w["watershed_code"]
        if (len(code) != 6 or not code.isascii() or not code.isdecimal()
                or w["source_url"] != SOURCE_WATER_URL
                or w["identity_status"] != "coded_watershed_name_only"
                or code in by_ws):
            raise ValueError("Invalid watershed code row")
        by_ws[code] = w["watershed_name"]
    by_code = {}
    for r in rivers:
        code = r["river_code"]
        if (len(code) != 10 or not code.isascii() or not code.isdecimal()
                or code in by_code or code[:6] != r["watershed_code"]
                or code[:2] != r["code_region_prefix"]
                or r["source_url"] != SOURCE_RIVER_URL
                or r["identity_status"] != "coded_name_only_not_geographically_verified"
                or r["site_status"] != "research_only"
                or (code[:6] in by_ws and r["watershed_name"] != by_ws[code[:6]])):
            raise ValueError("Invalid national river code row")
        by_code[code] = r
    return rivers, waters


def compare(source_rows, rivers, waters, region, source_manifest):
    validate_manifest(region, source_manifest)
    if not source_rows:
        raise ValueError("Empty official source")
    watershed_codes = collections.defaultdict(set)
    for w in waters:
        watershed_codes[basin(w["watershed_name"])].add(w["watershed_code"])
    indexed = collections.defaultdict(set)
    for r in rivers:
        if not r["watershed_name"]:
            continue
        indexed[(basin(r["watershed_name"]), r["river_name"].strip())].add(r["river_code"])
    grouped = collections.defaultdict(list)
    for row in source_rows:
        if (set(row) != set(SOURCE_FIELDS)
                or row["region"] != region
                or row["source_url"] != source_manifest["source_url"]
                or row["source_sha256"] != source_manifest["source_sha256"]
                or row["review_status"] != "unapproved_requires_conservation_and_identity_review"):
            raise ValueError("Official source row provenance or status changed")
        if not all(row[k].strip() for k in ("watershed", "river_name", "survey_year", "recorded_name")):
            raise ValueError("Empty fish river source field")
        grouped[(basin(row["watershed"]), row["river_name"].strip())].append(row)
    out = []
    for (water, river), items in sorted(grouped.items()):
        codes = sorted(indexed.get((water, river), ()))
        ws_codes = sorted(watershed_codes.get(water, ()))
        status = ("WATERSHED_NOT_IN_CODE_LIST" if not ws_codes else
                  "NO_RIVER_CODE_NAME_CANDIDATE" if not codes else
                  "SINGLE_CODE_NAME_CANDIDATE_NOT_VERIFIED" if len(codes) == 1 else
                  "MULTIPLE_CODE_NAME_CANDIDATES")
        out.append({
            "region": region, "watershed": water, "river": river,
            "official_fish_year_records": len(items),
            "source_fish_label_count": len({x["recorded_name"] for x in items}),
            "national_watershed_code_candidates": ws_codes,
            "national_river_code_candidates": codes,
            "status": status,
            "code_identity_verified": False,
            "prefecture_verified": False,
            "fish_species_publication_review": "required",
            "approved_for_publication": False,
        })
    return {
        "schema": SCHEMA,
        "status": "REVIEW_ONLY_DO_NOT_UPLOAD",
        "region": region,
        "source_river_name_groups": len(out),
        "source_fish_year_records": len(source_rows),
        "river_name_groups": out,
        "source_granularity": "named river in fish survey; no site, coordinates or catch promise",
        "code_granularity": "national code list name only; no verified prefecture or individual river identity",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--region", choices=REGIONS, required=True)
    p.add_argument("--source-csv", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    source = read_csv(args.source_csv, SOURCE_FIELDS, 100000)
    rivers, waters = load_codes()
    data = compare(source, rivers, waters, args.region, manifest_for(args.region))
    if args.out.exists():
        raise FileExistsError("Refuse to overwrite review output")
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    counts = dict(sorted(collections.Counter(x["status"] for x in data["river_name_groups"]).items()))
    print("OFFICIAL_CODE_CANDIDATES_V05", json.dumps({
        "region": args.region,
        "river_groups": data["source_river_name_groups"],
        "fish_year_records": data["source_fish_year_records"],
        "match_classes": counts,
        "site_updated": False,
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
