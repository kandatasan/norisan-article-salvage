#!/usr/bin/env python3
"""Two-way exact-name search over research-only Hino River records."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "hinogawa_diadr_fish_records_v01.csv"
NOTICE = (
    "過去の公的調査資料に載る記録で、現在の生息や釣果を保証しません。"
    "河川コード・調査地点の確認と保全審査が未完了の研究用候補です。"
)


def search(records: list[dict[str, str]], river: str = "", fish: str = "") -> dict:
    river, fish = river.strip(), fish.strip()
    if not river and not fish:
        raise ValueError("Provide an exact river or fish name")
    matches = [r for r in records
               if (not river or r["river_as_published"] == river)
               and (not fish or r["fish_name_as_published"] == fish)]
    return {
        "query": {"river": river or None, "fish": fish or None},
        "status": "RESEARCH_ONLY_CANDIDATES_NOT_PUBLICATION",
        "notice": NOTICE,
        "records": [{
            "river": r["river_as_published"],
            "fish_name_as_published": r["fish_name_as_published"],
            "survey_year": int(r["survey_year"]),
            "reported_individual_count": int(r["reported_individual_count"]),
            "source_title": r["source_title"],
            "source_url": r["source_url"],
            "publication_approval": r["fish_publication_approval"],
        } for r in matches],
        "record_count": len(matches),
        "zero_results_mean_absence": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--river", default="", help="Exact river name as printed in source")
    parser.add_argument("--fish", default="", help="Exact fish label as printed in source")
    args = parser.parse_args()
    with INPUT.open(encoding="utf-8-sig", newline="") as f:
        records = list(csv.DictReader(f))
    print(json.dumps(search(records, args.river, args.fish), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
