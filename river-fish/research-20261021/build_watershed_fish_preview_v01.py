#!/usr/bin/env python3
"""Create a noindex offline search preview for watershed-scoped fish records."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from build_watershed_fish_index_v01 import INPUT, SCHEMA, build

HTML = r"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>水系単位の魚類資料検索｜研究用</title>
<style>
:root{color-scheme:light;font-family:system-ui,-apple-system,"Noto Sans JP",sans-serif;color:#15313c;background:#f4f8f8}
*{box-sizing:border-box}body{margin:0}header{background:linear-gradient(120deg,#123c4e,#176c73);color:white;padding:1.7rem max(1rem,calc((100vw - 900px)/2))}
main{max-width:900px;margin:0 auto;padding:1rem 1rem 3rem}h1{font-size:clamp(1.4rem,5vw,2.2rem)}p{line-height:1.7}.notice{background:white;border-left:4px solid #c17732;padding:1rem;border-radius:8px}
.controls{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.8rem;margin:1.3rem 0}label{font-weight:700;display:block;margin-bottom:.35rem}input,select{width:100%;padding:.72rem;border:1px solid #91b2b9;border-radius:9px;font:inherit;background:white}
#summary{font-weight:700}.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem}article{background:white;border:1px solid #d3e2e4;border-radius:14px;padding:1rem}
article h2{margin:.1rem 0 .35rem}.sub,small{color:#56747d;line-height:1.6}.chips{display:flex;flex-wrap:wrap;gap:.4rem;margin:.7rem 0}.chip{border:1px solid #c3dcd7;border-radius:99px;padding:.35rem .65rem;background:#e6f4f1;cursor:pointer;color:#164a4a;font:inherit}a{color:#16618c}
@media(max-width:700px){.controls,.cards{grid-template-columns:1fr}header{padding:1.3rem 1rem}}
</style></head><body>
<header><div>つりくえ！日本の河川図鑑・研究用</div><h1>水系に残る魚類資料を探す</h1><p>魚名から水系へ、水系から魚の記録へ。</p></header>
<main><div class="notice"><strong>研究用・公開未承認。</strong>ここに表示するのは水系単位の過去資料です。個別の川や調査地点には割り当てず、現在の生息や釣果も保証しません。</div>
<div class="controls"><div><label for="pref">資料の発行県</label><select id="pref"><option value="">すべて</option></select></div><div><label for="water">水系名</label><input id="water" type="search" maxlength="60" placeholder="例：錦川"></div><div><label for="fish">魚名</label><input id="fish" type="search" maxlength="60" placeholder="例：オオクチバス"></div></div>
<p id="summary" role="status" aria-live="polite"></p><div id="results" class="cards"></div><p><small>水系名が一致しても個別河川の記録ではありません。出典に調査年がない場合は空欄です。</small></p></main>
<script id="data" type="application/json">__DATA__</script><script>
(function(){"use strict";const d=JSON.parse(document.getElementById("data").textContent);if(d.schema!=="tsurikue-source-watershed-fish-v01"||d.individual_river_links!==0)throw Error("Invalid source scope");const $=id=>document.getElementById(id),norm=s=>String(s||"").trim().toLocaleLowerCase(),el=(tag,t,cl)=>{const x=document.createElement(tag);if(t!==undefined)x.textContent=t;if(cl)x.className=cl;return x};
for(const p of [...new Set(d.watershed_groups.map(x=>x.prefecture))].sort((a,b)=>a.localeCompare(b,"ja"))){const o=document.createElement("option");o.value=p;o.textContent=p;$("pref").append(o)}
function render(){const p=$("pref").value,w=norm($("water").value),f=norm($("fish").value),xs=d.watershed_groups.filter(x=>(!p||x.prefecture===p)&&(!w||norm(x.watershed).includes(w))&&(!f||x.fish_labels.some(y=>norm(y.recorded_name).includes(f))));$("results").replaceChildren();$("summary").textContent="水系単位の資料記録 "+xs.length+"件（個別河川には未接続）";if(!xs.length){$("results").append(el("p","該当する資料記録がありません。魚がいないことを示すものではありません。"));return}for(const x of xs){const card=el("article");card.append(el("h2",x.watershed+"水系"));card.append(el("p",x.prefecture+"｜水系単位（個別河川は未特定）","sub"));const chips=el("div",undefined,"chips");for(const fish of [...new Set(x.fish_labels.map(y=>y.recorded_name))]){const b=el("button",fish,"chip");b.type="button";b.addEventListener("click",()=>{$("fish").value=fish;$("water").value="";render()});chips.append(b)}card.append(chips);for(const f of x.fish_labels){const p=el("p",f.claim+"。調査年："+(f.survey_year||"資料に記載なし"));card.append(p);const a=el("a","出典資料");a.href=f.source_url;a.target="_blank";a.rel="noopener noreferrer";card.append(a)}$("results").append(card)}}
for(const id of ["pref","water","fish"])$(id).addEventListener(id==="pref"?"change":"input",render);render()})();
</script></body></html>"""


def render(layer: dict) -> str:
    if layer.get("schema") != SCHEMA or layer.get("status") != "RESEARCH_ONLY_NOT_FOR_LIVE_SITE":
        raise ValueError("Not the watershed-only research index")
    if layer.get("individual_river_links") != 0 or layer.get("current_distribution_verified") is not False:
        raise ValueError("Unexpected publication or river scope")
    data = json.dumps(layer, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    page = HTML.replace("__DATA__", data)
    if "__DATA__" in page or 'name="robots" content="noindex,nofollow"' not in page:
        raise ValueError("Preview did not render as an offline noindex page")
    return page


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError("Refuse to overwrite watershed fish preview")
    with INPUT.open(encoding="utf-8-sig", newline="") as handle:
        page = render(build(list(csv.DictReader(handle))))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(page, encoding="utf-8")
    print("WATERSHED_FISH_PREVIEW_V01", json.dumps({
        "bytes": len(page.encode("utf-8")), "noindex": True, "published": False,
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
