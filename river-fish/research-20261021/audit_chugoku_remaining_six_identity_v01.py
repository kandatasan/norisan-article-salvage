#!/usr/bin/env python3
"""Audit the six non-priority Chugoku river groups against official sources.

This is a research identity audit only. It does not approve fish records or
publish river/fish links. Code identity and fish-source verification are
separate gates; the Yamaguchi fish source remains excerpt-only.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from urllib.parse import urlsplit

from audit_chugoku_seven_river_identity_v01 import load as load_priority_identity
from build_official_river_code_candidates_v05 import load_codes

HERE = Path(__file__).resolve().parent
INPUT = HERE / "chugoku_remaining_six_identity_review_v01.csv"
PROVINCIAL = HERE / "fish_river_evidence_candidates_20261021.csv"
FIELDS = (
    "prefecture", "watershed", "river", "river_code_candidates",
    "confirmed_river_code", "identity_status", "identity_basis",
    "code_source_url", "code_source_locator", "topology_source_url",
    "topology_source_locator", "local_source_url",
    "local_source_locator", "fish_source_ids", "fish_evidence_scopes",
    "fish_source_verification", "survey_year_status",
    "fish_publication_approval",
)
PROVINCIAL_FIELDS = (
    "prefecture", "watershed", "river", "evidence_scope", "recorded_name",
    "evidence_kind", "survey_year", "source_id", "source_locator",
    "verification_status", "source_url", "conservation_review",
    "integration_status", "notes",
)
EXPECTED = {
    ("島根県", "斐伊川", "赤川"): ("8707040161", "official_system_identity_confirmed"),
    ("岡山県", "笹ヶ瀬川", "笹ヶ瀬川"): ("3300090001", "official_system_identity_confirmed"),
    ("岡山県", "笹ヶ瀬川", "足守川"): ("3300090002", "official_system_identity_confirmed"),
    ("広島県", "八幡川", "八幡川"): ("3400290001", "official_system_identity_confirmed"),
    ("広島県", "江の川", "長瀬川"): ("8707050140", "official_system_identity_confirmed"),
    ("山口県", "佐波川", "小島川"): ("8707070003", "official_system_identity_confirmed"),
}
OFFICIAL_HOSTS = {
    "www.cgr.mlit.go.jp", "www.pref.shimane.lg.jp", "www.pref.okayama.jp",
    "www.pref.hiroshima.lg.jp", "www.pref.yamaguchi.lg.jp",
}


def read_rows(path: Path, fields: tuple[str, ...]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != fields:
            raise ValueError(f"CSV header drift: {path}")
        rows = list(reader)
    if not rows or any(set(row) != set(fields) for row in rows):
        raise ValueError(f"Malformed or empty CSV: {path}")
    return rows


def load(path: Path = INPUT, provincial_path: Path = PROVINCIAL) -> list[dict[str, str]]:
    rows = read_rows(path, FIELDS)
    provincial = read_rows(provincial_path, PROVINCIAL_FIELDS)
    priority_rows = load_priority_identity()
    river_codes, _ = load_codes()
    code_index: dict[tuple[str, str], set[str]] = {}
    for code in river_codes:
        watershed = code["watershed_name"].removesuffix("水系")
        code_index.setdefault((watershed, code["river_name"].strip()), set()).add(code["river_code"])

    source_index: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    watershed_only_rows = 0
    for item in provincial:
        if item["evidence_scope"] == "watershed_only":
            if item["river"]:
                raise ValueError("Watershed-only record unexpectedly names a river")
            watershed_only_rows += 1
            continue
        key = (item["prefecture"], item["watershed"].removesuffix("水系"), item["river"])
        source_index.setdefault(key, []).append(item)

    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        key = (row["prefecture"], row["watershed"], row["river"])
        if key not in EXPECTED or key in seen:
            raise ValueError(f"Unexpected or duplicate river group: {key}")
        seen.add(key)
        expected_code, expected_status = EXPECTED[key]
        if row["confirmed_river_code"] != expected_code or row["identity_status"] != expected_status:
            raise ValueError(f"Unexpected code or status for {key}")
        candidates = set(filter(None, row["river_code_candidates"].split(";")))
        official_candidates = code_index.get((row["watershed"], row["river"]), set())
        if candidates != official_candidates:
            raise ValueError(f"Candidate list differs from official code snapshot: {key}")
        if expected_code and expected_code not in candidates:
            raise ValueError(f"Confirmed code is not among official candidates: {key}")
        if not expected_code and row["confirmed_river_code"]:
            raise ValueError(f"Unverified code must remain unassigned: {key}")
        if (row["fish_publication_approval"] != "not_approved"
                or not row["identity_basis"] or not row["code_source_locator"]
                or not row["topology_source_locator"]
                or not row["local_source_locator"] or not row["fish_source_ids"]
                or not row["fish_evidence_scopes"] or not row["survey_year_status"]):
            raise ValueError(f"Missing review boundary or evidence locator: {key}")
        if row["fish_source_verification"] not in {
            "source_text_checked", "official_pdf_table_image_checked", "search_excerpt_only"
        }:
            raise ValueError(f"Unexpected source verification state: {key}")
        if row["fish_source_verification"] == "search_excerpt_only" and expected_code:
            # A search excerpt cannot verify a fish record. A separately cited
            # official code/topology source may still resolve river identity.
            if not row["topology_source_url"] or not row["topology_source_locator"]:
                raise ValueError(f"Search-excerpt source lacks an independent topology source: {key}")
        for field in ("code_source_url", "topology_source_url", "local_source_url"):
            parts = urlsplit(row[field])
            if parts.scheme != "https" or parts.hostname not in OFFICIAL_HOSTS:
                raise ValueError(f"Non-official or insecure source URL: {key} {field}")
        source_rows = source_index.get(key, [])
        if not source_rows:
            raise ValueError(f"No staged fish-source group found: {key}")
        if {item["source_id"] for item in source_rows} != set(row["fish_source_ids"].split(";")):
            raise ValueError(f"Fish source IDs changed: {key}")
        if {item["evidence_scope"] for item in source_rows} != set(row["fish_evidence_scopes"].split(";")):
            raise ValueError(f"Fish evidence scope changed: {key}")
        verification = {item["verification_status"] for item in source_rows}
        expected_verification = {row["fish_source_verification"]}
        if verification != expected_verification:
            raise ValueError(f"Fish source verification state changed: {key}")

    priority_keys = {
        (row["prefecture_source_publisher"], row["watershed"], row["river"])
        for row in priority_rows
    }
    if len(priority_keys) != 7 or priority_keys & set(EXPECTED):
        raise ValueError("Priority and remaining river groups overlap or drifted")
    source_group_keys = set(source_index)
    if source_group_keys != priority_keys | set(EXPECTED):
        raise ValueError("13 named-river source groups do not match the reviewed ledgers")
    if watershed_only_rows != 9:
        raise ValueError("Watershed-only inventory changed; do not attach it to a river")
    if seen != set(EXPECTED):
        raise ValueError("Expected all six non-priority river groups")
    return rows


def render(rows: list[dict[str, str]]) -> str:
    confirmed = sum(bool(row["confirmed_river_code"]) for row in rows)
    lines = [
        "# 中国地方・残る6河川群の同一性監査 v01",
        "",
        "**研究専用。公開サイト、WordPress、公開JSONには未反映。魚記録は全件未承認。**",
        "",
        f"監査上の判定：優先7群と合わせた13群のうち{7 + confirmed}群で河川コードの同一性を確認。山口県・小島川のコード同一性は模式図で確認したが、魚類報告は検索抜粋のみで未承認のまま。",
        "",
        "## 一次資料で確認した事実",
        "",
        "- 島根県の計画表は赤川の対象区間を斐伊川合流点から19.31kmと記載する。国交省の2016年コード台帳には、斐伊川水系の同名候補3件が次数2・1・4で掲載されている。",
        "- 岡山県の計画表は足守川の下流端を笹ヶ瀬川への合流点として記載する。国交省台帳では笹ヶ瀬川を次数0、足守川を同水系の次数1として別コードで記録する。",
        "- 広島県の八幡川計画本文は源流と木末川・石内川の合流を説明する。中国地方整備局の広島県詳細模式図には八幡川・石内川・木末川のコードと位置関係が掲載されている。",
        "- 広島県の江の川本川ブロック計画は長瀬川を江の川の支川として個別に扱い、環境説明にも長瀬川を明記する。国交省の江の川コード台帳には長瀬川のコードが掲載されている。",
        "- 山口県の研究報告検索抜粋は2005年の佐波川水系小島川を記載する。国交省の2016年コード表は小島川を次数2・コード8707070003・防府市管理として掲載し、同版の佐波川水系模式図にもコード付きの小島川支川を表示する。",
        "",
        "## 照合判断（推定）",
        "",
        "- 赤川は県計画が斐伊川本川への直接合流を明記するため、コード台帳の同名3候補のうち一次支川の8707040161を対応先と判断した。名前と水系名の一致だけでは選んでいない。",
        "- 足守川は県計画の合流点記述と国交省台帳の水系階層が一致するため、3300090002を対応先と判断した。笹ヶ瀬川本川の3300090001とは分けて扱う。",
        "- 八幡川と長瀬川は、県資料の河道・支川関係と中国地方整備局の地域模式図・コード台帳が一致するため、3400290001と8707050140をそれぞれ対応先と判断した。",
        "- 小島川はコード表と佐波川水系模式図の系統関係から8707070003を対応先と判断した。これは魚類報告の原本照合や採集地点の確認を意味しない。",
        "- 6群のコード対応は研究用の河川同一性判断。魚類調査の地点・区間をこれらのコードへ結び付けたものではない。",
        "",
        "## 監査表",
        "",
        "| 県 | 水系 | 河川 | コード候補 | 監査状態 | 魚記録の状態 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        code = row["confirmed_river_code"] or f"未確定（候補 {row['river_code_candidates']}）"
        lines.append("| " + " | ".join([
            row["prefecture"], row["watershed"], row["river"], code,
            row["identity_status"], row["fish_source_verification"],
        ]) + " |")
    lines.extend([
        "",
        "## 未確認・公開判断",
        "",
        "- 河川コードの同一性確認は、魚類調査の採集地点・調査区間・現在の生息を示さない。",
        "- 県資料に魚名と河川名が同時に載る群でも、個体の採集地点・魚種別調査年は確認できていない。小島川の2005年は検索抜粋のみで、原本確認前の参考情報。",
        "- 魚名の記載範囲、原文表記、希少種の公開粒度、資料の利用条件は個別に審査が必要。",
        "- 小島川の河川コード同一性と魚類記録の検証状態は別管理する。魚類報告の原本該当頁・採集地点・調査範囲は未確認のため、魚↔川検索候補へ入れない。",
        "- 河川コードは公式台帳の版（2016年）に依存する。最新河道との完全一致を保証しない。",
        "",
        "## 一次資料",
        "",
        "- [中国地方整備局・斐伊川水系コード台帳（2016年）](https://www.cgr.mlit.go.jp/kasen/code/pdf/004hii201612.pdf)",
        "- [中国地方整備局・岡山県二級水系コード台帳（2016年）](https://www.cgr.mlit.go.jp/kasen/code/pdf/100ikkatu201612.pdf)",
        "- [中国地方整備局・江の川水系コード台帳（2016年）](https://www.cgr.mlit.go.jp/kasen/code/pdf/005gouno201612.pdf)",
        "- [中国地方整備局・佐波川水系コード台帳（2016年）](https://www.cgr.mlit.go.jp/kasen/code/pdf/000ikkatu201612.pdf)",
        "- [中国地方整備局・佐波川水系詳細模式図（2016年）](https://www.cgr.mlit.go.jp/kasen/code/pdf/1mosiki201612.pdf)",
        "- [中国地方整備局・県別詳細模式図（2011年）](https://www.cgr.mlit.go.jp/chiki/kasenj/code/data/h2103_moshiki2.pdf)",
        "- [島根県・斐伊川水系中流支川域河川整備計画](https://www.pref.shimane.lg.jp/infra/river/kasen/hoshin/hiikawachuryusisen_kawadukuri/)",
        "- [岡山県・笹ヶ瀬川水系河川整備計画](https://www.pref.okayama.jp/uploaded/life/879682_8371002_misc.pdf)",
        "- [広島県・八幡川水系河川整備計画 1-1](https://www.pref.hiroshima.lg.jp/soshiki/99/1172534900627.html)",
        "- [広島県・江の川本川ブロック環境説明](https://www.pref.hiroshima.lg.jp/soshiki/99/1172196461943.html)",
        "- [山口県水産研究センター研究報告第07号](https://www.pref.yamaguchi.lg.jp/uploaded/attachment/197780.pdf)",
        "",
        "この監査は河川コードの候補同一性を確認するもので、魚の公開承認や本番図鑑の更新を意味しない。",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    rows = load()
    report = render(rows)
    if args.out:
        if args.out.exists():
            raise FileExistsError(f"refusing to overwrite {args.out}")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report, encoding="utf-8")
    print(f"CHUGOKU_REMAINING_SIX_IDENTITY_V01 groups={len(rows)} confirmed_codes={sum(bool(x['confirmed_river_code']) for x in rows)} fish_publication_approvals=0")


if __name__ == "__main__":
    main()
