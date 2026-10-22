#!/usr/bin/env python3
"""Build a reproducible, RESEARCH-ONLY river↔fish evidence layer from source CSV.

This layer is not a site export, not a verified river-code join, and not a
statement of current species distribution. Never auto-upload it to WordPress.
"""
from __future__ import annotations
import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "fish_river_evidence_candidates_20261021.csv"
EDITION = "tsurikue-source-named-river-fish-v01"
PUBLISHABLE = False


def build(rows):
    if len(rows) != 155:
        raise ValueError("Expected 155 source observations, not a new or changed source file")
    by_river = collections.defaultdict(list)
    excluded = collections.Counter()
    reverse = collections.defaultdict(set)
    sources = {}
    seen = set()
    for row in rows:
        if row["integration_status"] != "staged_only":
            raise ValueError("Unexpected publication status")
        key = (row["prefecture"], row["watershed"], row["river"])
        identity = (*key, row["recorded_name"], row["source_id"])
        if identity in seen:
            raise ValueError("Duplicate source record")
        seen.add(identity)
        if row["evidence_scope"] not in ("named_river", "named_river_context", "watershed_only"):
            raise ValueError("Unrecognized evidence granularity")
        if not row["prefecture"] or not row["watershed"]:
            raise ValueError("Source record missing prefecture or watershed")
        if row["evidence_scope"] == "watershed_only" and row["river"]:
            raise ValueError("Watershed-only evidence has river name")
        if row["evidence_scope"] != "watershed_only" and not row["river"]:
            raise ValueError("Named-river record missing river name")
        if row["verification_status"] != "source_text_checked":
            excluded["source_not_fully_checked"] += 1
            continue
        if row["conservation_review"] == "required":
            excluded["conservation_review_required"] += 1
            continue
        if row["evidence_scope"] == "watershed_only":
            excluded["watershed_only"] += 1
            continue
        source_id = row["source_id"]
        src = sources.setdefault(source_id, {
            "source_id": source_id, "source_url": row["source_url"],
            "source_locator": row["source_locator"]
        })
        if src["source_url"] != row["source_url"] or src["source_locator"] != row["source_locator"]:
            raise ValueError("Source ID unexpectedly mapped to multiple URLs/locators")
        item = {
            "recorded_name": row["recorded_name"],
            "evidence_scope": row["evidence_scope"],
            "evidence_kind": row["evidence_kind"],
            "survey_year": row["survey_year"] or None,
            "source_id": source_id,
            "source_url": row["source_url"],
            "source_locator": row["source_locator"],
            "claim": ("県資料の魚類確認種表に掲載" if row["evidence_scope"] == "named_river"
                      and row["evidence_kind"] == "official_survey_summary"
                      else "県の河川環境資料に魚名が記載"),
        }
        by_river[key].append(item)
        reverse[row["recorded_name"]].add(key)
    rivers = []
    for (pref, water, river), fish in sorted(by_river.items()):
        fish.sort(key=lambda x: (x["recorded_name"], x["source_id"]))
        rivers.append({
            "source_river_key": "|".join((pref, water, river)),
            "prefecture": pref, "watershed": water, "river": river,
            "national_river_code": None,
            "national_river_code_identity_verified": False,
            "source_narrative_only_not_sampling_station": True,
            "fish_labels": fish,
            "fish_label_count": len({x["recorded_name"] for x in fish}),
            "source_record_count": len(fish),
            "publication_review": "not_approved",
        })
    if sum(x["source_record_count"] for x in rivers) + sum(excluded.values()) != len(rows):
        raise ValueError("Record loss during transformation")
    return {
        "schema": EDITION,
        "status": "RESEARCH_ONLY_NOT_FOR_LIVE_SITE",
        "verified_river_code_links": 0,
        "current_habitat_verified": False,
        "catchability_verified": False,
        "river_groups": rivers,
        "fish_reverse_index": {
            fish: sorted("|".join(k) for k in keys) for fish, keys in sorted(reverse.items())
        },
        "sources": [sources[k] for k in sorted(sources)],
        "excluded_counts": dict(sorted(excluded.items())),
        "notice": "過去の県資料に記載された魚名です。現在の生息・釣果・個別の採集地点は保証しません。",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    with INPUT.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    layer = build(rows)
    if args.out.exists():
        raise FileExistsError("Research layer output already exists; refuse overwrite")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(layer, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    args.out.write_bytes(payload)
    print("RIVER_FISH_RESEARCH_LAYER_BUILT", json.dumps({
        "source_rows": len(rows), "river_groups": len(layer["river_groups"]),
        "safe_research_records": sum(x["source_record_count"] for x in layer["river_groups"]),
        "reverse_fish_labels": len(layer["fish_reverse_index"]),
        "excluded": layer["excluded_counts"],
        "sha256": hashlib.sha256(payload).hexdigest(),
        "published": False,
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
