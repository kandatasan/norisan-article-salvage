
#!/usr/bin/env python3
"""Build privacy-minimized Kanagawa eDNA river-group candidates.

Workbook rows are read in memory. Output contains group names and aggregate
counts only: never fish names, sampling-site names, coordinates, row values, or
river codes. All results remain unapproved research candidates.
"""
from __future__ import annotations

import argparse
import csv
import concurrent.futures
import hashlib
import io
import json
import math
import re
import sys
import unicodedata
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

from inspect_supplement import MAX_BYTES, SOURCES

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "river-fish" / "research-20261021"))
sys.path.insert(0, str(REPO_ROOT / "river-fish" / "source-connections-v01"))

from audit_live_atlas_fish_coverage_v01 import (  # noqa: E402
    IDENTITY_HOLD_KIND,
    RIVER_KINDS,
    load_live,
    summarize,
)
from audit_connections import coverage as summarize_published_coverage  # noqa: E402
from audit_connections import read_public_layer  # noqa: E402

PREFECTURE = "神奈川県"
LAYOUTS = {
    "FY2021_water_source_fish": {"sample_start": 8, "year_row": 1, "water_row": 3, "river_row": 4, "data_start": 7},
    "FY2022_water_source_fish": {"sample_start": 8, "year_row": 1, "water_row": 3, "river_row": 4, "data_start": 7},
    "FY2023_water_source_fish": {"sample_start": 8, "year_row": 1, "water_row": 3, "river_row": 4, "data_start": 7},
    "FY2023_prefecture_wide_fish": {"sample_start": 8, "year_row": 1, "water_row": 3, "river_row": 4, "data_start": 7},
    "FY2024_water_source_all_taxa": {"sample_start": 16, "year_row": 1, "water_row": 3, "river_row": 4, "data_start": 7},
    "FY2024_prefecture_wide_all_taxa": {"sample_start": 14, "year_row": 1, "water_row": 2, "river_row": 3, "data_start": 7},
    "FY2025_water_source_all_taxa": {"sample_start": 11, "year_row": 1, "water_row": 3, "river_row": 4, "data_start": 8},
    "FY2025_prefecture_wide_all_taxa": {"sample_start": 17, "year_row": 1, "water_row": 3, "river_row": 4, "data_start": 7},
}
FIELD_HEADERS = {
    "水系", "水系名", "河川", "河川名", "年度", "調査年度", "調査日", "採水日",
    "採取日", "市町村", "市町村名", "地点名", "採水地点", "採水地点名", "調査地点",
    "調査地点名", "都道府県", "県名",
}
POSITIVE_TEXT = {"検出", "陽性", "有", "あり", "○", "〇", "1", "+", "＋"}
FISH_REFERENCE = REPO_ROOT / "river-fish" / "biota" / "official_biota_reference_2025_v18.csv"


def normalize(value) -> str:
    if value is None:
        return ""
    return unicodedata.normalize("NFKC", re.sub(r"\s+", "", str(value))).strip()


def parse_survey_year(value, fallback: int | None = None) -> int | None:
    if isinstance(value, (datetime, date)):
        return value.year
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = int(value)
        return number if 1900 <= number <= 2100 else fallback
    text = normalize(value)
    match = re.search(r"(?:19|20)\d{2}", text)
    if match:
        return int(match.group(0))
    for era, base in (("令和", 2018), ("R", 2018), ("平成", 1988), ("H", 1988), ("昭和", 1925), ("S", 1925)):
        flags = re.IGNORECASE if era in {"R", "H", "S"} else 0
        match = re.search(era + r"(\d+)", text, flags)
        if match:
            return base + int(match.group(1))
    return fallback


def is_positive_detection(value) -> bool:
    if isinstance(value, bool) or value is None:
        return False
    if isinstance(value, (int, float)):
        return math.isfinite(float(value)) and value > 0
    text = normalize(value)
    if text in POSITIVE_TEXT:
        return True
    if re.fullmatch(r"\+?\d+(?:\.\d+)?", text):
        try:
            return float(text) > 0
        except ValueError:
            return False
    return False


def load_fish_reference(path: Path = FISH_REFERENCE) -> dict[str, str]:
    """Map exact official Japanese/scientific fish labels to internal taxon IDs."""
    lookup: dict[str, str] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if normalize(row.get("fish")).lower() not in {"1", "true"}:
                continue
            taxon_id = normalize(row.get("official_taxon_code"))
            if not taxon_id:
                continue
            for label in (row.get("japanese_name"), row.get("scientific_name")):
                key = normalize(label)
                if key:
                    lookup[key] = taxon_id
    if not lookup:
        raise ValueError("Official fish reference did not contain usable fish labels")
    return lookup


def source_fiscal_year(source_id: str) -> int | None:
    match = re.search(r"FY(\d{4})", source_id)
    return int(match.group(1)) if match else None


def extract_workbook(raw: bytes, source_id: str, fish_label_to_taxon: dict[str, str]) -> dict:
    if source_id not in LAYOUTS:
        raise ValueError("Workbook source has no reviewed layout")
    if len(raw) > MAX_BYTES or len(raw) < 1000:
        raise ValueError("Unexpected workbook size")

    from openpyxl import load_workbook

    workbook = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    sheet = workbook.worksheets[0]
    layout = LAYOUTS[source_id]
    row_cache = {}
    for row_number in {layout["year_row"], layout["water_row"], layout["river_row"]}:
        row_cache[row_number] = next(sheet.iter_rows(min_row=row_number, max_row=row_number, values_only=True))

    sample_columns = []
    for column_index in range(layout["sample_start"] - 1, sheet.max_column or 0):
        year_value = row_cache[layout["year_row"]][column_index]
        water = normalize(row_cache[layout["water_row"]][column_index])
        river = normalize(row_cache[layout["river_row"]][column_index])
        if not water or not river or water in FIELD_HEADERS or river in FIELD_HEADERS:
            continue
        year = parse_survey_year(year_value, source_fiscal_year(source_id))
        if year is not None:
            sample_columns.append((column_index, year, water, river))
    if not sample_columns:
        workbook.close()
        raise ValueError("No sample columns matched the reviewed source layout")

    # The site-name metadata row is never read into the result.
    groups: dict[tuple[str, str], dict] = defaultdict(
        lambda: {"years": set(), "sources": set(), "taxa": set(), "positive_cells": 0}
    )
    matched_taxon_rows = 0
    positive_cells = 0
    max_left_column = layout["sample_start"] - 1
    for row in sheet.iter_rows(min_row=layout["data_start"], values_only=True):
        taxon_ids = {
            fish_label_to_taxon[normalize(value)]
            for value in row[:max_left_column]
            if normalize(value) in fish_label_to_taxon
        }
        if not taxon_ids:
            continue
        matched_taxon_rows += 1
        for column_index, year, water, river in sample_columns:
            if column_index >= len(row) or not is_positive_detection(row[column_index]):
                continue
            group = groups[(water, river)]
            group["years"].add(year)
            group["sources"].add(source_id)
            group["taxa"].update(taxon_ids)
            group["positive_cells"] += 1
            positive_cells += 1
    if not matched_taxon_rows:
        workbook.close()
        raise ValueError("No official-reference fish labels matched the reviewed source layout")

    result = {
        "source_id": source_id,
        "source_url": SOURCES[source_id],
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "worksheet_rows": sheet.max_row,
        "worksheet_columns": sheet.max_column,
        "metadata_complete_sample_columns": len(sample_columns),
        "matched_fish_taxon_rows": matched_taxon_rows,
        "positive_fish_sample_cells": positive_cells,
        "groups": dict(groups),
    }
    workbook.close()
    return result


def collect_sources(fish_label_to_taxon: dict[str, str]) -> tuple[list[dict], dict]:
    """Fetch each fixed official source once and merge source-level aggregates."""
    def fetch_and_extract(item):
        source_id, url = item
        request = urllib.request.Request(url, headers={
            "User-Agent": "tsurikue-kanagawa-edna-research-aggregation/1.0",
            "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "Referer": "https://www.pref.kanagawa.jp/docs/b4f/suigen/edna.html",
        })
        with urllib.request.urlopen(request, timeout=90) as response:
            host = response.geturl().split("/", 3)[2]
            if response.status != 200 or host not in {"www.pref.kanagawa.jp", "www.pref.kanagawa.jp:443"}:
                raise ValueError("Prefecture response left the pinned official host")
            raw = response.read(MAX_BYTES + 1)
        return source_id, extract_workbook(raw, source_id, fish_label_to_taxon)

    summaries = []
    merged: dict[tuple[str, str], dict] = defaultdict(
        lambda: {"years": set(), "sources": set(), "taxa": set(), "positive_cells": 0}
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        fetched = list(executor.map(fetch_and_extract, SOURCES.items()))
    for source_id, source in fetched:
        groups = source.pop("groups")
        summaries.append(source)
        for pair, values in groups.items():
            merged[pair]["years"].update(values["years"])
            merged[pair]["sources"].update(values["sources"])
            merged[pair]["taxa"].update(values["taxa"])
            merged[pair]["positive_cells"] += values["positive_cells"]
    return summaries, merged


def classify_atlas_pairs(groups: dict, atlas: dict, label_counts: dict, layer: dict) -> Counter:
    by_pair: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for entry in atlas["entries"]:
        if entry.get("kind") not in RIVER_KINDS:
            continue
        pair = (normalize(entry.get("water")), normalize(entry.get("name")))
        if all(pair):
            by_pair[pair].append(entry)
    published_pairs = {
        (normalize(group.get("watershed")), normalize(group.get("river")))
        for group in layer.get("groups", [])
    }
    label_by_id = {str(item["survey_river_group_id"]): item for item in label_counts["entries"]}
    status_counts = Counter()
    for pair in groups:
        lookup_pair = (normalize(pair[0]), normalize(pair[1]))
        if lookup_pair in published_pairs:
            status = "already_in_published_source_layer"
        else:
            matches = by_pair.get(lookup_pair, [])
            if not matches:
                status = "unmatched_exact_water_river_pair_needs_crosswalk"
            elif len(matches) > 1:
                status = "multiple_atlas_groups_hold"
            elif matches[0].get("kind") == IDENTITY_HOLD_KIND:
                status = "identity_hold_excluded"
            elif label_by_id.get(str(matches[0]["id"]), {}).get("fish_name_in_source_records"):
                status = "already_fish_positive"
            else:
                status = "exact_empty_group_candidate_prefecture_check_pending"
        groups[pair]["atlas_pair_status"] = status
        status_counts[status] += 1
    return status_counts


def build_report() -> dict:
    taxon_lookup = load_fish_reference()
    source_summaries, group_data = collect_sources(taxon_lookup)
    atlas, atlas_hash = load_live("atlas.json")
    label_counts, label_hash = load_live("river_fish_label_counts_v25.json")
    summarize(atlas, label_counts)
    public_layer = read_public_layer()
    published_coverage = summarize_published_coverage(atlas, label_counts, public_layer)
    status_counts = classify_atlas_pairs(group_data, atlas, label_counts, public_layer)

    candidate_groups = []
    for (water, river), values in sorted(group_data.items()):
        stable_id = hashlib.sha256(f"{PREFECTURE}\n{water}\n{river}".encode("utf-8")).hexdigest()[:16]
        candidate_groups.append({
            "candidate_id": f"kn_edna_{stable_id}",
            "prefecture": PREFECTURE,
            "watershed": water,
            "river": river,
            "survey_years": sorted(values["years"]),
            "source_ids": sorted(values["sources"]),
            "source_urls": sorted({SOURCES[source_id] for source_id in values["sources"]}),
            "positive_fish_taxon_count": len(values["taxa"]),
            "positive_sample_result_cells": values["positive_cells"],
            "evidence_method": "environmental_DNA",
            "atlas_pair_status": values["atlas_pair_status"],
            "individual_river_identity_approved": False,
            "publication_approval": False,
        })

    baseline_numerator = published_coverage["fish_evidence_groups"]
    baseline_denominator = published_coverage["river_name_display_groups"]
    exact_empty = status_counts["exact_empty_group_candidate_prefecture_check_pending"]
    unmatched = status_counts["unmatched_exact_water_river_pair_needs_crosswalk"]
    hypothetical_additions = exact_empty + unmatched
    projected_denominator = baseline_denominator + hypothetical_additions
    projected_numerator = baseline_numerator + hypothetical_additions
    return {
        "schema": "kanagawa-edna-river-group-candidates-v01",
        "status": "research_candidates_only_not_publication_approval",
        "candidate_rule": "At least one official-reference fish taxon with a positive eDNA result and explicit source water-system and river fields.",
        "source_files": source_summaries,
        "source_file_count": len(source_summaries),
        "source_group_candidate_count": len(candidate_groups),
        "atlas_pair_status_counts": dict(sorted(status_counts.items())),
        "published_coverage_snapshot": {
            "fish_evidence_groups": baseline_numerator,
            "river_name_display_groups": baseline_denominator,
            "coverage_percent": published_coverage["coverage_percent"],
            "additional_groups_needed_at_50_percent": published_coverage["additional_qualifying_groups_needed"],
            "atlas_json_sha256": atlas_hash,
            "fish_label_counts_sha256": label_hash,
        },
        "all_unmatched_pairs_as_new_group_hypothesis": {
            "hypothetical_only": True,
            "assumes_every_unmatched_pair_is_a_distinct_new_river_name_group": True,
            "fish_evidence_groups": projected_numerator,
            "river_name_display_groups": projected_denominator,
            "coverage_percent": round(projected_numerator / projected_denominator * 100, 1) if projected_denominator else 0,
            "additional_groups_needed_at_50_percent": max(0, math.ceil(projected_denominator / 2) - projected_numerator),
        },
        "species_names_included": False,
        "sampling_site_names_or_coordinates_included": False,
        "river_codes_included": False,
        "historical_or_environmental_DNA_records_are_not_current_presence": True,
        "groups": candidate_groups,
        "caveats": [
            "The public atlas does not carry a reliable prefecture field for every group, so exact water-system and river name matches still need a prefecture cross-check.",
            "Unmatched pairs may be aliases or duplicate groups and are not added to coverage until individually reviewed.",
            "eDNA evidence is kept separate from capture records and does not establish current presence, catchability, abundance, or habitat occupancy.",
            "All candidates remain unapproved and are excluded from public coverage until reviewed.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_report()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    safe_summary = {key: report[key] for key in (
        "status", "source_file_count", "source_group_candidate_count",
        "atlas_pair_status_counts", "published_coverage_snapshot",
        "all_unmatched_pairs_as_new_group_hypothesis",
    )}
    print("KANAGAWA_EDNA_RESEARCH_CANDIDATE_SUMMARY", json.dumps(safe_summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
