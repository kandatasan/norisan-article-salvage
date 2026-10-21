#!/usr/bin/env python3
"""Compare source-named river groups across 9 official regions to live atlas.

Name-only navigation candidates, not verified national river IDs. No fish
species details are copied into this overlay; publication review still required.
"""
from __future__ import annotations
import argparse
import collections
import csv
import json
from pathlib import Path
from audit_live_atlas_river_fish import load_live, basin
from extract_official_named_river_fish_nationwide_v04 import (
    REGIONS, FIELDS, manifest_for, validate_manifest
)


def compare(rows, atlas, region, source_manifest):
    validate_manifest(region, source_manifest)
    if (atlas.get("research_display_name_groups") != 511
            or atlas.get("fish_only_mvp") is not True):
        raise ValueError("Live atlas schema changed")
    entries = {str(x["id"]): x for x in atlas["entries"]}
    if len(entries) != len(atlas["entries"]):
        raise ValueError("Duplicate atlas river IDs")
    names = collections.defaultdict(set)
    for link in atlas["links"]:
        item = entries.get(str(link["river_id"]))
        if item is None:
            raise ValueError("Dangling atlas link")
        names[(basin(link["water"]), str(item["name"]).strip())].add(
            (str(link["prefecture"]), str(item["id"]))
        )
    grouped = collections.defaultdict(list)
    for row in rows:
        if (set(row) != set(FIELDS) or row["region"] != region
                or row["source_url"] != source_manifest["source_url"]
                or row["source_sha256"] != source_manifest["source_sha256"]
                or row["review_status"] != "unapproved_requires_conservation_and_identity_review"):
            raise ValueError("Official source row not from the expected pinned review dataset")
        if not all(row[k] for k in ("watershed", "river_name", "recorded_name", "survey_year")):
            raise ValueError("Incomplete official river fish record")
        grouped[(basin(row["watershed"]), row["river_name"])].append(row)
    result = []
    for (water, river), items in sorted(grouped.items()):
        candidates = sorted(names.get((water, river), ()))
        result.append({
            "region": region, "watershed": water, "river": river,
            "fish_year_record_count": len(items),
            "fish_name_label_count": len({x["recorded_name"] for x in items}),
            "atlas_name_candidates": [{"prefecture": pref, "atlas_id": aid} for pref, aid in candidates],
            "status": ("ONE_NAVIGATION_NAME_CANDIDATE_NOT_VERIFIED" if len(candidates) == 1
                       else "MULTIPLE_NAVIGATION_NAME_CANDIDATES" if len(candidates) > 1
                       else "SOURCE_NAMED_RIVER_NOT_IN_LIVE_ATLAS"),
            "official_prefecture_verified": False,
            "national_river_code_verified": False,
            "sensitive_species_publication_review": "required",
            "approved_for_publication": False,
        })
    return {
        "schema": "tsurikue-official-national-atlas-overlay-v04",
        "status": "REVIEW_ONLY_DO_NOT_UPLOAD",
        "region": region,
        "source_named_river_groups": len(result),
        "source_fish_year_records": len(rows),
        "groups": result,
        "notice": "原本に明記された河川名を公開図鑑の名前と比較。県名・河川コードの同一性は未確定、保全審査も未完了。",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--region", choices=REGIONS, required=True)
    p.add_argument("--source-csv", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    m = manifest_for(args.region)
    with args.source_csv.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != list(FIELDS):
            raise ValueError("Official source CSV schema changed")
        rows = list(reader)
    if not rows:
        raise ValueError("Empty official direct river data")
    atlas, sha = load_live("atlas.json")
    result = compare(rows, atlas, args.region, m)
    if args.out.exists():
        raise FileExistsError("Do not overwrite existing review")
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    counts = dict(sorted(collections.Counter(x["status"] for x in result["groups"]).items()))
    print("NATIONAL_DIRECT_RIVER_ATLAS_V04", json.dumps({
        "region": args.region,
        "source_river_groups": result["source_named_river_groups"],
        "source_fish_year_records": result["source_fish_year_records"],
        "atlas_sha256": sha,
        "match_status_counts": counts,
        "site_updated": False,
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
