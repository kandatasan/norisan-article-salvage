#!/usr/bin/env python3
"""Research-only v02: add source-scoped Hiroshima Kurose River fish narratives.

Do not mistake an old environmental overview for a dated specimen collection,
an identified national river code, or current habitat. No production writes.
"""
from __future__ import annotations
import argparse
import copy
import csv
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
from build_source_river_fish_layer import INPUT, ROOT, build as build_v01

HIROSHIMA = ROOT.parent / "hiroshima_river_fish_narratives_v08.csv"
SCHEMA = "tsurikue-source-named-river-fish-v02"


def load_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def build(base_rows, narratives):
    layer = copy.deepcopy(build_v01(base_rows))
    if len(narratives) != 9 or len({x["record_id"] for x in narratives}) != 9:
        raise ValueError("Hiroshima narratives inventory changed; manual review needed")
    by_river = {x["source_river_key"]: x for x in layer["river_groups"]}
    excluded = dict(layer["excluded_counts"])
    added = 0
    for row in narratives:
        if not row["record_id"].startswith("HE-"):
            raise ValueError("Unknown Hiroshima source ID")
        if (row["prefecture"] != "広島県" or row["river_name"] != "黒瀬川"
                or row["watershed_name"] != "黒瀬川"
                or row["evidence_scope"] != "named_river_general_no_specific_site"
                or row["source_kind"] != "prefectural_environment_narrative"
                or row["publication_status"] != "research_only_not_website_published"
                or row["identity_review_status"] != "unlinked_river_code_pending_review"
                or row["national_river_code"] or row["survey_year"]):
            raise ValueError("Hiroshima provenance/scope unexpectedly changed")
        url = urlsplit(row["source_url"])
        if (url.scheme != "https" or url.hostname != "www.pref.hiroshima.lg.jp"
                or not row["fish_label_as_written"] or not row["source_uncertainty"]):
            raise ValueError("Invalid source URL, label, or uncertainty")
        if row["sensitive_species_flag"] == "true":
            excluded["conservation_review_required"] = excluded.get("conservation_review_required", 0) + 1
            continue
        if row["sensitive_species_flag"] != "false":
            raise ValueError("Unreviewed sensitivity status")
        key = "|".join((row["prefecture"], row["watershed_name"], row["river_name"]))
        if key not in by_river:
            river = {
                "source_river_key": key,
                "prefecture": row["prefecture"], "watershed": row["watershed_name"],
                "river": row["river_name"], "national_river_code": None,
                "national_river_code_identity_verified": False,
                "source_narrative_only_not_sampling_station": True,
                "fish_labels": [], "fish_label_count": 0, "source_record_count": 0,
                "publication_review": "not_approved",
            }
            by_river[key] = river
        fish = {
            "recorded_name": row["fish_label_as_written"],
            "evidence_scope": "named_river_general_no_specific_site",
            "evidence_kind": row["source_kind"],
            "survey_year": None,
            "source_id": row["record_id"],
            "source_url": row["source_url"],
            "source_locator": "県公式の河川環境概説（掲載日≠調査年）",
            "claim": "県の過去の河川環境説明に魚名が掲載（採集地点・調査年未特定）",
            "source_uncertainty": row["source_uncertainty"],
            "source_page_date_not_survey_year": row["source_page_date"],
        }
        if any(x["source_id"] == fish["source_id"] for x in by_river[key]["fish_labels"]):
            raise ValueError("Duplicate Hiroshima fish record")
        by_river[key]["fish_labels"].append(fish)
        added += 1
    if added != 7:
        raise ValueError("Expected exactly seven non-sensitive narrative records")
    rivers = sorted(by_river.values(), key=lambda x: x["source_river_key"])
    reverse = {}
    for river in rivers:
        river["fish_labels"].sort(key=lambda x: (x["recorded_name"], x["source_id"]))
        river["fish_label_count"] = len({x["recorded_name"] for x in river["fish_labels"]})
        river["source_record_count"] = len(river["fish_labels"])
        for fish in river["fish_labels"]:
            reverse.setdefault(fish["recorded_name"], set()).add(river["source_river_key"])
    layer["schema"] = SCHEMA
    layer["river_groups"] = rivers
    layer["fish_reverse_index"] = {name: sorted(keys) for name, keys in sorted(reverse.items())}
    layer["excluded_counts"] = dict(sorted(excluded.items()))
    layer["source_inventories"] = {
        "source_river_evidence_v01": len(base_rows),
        "hiroshima_river_environment_narratives_v08": len(narratives),
        "narratives_added_research_only": added,
    }
    layer["sources"].append({
        "source_id": "HE-HIROSHIMA-KUROSE-ENVIRONMENT",
        "source_url": narratives[0]["source_url"],
        "source_locator": "広島県の河川環境概説（調査年未確定）",
    })
    layer["sources"].sort(key=lambda x: x["source_id"])
    if sum(r["source_record_count"] for r in rivers) != 112 or sum(excluded.values()) != 31:
        raise ValueError("Unexpected totals: fail closed")
    if len(rivers) != 13:
        raise ValueError("Unexpected river group count")
    return layer


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    layer = build(load_csv(INPUT), load_csv(HIROSHIMA))
    if args.out.exists():
        raise FileExistsError("No overwrite of existing research output")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(layer, ensure_ascii=False, indent=2) + "\n").encode()
    args.out.write_bytes(payload)
    print("RIVER_FISH_V02_RESEARCH", json.dumps({
        "river_groups": len(layer["river_groups"]),
        "research_fish_records": sum(r["source_record_count"] for r in layer["river_groups"]),
        "reverse_fish_names": len(layer["fish_reverse_index"]),
        "excluded": layer["excluded_counts"],
        "sha256": hashlib.sha256(payload).hexdigest(),
        "production_updated": False,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
