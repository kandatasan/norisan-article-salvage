#!/usr/bin/env python3
"""Summarize literal river-name overlap with the pinned NILIM China fish data.

Research-only: emit no fish labels, stations, dates finer than survey year,
coordinates, or abundance. A name match is not proof of same river reach.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from extract_official_named_river_fish_v03 import (
    EXPECTED_SHA256,
    get_official_zip,
    aggregate,
    workbook_records,
)

HERE = Path(__file__).resolve().parent
TARGETS = HERE / "chugoku_seven_river_plan_reaches_v01.csv"
FIELDS = (
    "prefecture", "watershed", "river", "river_code", "literal_match_status",
    "survey_years", "unique_year_fish_record_count", "source_id", "source_url",
    "source_sha256", "interpretation", "fish_publication_approval", "integration_status",
)
SOURCE_URL = "https://www.nilim.go.jp/lab/fbg/ksnkankyo/download/slist/RT87_B01.zip"


def summarize(records, targets):
    """Aggregate official unique (watershed, river, year, fish-label) tuples."""
    grouped = defaultdict(list)
    for watershed, river, year, _fish_label in records:
        grouped[(watershed, river)].append(year)

    rows = []
    for target in targets:
        key = (target["watershed"], target["river"])
        years = sorted(set(grouped.get(key, [])))
        count = len(grouped.get(key, []))
        matched = count > 0
        rows.append({
            "prefecture": target["prefecture"],
            "watershed": target["watershed"],
            "river": target["river"],
            "river_code": target["river_code"],
            "literal_match_status": (
                "LITERAL_NAME_MATCH_REQUIRES_REACH_CHECK" if matched else
                "NO_LITERAL_NAME_MATCH_IN_FILTERED_OFFICIAL_EXPORT"
            ),
            "survey_years": ";".join(years),
            "unique_year_fish_record_count": str(count),
            "source_id": "NILIM_CHUGOKU_FISH_B01",
            "source_url": SOURCE_URL,
            "source_sha256": EXPECTED_SHA256,
            "interpretation": (
                "水系名＋河川名の文字一致と調査年度の要約のみ。調査区間・地点の一致、"
                "県資料との独立性、現在の生息を証明しない。魚名・地点情報は非出力。"
                if matched else
                "この固定版の魚類公開表で水系名＋河川名の文字一致なし。調査対象外・"
                "不在・県資料記録の否定を意味しない。"
            ),
            "fish_publication_approval": "not_approved",
            "integration_status": "research_only",
        })
    return rows


def validate_rows(rows, require_pinned_counts=False):
    expected = {
        ("斐伊川", "斐伊川"): ("2009;2014;2019", "82"),
        ("日野川", "日野川"): ("2009;2014;2019", "102"),
    }
    if len(rows) != 7:
        raise ValueError("Expected exactly seven priority river groups")
    keys = [(r["watershed"], r["river"]) for r in rows]
    if len(set(keys)) != 7:
        raise ValueError("Duplicate priority river group")
    for row in rows:
        key = (row["watershed"], row["river"])
        if key in expected:
            if require_pinned_counts and (row["survey_years"], row["unique_year_fish_record_count"]) != expected[key]:
                raise ValueError("Pinned source aggregate changed; review before updating")
            if require_pinned_counts and row["literal_match_status"] != "LITERAL_NAME_MATCH_REQUIRES_REACH_CHECK":
                raise ValueError("Expected literal-name match disappeared")
        elif row["survey_years"] or row["unique_year_fish_record_count"] != "0":
            raise ValueError("Unexpected exact-name match; manual review required")
        if row["fish_publication_approval"] != "not_approved" or row["integration_status"] != "research_only":
            raise ValueError("Public integration is not authorized")
        if any(field in row for field in ("recorded_name", "fish_name", "station", "coordinates", "site")):
            raise ValueError("Sensitive or species-level field leaked into summary")


def run(out: Path):
    if out.exists():
        raise FileExistsError("Refuse to overwrite an existing output directory")
    raw, digest = get_official_zip()
    if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA256 or digest != EXPECTED_SHA256:
        raise ValueError("Pinned NILIM source SHA256 mismatch")
    records, _report = aggregate(workbook_records(raw))
    with TARGETS.open(encoding="utf-8", newline="") as f:
        targets = list(csv.DictReader(f))
    rows = summarize(records, targets)
    validate_rows(rows, require_pinned_counts=True)

    out.mkdir(parents=True)
    with (out / "chugoku_priority_national_fish_overlap_v01.csv").open(
        "w", encoding="utf-8", newline=""
    ) as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    matched = [r for r in rows if r["unique_year_fish_record_count"] != "0"]
    summary = {
        "schema": "tsurikue-chugoku-priority-national-fish-overlap-v01",
        "status": "REVIEW_ONLY_DO_NOT_PUBLISH",
        "source_url": SOURCE_URL,
        "source_sha256": EXPECTED_SHA256,
        "priority_river_groups": len(rows),
        "literal_name_match_groups": len(matched),
        "no_literal_name_match_groups": len(rows) - len(matched),
        "matched_groups": [
            {"watershed": r["watershed"], "river": r["river"],
             "survey_years": r["survey_years"],
             "unique_year_fish_record_count": int(r["unique_year_fish_record_count"]),
             "reach_identity_verified": False}
            for r in matched
        ],
        "fish_names_emitted": False,
        "station_or_coordinate_emitted": False,
        "site_updated": False,
    }
    (out / "chugoku_priority_national_fish_overlap_v01.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print("CHUGOKU_PRIORITY_FISH_OVERLAP_V01", json.dumps(run(args.out), ensure_ascii=False))


if __name__ == "__main__":
    main()
