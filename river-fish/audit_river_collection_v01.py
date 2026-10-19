#!/usr/bin/env python3
"""Audit source completeness and write an honest collection-status manifest.

Read-only: no network, database or WordPress access. Never convert a river
code jurisdiction prefix into a geographic prefecture assignment.
"""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def rows(path):
    with (ROOT / path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def audit():
    manifest = json.loads((ROOT / "national-codes-staged/river_code_manifest_v07.json").read_text(encoding="utf-8"))
    rivers = rows("national-codes-staged/river_codes_national_v07.csv")
    watersheds = rows("national-codes-staged/watershed_codes_national_v07.csv")
    assert len(rivers) == manifest["river_code_rows"]
    assert len(watersheds) == manifest["watershed_code_rows"]
    water_codes = {r["watershed_code"] for r in watersheds}
    assert len(water_codes) == len(watersheds)
    code_field = "river_code"
    assert all(code_field in r for r in rivers)
    river_codes = [r[code_field] for r in rivers]
    assert len(set(river_codes)) == len(rivers)
    unresolved = [r for r in rivers if r[code_field][:6] not in water_codes]
    assert len(unresolved) == manifest["river_rows_without_matching_watershed_code"]
    by_watershed = Counter(r[code_field][:6] for r in rivers if r[code_field][:6] in water_codes)
    return {
        "schemaVersion": "1",
        "sourceStatus": "research_only",
        "riverCodeCount": len(rivers),
        "watershedCodeCount": len(watersheds),
        "distinctWatershedsWithRiverCodes": len(by_watershed),
        "unmatchedRiverRows": len(unresolved),
        "unmatchedWatershedPrefixes": sorted({r[code_field][:6] for r in unresolved}),
        "unmatchedRiverCodes": sorted(river_codes for river_codes in [r[code_field] for r in unresolved]),
        "sourceUrls": manifest["source_pages"],
        "collectionMatrix": {
            "officialRiverCodes": "collected_with_19_unmatched_rows",
            "officialWatershedCodes": "collected",
            "47PrefectureSourceEntry": "collected_partial_official_mentions",
            "geographicPrefectureForEachRiver": "not_complete",
            "riverToRiverConfluences": "not_complete",
            "individualRiverBiota": "not_complete",
            "watershedFishSurvey": "collected_by_label_not_code_join",
            "fishingRulesAndSeasons": "not_complete",
            "rightsForPublicBulkReuse": "pending_review"
        },
        "safety": {
            "riverIdentity": "ten_digit_code",
            "prefectureFromCodePrefix": "prohibited",
            "speciesFromWatershedToRiver": "prohibited",
            "unmatchedCodes": "quarantine_no_guess",
            "liveSystemsTouched": False
        }
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    args = p.parse_args()
    dest = Path(args.out)
    if dest.exists():
        raise FileExistsError("Will not overwrite existing audit")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(audit(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(dest)
