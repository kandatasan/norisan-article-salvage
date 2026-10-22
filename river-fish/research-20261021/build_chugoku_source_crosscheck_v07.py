#!/usr/bin/env python3
"""Read-only crosscheck: 5 prefectures' 134 staged fish records vs official MLIT
Chugoku fish survey, national river code lists and live atlas navigation.

Every identity is a NAME CANDIDATE only. This deliberately emits NO fish names,
sampling sites, dates or coordinates. All publication approvals remain false.
"""
from __future__ import annotations
import argparse
import collections
import csv
import json
from pathlib import Path

from audit_live_atlas_river_fish import INPUT, load_live, basin
from build_official_river_code_candidates_v05 import load_codes, SOURCE_FIELDS
from extract_official_named_river_fish_nationwide_v04 import manifest_for, validate_manifest

PROVINCIAL_FIELDS = (
    "prefecture", "watershed", "river", "evidence_scope", "recorded_name",
    "evidence_kind", "survey_year", "source_id", "source_locator",
    "verification_status", "source_url", "conservation_review",
    "integration_status", "notes",
)
PROVINCES = {"島根県", "広島県", "岡山県", "鳥取県", "山口県"}
SOURCE_IDS = {"SH22", "HIY", "HIN", "OK19", "TO16", "YA07", "YA04"}
SCOPES = {"named_river", "named_river_context", "watershed_only"}
SCHEMA = "tsurikue-chugoku-5-prefecture-independent-fish-source-crosscheck-v07"


def read_rows(path, header):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        rd = csv.DictReader(handle)
        if tuple(rd.fieldnames or ()) != tuple(header):
            raise ValueError("CSV source header drift: " + str(path))
        rows = list(rd)
    if not rows or any(set(x) != set(header) or not all(isinstance(v, str) for v in x.values())
                       for x in rows):
        raise ValueError("Malformed or empty source rows")
    return rows


def analyze(provincial, national, atlas, rivers, waters, manifest):
    validate_manifest("chugoku", manifest)
    if atlas.get("research_display_name_groups") != 511 or atlas.get("fish_only_mvp") is not True:
        raise ValueError("Live atlas changed: manual review required")
    entries = {str(x["id"]): x for x in atlas["entries"]}
    if len(entries) != len(atlas["entries"]):
        raise ValueError("Duplicate live atlas entry ID")
    atlas_names = collections.defaultdict(set)
    for link in atlas["links"]:
        entry = entries.get(str(link["river_id"]))
        if entry is None:
            raise ValueError("Broken atlas link")
        atlas_names[(str(link["prefecture"]), basin(link["water"]),
                     str(entry["name"]).strip())].add(str(entry["id"]))

    watershed_codes = collections.defaultdict(set)
    for w in waters:
        watershed_codes[basin(w["watershed_name"])].add(w["watershed_code"])
    river_codes = collections.defaultdict(set)
    for r in rivers:
        if r["watershed_name"]:
            river_codes[(basin(r["watershed_name"]), r["river_name"].strip())].add(r["river_code"])

    national_names = collections.defaultdict(set)
    national_counts = collections.Counter()
    for row in national:
        if (set(row) != set(SOURCE_FIELDS) or row["region"] != "chugoku"
                or row["source_url"] != manifest["source_url"]
                or row["source_sha256"] != manifest["source_sha256"]
                or row["review_status"] != "unapproved_requires_conservation_and_identity_review"
                or not all(row[x] for x in ("watershed", "river_name", "survey_year", "recorded_name"))):
            raise ValueError("Official fish survey source drift")
        key = (basin(row["watershed"]), row["river_name"].strip())
        national_names[key].add(row["recorded_name"])
        national_counts[key] += 1

    groups = collections.defaultdict(list)
    held = collections.Counter()
    for row in provincial:
        if (set(row) != set(PROVINCIAL_FIELDS)
                or row["prefecture"] not in PROVINCES
                or row["source_id"] not in SOURCE_IDS
                or row["evidence_scope"] not in SCOPES
                or row["integration_status"] != "staged_only"
                or row["verification_status"] not in {"source_text_checked", "search_excerpt_only"}
                or row["conservation_review"] not in {"not_flagged", "required"}
                or not row["recorded_name"].strip()
                or not row["watershed"].strip()
                or not row["source_url"].startswith("https://")):
            raise ValueError("Provincial evidence provenance/status changed")
        if row["evidence_scope"] == "watershed_only":
            if row["river"]:
                raise ValueError("Watershed-only evidence must not name an individual river")
            held["watershed_only_not_linkable"] += 1
            continue
        if not row["river"]:
            raise ValueError("Individual river evidence without river name")
        key = (row["prefecture"], basin(row["watershed"]), row["river"].strip())
        groups[key].append(row)

    result = []
    for (pref, water, river), records in sorted(groups.items()):
        code_ids = sorted(river_codes.get((water, river), ()))
        atlas_ids = sorted(atlas_names.get((pref, water, river), ()))
        national_key = (water, river)
        names = {x["recorded_name"] for x in records}
        overlap = len(names & national_names.get(national_key, set()))
        direct = sum(x["evidence_scope"] == "named_river" for x in records)
        context = sum(x["evidence_scope"] == "named_river_context" for x in records)
        unread = sum(x["verification_status"] != "source_text_checked" for x in records)
        flagged = sum(x["conservation_review"] == "required" for x in records)
        if unread:
            evidence_gate = "SOURCE_ORIGINAL_NOT_FULLY_CHECKED"
        elif context:
            evidence_gate = "CONTEXT_ONLY_REQUIRES_SCOPE_REVIEW"
        elif flagged:
            evidence_gate = "CONSERVATION_REVIEW_REQUIRED"
        else:
            evidence_gate = "NAMED_RIVER_SOURCE_TEXT_CHECKED_NOT_IDENTITY_VERIFIED"
        if evidence_gate != "NAMED_RIVER_SOURCE_TEXT_CHECKED_NOT_IDENTITY_VERIFIED":
            priority = "C_EVIDENCE_SCOPE_OR_CONSERVATION_REVIEW"
        elif len(code_ids) == 1 and len(atlas_ids) == 1:
            priority = "A_EXISTING_ATLAS_RIVER_REVIEW"
        elif len(code_ids) == 1 and not atlas_ids:
            priority = "B_NEW_RIVER_REVIEW"
        else:
            priority = "D_AMBIGUOUS_OR_MISSING_CODE_REVIEW"
        result.append({
            "prefecture_source_publisher": pref, "watershed": water, "river": river,
            "source_ids": sorted({x["source_id"] for x in records}),
            "source_urls": sorted({x["source_url"] for x in records}),
            "provincial_evidence_rows": len(records),
            "named_river_table_rows": direct,
            "named_river_context_rows": context,
            "source_original_not_checked_rows": unread,
            "source_conservation_flag_rows": flagged,
            "national_chugoku_survey_records_same_water_river_name": national_counts[national_key],
            "independent_same_literal_fish_label_count": overlap,
            "national_watershed_code_name_candidates": sorted(watershed_codes.get(water, ())),
            "national_river_code_name_candidates": code_ids,
            "live_atlas_navigation_name_candidate_ids": atlas_ids,
            "evidence_gate": evidence_gate, "review_priority": priority,
            "source_name_identity_verified": False,
            "code_identity_verified": False,
            "atlas_identity_verified": False,
            "species_publication_review": "required",
            "approved_for_publication": False,
        })
    result.sort(key=lambda x: (x["review_priority"], -x["provincial_evidence_rows"],
                               x["prefecture_source_publisher"], x["river"]))
    return {
        "schema": SCHEMA,
        "status": "REVIEW_ONLY_DO_NOT_UPLOAD",
        "source": "5-prefecture staged official river plans/research and pinned NILIM fish survey",
        "national_chugoku_fish_year_records": len(national),
        "provincial_candidate_rows": len(provincial),
        "named_river_candidate_rows": sum(x["provincial_evidence_rows"] for x in result),
        "watershed_only_rows_held": held["watershed_only_not_linkable"],
        "river_groups": len(result),
        "priority_counts": dict(sorted(collections.Counter(x["review_priority"] for x in result).items())),
        "evidence_gate_counts": dict(sorted(collections.Counter(x["evidence_gate"] for x in result).items())),
        "river_groups_with_independent_literal_fish_overlap": sum(
            x["independent_same_literal_fish_label_count"] > 0 for x in result),
        "river_groups_with_national_river_code_single_name_candidate": sum(
            len(x["national_river_code_name_candidates"]) == 1 for x in result),
        "rows": result,
        "notice": ("県資料と国交省調査に同名の魚があっても独立地点・同一河川・現在の生息の証明ではない。"
                   "国交省河川コード表は都道府県と河川IDの照合を保証しない。魚名は公開JSONへ含めない。"),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--national-csv", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    provincial = read_rows(INPUT, PROVINCIAL_FIELDS)
    if len(provincial) != 134:
        raise ValueError("Provincial staged source count changed; stop for audit")
    national = read_rows(args.national_csv, SOURCE_FIELDS)
    rivers, waters = load_codes()
    atlas, atlas_sha = load_live("atlas.json")
    data = analyze(provincial, national, atlas, rivers, waters, manifest_for("chugoku"))
    if (data["river_groups"] != 13 or data["named_river_candidate_rows"] != 115
            or data["watershed_only_rows_held"] != 19
            or data["national_chugoku_fish_year_records"] != 3592):
        raise ValueError("Source inventory drift: manual review needed")
    data["live_atlas_json_sha256"] = atlas_sha
    if args.out.exists():
        raise FileExistsError("Refuse to overwrite output")
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("CHUGOKU_FISH_SOURCE_CROSSCHECK_V07", json.dumps({
        "river_groups": data["river_groups"], "provincial_rows": data["provincial_candidate_rows"],
        "watershed_only_held": data["watershed_only_rows_held"],
        "independent_overlap_groups": data["river_groups_with_independent_literal_fish_overlap"],
        "single_river_code_candidate_groups": data["river_groups_with_national_river_code_single_name_candidate"],
        "priority_counts": data["priority_counts"], "site_updated": False,
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
