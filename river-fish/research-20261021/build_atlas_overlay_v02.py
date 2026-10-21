#!/usr/bin/env python3
"""Build safe non-published bridge: live atlas names + source-backed river fish.

The output never changes existing atlas.json or claims a code-level join.
New river names remain source-backed candidates, not confirmed atlas entities.
"""
from __future__ import annotations
import argparse
import collections
import json
from pathlib import Path
from audit_live_atlas_river_fish import load_live, basin
from build_river_fish_layer_v02 import build, load_csv, INPUT, HIROSHIMA


def overlay(layer, atlas):
    if (layer["status"] != "RESEARCH_ONLY_NOT_FOR_LIVE_SITE"
            or atlas.get("research_display_name_groups") != 511
            or atlas.get("fish_only_mvp") is not True):
        raise ValueError("Unexpected data schema")
    entries = {str(x["id"]): x for x in atlas["entries"]}
    if len(entries) != len(atlas["entries"]):
        raise ValueError("Duplicate live atlas IDs")
    index = collections.defaultdict(set)
    for nav in atlas["links"]:
        entry = entries.get(str(nav["river_id"]))
        if entry is None:
            raise ValueError("Dangling live atlas navigation link")
        index[(nav["prefecture"], basin(nav["water"]), entry["name"].strip())].add(str(entry["id"]))
    rows = []
    for river in layer["river_groups"]:
        key = (river["prefecture"], basin(river["watershed"]), river["river"])
        candidates = sorted(index.get(key, ()))
        rows.append({
            "source_river_key": river["source_river_key"],
            "prefecture": river["prefecture"],
            "watershed": river["watershed"],
            "river": river["river"],
            "research_fish_record_count": river["source_record_count"],
            "fish_labels": [x["recorded_name"] for x in river["fish_labels"]],
            "candidate_atlas_ids": candidates,
            "match_class": "EXACT_SINGLE_NAME_CANDIDATE" if len(candidates) == 1 else
                           "AMBIGUOUS_SAME_NAME" if len(candidates) > 1 else
                           "SOURCE_NAMED_RIVER_NOT_IN_ATLAS",
            "national_river_code_verified": False,
            "approved_for_publication": False,
        })
    return {
        "schema": "tsurikue-atlas-river-fish-overlay-v02",
        "publication_status": "REVIEW_ONLY_DO_NOT_UPLOAD",
        "atlas_existing_entries_unchanged": len(atlas["entries"]),
        "atlas_existing_links_unchanged": len(atlas["links"]),
        "source_river_groups": len(rows),
        "source_fish_records": sum(x["research_fish_record_count"] for x in rows),
        "river_links": rows,
        "notice": "既存図鑑と資料掲載河川名の照合候補。完全一致でも個別河川コード・調査地点の同一性は未承認。",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    atlas, atlas_sha = load_live("atlas.json")
    layer = build(load_csv(INPUT), load_csv(HIROSHIMA))
    data = overlay(layer, atlas)
    if args.out.exists():
        raise FileExistsError("Do not overwrite previous review")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    counts = dict(sorted(collections.Counter(x["match_class"] for x in data["river_links"]).items()))
    print("RIVER_FISH_V02_ATLAS_OVERLAY", json.dumps({
        "atlas_sha256": atlas_sha,
        "source_river_groups": data["source_river_groups"],
        "source_fish_records": data["source_fish_records"],
        "match_classes": counts,
        "published": False,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
