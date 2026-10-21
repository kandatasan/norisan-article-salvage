#!/usr/bin/env python3
"""Audit identity links for seven Chugoku fish-source river names.

Research only. This validates a human-reviewed evidence ledger; it does not
publish fish records or imply that historical records describe current fish.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
INPUT = HERE / "chugoku_seven_river_identity_audit_v01.csv"
EXPECTED = {
    ("島根県", "斐伊川", "斐伊川"): "8707040001",
    ("島根県", "斐伊川", "三刀屋川"): "8707040191",
    ("島根県", "斐伊川", "久野川"): "8707040204",
    ("島根県", "斐伊川", "阿井川"): "8707040213",
    ("島根県", "斐伊川", "深野川"): "8707040211",
    ("鳥取県", "日野川", "日野川"): "8707030001",
    ("鳥取県", "日野川", "大川"): "8707030012",
}
OFFICIAL_HOSTS = {
    "nlftp.mlit.go.jp", "www.cgr.mlit.go.jp",
    "www.pref.shimane.lg.jp", "www.pref.tottori.lg.jp",
}
REQUIRED_FIELDS = (
    "prefecture_source_publisher", "watershed", "river", "river_code",
    "code_name_match", "official_system_map", "source_area_relation",
    "locality_precision", "identity_status", "fish_record_approval",
    "source_ids", "source_urls", "source_locators", "notes",
)


def load(path: Path = INPUT) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if tuple(reader.fieldnames or ()) != REQUIRED_FIELDS:
            raise ValueError("identity audit CSV header drift")
        rows = list(reader)
    if len(rows) != len(EXPECTED):
        raise ValueError("expected exactly seven reviewed river groups")
    seen: set[tuple[str, str, str]] = set()
    codes: set[str] = set()
    for row in rows:
        key = (row["prefecture_source_publisher"], row["watershed"], row["river"])
        if key not in EXPECTED or row["river_code"] != EXPECTED[key]:
            raise ValueError(f"unexpected name/code pairing: {key}")
        if key in seen or row["river_code"] in codes:
            raise ValueError("duplicate river group or code")
        seen.add(key)
        codes.add(row["river_code"])
        expected_prefix = "870704" if row["watershed"] == "斐伊川" else "870703"
        if not row["river_code"].startswith(expected_prefix):
            raise ValueError("river code does not belong to the named system prefix")
        if (row["code_name_match"] != "confirmed"
                or row["official_system_map"] != "confirmed"
                or row["identity_status"] != "official_system_identity_confirmed"
                or row["fish_record_approval"] != "not_approved"):
            raise ValueError("identity evidence or publication boundary changed")
        if not row["source_area_relation"] or not row["locality_precision"] or not row["notes"]:
            raise ValueError("missing qualification or scope note")
        source_ids = set(row["source_ids"].split(";"))
        required_source = "SH22" if row["prefecture_source_publisher"] == "島根県" else "TO16"
        if source_ids != {required_source}:
            raise ValueError("unexpected source group")
        urls = row["source_urls"].split(";")
        if len(urls) < 3:
            raise ValueError("need code list, system schematic and prefectural source")
        hosts = {urlsplit(url).hostname for url in urls}
        if not hosts <= OFFICIAL_HOSTS or len(hosts) < 3:
            raise ValueError("non-official or incomplete source set")
        if any(urlsplit(url).scheme != "https" for url in urls):
            raise ValueError("all evidence URLs must use HTTPS")
    if seen != set(EXPECTED):
        raise ValueError("reviewed river set changed")
    return rows


def render(rows: list[dict[str, str]]) -> str:
    lines = [
        "# 中国地方・優先7河川の同一性確認 v01",
        "",
        "**研究専用。公開サイト、WordPress、検索JSONには未反映。魚記録の公開承認は0件。**",
        "",
        "## 確認した事実",
        "",
        "- 国土交通省の河川コード一覧で、7河川名と各コードの組み合わせを照合した。",
        "- 中国地方整備局の河川模式図で、各コードが対象の斐伊川水系または日野川水系に属することと、流路網上の位置関係を確認した。",
        "- 島根県の計画範囲は尾原ダムから斐伊川放水路までの本川・流入支川域。三刀屋川、久野川、阿井川は県が主な支川として明記。深野川は模式図で独立した河川名・コードを確認した。",
        "- 鳥取県の計画は大川を日野川本川と区別し、日野川本川合流点から上流の対象区間を記載している。",
        "",
        "## 対応表",
        "",
        "| 県資料 | 水系 | 資料の河川名 | 照合した河川コード | 位置・関係の確認範囲 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append("| " + " | ".join([
            row["prefecture_source_publisher"], row["watershed"], row["river"],
            row["river_code"], row["locality_precision"]
        ]) + " |")
    lines.extend([
        "",
        "## 推定・未確認",
        "",
        "- この照合により、資料の河川名を同じ名称の別水系の河川へ誤接続するリスクは大きく下げられた。コード名だけでなく、水系別模式図と県の計画範囲を併用した。",
        "- 河川模式図は水系内の位置関係図で、調査地点の座標や河道の全区間を表す地図ではない。島根県の5河川について、市町境界を含む河道ポリラインとのGIS交差照合は未実施。",
        "- 県資料の魚名一覧と河川コードの対応は河川名・計画範囲レベル。個々の魚の採集地点、同一年度、現在の生息、釣果は確認していない。",
        "- 河川コードや河川形状データの版・基準年は資料ごとに異なる。コードの永続性や現行河道の完全な一致を保証しない。",
        "- 希少種・保全審査、原本転載条件、検索UIとの重複・逆引きQAは別工程として未完了。",
        "",
        "## 一次資料",
        "",
        "- [国土交通省・河川コード一覧](https://nlftp.mlit.go.jp/ksj/gml/codelist/RiverCodeCd.html)",
        "- [中国地方整備局・河川コード台帳（2011年3月、河川模式図編）](https://www.cgr.mlit.go.jp/chiki/kasenj/code/data/h2303_moshiki1.pdf)",
        "- [島根県・斐伊川水系中流支川域河川整備計画](https://www.pref.shimane.lg.jp/infra/river/kasen/hoshin/hiikawachuryusisen_kawadukuri/)",
        "- [鳥取県・日野川水系（指定区間）河川整備計画](https://www.pref.tottori.lg.jp/secure/210292/hinogawasiteikukan_kasenseibikeikaku20160121.pdf)",
        "",
        "この監査は研究用の名称・水系同一性確認であり、魚類記録の公開や図鑑データ更新を意味しない。",
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
    print(f"SEVEN_RIVER_IDENTITY_AUDIT_V01 rows={len(rows)} publication_approvals=0")


if __name__ == "__main__":
    main()
