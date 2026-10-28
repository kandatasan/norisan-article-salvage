#!/usr/bin/env python3
"""Append the second reviewed Gifu/Saitama evidence batch to existing groups."""
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

gifu_plan = "https://www.pref.gifu.lg.jp/uploaded/attachment/1497.pdf"
saitama_report = "https://www.pref.saitama.lg.jp/documents/253444/j036-hyoukasho-10_8.pdf"
saitama_text = "https://www.pref.saitama.lg.jp/documents/4705/kawakentext.pdf"

# Fish labels are copied literally. Precise reaches and conservation-sensitive fish are omitted.
sources = [
    ("岐阜県", "木曽川", "大江川", "B", ["フナ類", "モツゴ"],
     "一級河川木曽川水系 境川圏域河川整備計画", "岐阜県", gifu_plan,
     "1.2.3 (2)河川ごとの特徴・大江川／資料p19・PDF p20", None,
     "大江川の河川別説明で、緩流域を好む魚として明記。詳細区間は収録しない。"),
    ("埼玉県", "利根川", "綾瀬川", "A", ["タイリクバラタナゴ"],
     "蓮田都市計画事業高虫西部土地区画整理事業環境影響評価書 第10章10.8 動物", "蓮田市", saitama_report,
     "魚類現地調査結果・表10.8-9／資料p10.8-16・PDF p16", 2021,
     "網等による捕獲と直接観察による現地調査で、綾瀬川の確認魚として明記。保全対象魚と詳細地点は収録しない。"),
    ("埼玉県", "利根川", "大落古利根川", "B", ["モツゴ"],
     "令和元年度版 川の国埼玉検定（中・上級編）検定用テキスト", "埼玉県", saitama_text,
     "2 川の形態と自然・環境「埼玉県に生息する主な魚類」／資料p5・PDF p5", None,
     "埼玉県環境科学国際センターの魚類研究成果から作成された資料で、大落古利根川産モツゴとして掲載。詳細地点は収録しない。"),
    ("埼玉県", "利根川", "神流川", "B", ["カジカ"],
     "令和元年度版 川の国埼玉検定（中・上級編）検定用テキスト", "埼玉県", saitama_text,
     "2 川の形態と自然・環境「埼玉県に生息する主な魚類」／資料p5・PDF p5", None,
     "埼玉県環境科学国際センターの魚類研究成果から作成された資料で、神流川産カジカとして掲載。詳細地点は収録しない。"),
    ("埼玉県", "荒川", "赤平川", "B", ["ウグイ"],
     "令和元年度版 川の国埼玉検定（中・上級編）検定用テキスト", "埼玉県", saitama_text,
     "2 川の形態と自然・環境「埼玉県に生息する主な魚類」／資料p5・PDF p5", None,
     "埼玉県環境科学国際センターの魚類研究成果から作成された資料で、赤平川産ウグイとして掲載。詳細地点は収録しない。"),
]

for index, (pref, documented_water, river, grade, names, title, publisher, url, locator, year, summary) in enumerate(sources, 1):
    matches = [e for e in atlas["entries"] if e["name"] == river
               and e.get("source_prefecture") == pref
               and e["kind"] == "official_river_name_only_v21"]
    assert len(matches) == 1, (pref, river)
    entry = matches[0]
    assert entry["id"] not in used, entry["id"]
    used.add(entry["id"])
    records = [{
        "recorded_name": name,
        "source_literal_label": name,
        "survey_year": year,
        "source_id": f"RF-20261029-B2-{index:02d}",
        "source_title": title,
        "publisher": publisher,
        "source_url": url,
        "source_locator": locator,
        "evidence_class": grade,
        "evidence_kind": "official_fish_survey_table" if grade == "A" else "official_environment_narrative",
        "method_label": "魚類調査記録" if grade == "A" else "資料に掲載された生息魚",
        "evidence_summary": summary,
        "scope_note": summary,
        "river_identity_review": ("EXACT_EXISTING_PREFECTURE_WATERSHED_RIVER_LABEL"
                                  if entry["water"] == documented_water
                                  else "EXACT_EXISTING_PREFECTURE_RIVER_LABEL_WITH_SOURCE_WATERSHED"),
        "conservation_review": "NO_PRECISE_SITE_OR_SENSITIVE_FISH_PUBLISHED",
        "publication_status": "STAGING_CANDIDATE",
    } for name in names]
    group = {
        "prefecture": pref,
        "watershed": entry["water"],
        "river": river,
        "records": records,
        "scope_notes": [
            *([f"原資料の水系名は{documented_water}。既存グループの水系未確認表示を変更せず、川名と都道府県を照合しています。"]
              if entry["water"] != documented_water else []),
            "公的資料の記述です。現在の生息や実在河川の同一性を保証しません。",
        ],
        "id": "srcfish_" + hashlib.sha256((pref + "|" + entry["water"] + "|" + river).encode()).hexdigest()[:24],
        "navigation_target_id": entry["id"],
        "literal_fish_label_count": len(records),
        "individual_physical_river_identity_approved": False,
    }
    if entry["water"] != documented_water:
        group["documented_watershed"] = documented_water
    data["groups"].append(group)

data["release"] = "2026-10-29-gifu-saitama-evidence-batch2-staging"
data["group_count"] = len(data["groups"])
data["record_count"] = sum(len(g["records"]) for g in data["groups"])
DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
print(f"added {len(sources)} groups / {sum(len(row[4]) for row in sources)} records; total {data['group_count']} / {data['record_count']}")
