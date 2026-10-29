#!/usr/bin/env python3
"""Append reviewed Ibaraki and Chiba evidence without creating river groups."""
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
    dict(prefecture="茨城県", river="小貝川", names=["ウナギ(天然)"], year=2025,
         sid="RF-20261029-B6-01", title="魚介類の分析結果について（27種105検体）",
         publisher="茨城県農林水産部漁政課",
         url="https://www.pref.ibaraki.jp/nourinsuisan/gyosei/chosei/houshanou/documents/hp20250703.pdf",
         locator="（2）内水面魚介類・ウナギ(天然)／小貝川行", cls="A",
         kind="official_capture_record", method="魚類調査記録",
         summary="茨城県の2025年検査結果表で、小貝川の採取魚としてウナギ(天然)を明記。市町村以下の採取場所は収録しない。"),
    dict(prefecture="茨城県", river="里川", names=["ウキゴリ"], year=None,
         sid="RF-20261029-B6-02", title="いばらき魚顔帳 ウキゴリ類（ハゼ科）",
         publisher="茨城県水産試験場内水面支場",
         url="https://www.pref.ibaraki.jp/nourinsuisan/naisuishi/gyogancho/documents/019_ukigori.pdf",
         locator="県内の分布・ウキゴリ", cls="B", kind="official_environment_narrative",
         method="資料に掲載された生息魚",
         summary="県の魚類帳が、久慈川水系の一次支流では里川にウキゴリが確認される旨を明記。詳細地点は収録しない。"),
    dict(prefecture="千葉県", river="根木名川", names=["コイ", "ボラ", "モツゴ", "オイカワ"], year=None,
         sid="RF-20261029-B6-03", title="水生生物の保全に係る水質環境基準の水域類型指定（案）",
         publisher="千葉県", url="https://www.pref.chiba.lg.jp/suiho/shingikai/mizukankyou/documents/h230627_toushin.pdf",
         locator="根木名川・魚類の生息状況", cls="B", kind="official_environment_narrative",
         method="資料に掲載された生息魚", summary="千葉県資料の根木名川欄が魚類の生息状況として4魚名を明記。環境基準点名は収録しない。"),
    dict(prefecture="千葉県", river="長門川", names=["ウナギ", "ワカサギ", "シラウオ", "サケ", "ニゴイ", "タモロコ", "スゴモロコ", "モツゴ", "ウグイ", "オイカワ"], year=None,
         sid="RF-20261029-B6-04", title="水生生物の保全に係る水質環境基準の水域類型指定（案）",
         publisher="千葉県", url="https://www.pref.chiba.lg.jp/suiho/shingikai/mizukankyou/documents/h230627_toushin.pdf",
         locator="長門川・魚類の生息状況", cls="B", kind="official_environment_narrative",
         method="資料に掲載された生息魚", summary="千葉県資料の長門川欄に列挙された生息魚から一般魚10件を原表記のまま収録。希少性審査対象は除外。"),
    dict(prefecture="千葉県", river="黒部川", names=["シマドジョウ", "スゴモロコ"], year=None,
         sid="RF-20261029-B6-05", title="利根川水系香取・銚子圏域河川整備計画 第3章 河川の現状と課題",
         publisher="千葉県", url="https://www.pref.chiba.lg.jp/kasei/keikaku/rivers/plan/katori-choushi/documents/plan-kat-cho-03.pdf",
         locator="第3章（2）自然環境・黒部川", cls="B", kind="official_environment_narrative",
         method="資料に掲載された生息魚", summary="河川整備計画が黒部川で確認された魚介類として示す一般魚2件を収録。地点情報は収録しない。"),
    dict(prefecture="千葉県", river="与田浦川", names=["ヌマチチブ"], year=None,
         sid="RF-20261029-B6-06", title="利根川水系香取・銚子圏域河川整備計画 第3章 河川の現状と課題",
         publisher="千葉県", url="https://www.pref.chiba.lg.jp/kasei/keikaku/rivers/plan/katori-choushi/documents/plan-kat-cho-03.pdf",
         locator="第3章（2）自然環境・与田浦川", cls="B", kind="official_environment_narrative",
         method="資料に掲載された生息魚", summary="河川整備計画が与田浦川で確認された魚介類として示す一般魚ヌマチチブを収録。希少種は除外。"),
    dict(prefecture="千葉県", river="小野川", names=["タモロコ"], year=None,
         sid="RF-20261029-B6-07", title="利根川水系香取・銚子圏域河川整備計画 第3章 河川の現状と課題",
         publisher="千葉県", url="https://www.pref.chiba.lg.jp/kasei/keikaku/rivers/plan/katori-choushi/documents/plan-kat-cho-03.pdf",
         locator="第3章（2）自然環境・小野川", cls="B", kind="official_environment_narrative",
         method="資料に掲載された生息魚", summary="河川整備計画が小野川で確認された魚介類として示す一般魚タモロコを収録。保全審査対象魚は除外。"),
    dict(prefecture="千葉県", river="鹿島川", names=["コイ", "オイカワ", "カワムツ", "カマツカ", "モツゴ", "ドジョウ", "ヒガシシマドジョウ", "カダヤシ", "クロダハゼ"], year=2012,
         sid="RF-20261029-B6-08", title="鹿島川上流 ～千葉市の食を支える川づくり～",
         publisher="千葉市", url="https://www.city.chiba.jp/kankyo/kankyohozen/hozen/shizen/documents/mizukeikaku_chap4_3_2kashima.pdf",
         locator="鹿島川下流で確認された水生生物・H24現況", cls="A", kind="official_fish_survey_record",
         method="魚類調査記録", summary="千葉市資料の2012年現況欄で鹿島川に確認された一般魚9件を収録。調査地点名と保全審査対象魚は収録しない。"),
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
        "scope_notes": ["公的資料の記述です。現在の生息や実在河川の同一性を保証しません。", "詳細地点と保全審査対象魚は公開データに収録していません。"],
        "id": "srcfish_" + hashlib.sha256((row["prefecture"] + "|" + entry["water"] + "|" + row["river"]).encode()).hexdigest()[:24],
        "navigation_target_id": entry["id"], "literal_fish_label_count": len(records), "individual_physical_river_identity_approved": False,
    })

data["release"] = "2026-10-29-ibaraki-chiba-evidence-batch6-staging"
data["group_count"] = len(data["groups"])
data["record_count"] = sum(len(g["records"]) for g in data["groups"])
DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
print(f"added {len(sources)} groups / {sum(len(row['names']) for row in sources)} records; total {data['group_count']} / {data['record_count']}")
