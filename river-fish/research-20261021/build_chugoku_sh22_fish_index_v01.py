#!/usr/bin/env python3
"""Build a redaction-safe, research-only index for Shimane's SH22 fish table."""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE_INPUT = ROOT / "fish_river_evidence_candidates_20261021.csv"
ADDITIONS_INPUT = ROOT / "chugoku_sh22_fish_safe_additions_v01.csv"
SCHEMA = "tsurikue-shimane-sh22-fish-table-v01"
SOURCE_ID = "SH22"
SOURCE_URL = "https://www.pref.shimane.lg.jp/infra/river/kasen/hoshin/hiikawachuryusisen_kawadukuri/index.data/chuuryuuikifuzokusiryou.pdf"
SOURCE_LOCATOR = "表-2.4 資料p20 PDF p21"
RIVERS = {
    "斐伊川": 38,
    "赤川": 19,
    "三刀屋川": 21,
    "久野川": 20,
    "深野川": 15,
    "阿井川": 17,
}

# Species marked with red-list categories in the source table or its attached
# note remain held for review. Names are only used for filtering, never exported.
REVIEW_REQUIRED_NAMES = {
    "スナヤツメ南方種",
    "ハス",
    "カワヒガイ",
    "ホンモロコ",
    "スゴモロコ",
    "ドジョウ",
    "サンインコガタスジシマドジョウ",
    "アカザ",
    "ミナミメダカ(メダカ南日本集団)",
    "カジカ中卵型(ウツセミカジカ(中卵型：両側回遊型))",
    "オオヨシノボリ",
    "ニホンウナギ",
    "ヤマメ",
    "カジカ(大卵型：河川陸封型)",
}


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _key(row: dict[str, str]) -> tuple[str, str]:
    return row["river"], row["recorded_name"]


def build(base_rows: list[dict[str, str]], additions: list[dict[str, str]]) -> dict:
    base = [r for r in base_rows if r["source_id"] == SOURCE_ID]
    if len(base) != 77:
        raise ValueError("Expected the existing 77 SH22 river/fish rows")
    if any(r["prefecture"] != "島根県" or r["watershed"] != "斐伊川" for r in base):
        raise ValueError("SH22 rows escaped the source watershed")
    if any(r["river"] not in RIVERS or r["evidence_scope"] != "named_river" for r in base):
        raise ValueError("SH22 row has an unsupported river scope")
    if any(r["verification_status"] != "source_text_checked" for r in base):
        raise ValueError("Existing SH22 source row is not source-checked")
    if any(r["integration_status"] != "staged_only" for r in base):
        raise ValueError("SH22 source row is not research-staged")
    if any(r["survey_year"] for r in base):
        raise ValueError("Do not infer a fish-specific survey year")

    expected_additions = {
        ("斐伊川", "コイ"), ("斐伊川", "フナ類"), ("斐伊川", "タイリクバラタナゴ"),
        ("斐伊川", "モツゴ"), ("斐伊川", "ゼゼラ"), ("斐伊川", "コウライモロコ"),
        ("斐伊川", "ニシシマドジョウ（シマドジョウ）"), ("斐伊川", "ワカサギ"),
        ("斐伊川", "ウキゴリ"), ("斐伊川", "マハゼ"), ("斐伊川", "旧トウヨシノボリ類"),
        ("斐伊川", "ヌマチチブ"),
        ("赤川", "シマドジョウ"), ("赤川", "ヒメダカ"), ("赤川", "旧トウヨシノボリ類"),
        ("三刀屋川", "シマドジョウ"), ("三刀屋川", "旧トウヨシノボリ類"),
        ("久野川", "シマドジョウ"), ("久野川", "旧トウヨシノボリ類"),
        ("深野川", "シマドジョウ"), ("阿井川", "旧トウヨシノボリ類"),
    }
    addition_keys = {_key(r) for r in additions}
    if len(additions) != 21 or addition_keys != expected_additions:
        raise ValueError("Safe additions differ from the reviewed table delta")
    if any(r["conservation_review"] != "not_flagged" for r in additions):
        raise ValueError("Do not add review-held fish to the searchable additions")
    if any(r["survey_year"] for r in additions):
        raise ValueError("Do not infer a fish-specific survey year")
    if any(r["source_locator"] != SOURCE_LOCATOR for r in additions):
        raise ValueError("Addition row has an unexpected PDF locator")

    all_keys = [_key(r) for r in base] + [_key(r) for r in additions]
    if len(all_keys) != len(set(all_keys)):
        raise ValueError("Duplicate SH22 river/fish row")
    if any(r["river"] not in RIVERS for r in additions):
        raise ValueError("Addition references a river outside Table 2.4")

    raw_counts = collections.Counter(r["river"] for r in base)
    raw_counts.update(r["river"] for r in additions)
    # The source table has 130 rows. The new file contains only unflagged
    # additions; review-held new rows are counted but not transcribed by name.
    additions_by_river = collections.Counter(r["river"] for r in additions)
    expected_base_counts = {"斐伊川": 15, "赤川": 13, "三刀屋川": 14,
                            "久野川": 12, "深野川": 11, "阿井川": 12}
    base_counts = collections.Counter(r["river"] for r in base)
    if dict(base_counts) != expected_base_counts:
        raise ValueError("Existing SH22 river counts changed; re-review source matching")
    expected_addition_counts = {"斐伊川": 12, "赤川": 3, "三刀屋川": 2,
                                "久野川": 2, "深野川": 1, "阿井川": 1}
    if dict(additions_by_river) != expected_addition_counts:
        raise ValueError("Safe addition counts changed; re-review source table")
    for river, total in RIVERS.items():
        if raw_counts[river] > total:
            raise ValueError(f"Input rows exceed the official total for {river}")
        if total - raw_counts[river] < 0:
            raise ValueError("Invalid source-table row reconciliation")
        if additions_by_river[river] == 0:
            raise ValueError(f"No reviewed additions for {river}")

    visible_rows: list[dict] = []
    excluded_existing = 0
    for row in base:
        if row["conservation_review"] == "required" or row["recorded_name"] in REVIEW_REQUIRED_NAMES:
            excluded_existing += 1
            continue
        visible_rows.append({
            "river": row["river"],
            "recorded_name": row["recorded_name"],
            "evidence_scope": "named_river",
            "evidence_kind": "official_survey_summary",
            "survey_year": None,
            "source_id": SOURCE_ID,
            "source_url": SOURCE_URL,
            "source_locator": SOURCE_LOCATOR,
            "verification_status": "source_pdf_table_image_checked",
            "claim": "島根県資料の魚類確認種表に掲載",
        })
    if excluded_existing != 4:
        raise ValueError("Expected four existing SH22 rows to remain held for review")

    for row in additions:
        visible_rows.append({
            "river": row["river"],
            "recorded_name": row["recorded_name"],
            "evidence_scope": row["evidence_scope"],
            "evidence_kind": row["evidence_kind"],
            "survey_year": None,
            "source_id": SOURCE_ID,
            "source_url": SOURCE_URL,
            "source_locator": row["source_locator"],
            "verification_status": "source_pdf_table_image_checked",
            "claim": "島根県資料の魚類確認種表に掲載",
        })

    visible_counts = collections.Counter(r["river"] for r in visible_rows)
    expected_visible = {"斐伊川": 27, "赤川": 15, "三刀屋川": 15,
                        "久野川": 13, "深野川": 12, "阿井川": 12}
    if dict(visible_counts) != expected_visible:
        raise ValueError("Visible river totals changed; review before generating the index")
    if len(visible_rows) != 94:
        raise ValueError("Expected 94 searchable safe research records")
    withheld_count = sum(RIVERS.values()) - len(visible_rows)
    if sum(RIVERS.values()) != 130 or withheld_count != 36:
        raise ValueError("Official source total or review-held count changed")

    by_river: dict[str, list[dict]] = collections.defaultdict(list)
    reverse: dict[str, set[str]] = collections.defaultdict(set)
    for row in visible_rows:
        by_river[row["river"]].append(row)
        reverse[row["recorded_name"]].add(row["river"])

    groups = []
    for river in RIVERS:
        fish = sorted(by_river[river], key=lambda x: x["recorded_name"])
        scope_note = ("斐伊川放水路〜尾原ダムの区間。支川全体への拡張はしない。"
                      if river == "斐伊川" else
                      "表-2.4に河川名として掲載。魚類ごとの採集地点は特定できない。")
        groups.append({
            "prefecture": "島根県",
            "watershed": "斐伊川",
            "river": river,
            "source_scope_note": scope_note,
            "national_river_code": None,
            "national_river_code_identity_verified": False,
            "individual_sampling_station_identified": False,
            "fish_labels": fish,
            "fish_label_count": len({f["recorded_name"] for f in fish}),
            "source_record_count": len(fish),
            "publication_review": "not_approved",
        })

    return {
        "schema": SCHEMA,
        "status": "RESEARCH_ONLY_NOT_FOR_LIVE_SITE",
        "source_id": SOURCE_ID,
        "source_url": SOURCE_URL,
        "source_locator": SOURCE_LOCATOR,
        "source_table_record_total": 130,
        "searchable_research_record_total": len(visible_rows),
        "withheld_review_record_total": withheld_count,
        "withheld_review_record_names_exported": False,
        "verified_river_code_links": 0,
        "current_habitat_verified": False,
        "catchability_verified": False,
        "river_groups": groups,
        "fish_reverse_index": {
            name: sorted(rivers) for name, rivers in sorted(reverse.items())
        },
        "sources": [{"source_id": SOURCE_ID, "source_url": SOURCE_URL,
                     "source_locator": SOURCE_LOCATOR}],
        "notice": ("島根県資料の過去の確認種表に記載された魚名です。現在の生息・釣果・"
                   "個別の採集地点は保証しません。要審査記録と水系単位の記録は検索対象外です。"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    layer = build(load_csv(BASE_INPUT), load_csv(ADDITIONS_INPUT))
    if args.out.exists():
        raise FileExistsError("Research layer output already exists; refuse overwrite")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(layer, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    args.out.write_bytes(payload)
    print("SH22_FISH_INDEX_BUILT", json.dumps({
        "source_records": layer["source_table_record_total"],
        "searchable_records": layer["searchable_research_record_total"],
        "withheld_records": layer["withheld_review_record_total"],
        "rivers": len(layer["river_groups"]),
        "reverse_fish_names": len(layer["fish_reverse_index"]),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "live_site_updated": False,
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
