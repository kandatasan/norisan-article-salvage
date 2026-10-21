#!/usr/bin/env python3
"""Read-only exact-name check of Hino adviser river labels against live atlas."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "hinogawa_diadr_fish_records_v01.csv"
ATLAS_URL = "https://tsurikue.com/river-fish-atlas/data/atlas.json"
MAX_BYTES = 12_000_000


def load_atlas():
    req = Request(ATLAS_URL, headers={"User-Agent": "tsurikue-river-fish-research/1.0",
                                      "Accept": "application/json"})
    with urlopen(req, timeout=40) as response:
        if response.status != 200 or response.url != ATLAS_URL:
            raise ValueError("Live atlas response changed or redirected")
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("Live atlas exceeds safety size limit")
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def basin(value: str) -> str:
    value = str(value or "").strip()
    return value[:-2] if value.endswith("水系") else value


def exact_river_review(records, atlas, atlas_sha256):
    if atlas.get("research_display_name_groups") != 511 or atlas.get("fish_only_mvp") is not True:
        raise ValueError("Live atlas schema/count changed; stop and review")
    entries = atlas.get("entries")
    links = atlas.get("links")
    if not isinstance(entries, list) or not isinstance(links, list):
        raise ValueError("Live atlas lacks expected entries/links")
    by_id = {str(row["id"]): row for row in entries}
    if len(by_id) != len(entries):
        raise ValueError("Live atlas contains duplicate river IDs")
    linked = {}
    for link in links:
        river_id = str(link.get("river_id", ""))
        entry = by_id.get(river_id)
        if entry is None:
            raise ValueError("Live atlas has a dangling river link")
        key = (str(link.get("prefecture", "")), basin(link.get("water", "")),
               str(entry.get("name", "")).strip())
        linked.setdefault(key, set()).add(river_id)

    rivers = sorted({r["river_as_published"] for r in records})
    output = []
    for river in rivers:
        ids = sorted(linked.get(("鳥取県", "日野川", river), set()))
        output.append({
            "prefecture": "鳥取県",
            "water_system": "日野川水系",
            "river_as_published": river,
            "atlas_candidate_ids": ids,
            "join_status": ("EXACT_SINGLE_NAME_CANDIDATE" if len(ids) == 1 else
                            "AMBIGUOUS_SAME_NAME" if ids else "NO_EXACT_CURRENT_ATLAS_ENTRY"),
            "identity_verified": False,
            "approved_for_publication": False,
        })
    return {
        "mode": "READ_ONLY_CURRENT_ATLAS_REVIEW",
        "atlas_url": ATLAS_URL,
        "atlas_sha256": atlas_sha256,
        "live_atlas_entries": len(entries),
        "live_atlas_links": len(links),
        "river_review": output,
        "name_match_does_not_verify_river_identity": True,
        "site_updated": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    with INPUT.open(encoding="utf-8-sig", newline="") as f:
        records = list(csv.DictReader(f))
    atlas, sha = load_atlas()
    result = exact_river_review(records, atlas, sha)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("HINOGAWA_LIVE_ATLAS_READ_ONLY", json.dumps({
        "atlas_sha256": sha,
        "rivers": [{"river": r["river_as_published"], "status": r["join_status"],
                    "candidate_count": len(r["atlas_candidate_ids"])} for r in result["river_review"]],
        "site_updated": False,
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
