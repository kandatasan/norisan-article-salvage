#!/usr/bin/env python3
"""One-off, reviewed source-name fish additions; never creates river groups."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).parent / "source" / "data"
atlas = json.loads((ROOT / "atlas.json").read_text())
prior = json.loads((ROOT / "fish_source_connections_v01.json").read_text())
existing = {g["navigation_target_id"] for g in prior["groups"] if g["navigation_target_id"]}
data = {"schema": "tsurikue-source-fish-additions-v02", "release": "2026-10-28-river-evidence-review-staging",
        "display_scope": "SOURCE_PUBLISHED_RIVER_FISH_REFERENCES_ONLY", "no_precise_locations_or_river_codes": True,
        "held_records_excluded": True, "group_count": 0, "record_count": 0, "groups": []}
data_path = ROOT / "fish_source_connections_v02_additions.json"

# Each item is a river-specific passage/table, with conservative fish labels only.
# No rare species, exact survey stations or location coordinates are copied.
sources = [
    ("青森県", "岩木川", "旧十川", "A", ["コイ", "ギンブナ", "オイカワ", "ドジョウ", "ウグイ"],
     "岩木川流域保全計画", "青森県",
     "https://www.pref.aomori.lg.jp/soshiki/kankyo/kankyo/files/plan10.pdf", "図3・資料p23／PDF p25", None,
     "旧十川の欄に魚名を示し、現地調査時の確認種と注記。"),
    ("青森県", "岩木川", "十川", "A", ["コイ", "ギンブナ", "オイカワ", "アブラハヤ", "ドジョウ", "ウグイ"],
     "岩木川流域保全計画", "青森県",
     "https://www.pref.aomori.lg.jp/soshiki/kankyo/kankyo/files/plan10.pdf", "図3・資料p23／PDF p25", None,
     "十川の欄に魚名を示し、現地調査時の確認種と注記。"),
    ("大阪府", "石津川", "和田川", "A", ["コイ", "ギンブナ", "オイカワ", "タモロコ", "ドジョウ", "カダヤシ", "オオクチバス"],
     "参考資料3-3 大阪府内河川に生息している魚類", "大阪府",
     "https://www.pref.osaka.lg.jp/documents/824/18209-sankou-3-320.pdf", "和田川・平成21年以降の魚類調査結果欄／PDF p3", 2010,
     "和田川の調査結果欄に魚名を列記。出典欄は平成22年調査。"),
    ("大阪府", "石津川", "百済川", "B", ["ウナギ", "コイ", "トウヨシノボリ"],
     "石津川水系河川整備計画", "大阪府",
     "https://www.pref.osaka.lg.jp/documents/22182/ishizugawa.pdf", "第1章 3)自然環境 ②魚類等動物・資料p2／PDF p4", None,
     "百済川上流で挙げられた魚名。確認の方法や年は記載なし。"),
    ("広島県", "岡ノ下川", "岡ノ下川", "B", ["ボラ", "マハゼ", "フナ類", "オイカワ", "カワムツ"],
     "二級河川岡ノ下川水系河川整備計画", "広島県",
     "https://www.pref.hiroshima.lg.jp/uploaded/attachment/11095.pdf", "1章 (2)動植物・資料p6／PDF p6", None,
     "岡ノ下川の感潮区間と上流について魚名を記述。"),
    ("広島県", "二河川", "二河川", "B", ["カワムツ"],
     "二級河川二河川水系河川整備基本方針", "広島県",
     "https://www.pref.hiroshima.lg.jp/uploaded/attachment/11099.pdf", "1.1 (2)河川及び流域の自然環境・資料p2／PDF p2", None,
     "二河川の自然環境の説明で、カワムツがほぼ全域に分布と記述。"),
    ("広島県", "堺川", "堺川", "B", ["アユ"],
     "二級河川堺川水系河川整備基本方針", "広島県",
     "https://www.pref.hiroshima.lg.jp/uploaded/attachment/120360.pdf", "1.1 (4)河川環境・資料p5／PDF p4", None,
     "堺川でアユの遡上があると記述。放流記録とは扱わない。"),
    ("広島県", "太田川", "太田川", "B", ["オイカワ"],
     "太田川河川事務所・生きもの図鑑 オイカワ", "国土交通省中国地方整備局太田川河川事務所",
     "https://www.cgr.mlit.go.jp/ootagawa/Bio/fishes/index218.htm", "オイカワ・生息場所／太田川の記述", None,
     "太田川でオイカワが釣られると記述。"),
    ("広島県", "小瀬川", "小瀬川", "B", ["アユ"],
     "弥栄ダム周辺の生き物・アユ", "国土交通省中国地方整備局弥栄ダム管理所",
     "https://www.cgr.mlit.go.jp/yasaka/ikimono/organism2018/d0016.htm", "アユ・弥栄ダム周辺での記述", None,
     "ダム下流の小瀬川でアユが見られると記述。"),
    ("山口県", "佐波川", "佐波川", "B", ["ドジョウ", "カワムツ", "カワヨシノボリ", "ドンコ"],
     "佐波川小野水辺の楽校・佐波川の奈美地区にいる生き物", "国土交通省中国地方整備局山口河川国道事務所",
     "https://www.cgr.mlit.go.jp/yamaguchi/river/school/08.html", "魚類欄", None,
     "佐波川で見られる魚として記述。希少種と細かな地点は収録しない。"),
    ("広島県", "太田川", "三篠川", "B", ["ニホンウナギ", "ドジョウ", "ドンコ"],
     "太田川水系河川整備計画（令和2年版）・現状と課題", "国土交通省中国地方整備局太田川河川事務所",
     "https://www.cgr.mlit.go.jp/ootagawa/plan2/plan2pdf/03plan2.pdf", "3章 4)支川三篠川・資料p77／PDF p52", None,
     "支川三篠川の節で生息魚として列記。希少種と詳細地点は収録しない。"),
    ("広島県", "太田川", "滝山川", "B", ["アユ", "カワヨシノボリ"],
     "太田川水系河川整備計画（令和2年版）・現状と課題", "国土交通省中国地方整備局太田川河川事務所",
     "https://www.cgr.mlit.go.jp/ootagawa/plan2/plan2pdf/03plan2.pdf", "3章 6)支川滝山川・資料p78／PDF p53", None,
     "支川滝山川の節で生息魚として列記。希少種と詳細地点は収録しない。"),
    ("広島県", "太田川", "根谷川", "B", ["ニホンウナギ", "ドンコ"],
     "太田川水系河川整備計画（令和2年版）・現状と課題", "国土交通省中国地方整備局太田川河川事務所",
     "https://www.cgr.mlit.go.jp/ootagawa/plan2/plan2pdf/03plan2.pdf", "3章 5)支川根谷川・資料p78／PDF p53", None,
     "支川根谷川の節で見られる魚として列記。希少種と詳細地点は収録しない。"),
    ("広島県", "瀬野川", "熊野川", "B", ["オイカワ", "カワムツ"],
     "二級河川瀬野川水系河川整備計画【変更】", "広島県",
     "https://www.pref.hiroshima.lg.jp/uploaded/attachment/554947.pdf", "1.2.3 (2)動植物・熊野川の段落・資料p13／PDF p14", None,
     "熊野川の河川環境説明で生息魚として列記。重要種と詳細地点は収録しない。"),
    ("広島県", "江の川", "江の川", "B", ["アユ", "ウグイ", "オイカワ", "カワムツ"],
     "江の川本川ブロック河川環境に関する現状と課題", "広島県",
     "https://www.pref.hiroshima.lg.jp/soshiki/99/1172196461943.html", "1-2-3 (2)動植物・土師ダムから三次市に至る本川中流域", None,
     "江の川本川の中流域の説明で生息魚として列記。支川全体への割り振りはしない。"),
    ("山口県", "錦川", "錦川", "A", ["オイカワ", "ウナギ"],
     "錦川で採集されたアユ及びその他の魚類からのPCRによるEdwardsiella ictaluriの検出状況", "山口県水産研究センター",
     "https://www.pref.yamaguchi.lg.jp/uploaded/attachment/197780.pdf", "研究報告第7号・資料pp77-82／PDF pp75-80、材料及び方法・結果", 2008,
     "錦川の河川生息魚を採捕して検査した調査の魚名。放流稚アユは収録しない。"),
]

for pref, water, river, grade, names, title, publisher, url, locator, year, summary in sources:
    matches = [e for e in atlas["entries"] if e["name"] == river and e["water"] == water
               and e.get("source_prefecture") == pref and e["kind"] == "official_river_name_only_v21"]
    assert len(matches) == 1, (pref, water, river)
    entry = matches[0]
    assert entry["id"] not in existing, entry["id"]
    existing.add(entry["id"])
    group_id = "srcfish_" + hashlib.sha256((pref+"|"+water+"|"+river).encode()).hexdigest()[:24]
    records = [{
        "recorded_name": name, "source_literal_label": name, "survey_year": year,
        "source_id": "RF-20261028-" + str(sources.index((pref, water, river, grade, names, title, publisher, url, locator, year, summary)) + 1).zfill(2),
        "source_title": title, "publisher": publisher, "source_url": url, "source_locator": locator,
        "evidence_class": grade,
        "evidence_kind": "official_fish_survey_table" if grade == "A" else "official_environment_narrative",
        "method_label": "魚類調査記録" if grade == "A" else "資料に掲載された生息魚",
        "evidence_summary": summary, "scope_note": summary,
        "river_identity_review": "EXACT_EXISTING_PREFECTURE_WATERSHED_RIVER_LABEL",
        "conservation_review": "NO_PRECISE_SITE_OR_SENSITIVE_FISH_PUBLISHED",
        "publication_status": "STAGING_CANDIDATE"
    } for name in names]
    data["groups"].append({
        "prefecture": pref, "watershed": water, "river": river, "records": records,
        "scope_notes": ["公的資料の記述です。現在の生息や実在河川の同一性を保証しません。"],
        "id": group_id, "navigation_target_id": entry["id"],
        "literal_fish_label_count": len(records), "individual_physical_river_identity_approved": False,
    })

data["group_count"] = len(data["groups"])
data["record_count"] = sum(len(g["records"]) for g in data["groups"])
data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
print(f"added {len(sources)} groups / {sum(len(x[4]) for x in sources)} records; total {data['group_count']} / {data['record_count']}")
