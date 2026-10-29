#!/usr/bin/env python3
"""Append reviewed Tokyo fish-survey and river-environment evidence."""
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
    dict(prefecture="東京都", river="境川", names=["アユ", "コイ", "アブラハヤ", "モツゴ"],
         year=None, sid="RF-20261029-B9-01", title="境川水系河川整備計画",
         publisher="神奈川県・東京都・横浜市",
         url="https://www.kensetsu.metro.tokyo.lg.jp/content/000007308.pdf",
         locator="第2章第3節 河川環境の整備と保全に関する事項・動植物の生息状況",
         cls="B", kind="official_environment_narrative", method="資料に掲載された生息魚",
         summary="河川整備計画が境川の水域で生息を確認した魚類から一般魚4件を収録。詳細地点と保全審査対象魚は収録しない。"),
    dict(prefecture="東京都", river="八ツ瀬川", names=["カダヤシ"],
         year=None, sid="RF-20261029-B9-02", title="八ツ瀬川河川整備基本方針",
         publisher="東京都建設局",
         url="https://www.kensetsu.metro.tokyo.lg.jp/documents/d/kensetsu/000052243",
         locator="第1章（10）河川環境",
         cls="B", kind="official_environment_narrative", method="資料に掲載された生息魚",
         summary="東京都の河川整備基本方針が八ツ瀬川に生息すると明記した魚類から一般魚1件を収録。固有種等の保全審査対象魚は収録しない。"),
    dict(prefecture="東京都", river="立会川", names=["ボラ"],
         year=None, sid="RF-20261029-B9-03", title="立会川河川整備基本方針",
         publisher="東京都建設局",
         url="https://www.kensetsu.metro.tokyo.lg.jp/documents/d/kensetsu/000007330",
         locator="第1章（10）河川環境",
         cls="B", kind="official_environment_narrative", method="資料に掲載された生息魚",
         summary="東京都の河川整備基本方針が立会川に生息する魚類としてボラを明記。開渠区間などの詳細は収録しない。"),
    dict(prefecture="東京都", river="横十間川", names=["ハゼ類"],
         year=2005, sid="RF-20261029-B9-04", title="第6回 横十間川底質関連対策検討会 要旨",
         publisher="東京都建設局",
         url="https://www.kensetsu.metro.tokyo.lg.jp/river/kankyo/yokoju_dxn/contents6",
         locator="議事要旨1（1）魚類調査の結果について",
         cls="A", kind="official_fish_survey_record", method="魚類調査記録",
         summary="東京都の検討会要旨が横十間川の魚類調査でハゼ類203個体を採取したと報告。数量・分析値・地点は収録せず、類表記を維持する。"),
    dict(prefecture="東京都", river="多摩川",
         names=["ヤマメ", "ニジマス", "ウグイ", "タカハヤ", "カワムツ", "オイカワ", "タモロコ", "スゴモロコ", "カマツカ", "シマドジョウ", "カジカ", "カワヨシノボリ", "ヌマチチブ"],
         year=2023, sid="RF-20261029-B9-05", title="内水面魚類生息環境調査～多摩川上流域および日原川における魚類相モニタリング～",
         publisher="東京都島しょ農林水産総合センター",
         url="https://www.ifarc.metro.tokyo.lg.jp/survey/uploads/4474406c08d0b20c57b1886325d6348a.pdf",
         locator="表1 令和5年における多摩川上流域および日原川の魚種別採集個体数・多摩川上流域",
         cls="A", kind="official_fish_survey_record", method="魚類調査記録",
         summary="東京都の2023年採集表で多摩川上流域から採集された原表記13件を収録。地点・尾数と保全審査対象魚は収録しない。"),
    dict(prefecture="東京都", river="日原川",
         names=["イワナ", "ヤマメ", "ニジマス", "ウグイ", "タカハヤ", "カジカ"],
         year=2023, sid="RF-20261029-B9-06", title="内水面魚類生息環境調査～多摩川上流域および日原川における魚類相モニタリング～",
         publisher="東京都島しょ農林水産総合センター",
         url="https://www.ifarc.metro.tokyo.lg.jp/survey/uploads/4474406c08d0b20c57b1886325d6348a.pdf",
         locator="表1 令和5年における多摩川上流域および日原川の魚種別採集個体数・日原川",
         cls="A", kind="official_fish_survey_record", method="魚類調査記録",
         summary="東京都の2023年採集表で日原川から採集された原表記6件を収録。地点・尾数は収録しない。"),
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

data["release"] = "2026-10-29-tokyo-evidence-batch9-staging"
data["group_count"] = len(data["groups"])
data["record_count"] = sum(len(g["records"]) for g in data["groups"])
DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
print(f"added {len(sources)} groups / {sum(len(row['names']) for row in sources)} records; total {data['group_count']} / {data['record_count']}")
