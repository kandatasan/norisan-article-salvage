#!/usr/bin/env python3
"""Append reviewed Saitama/Shiga evidence without creating river groups."""
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

saitama_text = "https://www.pref.saitama.lg.jp/documents/4705/kawakentext.pdf"
shiga_plan = "https://www.pref.shiga.lg.jp/documents/1178/5466370.pdf"

# Fish labels are copied literally. Precise reaches and conservation-sensitive fish are omitted.
sources = [
    ("埼玉県", "荒川", "越辺川", None, ["オイカワ"],
     "令和元年度版 川の国埼玉検定（中・上級編）検定用テキスト", "埼玉県", saitama_text,
     "2 川の形態と自然・環境「埼玉県に生息する主な魚類」／資料p5・PDF p5",
     "埼玉県環境科学国際センターの魚類研究成果から作成された資料で、越辺川産オイカワとして掲載。詳細地点は収録しない。"),
    ("滋賀県", "淀川", "野洲川", None, ["タカハヤ", "アユ", "ナマズ"],
     "淀川水系 甲賀・湖南圏域河川整備計画（変更）", "滋賀県", shiga_plan,
     "1.2.3 (1)生物の生息、生育・魚類／資料pp13-14・PDF pp14-15",
     "野洲川の河川別説明で生息魚として明記。資料中で希少性が明記された魚と詳細区間は収録しない。"),
    ("滋賀県", "淀川", "山賀川", "山賀川(新守山川)",
     ["オオクチバス", "ブルーギル", "オイカワ", "カワムツ", "タモロコ", "カマツカ"],
     "淀川水系 甲賀・湖南圏域河川整備計画（変更）", "滋賀県", shiga_plan,
     "1.2.3 (1)生物の生息、生育・山賀川(新守山川)／資料pp15-16・PDF pp16-17",
     "資料表記「山賀川(新守山川)」の河川別説明で生息魚として明記。希少魚と詳細区間は収録しない。"),
    ("滋賀県", "淀川", "葉山川", None, ["アユ", "オウミヨシノボリ"],
     "淀川水系 甲賀・湖南圏域河川整備計画（変更）", "滋賀県", shiga_plan,
     "1.2.3 (1)生物の生息、生育・葉山川／資料p16・PDF p17",
     "葉山川の河川別説明で確認魚として明記。詳細区間は収録しない。"),
    ("滋賀県", "淀川", "草津川", None, ["オイカワ"],
     "淀川水系 甲賀・湖南圏域河川整備計画（変更）", "滋賀県", shiga_plan,
     "1.2.3 (1)生物の生息、生育・草津川／資料p16・PDF p17",
     "草津川の河川別説明で優占魚として明記。資料中で要注目等とされた魚と詳細区間は収録しない。"),
]

for index, (pref, water, river, documented_river, names, title, publisher, url, locator, summary) in enumerate(sources, 1):
    matches = [e for e in atlas["entries"] if e["name"] == river
               and e.get("source_prefecture") == pref
               and e["kind"] == "official_river_name_only_v21"]
    assert len(matches) == 1, (pref, river)
    entry = matches[0]
    assert entry["water"] == water, (pref, river, entry["water"])
    assert entry["id"] not in used, entry["id"]
    used.add(entry["id"])
    identity_review = ("EXISTING_PREFECTURE_WATERSHED_RIVER_LABEL_WITH_DOCUMENTED_ALIAS"
                       if documented_river else "EXACT_EXISTING_PREFECTURE_WATERSHED_RIVER_LABEL")
    records = [{
        "recorded_name": name,
        "source_literal_label": name,
        "survey_year": None,
        "source_id": f"RF-20261029-B3-{index:02d}",
        "source_title": title,
        "publisher": publisher,
        "source_url": url,
        "source_locator": locator,
        "evidence_class": "B",
        "evidence_kind": "official_environment_narrative",
        "method_label": "資料に掲載された生息魚",
        "evidence_summary": summary,
        "scope_note": summary,
        "river_identity_review": identity_review,
        "conservation_review": "NO_PRECISE_SITE_OR_SENSITIVE_FISH_PUBLISHED",
        "publication_status": "STAGING_CANDIDATE",
    } for name in names]
    group = {
        "prefecture": pref,
        "watershed": entry["water"],
        "river": river,
        "records": records,
        "scope_notes": [
            *([f"原資料の河川表記は{documented_river}。既存グループ名を変更せず、同じ資料内の表記を別フィールドに保持しています。"]
              if documented_river else []),
            "公的資料の記述です。現在の生息や実在河川の同一性を保証しません。",
        ],
        "id": "srcfish_" + hashlib.sha256((pref + "|" + entry["water"] + "|" + river).encode()).hexdigest()[:24],
        "navigation_target_id": entry["id"],
        "literal_fish_label_count": len(records),
        "individual_physical_river_identity_approved": False,
    }
    if documented_river:
        group["documented_river_label"] = documented_river
    data["groups"].append(group)

data["release"] = "2026-10-29-saitama-shiga-evidence-batch3-staging"
data["group_count"] = len(data["groups"])
data["record_count"] = sum(len(g["records"]) for g in data["groups"])
DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
print(f"added {len(sources)} groups / {sum(len(row[4]) for row in sources)} records; total {data['group_count']} / {data['record_count']}")
