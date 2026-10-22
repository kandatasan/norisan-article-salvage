#!/usr/bin/env python3
"""Read-only audit: source-backed individual-river fish evidence vs LIVE atlas JSON.

No uploads to tsurikue.com. No code/river identity is approved by this script.
Only exact prefecture + watershed + river-name candidates are surfaced.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import pathlib
import urllib.request

BASE = "https://tsurikue.com/river-fish-atlas/data/"
ROOT = pathlib.Path(__file__).resolve().parent
INPUT = ROOT / "fish_river_evidence_candidates_20261021.csv"
SCOPES = {"named_river", "named_river_context", "watershed_only"}


def load_live(filename: str):
    if filename not in {"atlas.json", "fish_master.json", "river_fish_label_counts_v25.json"}:
        raise ValueError("Only approved public atlas data may be fetched")
    req = urllib.request.Request(BASE + filename, headers={
        "User-Agent": "tsurikue-atlas-research-audit/1.0",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=40) as response:
        if response.status != 200:
            raise ValueError(f"Unexpected HTTP {response.status}")
        raw = response.read(12_000_001)
        if len(raw) > 12_000_000:
            raise ValueError("Live data exceeded 12 MB")
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def basin(value):
    """Strip only a terminal 水系 label; never fuzzy-match river names."""
    value = str(value or "").strip()
    return value[:-2] if value.endswith("水系") else value


def classify(rows, atlas):
    if atlas.get("research_display_name_groups") != 511 or atlas.get("fish_only_mvp") is not True:
        raise ValueError("Live atlas schema/count changed; fail closed")
    entries = atlas.get("entries")
    links = atlas.get("links")
    if not isinstance(entries, list) or not isinstance(links, list):
        raise ValueError("Atlas missing entries/links")
    by_id = {str(e["id"]): e for e in entries}
    if len(by_id) != len(entries):
        raise ValueError("Duplicate atlas entry IDs")
    linked = collections.defaultdict(set)
    for x in links:
        if not {"prefecture", "water", "river_id"}.issubset(x):
            raise ValueError("Unexpected atlas navigation schema")
        entry = by_id.get(str(x["river_id"]))
        if entry is None:
            raise ValueError("Dangling atlas link")
        key = (str(x["prefecture"]), basin(x["water"]), str(entry["name"]).strip())
        linked[key].add(str(entry["id"]))
    result = []
    for row in rows:
        if row["evidence_scope"] not in SCOPES or row["integration_status"] != "staged_only":
            raise ValueError("Unapproved source record")
        if row["evidence_scope"] == "watershed_only":
            ids = []
            status = "WATERSHED_ONLY_NOT_LINKABLE"
        elif row["verification_status"] != "source_text_checked":
            ids = []
            status = "SOURCE_NOT_FULLY_CHECKED"
        elif row["conservation_review"] == "required":
            ids = sorted(linked.get((row["prefecture"], basin(row["watershed"]), row["river"]), ()))
            status = "CONSERVATION_REVIEW_REQUIRED"
        else:
            ids = sorted(linked.get((row["prefecture"], basin(row["watershed"]), row["river"]), ()))
            status = ("EXACT_SINGLE_NAME_CANDIDATE" if len(ids) == 1
                      else "AMBIGUOUS_SAME_NAME" if len(ids) > 1
                      else "NOT_FOUND_IN_LIVE_ATLAS")
        result.append({
            "prefecture": row["prefecture"],
            "watershed": row["watershed"],
            "river": row["river"],
            "recorded_name": row["recorded_name"],
            "evidence_scope": row["evidence_scope"],
            "source_id": row["source_id"],
            "verification_status": row["verification_status"],
            "conservation_review": row["conservation_review"],
            "join_review_status": status,
            "atlas_name_candidate_ids": "|".join(ids),
            "approved_for_publish": "NO",
        })
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args()
    with INPUT.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 134:
        raise ValueError("Source count changed; review first")
    atlas, sha = load_live("atlas.json")
    fish_master, fish_sha = load_live("fish_master.json")
    if fish_master.get("scope") != "SOURCE_RECORDED_FISH_LABELS_NOT_VALIDATED_TAXONOMIC_SPECIES":
        raise ValueError("Live fish master changed")
    out = classify(rows, atlas)
    args.out.mkdir(parents=True, exist_ok=False)
    cols = list(out[0])
    with (args.out / "review_only_atlas_join_candidates.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, cols)
        writer.writeheader()
        writer.writerows(out)
    by_status = dict(sorted(collections.Counter(x["join_review_status"] for x in out).items()))
    grouped = collections.defaultdict(list)
    for row in out:
        if row["river"]:
            grouped[(row["prefecture"], row["watershed"], row["river"])].append(row)
    river_group_review = [
        {"prefecture": key[0], "watershed": key[1], "river": key[2],
         "candidate_rows": len(group), "statuses": dict(sorted(collections.Counter(
             x["join_review_status"] for x in group).items()))}
        for key, group in sorted(grouped.items())
    ]
    summary = {
        "mode": "READ_ONLY_REVIEW_NOT_PUBLICATION",
        "source_candidate_rows": len(rows),
        "atlas_json_sha256": sha,
        "fish_master_json_sha256": fish_sha,
        "live_atlas_entries": len(atlas["entries"]),
        "live_atlas_links": len(atlas["links"]),
        "atlas_schema_keys": sorted(atlas.keys()),
        "fish_master_schema_keys": sorted(fish_master.keys()),
        "status_counts": by_status,
        "river_group_review": river_group_review,
        "exact_unique_name_river_groups": len({
            (x["prefecture"], x["watershed"], x["river"], x["atlas_name_candidate_ids"])
            for x in out if x["join_review_status"] == "EXACT_SINGLE_NAME_CANDIDATE"
        }),
        "important": "Matching name+prefecture+watershed does NOT verify river code or permit publishing.",
    }
    (args.out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("LIVE_ATLAS_FISH_JOIN_REVIEW", json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
