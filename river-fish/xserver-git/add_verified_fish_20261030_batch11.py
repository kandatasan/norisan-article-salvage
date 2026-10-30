#!/usr/bin/env python3
"""Append reviewed Fukuoka and Okinawa river-specific fish evidence."""
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
    dict(prefecture="福岡県", river="若久川", names=["ウナギ", "アユ"],
         year=2012, sid="RF-20261030-B11-01", title="議事の要旨 平成24年7月31日",
         publisher="福岡市", url="https://www.city.fukuoka.lg.jp/kankyo/k-chosei/hp/assess/giji/h191129_2_2.html",
         locator="委員発言（若久川にウナギやアユが上ってきている）",
         cls="B", kind="official_environment_narrative", method="資料に掲載された生息魚",
         summary="福岡市の公開議事要旨が若久川へ遡上している魚として明記した2魚名を原表記で収録。地点は収録しない。"),
    dict(prefecture="沖縄県", river="安謝川",
         names=["コボラ", "オキナヒメジ", "コバンヒメジ", "Apogon robustus", "クロサギ",
                "ヒトスジタマガシラ", "ミナミクロダイ", "ハマフエフキ", "マトフエフキ",
                "シモフリフエフキ", "オキフエダイ", "ニセクロホシフエダイ", "ナミフエダイ",
                "ヨスジフエダイ", "ヒメフエダイ", "ロウニンアジ", "ギンガメアジ", "シマヒイラギ",
                "スミゾメスズメダイ", "シロクラベラ", "ハラスジベラ", "クロハギ", "アミアイゴ", "アイゴ"],
         year=1981, sid="RF-20261030-B11-02", title="糸満周辺海域のハマフエフキ幼稚仔保育場造成事業調査",
         publisher="沖縄県水産試験場", url="https://www.pref.okinawa.jp/fish/kenkyu/jigyohokoku-data/jihous56/76_128.pdf",
         locator="89頁 表III-6 安謝川河口で得られた魚類",
         cls="A", kind="official_fish_survey_record", method="魚類調査記録",
         summary="沖縄県水産試験場報告の1981年安謝川河口域2回採集表から、保全審査記号のない24魚名だけを原表記で収録。採集点、個体数、体長は収録しない。"),
    dict(prefecture="沖縄県", river="比謝川", names=["Anguilla marmorata QPG"],
         year=None, sid="RF-20261030-B11-03", title="沖縄県水産試験場事業報告書（魚類目録）",
         publisher="沖縄県水産試験場", url="https://www.pref.okinawa.jp/fish/kenkyu/jigyohokoku-data/jihous07/142_160.pdf",
         locator="魚類目録 6. Anguilla marmorata QPG・採集地欄",
         cls="A", kind="official_fish_survey_record", method="魚類調査記録",
         summary="沖縄県水産試験場の魚類目録が採集地として比謝川を明記した学名1件を原表記のまま収録。和名への置換と地点補完は行わない。"),
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

data["release"] = "2026-10-30-fukuoka-okinawa-evidence-batch11-staging"
data["group_count"] = len(data["groups"])
data["record_count"] = sum(len(g["records"]) for g in data["groups"])
DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
print(f"added {len(sources)} groups / {sum(len(row['names']) for row in sources)} records; total {data['group_count']} / {data['record_count']}")
