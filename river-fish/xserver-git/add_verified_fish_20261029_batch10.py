#!/usr/bin/env python3
"""Append reviewed Tokyo and Saitama river-specific fish evidence."""
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

sources = [
    dict(prefecture="東京都", river="秋川",
         names=["タモロコ", "トウヨシノボリ", "アユ", "ドジョウ", "ウグイ", "モツゴ", "オイカワ", "カマツカ", "カワムツ", "ギンブナ", "ヨシノボリ"],
         year=None, sid="RF-20261029-B10-01", title="秋川流域河川整備計画", publisher="東京都建設局",
         url="https://www.kensetsu.metro.tokyo.lg.jp/documents/d/kensetsu/000007256",
         locator="表2-3 秋川流域内の主な生物確認状況一覧表・秋川3地点",
         cls="B", kind="official_environment_narrative", method="資料に掲載された生息魚",
         summary="東京都の河川整備計画が秋川の3地点で確認した魚類から一般魚11件を原表記で収録。地点名と貴重種等は収録しない。"),
    dict(prefecture="東京都", river="三沢川", names=["アブラハヤ", "タモロコ", "モツゴ", "コイ"],
         year=None, sid="RF-20261029-B10-02", title="三沢川河川整備計画", publisher="東京都・神奈川県",
         url="https://www.kensetsu.metro.tokyo.lg.jp/content/000007289.pdf",
         locator="第2章第3節 河川の生態系・魚類",
         cls="B", kind="official_environment_narrative", method="資料に掲載された生息魚",
         summary="河川整備計画が三沢川で優占すると明記した一般魚4件を収録。貴重種、地点、都県別の確認表は収録しない。"),
    dict(prefecture="埼玉県", river="忍川", names=["タモロコ", "モツゴ", "ギンブナ", "タイリクバラタナゴ", "ナマズ"],
         year=2021, sid="RF-20261029-B10-03", title="忍川・旧忍川（さきたま調節池）の自然", publisher="埼玉県",
         url="https://www.pref.saitama.lg.jp/documents/210224/07osikawa2.pdf",
         locator="2021年忍川における魚種と捕獲数",
         cls="A", kind="official_fish_survey_record", method="魚類調査記録",
         summary="埼玉県公開資料の2021年忍川捕獲表に掲載された魚類5件を収録。橋名と捕獲数は収録しない。"),
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
        "scope_notes": ["公的な魚類調査または河川環境資料の記述です。現在の生息や実在河川の同一性を保証しません。", "詳細地点・数量と保全審査対象魚は公開データに収録していません。"],
        "id": "srcfish_" + hashlib.sha256((row["prefecture"] + "|" + entry["water"] + "|" + row["river"]).encode()).hexdigest()[:24],
        "navigation_target_id": entry["id"], "literal_fish_label_count": len(records), "individual_physical_river_identity_approved": False,
    })

data["release"] = "2026-10-29-tokyo-saitama-evidence-batch10-staging"
data["group_count"] = len(data["groups"])
data["record_count"] = sum(len(g["records"]) for g in data["groups"])
DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
print(f"added {len(sources)} groups / {sum(len(row['names']) for row in sources)} records; total {data['group_count']} / {data['record_count']}")
