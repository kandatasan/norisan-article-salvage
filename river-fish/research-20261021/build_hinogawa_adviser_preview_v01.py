#!/usr/bin/env python3
"""Build a noindex, offline river/fish preview from the existing HINO25 rows."""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from build_hinogawa_adviser_fish_records_v01 import (
    ALLOWED_FISH,
    YEAR_LABELS,
    RIVERS,
    SOURCE_DOCUMENT_DATE,
    SOURCE_ID,
    SOURCE_TITLE,
    SOURCE_URL,
    SOURCE_LOCATOR,
)
from search_hinogawa_records_v01 import NOTICE

SCHEMA = "tsurikue-hinogawa-adviser-preview-v01"
RIVER_ORDER = tuple(RIVERS.values())
EXPECTED_COUNTS = {"日野川": 47, "法勝寺川": 10}
HTML = r'''<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>日野川・法勝寺川の魚類記録｜研究用プレビュー</title>
<style>
:root{color-scheme:light;font-family:system-ui,-apple-system,"Noto Sans JP",sans-serif;color:#173542;background:#f3f8f8}
*{box-sizing:border-box}body{margin:0}header{background:linear-gradient(120deg,#123e52,#176d73);color:#fff;padding:2rem max(1rem,calc((100vw - 960px)/2))}
main{max-width:960px;margin:auto;padding:1rem 1rem 3rem}h1{font-size:clamp(1.5rem,5vw,2.25rem);margin:.25rem 0}p{line-height:1.75}
.notice{background:#fff;padding:1rem 1.2rem;border-left:4px solid #438c8c;border-radius:8px}.controls{display:grid;grid-template-columns:1fr 1fr;gap:.8rem;margin:1.4rem 0}
label{font-weight:700;display:block;margin-bottom:.35rem}input{width:100%;border:1px solid #8eafb5;border-radius:10px;background:#fff;padding:.75rem;font:inherit}
#summary{font-weight:700}.cards{display:grid;grid-template-columns:1fr;gap:1rem}article{background:#fff;border:1px solid #d4e2e3;border-radius:14px;padding:1rem}
article h2{margin:.1rem 0 .4rem}.sub,small{color:#54717a;font-size:.91rem;line-height:1.7}.fish{border-top:1px solid #d4e2e3;padding-top:.6rem;margin-top:.6rem}
.fish h3{display:flex;gap:.6rem;align-items:center;flex-wrap:wrap;margin:.3rem 0}.chip{background:#e4f3f0;border:1px solid #c1dcd7;border-radius:99px;padding:.35rem .65rem;cursor:pointer;color:#164b4b;font:inherit}
.chip:hover,.chip:focus-visible{background:#c9ebe4}.chip:focus-visible{outline:2px solid #285d7b}table{border-collapse:collapse;width:100%;max-width:540px}th,td{padding:.35rem .55rem;text-align:left;border-bottom:1px solid #e0ebeb}th{font-weight:700}
a{color:#145f8b}@media(max-width:680px){.controls{grid-template-columns:1fr}header{padding:1.5rem 1rem}}
</style></head><body>
<header><div>つりくえ！日本の河川図鑑・研究用</div><h1>日野川・法勝寺川の魚類記録</h1>
<p>国土交通省資料の河川別・調査年度別の確認個体数を、川からも魚からも探せる形にしています。</p></header>
<main><div class="notice"><strong>公開前の研究用プレビューです。</strong>過去の調査記録で、現在の生息・個体数・釣果を示しません。全記録が未承認です。保護上非公表の欄や、数値のない欄は検索対象に含めていません。</div>
<div class="controls"><div><label for="river">川の名前</label><input id="river" type="search" placeholder="例：日野川" maxlength="60"></div>
<div><label for="fish">魚の名前</label><input id="fish" type="search" placeholder="例：アユ" maxlength="60"></div></div>
<p id="summary" role="status" aria-live="polite"></p><div id="results" class="cards"></div>
<p class="sub">表は日野川本川と法勝寺川を別に掲載しています。個別の採集地点・調査区間は未確認で、河川コードにも接続していません。資料公表年月（2025年9月）と調査年度（1994〜2024年度）は分けて保持しています。</p>
<script id="source-layer" type="application/json">__LAYER__</script>
<script>(function(){"use strict";const d=JSON.parse(document.getElementById("source-layer").textContent);
if(d.schema!=="tsurikue-hinogawa-adviser-preview-v01"||d.status!=="RESEARCH_ONLY_CANDIDATES_NOT_PUBLICATION")throw Error("Invalid research preview data");
const $=id=>document.getElementById(id),norm=s=>String(s||"").trim().toLocaleLowerCase();
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n}
function render(){const r=norm($("river").value),f=norm($("fish").value),found=d.river_groups.filter(x=>(!r||norm(x.river).includes(r))&&(!f||x.fish_records.some(y=>norm(y.recorded_name).includes(f))));
$("results").replaceChildren();$("summary").textContent="該当する資料記録のある川："+found.length+"件（実在する川の全数ではありません）";
if(!found.length){$("results").append(el("p","該当する資料記録がありません。魚がいないという意味ではありません。"));return}
for(const x of found){const card=el("article");card.append(el("h2",x.river));card.append(el("p",x.prefecture+"｜"+x.water_system,"sub"));card.append(el("small",x.source_scope_note));
for(const fish of x.fish_records){if(f&&!norm(fish.recorded_name).includes(f))continue;const section=el("section",undefined,"fish"),heading=el("h3");const button=el("button",fish.recorded_name,"chip");button.type="button";button.title="この魚が記載された川を探す";button.addEventListener("click",()=>{$("fish").value=fish.recorded_name;$("river").value="";render();$("fish").focus()});heading.append(button);section.append(heading);
const table=el("table"),thead=el("thead"),tr=el("tr");tr.append(el("th","調査年度"),el("th","個体数"));thead.append(tr);table.append(thead);const body=el("tbody");
for(const o of fish.observations){const line=el("tr");line.append(el("td",String(o.survey_year)+"年（"+o.survey_year_label+"）"),el("td",String(o.individual_count)));body.append(line)}table.append(body);section.append(table);card.append(section)}
const a=el("a","国土交通省の原資料を確認");a.href=d.source_url;a.target="_blank";a.rel="noopener noreferrer";card.append(a);$("results").append(card)}}
for(const id of ["river","fish"])$(id).addEventListener("input",render);render()})();</script></main></body></html>'''


def build_layer(records: list[dict[str, str]]) -> dict:
    if len(records) != 57:
        raise ValueError("Preview requires exactly the reviewed 57 HINO25 records")

    by_river: dict[str, dict[str, list[dict]]] = {
        river: defaultdict(list) for river in RIVER_ORDER
    }
    counts: Counter[str] = Counter()
    seen = set()
    for row in records:
        if (row["source_id"] != SOURCE_ID or row["prefecture"] != "鳥取県"
                or row["water_system"] != "日野川水系"
                or row["river_as_published"] not in RIVER_ORDER):
            raise ValueError("Record is outside the reviewed Hino River table")
        if row["river_code"]:
            raise ValueError("Do not join river codes into this source-only preview")
        if (row["fish_name_as_published"] not in ALLOWED_FISH
                or row["fish_publication_approval"] != "not_approved"
                or row["conservation_review"] != "pending"
                or row["integration_status"] != "research_only"):
            raise ValueError("Unexpected fish label or release status")
        if (row["source_title"] != SOURCE_TITLE
                or row["source_document_date"] != SOURCE_DOCUMENT_DATE
                or row["source_url"] != SOURCE_URL
                or row["source_locator"] != SOURCE_LOCATOR
                or row["verification_status"] != "official_pdf_table_image_checked"):
            raise ValueError("Source provenance differs from the page-checked record set")
        year_label = row["survey_year_label"]
        if year_label not in YEAR_LABELS or row["survey_year"] != str(YEAR_LABELS[year_label]):
            raise ValueError("Survey year and era label do not match")
        try:
            individual_count = int(row["reported_individual_count"])
        except ValueError as exc:
            raise ValueError("Only positive numeric table cells are searchable") from exc
        if individual_count <= 0:
            raise ValueError("Dashes, blanks, and zero counts are not searchable records")
        key = (row["river_as_published"], row["fish_name_as_published"], row["survey_year"])
        if key in seen:
            raise ValueError("Duplicate source river/fish/year record")
        seen.add(key)
        by_river[row["river_as_published"]][row["fish_name_as_published"]].append({
            "survey_year": int(row["survey_year"]),
            "survey_year_label": year_label,
            "individual_count": individual_count,
        })
        counts[row["river_as_published"]] += 1

    if dict(counts) != EXPECTED_COUNTS:
        raise ValueError("River record totals changed; review the source before previewing")

    groups = []
    reverse: dict[str, list[dict]] = defaultdict(list)
    for river in RIVER_ORDER:
        fish_records = []
        for name in sorted(by_river[river]):
            observations = sorted(by_river[river][name], key=lambda item: item["survey_year"])
            fish_records.append({"recorded_name": name, "observations": observations})
            reverse[name].append({"river": river, "observations": observations})
        groups.append({
            "prefecture": "鳥取県",
            "water_system": "日野川水系",
            "river": river,
            "source_scope_note": (
                "資料表の河川別列に掲載。個別地点・調査区間は不明。"
                "河川コードや支流全体への拡張は行っていません。"
            ),
            "national_river_code": None,
            "sampling_station_identified": False,
            "fish_records": fish_records,
            "fish_species_count": len(fish_records),
            "positive_count_observation_total": counts[river],
            "publication_review": "not_approved",
        })

    return {
        "schema": SCHEMA,
        "status": "RESEARCH_ONLY_CANDIDATES_NOT_PUBLICATION",
        "source_id": SOURCE_ID,
        "source_title": SOURCE_TITLE,
        "source_document_date": SOURCE_DOCUMENT_DATE,
        "source_url": SOURCE_URL,
        "source_locator": SOURCE_LOCATOR,
        "positive_count_observation_total": len(records),
        "fish_species_total": len({r["fish_name_as_published"] for r in records}),
        "protected_or_redacted_rows_exported": False,
        "verified_river_code_links": 0,
        "sampling_stations_identified": False,
        "current_habitat_verified": False,
        "catchability_verified": False,
        "publication_approval": "not_approved",
        "river_groups": groups,
        "fish_reverse_index": {name: matches for name, matches in sorted(reverse.items())},
        "notice": NOTICE,
        "site_updated": False,
    }


def render(records: list[dict[str, str]]) -> str:
    layer = build_layer(records)
    payload = json.dumps(layer, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = HTML.replace("__LAYER__", payload)
    if "__LAYER__" in html or 'name="robots" content="noindex,nofollow"' not in html:
        raise ValueError("Preview is incomplete or indexable")
    return html


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    with args.records.open(encoding="utf-8-sig", newline="") as stream:
        records = list(csv.DictReader(stream))
    if args.out.exists():
        raise FileExistsError("Refusing to overwrite a preview output")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    output = render(records)
    args.out.write_text(output, encoding="utf-8")
    print(json.dumps({
        "noindex": True,
        "preview_bytes": len(output.encode("utf-8")),
        "rivers": 2,
        "positive_count_observations": 57,
        "site_updated": False,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
