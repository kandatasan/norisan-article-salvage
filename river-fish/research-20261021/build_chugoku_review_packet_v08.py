#!/usr/bin/env python3
"""Generate a source-linked human review packet, never a publication data feed.

Input: verified v07 JSON from official survey + provincial plans + live atlas.
Output: Markdown with river NAME CANDIDATES and source links; no fish labels,
sites, coordinates, catch promises, approval flags or generated atlas data.
"""
from __future__ import annotations
import argparse
import html
import json
from pathlib import Path
from urllib.parse import urlsplit

from build_chugoku_source_crosscheck_v07 import SCHEMA as INPUT_SCHEMA

SOURCE_HOSTS = {
    "www1.pref.shimane.lg.jp",
    "www.pref.hiroshima.lg.jp",
    "www.pref.okayama.jp",
    "www.pref.tottori.lg.jp",
    "www.pref.yamaguchi.lg.jp",
}
CATEGORIES = {
    "A_EXISTING_ATLAS_RIVER_REVIEW",
    "B_NEW_RIVER_REVIEW",
    "C_EVIDENCE_SCOPE_OR_CONSERVATION_REVIEW",
    "D_AMBIGUOUS_OR_MISSING_CODE_REVIEW",
}


def clean(value):
    return html.escape(str(value), quote=True).replace("|", "｜").replace("\n", " ")


def source_links(row):
    urls = row["source_urls"]
    if not urls:
        raise ValueError("No provincial source link")
    links = []
    for url in urls:
        u = urlsplit(url)
        if u.scheme != "https" or u.hostname not in SOURCE_HOSTS or u.username or u.password:
            raise ValueError("Unexpected source domain")
        links.append("[県資料](" + url + ")")
    return " / ".join(links)


def render(data):
    if (data.get("schema") != INPUT_SCHEMA or data.get("status") != "REVIEW_ONLY_DO_NOT_UPLOAD"
            or data.get("provincial_candidate_rows") != 124
            or data.get("named_river_candidate_rows") != 115
            or data.get("watershed_only_rows_held") != 9
            or data.get("river_groups") != 13
            or data.get("national_chugoku_fish_year_records") != 3592
            or len(data.get("rows", [])) != 13):
        raise ValueError("Review source drift; manual review required")
    rows = data["rows"]
    if (sum(data["priority_counts"].values()) != 13
            or any(x["review_priority"] not in CATEGORIES
                   or x["approved_for_publication"] is not False
                   or x["code_identity_verified"] is not False
                   or x["atlas_identity_verified"] is not False
                   or x["source_name_identity_verified"] is not False
                   or x["species_publication_review"] != "required" for x in rows)):
        raise ValueError("Input appears to contain approved or invalid review records")
    if any("recorded_name" in x or "survey_year" in x for x in rows):
        raise ValueError("Fish names or survey year leaked into review rows")
    names = [(x["prefecture_source_publisher"], x["watershed"], x["river"]) for x in rows]
    if len(set(names)) != 13:
        raise ValueError("Duplicate review river group")
    eligible = [x for x in rows if x["review_priority"] in {
        "A_EXISTING_ATLAS_RIVER_REVIEW", "B_NEW_RIVER_REVIEW"}]
    held = [x for x in rows if x["review_priority"] not in {
        "A_EXISTING_ATLAS_RIVER_REVIEW", "B_NEW_RIVER_REVIEW"}]
    if len(eligible) != 7 or len(held) != 6:
        raise ValueError("Review queue counts changed")
    lines = [
        "# 中国地方5県｜魚の調査記録を川につなぐための公開前確認票（v08）",
        "",
        "**研究専用・公開不可。** 県資料の発行県は、河川全流域の所在地の確定ではありません。",
        "川名・水系名・河川コード名が一致しても、同一河川IDと確定したわけではありません。",
        "",
        "## 今回の実測",
        "",
        "- 県資料124記載のうち個別河川名あり115記載、13河川名グループ。水系だけの9記載は接続禁止。",
        "- 国交省中国地方の魚類調査原本3,592件と河川名・魚の**原文表記**を照合。",
        "- 国交省の河川コード名候補が1件の河川名グループ：" +
          str(data["river_groups_with_national_river_code_single_name_candidate"]) + "。",
        "- 県資料と国交省調査の原文魚名が一致した河川名グループ：" +
          str(data["river_groups_with_independent_literal_fish_overlap"]) + "。同一地点・独立観測の証明ではありません。",
        "- **次の河川同定レビュー対象7、資料・保全等で保留6。公開承認は0。**",
        "",
        "## 1. 先に同一河川を確認する7グループ",
        "",
        "| 県資料発行県 | 水系 | 河川名 | 県資料の記載数 | 国交省の同名河川記録数 | 同じ原文魚名数 | 河川コード**名候補** | 既存図鑑**名候補** | 出典 |",
        "| --- | --- | --- | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for row in eligible:
        code = " / ".join(clean(c) for c in row["national_river_code_name_candidates"]) or "なし"
        atlas = " / ".join(clean(c) for c in row["live_atlas_navigation_name_candidate_ids"]) or "なし（追加候補）"
        lines.append("| " + " | ".join([
            clean(row["prefecture_source_publisher"]), clean(row["watershed"]), clean(row["river"]),
            str(row["provincial_evidence_rows"]),
            str(row["national_chugoku_survey_records_same_water_river_name"]),
            str(row["independent_same_literal_fish_label_count"]),
            code, atlas, source_links(row)
        ]) + " |")
    lines.extend([
        "",
        "## 2. まだ個別河川へつなげない6グループ",
        "",
        "| 県資料発行県 | 水系 | 河川名 | 保留理由 | 資料記載数 | 保全フラグ数 | 原本未通読数 | 出典 |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | --- |",
    ])
    for row in held:
        lines.append("| " + " | ".join([
            clean(row["prefecture_source_publisher"]), clean(row["watershed"]),
            clean(row["river"]), clean(row["evidence_gate"]),
            str(row["provincial_evidence_rows"]),
            str(row["source_conservation_flag_rows"]),
            str(row["source_original_not_checked_rows"]), source_links(row)
        ]) + " |")
    lines.extend([
        "",
        "## 3. 公開前の必須確認（各河川ごと）",
        "",
        "- [ ] 県の河川整備計画・国交省調査の**同一河川・同一水系**を一次資料で確認（単なる同名一致は禁止）",
        "- [ ] 河川コードの実河川同定・都道府県・同名異川・支流関係を別資料で確認",
        "- [ ] 県資料の『確認魚』が本川・支流・上中下流のどの範囲かを確認。文脈のみの資料を採集事実に格上げしない",
        "- [ ] 保全上の希少種・保護種・外来種の公開粒度を審査（原本の魚名を勝手に分類名へ正規化しない）",
        "- [ ] 出典、転載条件、調査年と公表年の区別、現在の生息・釣果を保証しない注記を確認",
        "- [ ] 既存公開図鑑との重複、魚→川・川→魚の逆引き、47都道府県の検索を回帰テスト",
        "- [ ] 承認済みだけを別の公開候補ファイルへ移し、差分レビュー後に本番反映",
        "",
        "**この確認票自体は公開JSONに使わない。** 全行が未承認であり、魚名・採集地点・座標・採集日は含めない。",
        "",
        "照合対象の公開図鑑 atlas.json SHA256: `" +
        clean(data.get("live_atlas_json_sha256", "未記録")) + "`",
        "",
    ])
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--review-json", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    data = json.loads(args.review_json.read_text(encoding="utf-8"))
    report = render(data)
    if args.out.exists():
        raise FileExistsError("Refuse to overwrite human review packet")
    args.out.write_text(report, encoding="utf-8")
    print("CHUGOKU_SEVEN_RIVERS_PACKET_V08", json.dumps({
        "review_rivers": 7, "held_rivers": 6, "site_updated": False
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
