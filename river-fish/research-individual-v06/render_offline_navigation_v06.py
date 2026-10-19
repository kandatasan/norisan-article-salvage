#!/usr/bin/env python3
"""Offline no-iframe interactive demo: 47 prefectures -> sourced watersheds
-> surveyed river labels -> four historical biota categories.
Only research data, no WP, no network calls. ALL text via textContent.
"""
import argparse
import json
from pathlib import Path

TEMPLATE=r"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>日本の河川大図鑑・資料調査プレビュー</title>
<style>
:root{color:#223542;font-family:system-ui,-apple-system,"Hiragino Sans",sans-serif;background:#f2f7f8}
*{box-sizing:border-box}body{margin:0}header{padding:22px 15px;background:linear-gradient(115deg,#075979,#149890);color:white}
main{padding:14px;max-width:900px;margin:0 auto}h1{font-size:1.35rem;margin:0}h2{font-size:1.1rem;margin:14px 0 8px}
p{line-height:1.6}small,.muted{color:#5a6e79}.hint{padding:12px 14px;background:white;border-left:4px solid #12938d;border-radius:8px;font-size:.89rem}
#crumb{display:flex;align-items:center;flex-wrap:wrap;gap:5px;margin-top:14px}
#crumb button{color:#08748a;background:none;border:0;text-decoration:underline;padding:7px 4px;cursor:pointer}
#filter{width:100%;border:1px solid #bbd2da;border-radius:9px;padding:12px;margin:8px 0 12px}
#choices,.four{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.pick,.category{font:inherit;color:inherit;text-align:left;cursor:pointer;background:white;border:1px solid #bcd4dc;border-radius:11px;padding:13px;min-height:76px}
.pick:hover,.pick:focus-visible,.category:hover{background:#eaf8f9;border-color:#198e96}
.pick strong,.pick small,.category strong,.category small{display:block;overflow-wrap:anywhere}
.pick small,.category small{margin-top:6px;line-height:1.35}
.category.active{background:#e7f9fa;border:2px solid #108394}
#detail{padding:14px;background:white;border:1px solid #c2d9de;border-radius:12px}
#detail-meta{font-size:.88rem;color:#4c6670}.src{border-top:1px solid #e1eaee;padding-top:9px;margin-top:8px}
a{color:#04708c}footer{margin:24px 0}.rehome{font:inherit;background:#077d8f;color:white;border:0;padding:11px 16px;border-radius:10px}
@media(min-width:680px){#choices{grid-template-columns:repeat(3,minmax(0,1fr))}}
</style></head><body>
<header><main><h1>🌊 日本の河川大図鑑</h1><div>研究用試作品｜都道府県 → 水系 → 河川 → 生物4分類</div></main></header>
<main>
<p class="hint">県の公式資料に掲載された水系と、全国の生物調査で使われた水系名を照合した研究用画面です。<strong>その水系内のすべての川が、選択した県内にあるとは限りません。</strong>調査記録は過去のもので、現在の生息状況を保証しません。未照合の県・水系も残っています。</p>
<nav id="crumb" aria-label="選択経路"></nav>
<h2 id="heading">都道府県を選ぶ</h2><p id="subtitle" class="muted"></p>
<input id="filter" type="search" placeholder="ここに名前を入力して絞り込み" aria-label="一覧を検索">
<div id="choices"></div>
<section id="detail" hidden>
<h2 id="detail-title"></h2><p id="detail-meta"></p>
<p class="hint">個別河川の過去の調査資料にある記載名です。0件は生物がいないことを意味しません。魚類・底生動物・鳥類・植物を別々に表示します。</p>
<div class="four" id="four"></div><section id="category-result" aria-live="polite"></section>
</section>
<footer><button class="rehome" id="reset">← 都道府県から選び直す</button></footer>
</main>
<script type="application/json" id="dataset">__DATA__</script>
<script>
'use strict';
const dataset=JSON.parse(document.getElementById('dataset').textContent);
const riv=new Map(dataset.rivers.map(function(r){return [r.identity_key,r]}));
const el={crumb:document.getElementById('crumb'),heading:document.getElementById('heading'),
subtitle:document.getElementById('subtitle'),filter:document.getElementById('filter'),
choices:document.getElementById('choices'),detail:document.getElementById('detail'),
title:document.getElementById('detail-title'),meta:document.getElementById('detail-meta'),
four:document.getElementById('four'),result:document.getElementById('category-result')};
let state={pref:null,water:null,river:null,group:null};
const groupItems=[['fish','🐟 魚類'],['benthic_animals','🪲 底生動物'],['birds','🐦 鳥類'],['plants','🌿 植物']];
function elem(tag,content,classname){
  const e=document.createElement(tag);if(content!==undefined)e.textContent=content;
  if(classname)e.className=classname;return e;
}
function empty(e){e.replaceChildren()}
function goto(key,value){
  state[key]=value;
  if(key==='pref'){state.water=null;state.river=null;state.group=null}
  else if(key==='water'){state.river=null;state.group=null}
  else if(key==='river'){state.group=null}
  el.filter.value='';paint();
}
function item(title,description,click){
  const b=elem('button',undefined,'pick');b.type='button';
  b.appendChild(elem('strong',title));b.appendChild(elem('small',description));
  b.addEventListener('click',click);el.choices.appendChild(b)
}
function crumb(){
  empty(el.crumb);
  function nav(label,key,val){
    const b=elem('button',label);b.addEventListener('click',function(){goto(key,val)});el.crumb.appendChild(b)
  }
  nav('都道府県','pref',null);
  if(state.pref){el.crumb.appendChild(elem('span','›'));nav(state.pref,'water',null)}
  if(state.water){el.crumb.appendChild(elem('span','›'));nav(state.water,'river',null)}
  if(state.river){el.crumb.appendChild(elem('span','›'));el.crumb.appendChild(elem('strong',riv.get(state.river).river_name))}
}
function selections(){
  empty(el.choices);el.choices.hidden=false;el.filter.hidden=false;el.detail.hidden=true;
  const q=el.filter.value.trim();
  if(!state.pref){
    el.heading.textContent='① 都道府県を選ぶ';
    el.subtitle.textContent='47都道府県。水系の調査記録との照合ができていない県は「調査中」。';
    dataset.prefectures.filter(function(p){return p.prefecture.includes(q)}).forEach(function(p){
      item(p.prefecture,p.available_watersheds?('水系の入口 '+p.available_watersheds+'件'):'生物調査との照合は調査中',
        function(){goto('pref',p.prefecture)})
    });
  }else if(!state.water){
    el.heading.textContent='② 水系を選ぶ';
    el.subtitle.textContent='この段階では生物の一覧は表示しません。';
    const ws=dataset.prefecture_watershed_entries.filter(function(w){return w.prefecture===state.pref&&w.watershed.includes(q)});
    ws.forEach(function(w){
      item(w.watershed,'水系に掲載された河川 '+w.surveyed_river_name_ids+'件（県内の流路は未確認）',
        function(){goto('water',w.watershed)})
    });
    if(!ws.length)el.choices.appendChild(elem('p','この県については、個別河川の生物調査記録と照合できた水系がまだありません。','muted'));
  }else{
    el.heading.textContent='③ 河川を選ぶ';
    el.subtitle.textContent='対象水系内の調査資料に掲載された川。すべてが選択県内にあるという意味ではありません。';
    const links=dataset.prefecture_river_links.filter(function(x){return x.prefecture===state.pref&&x.watershed===state.water&&x.river_name.includes(q)});
    links.forEach(function(link){
      const r=riv.get(link.identity_key);
      let msg=r.survey_record_contexts.toLocaleString()+'件の過去調査記録';
      if(link.individual_river_explicit_prefecture_mentions)msg+='／県公式資料にも名称掲載';
      item(link.river_name,msg,function(){goto('river',link.identity_key)})
    })
  }
}
function detail(){
  const r=riv.get(state.river);if(!r)return;
  el.choices.hidden=true;el.filter.hidden=true;el.detail.hidden=false;
  el.heading.textContent='④ 生物調査記録';el.subtitle.textContent='分類をタップして確認';
  el.title.textContent=r.river_name;
  el.meta.textContent='水系：'+r.watershed_name+' ／ 10桁河川コード：'+(r.river_code||'未確認')+' ／ 調査記録：'+r.survey_record_contexts.toLocaleString()+'件';
  empty(el.four);
  groupItems.forEach(function(row){
    const g=r.biota[row[0]],b=elem('button',undefined,'category'+(state.group===row[0]?' active':''));
    b.appendChild(elem('strong',row[1]));
    b.appendChild(elem('small',g.record_contexts?(g.record_contexts.toLocaleString()+'件の記録'):'個別記録は未確認'));
    b.addEventListener('click',function(){state.group=state.group===row[0]?null:row[0];detail()});
    el.four.appendChild(b)
  });
  empty(el.result);
  if(!state.group){el.result.appendChild(elem('p','4つの分類から選ぶと、実際の生物名・年度・出典の例を表示します。','muted'));return}
  const g=r.biota[state.group];el.result.appendChild(elem('h2',groupItems.find(function(x){return x[0]===state.group})[1]));
  if(!g.record_contexts){el.result.appendChild(elem('p','個別河川の調査記録は未確認です。存在しないとは断定できません。'));return}
  el.result.appendChild(elem('p','資料の掲載名表記：'+g.literal_names_not_species+' ／ 調査年度：'+g.year_min+'〜'+g.year_max,'muted'));
  g.examples.forEach(function(row){
    const d=elem('div',undefined,'src');
    d.appendChild(elem('strong',row.recorded_name+'（'+row.survey_year+'年）'));
    const a=elem('a',' 原資料');a.href=row.source_url;a.target='_blank';a.rel='noopener noreferrer';d.appendChild(a);
    el.result.appendChild(d)
  });
  el.result.appendChild(elem('p','研究用プレビューでは各分類の例を最大2件表示。全件は研究用SQLiteに保存しています。','muted'))
}
function paint(){crumb();if(state.river)detail();else selections()}
el.filter.addEventListener('input',function(){if(!state.river)selections()});
document.getElementById('reset').addEventListener('click',function(){state={pref:null,water:null,river:null,group:null};el.filter.value='';paint()});
paint();
</script></body></html>"""

def render(source,dest):
    info=json.loads(Path(source).read_text(encoding="utf-8"))
    if len(info["prefectures"])!=47 or len(info["rivers"])!=428:
        raise ValueError("Incomplete prefab data")
    payload=json.dumps(info,ensure_ascii=False,separators=(",",":"))
    payload=payload.replace("<","\\u003c").replace(">","\\u003e").replace("&","\\u0026").replace("\u2028","\\u2028")
    html=TEMPLATE.replace("__DATA__",payload)
    if "<iframe" in html or "fetch(" in html:raise ValueError("No iframes or network requests allowed")
    dest=Path(dest);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(html,encoding="utf-8")
    print("PREVIEW",str(dest),dest.stat().st_size)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--source",required=True);p.add_argument("--out",required=True)
    a=p.parse_args();render(a.source,a.out)
