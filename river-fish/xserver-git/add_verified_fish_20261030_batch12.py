#!/usr/bin/env python3
"""Append reviewed Miyagi river-specific fish evidence."""
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

source_title = "水生生物の保全に係る水質環境基準の類型指定に係る資料 ―類型指定（案）―"
source_url = "https://www.pref.miyagi.jp/documents/35713/09_r3fy-2-sin3-3.pdf"
sources = [
    dict(prefecture="宮城県", river="白石川",
         names=["エゾイワナ", "ニッコウイワナ", "ヤマメ", "カジカ", "ウグイ", "ナマズ",
                "トウヨシノボリ類", "コイ", "ギンブナ", "オイカワ", "ドジョウ",
                "オオヨシノボリ", "アユ"],
         sid="RF-20261030-B12-01", locator="22頁 表22 魚介類の生息状況（白石川）",
         summary="宮城県の水生生物保全環境基準資料が白石川上流・下流に生息する魚介類として明記した13魚名を原表記で収録。上流・下流区分、調査地点、産卵場位置は収録しない。"),
    dict(prefecture="宮城県", river="荒川",
         names=["ヤマメ", "コイ", "ギンブナ", "オイカワ", "ウグイ", "ナマズ", "オオヨシノボリ", "アユ"],
         sid="RF-20261030-B12-02", locator="26頁 表26 魚介類の生息状況（荒川）",
         summary="宮城県の水生生物保全環境基準資料が荒川に生息する魚介類として明記した8魚名を原表記で収録。調査地点などの詳細位置は収録しない。"),
    dict(prefecture="宮城県", river="松川",
         names=["イワナ", "ヤマメ", "カジカ", "コイ", "ギンブナ", "オイカワ", "ウグイ", "ドジョウ", "ナマズ", "アユ"],
         sid="RF-20261030-B12-03", locator="30頁 表30 魚介類の生息状況（松川）",
         summary="宮城県の水生生物保全環境基準資料が松川に生息する魚介類として明記した10魚名を原表記で収録。調査地点などの詳細位置は収録しない。"),
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
        "recorded_name": name, "source_literal_label": name, "survey_year": None,
        "source_id": row["sid"], "source_title": source_title, "publisher": "宮城県",
        "source_url": source_url, "source_locator": row["locator"], "evidence_class": "B",
        "evidence_kind": "official_environment_narrative", "method_label": "資料に掲載された生息魚",
        "evidence_summary": row["summary"], "scope_note": row["summary"],
        "river_identity_review": "EXACT_EXISTING_PREFECTURE_WATERSHED_RIVER_LABEL",
        "conservation_review": "RIVER_LEVEL_ONLY_PRECISE_SITE_NOT_PUBLISHED",
        "publication_status": "STAGING_CANDIDATE",
    } for name in row["names"]]
    data["groups"].append({
        "prefecture": row["prefecture"], "watershed": entry["water"], "river": row["river"],
        "records": records,
        "scope_notes": ["公的な河川環境資料の生息記述です。現在の生息や実在河川の同一性を保証しません。", "詳細地点・数量は公開データに収録していません。"],
        "id": "srcfish_" + hashlib.sha256((row["prefecture"] + "|" + entry["water"] + "|" + row["river"]).encode()).hexdigest()[:24],
        "navigation_target_id": entry["id"], "literal_fish_label_count": len(records),
        "individual_physical_river_identity_approved": False,
    })

data["release"] = "2026-10-30-miyagi-evidence-batch12-staging"
data["group_count"] = len(data["groups"])
data["record_count"] = sum(len(g["records"]) for g in data["groups"])
DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
print(f"added {len(sources)} groups / {sum(len(row['names']) for row in sources)} records; total {data['group_count']} / {data['record_count']}")
