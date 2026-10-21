#!/usr/bin/env python3
"""Read-only name match from official river fish records to live atlas nav links.

Official source does not identify prefecture. Never assign a prefecture, river
code, or a species observation to a specific atlas river automatically.
"""
from __future__ import annotations
import argparse
import collections
import csv
import json
from pathlib import Path
from audit_live_atlas_river_fish import load_live, basin
from extract_official_named_river_fish_v03 import EXPECTED_SHA256, FIELDS


def compare(rows, atlas):
    if (atlas.get("research_display_name_groups") != 511 or
            atlas.get("fish_only_mvp") is not True):
        raise ValueError("Unexpected live atlas schema")
    entries = {str(x["id"]): x for x in atlas["entries"]}
    if len(entries) != len(atlas["entries"]):
        raise ValueError("Duplicate atlas IDs")
    links = collections.defaultdict(set)
    for nav in atlas["links"]:
        entry = entries.get(str(nav["river_id"]))
        if entry is None:
            raise ValueError("Atlas nav refers to missing river ID")
        links[(basin(nav["water"]), str(entry["name"]).strip())].add(
            (str(nav["prefecture"]), str(entry["id"]))
        )
    grouped = collections.defaultdict(list)
    for row in rows:
        if (set(row) != set(FIELDS)
                or row["source_sha256"] != EXPECTED_SHA256
                or row["review_status"] != "unapproved_requires_conservation_and_identity_review"
                or row["region"] != "chugoku"):
            raise ValueError("Source data schema, hash, or review status changed")
        if not all(row[k] for k in ("watershed", "river_name", "survey_year", "recorded_name")):
            raise ValueError("Missing source river evidence")
        grouped[(basin(row["watershed"]), row["river_name"])].append(row)
    output = []
    for (water, river), group in sorted(grouped.items()):
        candidates = sorted(links.get((water, river), ()))
        status = ("ONE_NAVIGATION_NAME_CANDIDATE_NOT_VERIFIED" if len(candidates) == 1 else
                  "MULTIPLE_NAVIGATION_NAME_CANDIDATES" if len(candidates) > 1 else
                  "SOURCE_NAMED_RIVER_NOT_IN_LIVE_ATLAS")
        output.append({
            "watershed": water, "river": river,
            "official_fish_year_records": len(group),
            "distinct_source_fish_labels": len({x["recorded_name"] for x in group}),
            "candidate_navigation": [{"prefecture": pref, "atlas_id": aid} for pref, aid in candidates],
            "match_class": status,
            "official_prefecture_verified": False,
            "national_river_code_verified": False,
            "species_publication_review": "required",
            "approved_for_publication": False,
        })
    return {
        "schema": "tsurikue-official-named-river-atlas-review-v03",
        "publication_status": "REVIEW_ONLY_DO_NOT_UPLOAD",
        "river_name_groups": len(output),
        "source_fish_year_records": len(rows),
        "groups": output,
        "notice": "国交省の原本に河川名があるが県・全国河川コードは未同定。魚名も保全審査前のため公開不可。",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source-csv", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    with args.source_csv.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != list(FIELDS):
            raise ValueError("Unexpected source CSV headers")
        rows = list(reader)
    if len(rows) < 100:
        raise ValueError("Source rows unexpectedly small")
    atlas, sha = load_live("atlas.json")
    result = compare(rows, atlas)
    if args.out.exists():
        raise FileExistsError("Refuse to overwrite review output")
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    counts = dict(sorted(collections.Counter(x["match_class"] for x in result["groups"]).items()))
    print("OFFICIAL_DIRECT_RIVER_ATLAS_REVIEW", json.dumps({
        "atlas_sha256": sha,
        "official_source_fish_year_records": result["source_fish_year_records"],
        "source_river_groups": result["river_name_groups"],
        "name_match_classes": counts,
        "published": False,
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
