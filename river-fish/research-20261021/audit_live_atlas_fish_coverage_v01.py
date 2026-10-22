#!/usr/bin/env python3
"""Read-only aggregate audit of fish-evidence coverage in the live river atlas.

Counts source fish-name evidence by river-name display group. Watershed-only
directory entries are excluded. Identity-held groups remain in the denominator
but not the qualifying numerator. Results are research coverage metrics, not
publication approval or counts of distinct physical rivers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import urllib.request
from collections import Counter
from datetime import datetime, timezone

BASE = "https://tsurikue.com/river-fish-atlas/data/"
MAX_BYTES = 12_000_000
RIVER_KINDS = {
    "historical_national_river_survey",
    "historical_survey_river_name_multiple_code_candidates",
    "official_river_name_only_v21",
    "prefectural_environmental_DNA_only",
}
WATERSHED_KIND = "official_watershed_name_only_v21"
IDENTITY_HOLD_KIND = "historical_survey_river_name_multiple_code_candidates"


def load_live(filename: str):
    if filename not in {"atlas.json", "river_fish_label_counts_v25.json"}:
        raise ValueError("Only approved public atlas data may be fetched")
    req = urllib.request.Request(BASE + filename, headers={
        "User-Agent": "tsurikue-atlas-coverage-audit/1.0",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=40) as response:
        if response.status != 200:
            raise ValueError(f"Unexpected HTTP {response.status}")
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("Live data exceeded 12 MB")
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def summarize(atlas: dict, label_counts: dict) -> dict:
    """Compute a name-group coverage proxy and fail closed on schema drift."""
    if atlas.get("fish_only_mvp") is not True:
        raise ValueError("Unexpected atlas purpose")
    if atlas.get("location_sensitive_data_excluded") is not True:
        raise ValueError("Atlas location-sensitive-data policy changed")
    if atlas.get("fish_editorial_work_is_still_unverified") is not True:
        raise ValueError("Atlas editorial-review status changed; inspect first")
    if atlas.get("strictly_source_named_river_groups_not_geographically_unique_rivers") is not True:
        raise ValueError("Atlas river-identity caveat changed")
    if label_counts.get("schema") != "tsurikue-original-survey-fish-label-counts-v25":
        raise ValueError("Unexpected fish label-count schema")
    for key in (
        "historical_fish_labels_do_not_confirm_current_presence",
        "DNA_positive_labels_do_not_mean_capture_or_visual_confirmation",
        "is_recorded_name_label_count_not_distinct_taxonomic_species",
    ):
        if label_counts.get(key) is not True:
            raise ValueError(f"Required evidence caveat missing: {key}")

    entries = atlas.get("entries")
    labels = label_counts.get("entries")
    if not isinstance(entries, list) or not isinstance(labels, list):
        raise ValueError("Live data missing entries")

    ids = [str(x.get("id", "")) for x in entries]
    if not all(ids) or len(set(ids)) != len(ids):
        raise ValueError("Missing or duplicate atlas entry IDs")
    known_kinds = RIVER_KINDS | {WATERSHED_KIND}
    unknown_kinds = sorted(str(x) for x in ({e.get("kind") for e in entries} - known_kinds))
    if unknown_kinds:
        raise ValueError(f"Unreviewed atlas entry kinds: {unknown_kinds}")

    fish_ids = [str(x.get("survey_river_group_id", "")) for x in labels]
    if not all(fish_ids) or len(set(fish_ids)) != len(fish_ids):
        raise ValueError("Missing or duplicate fish-group IDs")
    fish_id_set = set(fish_ids)
    research_entries = [x for x in entries if x["kind"] in {
        "historical_national_river_survey",
        IDENTITY_HOLD_KIND,
        "prefectural_environmental_DNA_only",
    }]
    research_id_set = {str(x["id"]) for x in research_entries}
    if fish_id_set != research_id_set:
        raise ValueError("Fish label groups and atlas research groups no longer match")
    if label_counts.get("original_source_groups") != len(labels):
        raise ValueError("Fish label group total changed")

    label_by_id = {str(x["survey_river_group_id"]): x for x in labels}
    river_entries = [x for x in entries if x["kind"] in RIVER_KINDS]
    if not river_entries:
        raise ValueError("No river-name groups found")
    by_kind = Counter(x["kind"] for x in river_entries)
    positive_ids = set()
    historical_positive = 0
    edna_positive_ids = set()
    identity_hold_positive = 0

    for entry in river_entries:
        ident = str(entry["id"])
        label = label_by_id.get(ident)
        if label is None:
            continue  # name-only directory entries have no fish group record
        historic = label.get("historical_fish_literal_name_count")
        edna = label.get("environmental_DNA_fish_literal_name_rows")
        has_fish = label.get("fish_name_in_source_records")
        if not isinstance(historic, int) or historic < 0:
            raise ValueError("Invalid historical fish label count")
        if not isinstance(edna, int) or edna < 0:
            raise ValueError("Invalid environmental DNA row count")
        if not isinstance(has_fish, bool):
            raise ValueError("Invalid fish-evidence flag")
        evidence_present = historic > 0 or edna > 0
        if has_fish != evidence_present:
            raise ValueError("Fish evidence flag disagrees with source label counts")
        if evidence_present:
            positive_ids.add(ident)
        if historic > 0:
            historical_positive += 1
        if edna > 0:
            edna_positive_ids.add(ident)
        if entry["kind"] == IDENTITY_HOLD_KIND and evidence_present:
            identity_hold_positive += 1

    entry_by_id = {str(x["id"]): x for x in river_entries}
    qualifying_ids = {
        ident for ident in positive_ids
        if entry_by_id[ident]["kind"] != IDENTITY_HOLD_KIND
    }
    denominator = len(river_entries)
    target_percent = 50
    target_groups = math.ceil(denominator * target_percent / 100)
    qualifying_count = len(qualifying_ids)
    linked_count = len(positive_ids)
    watershed_count = sum(1 for x in entries if x["kind"] == WATERSHED_KIND)
    identity_hold_count = sum(1 for x in river_entries if x["kind"] == IDENTITY_HOLD_KIND)

    return {
        "status": "LIVE_RESEARCH_COVERAGE_NOT_PUBLICATION_APPROVAL",
        "unit": "river-name display groups; not distinct physical rivers",
        "denominator_rule": "All live atlas river-name entry groups; watershed-only entries excluded.",
        "numerator_rule": (
            "At least one historical fish label or environmental-DNA fish label in the source group; "
            "multiple-code identity-hold groups excluded from the 50% qualifying numerator."
        ),
        "river_name_display_groups": denominator,
        "fish_evidence_groups_including_identity_holds": linked_count,
        "coverage_percent_including_identity_holds": round(linked_count / denominator * 100, 1),
        "identity_hold_groups_in_denominator": identity_hold_count,
        "identity_hold_groups_with_fish_evidence_excluded": identity_hold_positive,
        "fish_evidence_groups_excluding_identity_holds": qualifying_count,
        "coverage_percent_excluding_identity_holds": round(qualifying_count / denominator * 100, 1),
        "fish_evidence_groups_with_historical_labels": historical_positive,
        "fish_evidence_groups_with_environmental_DNA_labels": len(edna_positive_ids),
        "watershed_only_entries_excluded_from_denominator": watershed_count,
        "river_name_display_groups_by_kind": dict(sorted(by_kind.items())),
        "target_percent": target_percent,
        "target_groups_at_current_denominator": target_groups,
        "additional_qualifying_groups_needed": max(0, target_groups - qualifying_count),
        "site_editorial_review_is_unverified": atlas["fish_editorial_work_is_still_unverified"],
        "caveats": [
            "Display-name groups are not geographically deduplicated physical rivers.",
            "Historical source records do not establish current fish presence or catchability.",
            "Environmental-DNA detections are not capture or visual-confirmation records.",
            "Coverage counts do not approve any record for public addition or relax source-review requirements.",
            "The separate watershed-only directory contributes no river-level fish links to this metric.",
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args()
    atlas, atlas_sha = load_live("atlas.json")
    labels, labels_sha = load_live("river_fish_label_counts_v25.json")
    report = summarize(atlas, labels)
    report["retrieved_at_utc"] = datetime.now(timezone.utc).isoformat()
    report["source_urls"] = {
        "atlas": BASE + "atlas.json",
        "fish_label_counts": BASE + "river_fish_label_counts_v25.json",
    }
    report["atlas_json_sha256"] = atlas_sha
    report["fish_label_counts_json_sha256"] = labels_sha
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("LIVE_ATLAS_FISH_COVERAGE_RESEARCH_ONLY", json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
