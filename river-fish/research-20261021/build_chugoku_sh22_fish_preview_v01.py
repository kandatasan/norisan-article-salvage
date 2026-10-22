#!/usr/bin/env python3
"""Create a noindex, offline two-way search preview for the safe SH22 layer."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from build_chugoku_sh22_fish_index_v01 import (
    ADDITIONS_INPUT, BASE_INPUT, SCHEMA, build, load_csv,
)

HTML = r'''<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>斐伊川水系の魚類資料｜研究用検索プレビュー</title>
<style>
:root{color-scheme:light;font-family:system-ui,-apple-system,"Noto Sans JP",sans-serif;color:#173542;background:#f3f8f8}
*{box-sizing:border-box}body{margin:0}header{background:linear-gradient(120deg,#123e52,#176d73);color:white;padding:2rem max(1rem,calc((100vw - 960px)/2))}
main{max-width:960px;margin:auto;padding:1rem 1rem 3rem}h1{font-size:clamp(1.5rem,5vw,2.25rem);margin:.25rem 0}
p{line-height:1.75}.notice{background:#fff;padding:1rem 1.2rem;border-left:4px solid #438c8c;border-radius:8px}
.controls{display:grid;grid-template-columns:1fr 1fr;gap:.8rem;margin:1.4rem 0}label{font-weight:700;display:block;margin-bottom:.35rem}
input{width:100%;border:1px solid #8eafb5;border-radius:10px;background:white;padding:.75rem;font:inherit}
#summary{font-weight:700}.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem}
article{background:#fff;border:1px solid #d4e2e3;border-radius:14px;padding:1rem}article h2{margin:.1rem 0 .4rem}
.sub,small{color:#54717a;font-size:.91rem;line-height:1.7}.chips{display:flex;flex-wrap:wrap;gap:.4rem;margin:.7rem 0}
.chip{background:#e4f3f0;border:1px solid #c1dcd7;border-radius:99px;padding:.35rem .65rem;cursor:pointer;color:#164b4b;font:inherit}
.chip:hover,.chip:focus-visible{background:#c9ebe4}.chip:focus-visible{outline:2px solid #285d7b}a{color:#145f8b}
@media(max-width:680px){.controls,.cards{grid-template-columns:1fr}header{padding:1.5rem 1rem}}
</style></head><body>
<header><div>つりくえ！日本の河川図鑑・研究用</div><h1>斐伊川水系の川から魚へ、魚から川へ</h1>
<p>島根県資料の魚類確認種表から、検索用の候補を整理しています。</p></header>
<main><div class="notice"><strong>公開前の研究用プレビューです。</strong>過去の資料に記載された魚名で、現在の生息・釣果を示しません。要審査記録は魚種名と河川の組み合わせを含めて検索対象から外しています。水系のみの記録も個別河川へ広げていません。</div>
<div class="controls"><div><label for="river">川の名前</label><input id="river" type="search" placeholder="例：三刀屋川" maxlength="60"></div>
<div><label for="fish">魚の名前</label><input id="fish" type="search" placeholder="例：タカハヤ" maxlength="60"></div></div>
<p id="summary" role="status" aria-live="polite"></p><div id="results" class="cards"></div>
<p class="sub">斐伊川本川は資料記載の「斐伊川放水路〜尾原ダム」区間に限ります。支川・水系全体に魚名を拡張していません。採集地点、個別調査年、全国河川コードは未確認です。</p>
<script id="source-layer" type="application/json">__LAYER__</script>
<script>(function(){"use strict";const d=JSON.parse(document.getElementById("source-layer").textContent);
if(d.schema!=="tsurikue-shimane-sh22-fish-table-v01"||d.status!=="RESEARCH_ONLY_NOT_FOR_LIVE_SITE")throw Error("Invalid research layer");
const $=id=>document.getElementById(id),norm=s=>String(s||"").trim().toLocaleLowerCase();
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n}
function render(){const r=norm($("river").value),f=norm($("fish").value),found=d.river_groups.filter(x=>(!r||norm(x.river).includes(r))&&(!f||x.fish_labels.some(y=>norm(y.recorded_name).includes(f))));
$("results").replaceChildren();$("summary").textContent="該当する資料記録のある川："+found.length+"件（実在する川の全数ではありません）";
if(!found.length){$("results").append(el("p","該当する資料記録がありません。魚がいないという意味ではありません。"));return}
for(const x of found){const card=el("article");card.append(el("h2",x.river));card.append(el("p",x.prefecture+"｜"+x.watershed+"水系","sub"));card.append(el("small",x.source_scope_note));
const chips=el("div",undefined,"chips"),names=[...new Set(x.fish_labels.map(y=>y.recorded_name))].sort((a,b)=>a.localeCompare(b,"ja"));
for(const name of names){const b=el("button",name,"chip");b.type="button";b.title="この魚が記載された川を探す";b.addEventListener("click",()=>{$("fish").value=name;$("river").value="";render();$("fish").focus()});chips.append(b)}card.append(chips);
const a=el("a","島根県の原資料を確認");a.href=d.source_url;a.target="_blank";a.rel="noopener noreferrer";card.append(a);$("results").append(card)}}
for(const id of ["river","fish"])$(id).addEventListener("input",render);render()})();</script></main></body></html>'''


def render(layer: dict) -> str:
    if layer["schema"] != SCHEMA or layer["status"] != "RESEARCH_ONLY_NOT_FOR_LIVE_SITE":
        raise ValueError("Not the reviewed research-only SH22 layer")
    data = json.dumps(layer, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    result = HTML.replace("__LAYER__", data)
    if "__LAYER__" in result or 'name="robots" content="noindex,nofollow"' not in result:
        raise ValueError("Preview is incomplete or indexable")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    layer = build(load_csv(BASE_INPUT), load_csv(ADDITIONS_INPUT))
    if args.out.exists():
        raise FileExistsError("Refusing to overwrite an existing preview")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    content = render(layer)
    args.out.write_text(content, encoding="utf-8")
    print(json.dumps({"preview_bytes": len(content.encode()), "noindex": True,
                      "searchable_records": layer["searchable_research_record_total"],
                      "live_site_updated": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
