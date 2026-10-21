#!/usr/bin/env python3
"""Expand the visually checked Hino River adviser table into research-only records.

This does not approve records for publication, assign a river code, or infer
absence from a dash. The eight visible fish rows were checked against the
official PDF page image; redacted conservation-sensitive rows remain excluded.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TABLE = ROOT / "hinogawa_diadr_fish_table_v01.csv"
OUT_FIELDS = [
    "record_id", "source_id", "prefecture", "water_system",
    "river_as_published", "river_code", "survey_year", "survey_year_label",
    "fish_name_as_published", "reported_individual_count", "source_title",
    "source_document_date", "source_url", "source_locator", "survey_basis",
    "verification_status",
    "conservation_review", "fish_publication_approval", "integration_status",
]
YEAR_LABELS = {"H6": 1994, "H11": 1999, "H16": 2004, "H21": 2009,
               "H26": 2014, "R1": 2019, "R6": 2024}
RIVERS = {"hino": "日野川", "hoshoji": "法勝寺川"}
ALLOWED_FISH = {
    "アユ", "サケ", "ヌマチチブ", "チチブ", "シマヨシノボリ",
    "ゴクラクハゼ", "スミウキゴリ", "ウキゴリ",
}
SOURCE_ID = "HINO_ADVISER_2025_MAIN_TABLE"
SOURCE_TITLE = "日野川水系自然再生計画（案）"
SOURCE_DOCUMENT_DATE = "2025-09"
SOURCE_URL = "https://www.cgr.mlit.go.jp/hinogawa/keikaku/09_adviser/pdf/250929_04_honpen.pdf"
SOURCE_LOCATOR = "第2章2.2(2)・通し回遊性の魚類の確認状況（PDF p.20/43、紙面p.18、画像目視照合済み）"


def read_transcription(path: Path = TABLE) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    expected = ["fish_name_as_published"] + [
        f"{river}_{label}" for river in RIVERS for label in YEAR_LABELS
    ]
    if not rows or list(rows[0]) != expected:
        raise ValueError("Transcription CSV schema/order changed; review source first")
    seen = set()
    for row in rows:
        fish = row["fish_name_as_published"]
        if fish not in ALLOWED_FISH or fish in seen:
            raise ValueError("Unexpected or repeated fish label in visible-row allowlist")
        seen.add(fish)
        for field in expected[1:]:
            value = row[field].strip()
            if value == "-":
                continue
            if not value or not value.isdecimal() or int(value) <= 0:
                raise ValueError(f"Expected a positive count or literal dash in {field}")
    if seen != ALLOWED_FISH:
        raise ValueError("One or more reviewed visible fish rows are missing")
    return rows


def expand_records(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    records = []
    serial = 1
    for source_row in rows:
        fish = source_row["fish_name_as_published"]
        for river_key, river_name in RIVERS.items():
            for year_label, year in YEAR_LABELS.items():
                cell = source_row[f"{river_key}_{year_label}"].strip()
                if cell == "-":
                    continue
                records.append({
                    "record_id": f"HINO-ADVISER-2025-{serial:03d}",
                    "source_id": SOURCE_ID,
                    "prefecture": "鳥取県",
                    "water_system": "日野川水系",
                    "river_as_published": river_name,
                    "river_code": "",
                    "survey_year": str(year),
                    "survey_year_label": year_label,
                    "fish_name_as_published": fish,
                    "reported_individual_count": cell,
                    "source_title": SOURCE_TITLE,
                    "source_document_date": SOURCE_DOCUMENT_DATE,
                    "source_url": SOURCE_URL,
                    "source_locator": SOURCE_LOCATOR,
                    "survey_basis": "河川水辺の国勢調査",
                    "verification_status": "official_pdf_table_image_checked",
                    "conservation_review": "pending",
                    "fish_publication_approval": "not_approved",
                    "integration_status": "research_only",
                })
                serial += 1
    return records


def write_records(records: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def build_overlap_summary(records: list[dict[str, str]]) -> dict:
    river_candidates = read_csv(ROOT / "fish_river_evidence_candidates_20261021.csv")
    older_named = {
        (row["prefecture"], row["watershed"], row["river"], row["recorded_name"])
        for row in river_candidates
    }
    named_source_pairs = {
        (r["prefecture"], "日野川", r["river_as_published"], r["fish_name_as_published"])
        for r in records
    }
    same_river_taxon = sum(pair in older_named for pair in named_source_pairs)

    curated = read_csv(ROOT.parent / "curated_fish_records_v03.csv")
    curated_labels = {
        (row["prefecture"], row["watershed"].removesuffix("水系"), row["recorded_name"])
        for row in curated
    }
    system_source_pairs = {
        (r["prefecture"], "日野川", r["fish_name_as_published"]) for r in records
    }
    same_system_taxon = sum(pair in curated_labels for pair in system_source_pairs)

    national = read_csv(ROOT.parent / "official_chugoku_watershed_year_fish_v05.csv")
    national_pairs = {
        (row["watershed"].removesuffix("水系"), row["survey_year"], row["recorded_name"])
        for row in national
    }
    overlap_years = {"2009", "2014", "2019"}
    same_system_round_taxon = sum(
        ("日野川", r["survey_year"], r["fish_name_as_published"]) in national_pairs
        for r in records if r["river_as_published"] == "日野川"
        and r["survey_year"] in overlap_years
    )

    return {
        "status": "RESEARCH_ONLY_OVERLAP_REVIEW_NOT_DEDUPLICATION",
        "new_table_rows": len(records),
        "named_rivers": sorted({r["river_as_published"] for r in records}),
        "source_taxon_labels": len({r["fish_name_as_published"] for r in records}),
        "same_river_name_and_taxon_matches_in_existing_candidate_ledger": same_river_taxon,
        "same_watershed_name_and_taxon_matches_in_curated_system_ledger": same_system_taxon,
        "same_watershed_year_and_taxon_matches_in_nilim_system_ledger": same_system_round_taxon,
        "nilim_overlap_years": sorted(overlap_years),
        "nilim_matches_are_watershed_level_not_river_level": True,
        "possible_same_census_coverage": "Matching name/year labels indicate a possible overlap, not duplicate sample proof; never sum counts across sources.",
        "all_records_research_only": all(r["integration_status"] == "research_only" for r in records),
        "approved_for_publication": False,
        "site_updated": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    rows = read_transcription()
    records = expand_records(rows)
    args.out.mkdir(parents=True, exist_ok=False)
    write_records(records, args.out / "hinogawa_diadr_fish_records_v01.csv")
    (args.out / "hinogawa_diadr_overlap_review_v01.json").write_text(
        json.dumps(build_overlap_summary(records), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("HINOGAWA_ADVISER_TABLE_RESEARCH_ONLY", json.dumps({
        "records": len(records), "rivers": len({r["river_as_published"] for r in records}),
        "fish_labels": len({r["fish_name_as_published"] for r in records}),
        "approval": "not_approved", "site_updated": False,
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
