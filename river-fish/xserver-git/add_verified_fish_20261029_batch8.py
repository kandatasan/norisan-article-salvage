#!/usr/bin/env python3
"""Append reviewed Saitama and Tokyo river-environment evidence."""
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
    dict(prefecture="埼玉県", river="びん沼川", names=["ヘラブナ", "コイ", "ブラックバス"],
         sid="RF-20261029-B8-01", title="【びん沼川】川から沼、沼から川へ。人の手で姿を変えてきた旧荒川の流路",
         publisher="SAITAMAリバーサポーターズ（埼玉県）",
         url="https://saitama-riversupporters.pref.saitama.lg.jp/magazine/picture-book-binnumakawa/",
         locator="地域と釣り人たちに愛される歴史ある川", summary="埼玉県の公式プロジェクト記事が、現在びん沼川に生息する魚として原表記3件を明記。釣り地点は収録しない。"),
    dict(prefecture="東京都", river="霞川", names=["アブラハヤ"],
         sid="RF-20261029-B8-02", title="霞川流域河川整備計画",
         publisher="東京都建設局", url="https://www.kensetsu.metro.tokyo.lg.jp/documents/d/kensetsu/000007279",
         locator="第2章第3節 自然環境・霞川", summary="東京都の河川整備計画が霞川で生息を確認した魚類から一般魚アブラハヤを収録。詳細地点と貴重種は収録しない。"),
    dict(prefecture="東京都", river="北秋川", names=["アブラハヤ", "ウグイ", "ニジマス"],
         sid="RF-20261029-B8-03", title="秋川流域河川整備計画",
         publisher="東京都建設局", url="https://www.kensetsu.metro.tokyo.lg.jp/documents/d/kensetsu/000007256",
         locator="表2-3 秋川流域内の主な生物確認状況一覧表・北秋川", summary="東京都の河川整備計画が北秋川で確認した魚類から一般魚3件を収録。詳細地点と貴重種は収録しない。"),
    dict(prefecture="東京都", river="養沢川", names=["アブラハヤ", "アユ", "ウグイ", "カワムツ"],
         sid="RF-20261029-B8-04", title="秋川流域河川整備計画",
         publisher="東京都建設局", url="https://www.kensetsu.metro.tokyo.lg.jp/documents/d/kensetsu/000007256",
         locator="表2-3 秋川流域内の主な生物確認状況一覧表・養沢川", summary="東京都の河川整備計画が養沢川で確認した魚類から一般魚4件を収録。詳細地点と貴重種は収録しない。"),
    dict(prefecture="東京都", river="谷沢川", names=["タモロコ", "モツゴ", "カワムツ", "ウグイ", "ギンブナ", "キンギョ", "コイ", "トウヨシノボリ", "ウキゴリ", "スミウキゴリ"],
         sid="RF-20261029-B8-05", title="谷沢川及び丸子川流域河川整備計画",
         publisher="東京都建設局", url="https://www.kensetsu.metro.tokyo.lg.jp/documents/d/kensetsu/000028989",
         locator="表2-2 主な生物確認状況・谷沢川", summary="東京都の河川整備計画が谷沢川で確認した魚類から一般魚10件を原表記のまま収録。詳細地点と注目種は収録しない。"),
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
        "source_id": row["sid"], "source_title": row["title"], "publisher": row["publisher"],
        "source_url": row["url"], "source_locator": row["locator"], "evidence_class": "B",
        "evidence_kind": "official_environment_narrative", "method_label": "資料に掲載された生息魚",
        "evidence_summary": row["summary"], "scope_note": row["summary"],
        "river_identity_review": "EXACT_EXISTING_PREFECTURE_WATERSHED_RIVER_LABEL",
        "conservation_review": "RIVER_LEVEL_ONLY_PRECISE_SITE_NOT_PUBLISHED", "publication_status": "STAGING_CANDIDATE",
    } for name in row["names"]]
    data["groups"].append({
        "prefecture": row["prefecture"], "watershed": entry["water"], "river": row["river"], "records": records,
        "scope_notes": ["公的な河川環境資料の記述です。現在の生息や実在河川の同一性を保証しません。", "詳細地点と保全審査対象魚は公開データに収録していません。"],
        "id": "srcfish_" + hashlib.sha256((row["prefecture"] + "|" + entry["water"] + "|" + row["river"]).encode()).hexdigest()[:24],
        "navigation_target_id": entry["id"], "literal_fish_label_count": len(records), "individual_physical_river_identity_approved": False,
    })

data["release"] = "2026-10-29-saitama-tokyo-evidence-batch8-staging"
data["group_count"] = len(data["groups"])
data["record_count"] = sum(len(g["records"]) for g in data["groups"])
DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
print(f"added {len(sources)} groups / {sum(len(row['names']) for row in sources)} records; total {data['group_count']} / {data['record_count']}")
