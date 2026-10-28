#!/usr/bin/env python3
"""Append reviewed Gifu and Saitama evidence without creating river groups."""
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

gifu_plan = "https://www.pref.gifu.lg.jp/uploaded/attachment/1489.pdf"
gifu_guide = "https://www.pref.gifu.lg.jp/uploaded/attachment/1458.pdf"
saitama_report = "https://www.pref.saitama.lg.jp/documents/253444/j036-hyoukasho-10_8.pdf"

# Fish labels are copied literally. Rare fish, precise reaches and survey stations are omitted.
sources = [
    ("岐阜県", "木曽川", "可児川", "B", ["オイカワ", "カワムツ", "カマツカ"],
     "一級河川木曽川水系 木曽川中流圏域河川整備計画", "岐阜県", gifu_plan,
     "1.2.3 (2)河川ごとの特徴・可児川／資料p17・PDF p22", None,
     "可児川の河川別説明で確認魚として明記。貴重種と詳細区間は収録しない。"),
    ("岐阜県", "木曽川", "坂本川", "B", ["カワムツ", "オイカワ", "ヨシノボリ"],
     "岐阜県自然共生川づくりの手引き（案）巻末資料2 岐阜県の県土と水辺", "岐阜県", gifu_guide,
     "3.1 ②坂本川／巻末資料p2-39・PDF p40", None,
     "坂本川の河川別説明で確認魚として明記。ヨシノボリを確定種へ置換しない。"),
    ("岐阜県", "木曽川", "飛騨川", "B", ["アユ", "ウグイ", "オイカワ"],
     "岐阜県自然共生川づくりの手引き（案）巻末資料2 岐阜県の県土と水辺", "岐阜県", gifu_guide,
     "3.1 ③飛騨川／巻末資料p2-40・PDF p41", None,
     "飛騨川の河川別説明で生息魚として明記。希少性に懸念がある魚名は収録しない。"),
    ("岐阜県", "木曽川", "矢戸川", "B", ["オイカワ", "カワムツ", "ドジョウ", "カワヨシノボリ"],
     "一級河川木曽川水系 木曽川中流圏域河川整備計画", "岐阜県", gifu_plan,
     "1.2.3 (2)河川ごとの特徴・矢戸川／資料p17・PDF p22", None,
     "矢戸川の河川別説明で生息魚として明記。貴重種と詳細区間は収録しない。"),
    ("岐阜県", "木曽川", "久々利川", "B", ["オイカワ", "カワムツ", "トウヨシノボリ", "モツゴ"],
     "一級河川木曽川水系 木曽川中流圏域河川整備計画", "岐阜県", gifu_plan,
     "1.2.3 (2)河川ごとの特徴・久々利川／資料pp17-18・PDF pp22-23", None,
     "久々利川の河川別説明で確認魚として明記。貴重種と詳細区間は収録しない。"),
    ("岐阜県", "木曽川", "唐沢川", "B", ["オイカワ", "カワムツ"],
     "一級河川木曽川水系 木曽川中流圏域河川整備計画", "岐阜県", gifu_plan,
     "1.2.3 (2)河川ごとの特徴・唐沢川／資料p18・PDF p23", None,
     "唐沢川の河川別説明で確認魚として明記。貴重種と詳細区間は収録しない。"),
    ("岐阜県", "木曽川", "加茂川", "B", ["オイカワ", "カワムツ", "アユ", "ウキゴリ", "トウヨシノボリ"],
     "一級河川木曽川水系 木曽川中流圏域河川整備計画", "岐阜県", gifu_plan,
     "1.2.3 (2)河川ごとの特徴・加茂川／資料p18・PDF p23", None,
     "加茂川の河川別説明で確認魚として明記。詳細区間は収録しない。"),
    ("埼玉県", "利根川", "元荒川", "A", ["オイカワ", "モツゴ", "タモロコ", "カマツカ", "ニゴイ", "ウキゴリ"],
     "蓮田都市計画事業高虫西部土地区画整理事業環境影響評価書 第10章10.8 動物", "蓮田市", saitama_report,
     "魚類現地調査結果・表10.8-9／資料p10.8-16・PDF p16", 2021,
     "網等による捕獲と直接観察による現地調査で、元荒川の確認魚として明記。保全対象魚と詳細地点は収録しない。"),
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
        "source_id": f"RF-20261029-{index:02d}",
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

data["release"] = "2026-10-29-gifu-saitama-evidence-staging"
data["group_count"] = len(data["groups"])
data["record_count"] = sum(len(g["records"]) for g in data["groups"])
DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
print(f"added {len(sources)} groups / {sum(len(row[4]) for row in sources)} records; total {data['group_count']} / {data['record_count']}")
