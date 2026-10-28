#!/usr/bin/env python3
"""Append reviewed Gunma evidence without creating river groups."""
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

gunma_2026_test = "https://www.pref.gunma.jp/site/houdou/757954.html"
gunma_2023_test = "https://www.pref.gunma.jp/site/houdou/203552.html"
gunma_report_15 = "https://www.pref.gunma.jp/page/20869.html"
karasu_plan = "https://www.pref.gunma.jp/page/11140.html"
ora_tatebayashi_plan = "https://www.pref.gunma.jp/page/11156.html"
gunma_fisheries_news_48 = "https://www.pref.gunma.jp/page/20880.html"

# Fish labels are copied literally. Municipal sampling places and precise reaches are omitted.
sources = [
    {
        "prefecture": "群馬県", "watershed": "利根川", "river": "利根川",
        "names": ["アユ"], "survey_year": 2026, "source_id": "RF-20261029-B4-01",
        "source_title": "水産物に対する放射性物質の安全検査について（第349回）",
        "publisher": "群馬県", "source_url": gunma_2026_test,
        "source_locator": "2．検査結果（採捕魚・養殖魚）・利根川／アユ行",
        "evidence_class": "A", "evidence_kind": "official_capture_record",
        "method_label": "魚類調査記録",
        "summary": "群馬県の2026年検査結果表で、利根川の採捕魚としてアユを明記。市町村以下の採捕場所は収録しない。",
    },
    {
        "prefecture": "群馬県", "watershed": "利根川", "river": "吾妻川",
        "names": ["ヤマメ"], "survey_year": 2023, "source_id": "RF-20261029-B4-02",
        "source_title": "水産物に対する放射性物質の安全検査について（第315回）",
        "publisher": "群馬県", "source_url": gunma_2023_test,
        "source_locator": "2．検査結果（採捕魚）・吾妻川／ヤマメ行",
        "evidence_class": "A", "evidence_kind": "official_capture_record",
        "method_label": "魚類調査記録",
        "summary": "群馬県の2023年検査結果表で、吾妻川の採捕魚としてヤマメを明記。市町村以下の採捕場所は収録しない。",
    },
    {
        "prefecture": "群馬県", "watershed": "利根川", "river": "広瀬川",
        "names": ["コイ"], "survey_year": None, "source_id": "RF-20261029-B4-03",
        "source_title": "群馬県水産試験場研究報告第15号「KHV病既発生水域における野生コイのKHV保菌調査（桃ノ木川・広瀬川・荒砥川・神沢川）」",
        "publisher": "群馬県水産試験場", "source_url": gunma_report_15,
        "source_locator": "1 研究報告・KHV病既発生水域における野生コイのKHV保菌調査",
        "evidence_class": "A", "evidence_kind": "official_capture_record",
        "method_label": "魚類調査記録",
        "summary": "群馬県水産試験場の研究報告題名で、広瀬川を野生コイの調査水域として明記。詳細地点は収録しない。",
    },
    {
        "prefecture": "群馬県", "watershed": "利根川", "river": "烏川",
        "names": ["トウヨシノボリ", "ウグイ", "アブラハヤ", "オイカワ"],
        "survey_year": None, "source_id": "RF-20261029-B4-04",
        "source_title": "烏川圏域河川整備計画（変更）",
        "publisher": "群馬県", "source_url": karasu_plan,
        "source_locator": "第2章 第3節 河川環境について・烏川下流部",
        "evidence_class": "B", "evidence_kind": "official_environment_narrative",
        "method_label": "資料に掲載された生息魚",
        "summary": "烏川下流部の生息魚として明記された一般魚を原表記のまま収録。重要種と詳細区間は収録しない。",
    },
    {
        "prefecture": "群馬県", "watershed": "利根川", "river": "谷田川",
        "names": ["チャネルキャットフィッシュ"], "survey_year": None,
        "source_id": "RF-20261029-B4-05",
        "source_title": "水試だより48号「チャネルキャットフィッシュ」",
        "publisher": "群馬県水産試験場", "source_url": gunma_fisheries_news_48,
        "source_locator": "チャネルキャットフィッシュ・群馬県内の採捕記録",
        "evidence_class": "A", "evidence_kind": "official_capture_record",
        "method_label": "魚類調査記録",
        "summary": "群馬県水産試験場が、谷田川におけるチャネルキャットフィッシュの採捕記録を明記。詳細地点は収録しない。",
    },
    {
        "prefecture": "群馬県", "watershed": "利根川", "river": "赤谷川",
        "names": ["イワナ"], "survey_year": 2023, "source_id": "RF-20261029-B4-06",
        "source_title": "水産物に対する放射性物質の安全検査について（第315回）",
        "publisher": "群馬県", "source_url": gunma_2023_test,
        "source_locator": "2．検査結果（採捕魚）・赤谷川／イワナ行",
        "evidence_class": "A", "evidence_kind": "official_capture_record",
        "method_label": "魚類調査記録",
        "summary": "群馬県の2023年検査結果表で、赤谷川の採捕魚としてイワナを明記。市町村以下の採捕場所は収録しない。",
    },
    {
        "prefecture": "群馬県", "watershed": "利根川", "river": "鶴生田川",
        "names": ["カネヒラ"], "survey_year": 2017, "source_id": "RF-20261029-B4-07",
        "source_title": "邑楽・館林圏域河川整備計画（変更）",
        "publisher": "群馬県", "source_url": ora_tatebayashi_plan,
        "source_locator": "第2章 第3節（1）自然環境 2）魚類等",
        "evidence_class": "A", "evidence_kind": "official_fish_survey_record",
        "method_label": "魚類調査記録",
        "summary": "平成29年度河川水辺の国勢調査で鶴生田川のカネヒラを確認したと明記。詳細地点は収録しない。",
    },
]

for row in sources:
    matches = [e for e in atlas["entries"] if e["name"] == row["river"]
               and e.get("source_prefecture") == row["prefecture"]
               and e["kind"] == "official_river_name_only_v21"]
    assert len(matches) == 1, (row["prefecture"], row["river"])
    entry = matches[0]
    assert entry["water"] == row["watershed"], (row["river"], entry["water"])
    assert entry["id"] not in used, entry["id"]
    used.add(entry["id"])
    records = [{
        "recorded_name": name,
        "source_literal_label": name,
        "survey_year": row["survey_year"],
        "source_id": row["source_id"],
        "source_title": row["source_title"],
        "publisher": row["publisher"],
        "source_url": row["source_url"],
        "source_locator": row["source_locator"],
        "evidence_class": row["evidence_class"],
        "evidence_kind": row["evidence_kind"],
        "method_label": row["method_label"],
        "evidence_summary": row["summary"],
        "scope_note": row["summary"],
        "river_identity_review": "EXACT_EXISTING_PREFECTURE_WATERSHED_RIVER_LABEL",
        "conservation_review": "RIVER_LEVEL_ONLY_PRECISE_SITE_NOT_PUBLISHED",
        "publication_status": "STAGING_CANDIDATE",
    } for name in row["names"]]
    data["groups"].append({
        "prefecture": row["prefecture"],
        "watershed": entry["water"],
        "river": row["river"],
        "records": records,
        "scope_notes": [
            "公的資料の記述です。現在の生息や実在河川の同一性を保証しません。",
            "資料に市町村以下の採捕場所がある場合も、公開データには収録していません。",
        ],
        "id": "srcfish_" + hashlib.sha256(
            (row["prefecture"] + "|" + entry["water"] + "|" + row["river"]).encode()
        ).hexdigest()[:24],
        "navigation_target_id": entry["id"],
        "literal_fish_label_count": len(records),
        "individual_physical_river_identity_approved": False,
    })

data["release"] = "2026-10-29-gunma-evidence-batch4-staging"
data["group_count"] = len(data["groups"])
data["record_count"] = sum(len(g["records"]) for g in data["groups"])
DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
print(f"added {len(sources)} groups / {sum(len(row['names']) for row in sources)} records; "
      f"total {data['group_count']} / {data['record_count']}")
