#!/usr/bin/env python3
"""Append reviewed Saitama capture records without creating river groups."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).parent / "source" / "data"
DATA_PATH = ROOT / "fish_source_connections_v02_additions.json"
atlas = json.loads((ROOT / "atlas.json").read_text())
data = json.loads(DATA_PATH.read_text())
prior = json.loads((ROOT / "fish_source_connections_v01.json").read_text())
used = {g["navigation_target_id"] for g in prior["groups"] if g["navigation_target_id"]}
used.update(g["navigation_target_id"] for g in data["groups"])

common = dict(
    year=2022,
    sid="RF-20261029-B7-01",
    title="埼玉県水産研究所研究報告 第5号（令和4年度業務報告）",
    publisher="埼玉県水産研究所",
    url="https://www.pref.saitama.lg.jp/documents/9666/r4-kenkyu-hokoku.pdf",
    locator="漁場環境対策事業・表3 生息魚類調査結果",
    cls="A",
    kind="official_fish_survey_record",
    method="魚類調査記録",
)
sources = [
    dict(prefecture="埼玉県", river="荒川",
         names=["アブラハヤ", "ニゴイ", "オイカワ", "カマツカ", "シマドジョウ", "タモロコ", "ウグイ", "モツゴ"],
         summary="埼玉県水産研究所の2022年生息魚類調査表で荒川から採捕された一般魚8件を収録。調査地点と数量は収録しない。", **common),
    dict(prefecture="埼玉県", river="入間川",
         names=["オイカワ", "コクチバス", "カワムツ", "カマツカ"],
         summary="埼玉県水産研究所の2022年生息魚類調査表で入間川から採捕された一般魚4件を収録。調査地点と数量は収録しない。", **common),
    dict(prefecture="埼玉県", river="高麗川",
         names=["アブラハヤ", "カワムツ", "シマドジョウ", "ウグイ", "オイカワ"],
         summary="埼玉県水産研究所の2022年生息魚類調査表で高麗川から採捕された一般魚5件を収録。調査地点、数量、保全審査対象魚は収録しない。", **common),
    dict(prefecture="埼玉県", river="都幾川",
         names=["アブラハヤ", "オイカワ", "シマドジョウ", "カマツカ"],
         summary="埼玉県水産研究所の2022年生息魚類調査表で都幾川から採捕された一般魚4件を収録。調査地点、数量、保全審査対象魚は収録しない。", **common),
]

for row in sources:
    matches = [e for e in atlas["entries"] if e["name"] == row["river"]
               and e.get("source_prefecture") == row["prefecture"]
               and e["kind"] == "official_river_name_only_v21"]
    assert len(matches) == 1, (row["prefecture"], row["river"])
    entry = matches[0]
    assert entry["id"] not in used, entry["id"]
    used.add(entry["id"])
    records = [{
        "recorded_name": name, "source_literal_label": name, "survey_year": row["year"],
        "source_id": row["sid"], "source_title": row["title"], "publisher": row["publisher"],
        "source_url": row["url"], "source_locator": row["locator"], "evidence_class": row["cls"],
        "evidence_kind": row["kind"], "method_label": row["method"], "evidence_summary": row["summary"],
        "scope_note": row["summary"], "river_identity_review": "EXACT_EXISTING_PREFECTURE_WATERSHED_RIVER_LABEL",
        "conservation_review": "RIVER_LEVEL_ONLY_PRECISE_SITE_NOT_PUBLISHED", "publication_status": "STAGING_CANDIDATE",
    } for name in row["names"]]
    data["groups"].append({
        "prefecture": row["prefecture"], "watershed": entry["water"], "river": row["river"], "records": records,
        "scope_notes": ["公的資料の採捕記録です。現在の生息や実在河川の同一性を保証しません。", "詳細地点・数量と保全審査対象魚は公開データに収録していません。"],
        "id": "srcfish_" + hashlib.sha256((row["prefecture"] + "|" + entry["water"] + "|" + row["river"]).encode()).hexdigest()[:24],
        "navigation_target_id": entry["id"], "literal_fish_label_count": len(records), "individual_physical_river_identity_approved": False,
    })

data["release"] = "2026-10-29-saitama-evidence-batch7-staging"
data["group_count"] = len(data["groups"])
data["record_count"] = sum(len(g["records"]) for g in data["groups"])
DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
print(f"added {len(sources)} groups / {sum(len(row['names']) for row in sources)} records; total {data['group_count']} / {data['record_count']}")
