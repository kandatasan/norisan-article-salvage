#!/usr/bin/env python3
"""Build a separate, research-only index for fish records scoped to watersheds.

These rows must never be promoted into the individual river search. Keys include
the source ID so two reports with the same watershed name are not silently merged.
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "fish_river_evidence_candidates_20261021.csv"
SCHEMA = "tsurikue-source-watershed-fish-v01"
EXPECTED_YA04_WATERSHEDS = {
    "錦川", "島田川", "佐波川", "椹野川", "厚東川", "厚狭川", "木屋川", "阿武川",
    "小瀬川", "長沢川", "南若川", "土路石川", "井関川", "真締川", "有帆川",
    "西田川", "栗野川", "深川川",
}


def build(rows: list[dict[str, str]]) -> dict:
    grouped: dict[tuple[str, str, str], list[dict]] = collections.defaultdict(list)
    fish_reverse: dict[str, set[str]] = collections.defaultdict(set)
    excluded = collections.Counter()
    seen = set()
    for row in rows:
        if row.get("evidence_scope") != "watershed_only":
            continue
        identity = (row["prefecture"], row["source_id"], row["watershed"], row["recorded_name"])
        if identity in seen:
            raise ValueError("Duplicate watershed-only source record")
        seen.add(identity)
        if (row["river"] or row["integration_status"] != "staged_only"
                or row["verification_status"] != "source_text_checked"
                or row["conservation_review"] not in {"not_flagged", "required"}):
            raise ValueError("Watershed record violates source or publication boundary")
        if row["source_id"] not in {"YA04", "YA07"} or row["prefecture"] != "山口県":
            raise ValueError("Unexpected watershed-only source in this index")
        parsed = urlsplit(row["source_url"])
        if parsed.scheme != "https" or parsed.hostname != "www.pref.yamaguchi.lg.jp":
            raise ValueError("Unexpected source domain")
        if row["conservation_review"] == "required":
            excluded["conservation_review_required"] += 1
            continue
        key = (row["prefecture"], row["source_id"], row["watershed"])
        fish = {
            "recorded_name": row["recorded_name"],
            "evidence_scope": "watershed_only",
            "evidence_kind": row["evidence_kind"],
            "survey_year": row["survey_year"] or None,
            "source_id": row["source_id"],
            "source_url": row["source_url"],
            "source_locator": row["source_locator"],
            "claim": "公的資料に水系単位で魚名が記載（個別河川・調査地点は未特定）",
        }
        grouped[key].append(fish)

    if len(seen) != 19:
        raise ValueError("Watershed-only source inventory changed; manual review required")
    ya04 = {key[2] for key in grouped if key[1] == "YA04"}
    if ya04 != EXPECTED_YA04_WATERSHEDS:
        raise ValueError("YA04 Table 3 watershed list changed; manual review required")
    if excluded != {"conservation_review_required": 1}:
        raise ValueError("Conservation-held watershed inventory changed; manual review required")
    if len(grouped) != 18:
        raise ValueError("Searchable watershed inventory changed; manual review required")

    watersheds = []
    for (prefecture, source_id, watershed), fish_rows in sorted(grouped.items()):
        fish_rows.sort(key=lambda x: (x["recorded_name"], x["source_id"]))
        key = "|".join((prefecture, source_id, watershed))
        watersheds.append({
            "source_watershed_key": key,
            "prefecture": prefecture,
            "watershed": watershed,
            "source_id": source_id,
            "fish_labels": fish_rows,
            "fish_label_count": len({x["recorded_name"] for x in fish_rows}),
            "source_record_count": len(fish_rows),
            "individual_river_linked": False,
            "publication_review": "not_approved",
        })
        for fish in fish_rows:
            fish_reverse[fish["recorded_name"]].add(key)

    return {
        "schema": SCHEMA,
        "status": "RESEARCH_ONLY_NOT_FOR_LIVE_SITE",
        "individual_river_links": 0,
        "current_distribution_verified": False,
        "catchability_verified": False,
        "watershed_groups": watersheds,
        "source_watershed_rows": len(seen),
        "excluded_counts": dict(sorted(excluded.items())),
        "fish_to_watershed_index": {
            name: sorted(keys) for name, keys in sorted(fish_reverse.items())
        },
        "notice": "魚名の資料記録を水系単位で示します。個別河川・調査地点、現在の生息、釣果は保証しません。",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError("Refuse to overwrite watershed fish index")
    with INPUT.open(encoding="utf-8-sig", newline="") as handle:
        layer = build(list(csv.DictReader(handle)))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(layer, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    print("WATERSHED_FISH_INDEX_V01", json.dumps({
        "watershed_groups": len(layer["watershed_groups"]),
        "fish_names": len(layer["fish_to_watershed_index"]),
        "individual_river_links": layer["individual_river_links"],
        "published": False,
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
