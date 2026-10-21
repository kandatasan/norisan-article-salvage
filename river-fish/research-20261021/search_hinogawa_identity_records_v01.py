#!/usr/bin/env python3
"""Two-way exact search over identity-linked, research-only Hino fish rows."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
INPUT = HERE / "hinogawa_identity_linked_records_v01.csv"


def search(records: list[dict[str, str]], *, river: str = "", river_code: str = "",
           fish: str = "") -> dict:
    river, river_code, fish = river.strip(), river_code.strip(), fish.strip()
    if not (river or river_code or fish):
        raise ValueError("provide --river, --river-code, or --fish")
    matches = [row for row in records
               if (not river or row["river_as_published"] == river)
               and (not river_code or row["river_code"] == river_code)
               and (not fish or row["fish_name_as_published"] == fish)]
    return {
        "status": "RESEARCH_ONLY_IDENTITY_LINKED_CANDIDATES_NOT_PUBLICATION",
        "query": {"river": river or None, "river_code": river_code or None,
                  "fish": fish or None},
        "record_count": len(matches),
        "zero_results_mean_absence": False,
        "historical_count_is_not_current_presence_or_catch_guarantee": True,
        "site_updated": False,
        "records": matches,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--river", default="")
    parser.add_argument("--river-code", default="")
    parser.add_argument("--fish", default="")
    args = parser.parse_args()
    with INPUT.open(encoding="utf-8-sig", newline="") as f:
        records = list(csv.DictReader(f))
    print(json.dumps(search(records, river=args.river, river_code=args.river_code,
                            fish=args.fish), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
