#!/usr/bin/env python3
"""Enrich seven reviewed source-river groups with official river codes.

This produces research-only, staged rows. It never writes to the live atlas and
does not approve fish records for publication.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from audit_chugoku_seven_river_identity_v01 import INPUT as IDENTITY_INPUT
from audit_chugoku_seven_river_identity_v01 import load as load_identities

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "fish_river_evidence_candidates_20261021.csv"
OUTPUT_FIELDS_EXTRA = (
    "river_code",
    "river_identity_status",
    "fish_publication_approval",
    "source_document_title",
    "source_document_date",
    "survey_year_status",
)
SOURCE_METADATA = {
    "SH22": {
        "source_document_title": "斐伊川水系中流支川域河川整備計画【第1回変更】付属資料",
        "source_document_date": "2022-03",
        "source_locator": "2.5(4) 表-2.4（PDF p.21/81、紙面p.20、ページ画像照合済み）",
        "verification_status": "official_pdf_table_image_checked",
    },
    "TO16": {
        "source_document_title": "日野川水系（指定区間）河川整備計画",
        "source_document_date": "2016-01",
        "verification_status": "source_text_checked",
    },
}
EXPECTED_TOTALS = {
    ("島根県", "斐伊川", "斐伊川"): 15,
    ("島根県", "斐伊川", "三刀屋川"): 13,
    ("島根県", "斐伊川", "久野川"): 11,
    ("島根県", "斐伊川", "阿井川"): 11,
    ("島根県", "斐伊川", "深野川"): 11,
    ("鳥取県", "日野川", "日野川"): 9,
    ("鳥取県", "日野川", "大川"): 6,
}
EXPECTED_HELD_CONSERVATION = {
    ("島根県", "斐伊川", "三刀屋川", "ヤマメ", "SH22"),
    ("島根県", "斐伊川", "久野川", "ヤマメ", "SH22"),
    ("島根県", "斐伊川", "阿井川", "ヤマメ", "SH22"),
}
SOURCE_FIELDS = (
    "prefecture", "watershed", "river", "evidence_scope", "recorded_name",
    "evidence_kind", "survey_year", "source_id", "source_locator",
    "verification_status", "source_url", "conservation_review",
    "integration_status", "notes",
)


def build(source_path: Path = SOURCE) -> tuple[list[dict[str, str]], tuple[str, ...]]:
    identities = load_identities(IDENTITY_INPUT)
    identity_by_key = {
        (row["prefecture_source_publisher"], row["watershed"], row["river"]): row
        for row in identities
    }
    with source_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if tuple(reader.fieldnames or ()) != SOURCE_FIELDS:
            raise ValueError("source evidence CSV header drift")
        source_rows = list(reader)
    if len(source_rows) != 124:
        raise ValueError("source evidence row count changed; manual review required")

    enriched = []
    counts: dict[tuple[str, str, str], int] = {}
    held_conservation = set()
    for row in source_rows:
        key = (row["prefecture"], row["watershed"], row["river"])
        if key not in identity_by_key:
            continue
        expected_scope = "named_river" if row["prefecture"] == "島根県" else "named_river_context"
        if (row["evidence_scope"] != expected_scope
                or row["verification_status"] != "source_text_checked"
                or row["integration_status"] != "staged_only"
                or not row["recorded_name"].strip()):
            raise ValueError(f"selected record fails source/conservation gate: {key}")
        if row["conservation_review"] == "required":
            held_key = (*key, row["recorded_name"], row["source_id"])
            if held_key not in EXPECTED_HELD_CONSERVATION:
                raise ValueError(f"unexpected flagged source record in selected river: {held_key}")
            if "環NT" not in row["notes"]:
                raise ValueError(f"flagged record lacks its source conservation note: {held_key}")
            held_conservation.add(held_key)
            continue
        if row["conservation_review"] != "not_flagged":
            raise ValueError(f"unknown conservation state in selected river: {key}")
        identity = identity_by_key[key]
        expected_source = "SH22" if row["prefecture"] == "島根県" else "TO16"
        if row["source_id"] != expected_source:
            raise ValueError(f"source ID mismatch for {key}")
        metadata = SOURCE_METADATA.get(expected_source)
        if metadata is None:
            raise ValueError(f"no document metadata for source {expected_source}")
        enriched_row = {
            **row,
            **metadata,
            "survey_year_status": "not_reported_per_species_in_source",
            "river_code": identity["river_code"],
            "river_identity_status": identity["identity_status"],
            "fish_publication_approval": "not_approved",
        }
        enriched.append(enriched_row)
        counts[key] = counts.get(key, 0) + 1

    if (held_conservation != EXPECTED_HELD_CONSERVATION
            or counts != EXPECTED_TOTALS or len(enriched) != 76):
        raise ValueError(f"selected source rows changed: {counts}")
    if any(r["integration_status"] != "staged_only"
           or r["fish_publication_approval"] != "not_approved" for r in enriched):
        raise ValueError("publication boundary changed")
    fields = tuple(SOURCE_FIELDS) + OUTPUT_FIELDS_EXTRA
    return enriched, fields


def write(path: Path) -> int:
    rows, fields = build()
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    count = write(args.out)
    print(f"SEVEN_RIVER_FISH_CROSSWALK_V01 rows={count} publication_approvals=0")


if __name__ == "__main__":
    main()
