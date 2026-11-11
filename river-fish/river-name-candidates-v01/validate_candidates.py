#!/usr/bin/env python3
"""Validate that river-name candidates remain outside the fixed 1,127 groups."""
from __future__ import annotations

from collections import Counter
import csv
import json
from pathlib import Path
from urllib.parse import urlparse


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CANDIDATES = HERE / "river_name_candidates_v01.csv"
MANIFEST = HERE / "manifest_v01.json"
ATLAS = REPO / "river-fish/xserver-git/source/data/atlas.json"

FIELDS = [
    "candidate_id", "prefecture", "municipality", "river_name_as_written",
    "source_evidence_kind", "source_title", "publisher", "source_page_url",
    "source_document_url", "source_locator", "source_as_of", "source_page_updated",
    "watershed_name", "river_code", "fish_evidence_status", "identity_review_status",
    "publication_status", "coverage_denominator_status", "conservation_review",
    "existing_atlas_exact_name_other_context_count", "review_note",
]


def validate() -> dict:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    atlas = json.loads(ATLAS.read_text(encoding="utf-8"))
    with CANDIDATES.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FIELDS:
            raise ValueError("Candidate CSV schema changed")
        rows = list(reader)

    fixed_groups = [
        entry for entry in atlas["entries"]
        if entry["kind"] != "official_watershed_name_only_v21"
    ]
    if len(fixed_groups) != manifest["fixed_coverage_denominator"] != 1127:
        raise ValueError("Fixed coverage denominator changed")
    if len(rows) != manifest["candidate_count"] != 22:
        raise ValueError("Candidate count differs from reviewed manifest")
    if any(manifest[key] for key in (
        "candidate_rows_affect_fixed_denominator",
        "candidate_rows_are_published",
        "candidate_rows_have_fish_connections",
        "candidate_rows_have_inferred_watersheds_or_codes",
    )):
        raise ValueError("Candidate manifest exceeds research-only scope")

    ids: set[str] = set()
    names: set[tuple[str, str, str]] = set()
    all_atlas_name_counts = Counter(entry["name"] for entry in atlas["entries"])
    same_prefecture_exact = {
        (entry.get("source_prefecture"), entry["name"])
        for entry in atlas["entries"]
        if entry.get("source_prefecture")
    }
    cross_context_rows = 0
    for row in rows:
        if row["candidate_id"] in ids:
            raise ValueError(f"Duplicate candidate ID: {row['candidate_id']}")
        ids.add(row["candidate_id"])
        key = (row["prefecture"], row["municipality"], row["river_name_as_written"])
        if key in names:
            raise ValueError(f"Duplicate candidate name and jurisdiction: {key}")
        names.add(key)
        if (row["prefecture"], row["river_name_as_written"]) in same_prefecture_exact:
            raise ValueError(f"Candidate already exists in same-prefecture atlas context: {key}")

        expected_name_matches = all_atlas_name_counts[row["river_name_as_written"]]
        recorded_name_matches = int(row["existing_atlas_exact_name_other_context_count"])
        if recorded_name_matches != expected_name_matches:
            raise ValueError(f"Cross-context exact-name count changed: {key}")
        cross_context_rows += recorded_name_matches > 0

        urls = (row["source_page_url"], row["source_document_url"])
        if any(urlparse(url).scheme != "https" or urlparse(url).hostname != "www.city.hiroshima.lg.jp" for url in urls):
            raise ValueError(f"Candidate source is not the reviewed Hiroshima City host: {key}")
        if not row["river_name_as_written"] or row["river_name_as_written"][0] in "=+-@":
            raise ValueError(f"Unsafe or empty river name: {key}")
        if row["watershed_name"] or row["river_code"]:
            raise ValueError(f"Candidate inferred a watershed or river code: {key}")
        if row["fish_evidence_status"] != "not_examined":
            raise ValueError(f"Candidate gained unreviewed fish evidence: {key}")
        if row["identity_review_status"] != "candidate_not_promoted":
            raise ValueError(f"Candidate was promoted without review: {key}")
        if row["publication_status"] != "research_only_not_published":
            raise ValueError(f"Candidate entered a publication state: {key}")
        if row["coverage_denominator_status"] != "excluded_from_fixed_1127":
            raise ValueError(f"Candidate changed the fixed denominator: {key}")
        if row["conservation_review"] != "river_name_only_no_sensitive_location":
            raise ValueError(f"Candidate conservation status changed: {key}")
        if not all(row[field] for field in (
            "source_evidence_kind", "source_title", "publisher", "source_locator",
            "source_as_of", "source_page_updated", "review_note",
        )):
            raise ValueError(f"Candidate lacks source or review metadata: {key}")

    return {
        "schema": manifest["schema"],
        "fixed_coverage_denominator": len(fixed_groups),
        "connected_groups_at_baseline": manifest["connected_groups_at_baseline"],
        "candidate_count": len(rows),
        "candidate_rows_with_cross_context_exact_name_matches": cross_context_rows,
        "candidate_rows_added_to_fixed_denominator": 0,
        "candidate_rows_published": 0,
        "candidate_fish_connections": 0,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False, sort_keys=True))
