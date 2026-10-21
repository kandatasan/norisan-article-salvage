#!/usr/bin/env python3
"""Prioritize human river-identity review using independent atlas/code matches.

No fish names, precise locations, taxonomic claims or publication approvals.
One matching code and one atlas navigation ID are STILL not identity proof.
"""
from __future__ import annotations
import argparse
import collections
import json
from pathlib import Path

SCHEMA = "tsurikue-river-fish-identity-review-queue-v06"
CODE_SCHEMA = "tsurikue-official-direct-river-national-code-candidates-v05"
ATLAS_SCHEMA = "tsurikue-official-national-atlas-overlay-v04"
CODE_STATES = {
    "WATERSHED_NOT_IN_CODE_LIST",
    "NO_RIVER_CODE_NAME_CANDIDATE",
    "SINGLE_CODE_NAME_CANDIDATE_NOT_VERIFIED",
    "MULTIPLE_CODE_NAME_CANDIDATES",
}
ATLAS_STATES = {
    "ONE_NAVIGATION_NAME_CANDIDATE_NOT_VERIFIED",
    "MULTIPLE_NAVIGATION_NAME_CANDIDATES",
    "SOURCE_NAMED_RIVER_NOT_IN_LIVE_ATLAS",
}


def build(code_data, atlas_data):
    if (code_data.get("schema") != CODE_SCHEMA
            or code_data.get("status") != "REVIEW_ONLY_DO_NOT_UPLOAD"
            or atlas_data.get("schema") != ATLAS_SCHEMA
            or atlas_data.get("status") != "REVIEW_ONLY_DO_NOT_UPLOAD"
            or code_data.get("region") != atlas_data.get("region")):
        raise ValueError("Unexpected input schema, region or publication status")
    region = code_data["region"]
    codes = {}
    for row in code_data["river_name_groups"]:
        key = (row["watershed"], row["river"])
        if (key in codes or row["region"] != region
                or row["status"] not in CODE_STATES
                or row["approved_for_publication"] is not False
                or row["code_identity_verified"] is not False
                or row["prefecture_verified"] is not False):
            raise ValueError("Duplicate or unreviewed code group")
        codes[key] = row
    atlas = {}
    for row in atlas_data["groups"]:
        key = (row["watershed"], row["river"])
        if (key in atlas or row["region"] != region
                or row["status"] not in ATLAS_STATES
                or row["approved_for_publication"] is not False
                or row["national_river_code_verified"] is not False
                or row["official_prefecture_verified"] is not False):
            raise ValueError("Duplicate or unreviewed atlas group")
        atlas[key] = row
    if (set(codes) != set(atlas)
            or len(codes) != code_data["source_river_name_groups"]
            or len(atlas) != atlas_data["source_named_river_groups"]
            or code_data["source_fish_year_records"] != atlas_data["source_fish_year_records"]):
        raise ValueError("Code and atlas river groups do not match")
    queue = []
    for key in sorted(codes):
        code = codes[key]
        nav = atlas[key]
        if (code["official_fish_year_records"] != nav["fish_year_record_count"]
                or code["source_fish_label_count"] != nav["fish_name_label_count"]):
            raise ValueError("River source record counts differ between independent audits")
        cc = code["national_river_code_candidates"]
        ac = nav["atlas_name_candidates"]
        if (len(cc) == 1) != (code["status"] == "SINGLE_CODE_NAME_CANDIDATE_NOT_VERIFIED"):
            if not (len(cc) == 0 and code["status"] in {
                    "WATERSHED_NOT_IN_CODE_LIST", "NO_RIVER_CODE_NAME_CANDIDATE"}
                    or len(cc) > 1 and code["status"] == "MULTIPLE_CODE_NAME_CANDIDATES"):
                raise ValueError("Code status/count contradiction")
        if (len(ac) == 1) != (nav["status"] == "ONE_NAVIGATION_NAME_CANDIDATE_NOT_VERIFIED"):
            if not (len(ac) == 0 and nav["status"] == "SOURCE_NAMED_RIVER_NOT_IN_LIVE_ATLAS"
                    or len(ac) > 1 and nav["status"] == "MULTIPLE_NAVIGATION_NAME_CANDIDATES"):
                raise ValueError("Atlas status/count contradiction")
        if len(cc) == 1 and len(ac) == 1:
            priority = "A_EXISTING_ATLAS_IDENTITY_REVIEW"
        elif len(cc) == 1 and not ac:
            priority = "B_NEW_ATLAS_RIVER_IDENTITY_REVIEW"
        else:
            priority = "C_AMBIGUITY_OR_MISSING_CODE_REVIEW"
        queue.append({
            "region": region, "watershed": key[0], "river": key[1],
            "review_priority": priority,
            "official_fish_year_records": code["official_fish_year_records"],
            "source_fish_label_count": code["source_fish_label_count"],
            "code_name_candidate_ids": cc,
            "atlas_navigation_name_candidates": ac,
            "code_name_match_status": code["status"],
            "atlas_name_match_status": nav["status"],
            "identity_verified": False,
            "conservation_publication_review": "required",
            "approved_for_publication": False,
        })
    priority_counts = dict(sorted(collections.Counter(x["review_priority"] for x in queue).items()))
    return {
        "schema": SCHEMA, "status": "REVIEW_ONLY_DO_NOT_UPLOAD",
        "region": region, "river_groups": len(queue),
        "source_fish_year_records": code_data["source_fish_year_records"],
        "priority_counts": priority_counts,
        "queue": sorted(queue, key=lambda x: (x["review_priority"], -x["official_fish_year_records"],
                                            x["watershed"], x["river"])),
        "notice": "河川コード・図鑑ナビの双方に名前が一致しても、採集河川の同一性は未承認。魚名や地点は出力しない。",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--code-review", type=Path, required=True)
    p.add_argument("--atlas-review", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    data = build(json.loads(args.code_review.read_text(encoding="utf-8")),
                 json.loads(args.atlas_review.read_text(encoding="utf-8")))
    if args.out.exists():
        raise FileExistsError("Refusing to overwrite existing review")
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("RIVER_FISH_IDENTITY_QUEUE_V06", json.dumps({
        "region": data["region"], "river_groups": data["river_groups"],
        "priority_counts": data["priority_counts"], "site_updated": False,
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
