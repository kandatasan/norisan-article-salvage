#!/usr/bin/env python3
"""Append reviewed Ibaraki evidence without creating river groups."""
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

ibaraki_2025_test = (
    "https://www.pref.ibaraki.jp/nourinsuisan/gyosei/chosei/houshanou/"
    "documents/hp20250501.pdf"
)
ibaraki_2024_test = (
    "https://www.pref.ibaraki.jp/nourinsuisan/gyosei/chosei/houshanou/"
    "documents/hp20240516.pdf"
)
juo_plan = (
    "https://www.pref.ibaraki.jp/doboku/kasen/keikaku/kasen/"
    "documents/h28328juuougawaseibikeikaku3.pdf"
)
sakuragawa_observation = (
    "https://www.pref.ibaraki.jp/soshiki/seikatsukankyo/kasumigauraesc/"
    "03_event/kekka/h24_04-06/h240519_sizen02/h240519_sizen02.htm"
)
koise_report = (
    "https://www.pref.ibaraki.jp/nourinsuisan/naisuishi/bullechin/"
    "documents/bull4407.pdf"
)

# Existing atlas groups retain their original watershed label. Fish labels are literal.
# Municipal sampling places and precise reaches are omitted from public records.
sources = [
    {
        "river": "久慈川", "names": ["アユ"], "survey_year": 2025,
        "source_id": "RF-20261029-B5-01",
        "source_title": "魚介類の分析結果について（５種20検体）",
        "publisher": "茨城県農林水産部漁政課", "source_url": ibaraki_2025_test,
        "source_locator": "（2）内水面魚介類・アユ／久慈川行",
        "evidence_class": "A", "evidence_kind": "official_capture_record",
        "method_label": "魚類調査記録",
        "summary": "茨城県の2025年検査結果表で、久慈川の採取魚としてアユを明記。市町村以下の採取場所は収録しない。",
    },
    {
        "river": "那珂川", "names": ["アユ"], "survey_year": 2025,
        "source_id": "RF-20261029-B5-02",
        "source_title": "魚介類の分析結果について（５種20検体）",
        "publisher": "茨城県農林水産部漁政課", "source_url": ibaraki_2025_test,
        "source_locator": "（2）内水面魚介類・アユ／那珂川行",
        "evidence_class": "A", "evidence_kind": "official_capture_record",
        "method_label": "魚類調査記録",
        "summary": "茨城県の2025年検査結果表で、那珂川の採取魚としてアユを明記。市町村以下の採取場所は収録しない。",
    },
    {
        "river": "鬼怒川", "names": ["ウナギ（天然）"], "survey_year": 2025,
        "source_id": "RF-20261029-B5-03",
        "source_title": "魚介類の分析結果について（５種20検体）",
        "publisher": "茨城県農林水産部漁政課", "source_url": ibaraki_2025_test,
        "source_locator": "（2）内水面魚介類・ウナギ（天然）／鬼怒川行",
        "evidence_class": "A", "evidence_kind": "official_capture_record",
        "method_label": "魚類調査記録",
        "summary": "茨城県の2025年検査結果表で、鬼怒川の採取魚としてウナギ（天然）を明記。市町村以下の採取場所は収録しない。",
    },
    {
        "river": "利根川", "names": ["ウナギ（天然）"], "survey_year": 2025,
        "source_id": "RF-20261029-B5-04",
        "source_title": "魚介類の分析結果について（５種20検体）",
        "publisher": "茨城県農林水産部漁政課", "source_url": ibaraki_2025_test,
        "source_locator": "（2）内水面魚介類・ウナギ（天然）／利根川行",
        "evidence_class": "A", "evidence_kind": "official_capture_record",
        "method_label": "魚類調査記録",
        "summary": "茨城県の2025年検査結果表で、利根川の採取魚としてウナギ（天然）を明記。市町村以下の採取場所は収録しない。",
    },
    {
        "river": "大北川", "names": ["ヤマメ"], "survey_year": 2024,
        "source_id": "RF-20261029-B5-05",
        "source_title": "魚介類の分析結果について（１種２検体）",
        "publisher": "茨城県農林水産部漁政課", "source_url": ibaraki_2024_test,
        "source_locator": "（1）内水面魚介類・ヤマメ／大北川行",
        "evidence_class": "A", "evidence_kind": "official_capture_record",
        "method_label": "魚類調査記録",
        "summary": "茨城県の2024年検査結果表で、大北川の採取魚としてヤマメを明記。ダム名以下の採取場所は収録しない。",
    },
    {
        "river": "十王川",
        "names": ["ヤマメ", "ギンブナ", "オイカワ", "シマヨシノボリ", "サケ", "アユ"],
        "survey_year": None, "source_id": "RF-20261029-B5-06",
        "source_title": "十王川水系河川整備計画（変更）",
        "publisher": "茨城県", "source_url": juo_plan,
        "source_locator": "第1章 第2節 河川の現状と課題・（2）動植物の生息・生育・繁殖環境",
        "evidence_class": "B", "evidence_kind": "official_environment_narrative",
        "method_label": "資料に掲載された生息魚",
        "summary": "河川整備計画が十王川流域で生息確認済みとする一般魚を原表記のまま収録。重要種は収録しない。",
    },
    {
        "river": "桜川",
        "names": ["アユ", "スゴモロコ", "タモロコ", "ヌマチチブ", "ヨシノボリ", "ハス", "オイカワ", "アメリカナマズ"],
        "survey_year": 2012, "source_id": "RF-20261029-B5-07",
        "source_title": "平成24年度 第2回霞ヶ浦自然観察会 桜川の自然と魚観察会",
        "publisher": "茨城県霞ケ浦環境科学センター", "source_url": sakuragawa_observation,
        "source_locator": "本日観察した魚類等",
        "evidence_class": "A", "evidence_kind": "official_observation_record",
        "method_label": "魚類調査記録",
        "summary": "県の自然観察会結果ページが、桜川で当日観察した魚類として8魚名を列挙。集合場所等は収録しない。",
    },
    {
        "river": "恋瀬川", "names": ["オイカワ", "ハス", "アユ", "ニゴイ", "ヨシノボリ属"],
        "survey_year": None, "source_id": "RF-20261029-B5-08",
        "source_title": "霞ヶ浦流入河川における魚類の流程分布と河川形態",
        "publisher": "茨城県水産試験場内水面支場", "source_url": koise_report,
        "source_locator": "茨城内水試研究報告44・恋瀬川（1996年から2002年までの採集結果）",
        "evidence_class": "A", "evidence_kind": "official_fish_survey_record",
        "method_label": "魚類調査記録",
        "summary": "県水産試験場報告が、1996～2002年の恋瀬川採集個体数上位魚として5魚名を明記。属表記は確定種へ置換しない。",
    },
]

for row in sources:
    matches = [e for e in atlas["entries"] if e["name"] == row["river"]
               and e.get("source_prefecture") == "茨城県"
               and e["kind"] == "official_river_name_only_v21"]
    assert len(matches) == 1, row["river"]
    entry = matches[0]
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
        "prefecture": "茨城県",
        "watershed": entry["water"],
        "river": row["river"],
        "records": records,
        "scope_notes": [
            "公的資料の記述です。現在の生息や実在河川の同一性を保証しません。",
            "既存グループの水系未確認ラベルは変更せず、市町村以下の採取場所を公開しません。",
        ],
        "id": "srcfish_" + hashlib.sha256(
            ("茨城県|" + entry["water"] + "|" + row["river"]).encode()
        ).hexdigest()[:24],
        "navigation_target_id": entry["id"],
        "literal_fish_label_count": len(records),
        "individual_physical_river_identity_approved": False,
    })

data["release"] = "2026-10-29-ibaraki-evidence-batch5-staging"
data["group_count"] = len(data["groups"])
data["record_count"] = sum(len(g["records"]) for g in data["groups"])
DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
print(f"added {len(sources)} groups / {sum(len(row['names']) for row in sources)} records; "
      f"total {data['group_count']} / {data['record_count']}")
