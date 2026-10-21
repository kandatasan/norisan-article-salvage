#!/usr/bin/env python3
"""Create a portable, offline HTML preview of the safe research-only river/fish layer."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from build_source_river_fish_layer import build, INPUT
import csv

HTML = r"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>川と魚のつながり｜研究用プレビュー</title>
<style>
:root{color-scheme:light;font-family:system-ui,-apple-system,"Noto Sans JP",sans-serif;color:#15313c;background:#f4f8f8}
*{box-sizing:border-box}body{margin:0}header{background:linear-gradient(120deg,#123c4e,#176c73);color:white;padding:2.2rem max(1rem,calc((100vw - 980px)/2))}
main{max-width:980px;margin:0 auto;padding:1.2rem 1rem 3rem}h1{font-size:clamp(1.5rem,5vw,2.4rem);margin:.25rem 0}h2{font-size:1.18rem}
p{line-height:1.8}.notice{background:#fff;padding:1rem 1.2rem;border-left:4px solid #3e8b8e;border-radius:8px}
.controls{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.8rem;margin:1.5rem 0}
label{font-weight:700;display:block;margin-bottom:.35rem}input,select{width:100%;border:1px solid #91b2b9;background:white;border-radius:10px;padding:.75rem;font:inherit}
#summary{font-weight:700;margin:1rem 0}.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem}
article{background:white;border:1px solid #d3e2e4;border-radius:14px;padding:1rem;box-shadow:0 2px 9px #1a4c4b0d}
article h2{margin:.1rem 0 .4rem}.sub{color:#56747d;font-size:.9rem}.chips{display:flex;flex-wrap:wrap;gap:.4rem;margin:.7rem 0}
.chip{background:#e6f4f1;border:1px solid #c3dcd7;border-radius:99px;padding:.35rem .65rem;cursor:pointer;color:#164a4a;font:inherit}
.chip:hover,.chip:focus-visible{background:#c7ebe3}.chip:focus-visible{outline:2px solid #225c7a}
small{display:block;color:#547078;line-height:1.65;margin:.6rem 0}a{color:#16618c}footer{margin-top:2rem;color:#526e76}
@media(max-width:700px){.controls,.cards{grid-template-columns:1fr}header{padding:1.5rem 1rem}}
</style></head><body>
<header><div style="font-size:.85rem;letter-spacing:.1em">つりくえ！日本の河川図鑑・研究用</div>
<h1>川から魚へ。魚から川へ。</h1>
<p>名前をたどると、知らなかった川と魚がつながる。</p></header>
<main>
<div class="notice"><strong>公開前の研究用プレビューです。</strong>各県の過去の資料に記載された魚名を表示します。現在その川に生息することや釣れることを保証しません。希少種などの要審査データと、水系単位の記録は除外しています。</div>
<div class="controls">
<div><label for="pref">都道府県</label><select id="pref"><option value="">すべての県</option></select></div>
<div><label for="river">川の名前</label><input id="river" type="search" placeholder="例：三刀屋川" maxlength="60"></div>
<div><label for="fish">魚の名前</label><input id="fish" type="search" placeholder="例：タカハヤ" maxlength="60"></div>
</div>
<p id="summary" role="status" aria-live="polite"></p><div id="results" class="cards"></div>
<footer>出典を明記した資料名の記録を検索しています。川名の同一性・全国河川コードは未承認です。元資料にない河川・支流へ魚名を広げません。</footer>
</main>
<script id="source-layer" type="application/json">__EMBEDDED_LAYER__</script>
<script>
(function(){
"use strict";
const d=JSON.parse(document.getElementById("source-layer").textContent);
if(d.schema!=="tsurikue-source-named-river-fish-v01"||d.status!=="RESEARCH_ONLY_NOT_FOR_LIVE_SITE")throw Error("Invalid research layer");
const $=id=>document.getElementById(id);
const prefs=[...new Set(d.river_groups.map(x=>x.prefecture))].sort((a,b)=>a.localeCompare(b,"ja"));
for(const p of prefs){const o=document.createElement("option");o.value=p;o.textContent=p;$("pref").append(o)}
const norm=s=>String(s||"").trim().toLocaleLowerCase();
function elem(tag,content,cls){const x=document.createElement(tag);if(content!==undefined)x.textContent=content;if(cls)x.className=cls;return x}
function render(){
 const p=$("pref").value,r=norm($("river").value),f=norm($("fish").value);
 const results=d.river_groups.filter(x=>(!p||x.prefecture===p)&&(!r||norm(x.river).includes(r)||norm(x.watershed).includes(r))&&(!f||x.fish_labels.some(y=>norm(y.recorded_name).includes(f))));
 $("results").replaceChildren();
 $("summary").textContent="資料に名前のある川 "+results.length+"件（実在河川の全数ではありません）";
 if(!results.length){$("results").append(elem("p","該当する資料記録がありません。魚がいないという意味ではありません。"));return}
 for(const x of results){
  const card=elem("article");card.append(elem("h2",x.river));
  card.append(elem("p",x.prefecture+"｜"+x.watershed+"水系","sub"));
  const chips=elem("div",undefined,"chips");
  const names=[...new Set(x.fish_labels.map(y=>y.recorded_name))].sort((a,b)=>a.localeCompare(b,"ja"));
  for(const name of names){const b=elem("button",name,"chip");b.type="button";b.title="この魚が記載された別の川を探す";b.addEventListener("click",()=>{$("fish").value=name;$("river").value="";$("pref").value="";render();$("fish").focus()});chips.append(b)}
  card.append(chips);
  const types=[...new Set(x.fish_labels.map(y=>y.evidence_kind))];
  card.append(elem("small",types.includes("official_survey_summary")?"県の魚類確認種表・河川環境資料から整理":"県の河川環境説明に魚名が記載"));
  const sourceUrls=[...new Set(x.fish_labels.map(y=>y.source_url))];
  for(const [i,url] of sourceUrls.entries()){const a=elem("a","出典資料を確認 "+(i+1));a.href=url;a.target="_blank";a.rel="noopener noreferrer";card.append(a)}
  $("results").append(card)
 }
}
for(const id of ["pref","river","fish"])$(id).addEventListener(id==="pref"?"change":"input",render);
render();
})();
</script></body></html>"""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    with INPUT.open(encoding="utf-8-sig", newline="") as f:
        layer = build(list(csv.DictReader(f)))
    data = json.dumps(layer, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    content = HTML.replace("__EMBEDDED_LAYER__", data)
    if args.out.exists():
        raise FileExistsError("Refuse overwrite")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(content, encoding="utf-8")
    print("OFFLINE_RIVER_FISH_PREVIEW_BUILT", json.dumps({
        "river_groups": len(layer["river_groups"]),
        "fish_labels": len(layer["fish_reverse_index"]),
        "bytes": len(content.encode("utf-8")), "research_only": True
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
