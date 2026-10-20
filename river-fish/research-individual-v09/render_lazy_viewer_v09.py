#!/usr/bin/env python3
"""Standalone no-iframe atlas; load all historic names only after clicking category.

Reuses the preceding research V06 mobile layout, swaps the sample-only panel
for one static JSON fetch per selected river/category. Never deploys to WP.
"""
import argparse
import importlib.util
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/"research-individual-v06/render_offline_navigation_v06.py"
NAV=HERE.parent/"research-individual-v07/outputs/river_atlas_navigation_v07.json"
START="  g.examples.forEach(function(row){"
END="\n}\nfunction paint(){crumb();"

REPLACEMENT=r"""  loadAllNames(r,state.group,el.result);
}
let requestToken=0;
const PAGE=35;
function loadAllNames(r,category,container){
  const token=++requestToken,region=r.region,key=r.identity_key;
  if(!/^[a-z_]+$/.test(region)||!/^rn_[0-9a-f]{24}$/.test(key)){
    container.appendChild(elem('p','河川の識別情報が不正です。'));return
  }
  const path=region+'/'+key+'/'+category+'.json';
  container.appendChild(elem('p','掲載名を読み込み中…','muted'));
  fetch(path,{cache:'force-cache'}).then(function(response){
    if(!response.ok)throw new Error('HTTP '+response.status);
    return response.json()
  }).then(function(doc){
    if(token!==requestToken||state.river!==key||state.group!==category)return;
    if(doc.river_identity!==key||doc.category!==category||
       doc.survey_region!==region||doc.source_scope!=='individual_named_river_only'||
       !Array.isArray(doc.labels))throw new Error('河川・分類・記録の照合に失敗');
    empty(container);
    container.appendChild(elem('h2',groupItems.find(function(x){return x[0]===category})[1]+'の掲載名一覧'));
    if(!doc.labels.length){
      container.appendChild(elem('p','個別河川の調査記録は未確認です。生息していない意味ではありません。'));return
    }
    container.appendChild(elem('p','記載名 '+doc.literal_labels_not_species.toLocaleString()+'表記 ／ 調査記録 '+doc.historical_contexts.toLocaleString()+'件 ／ '+doc.year_min+'〜'+doc.year_max+'年','muted'));
    const input=elem('input');input.type='search';input.placeholder='この川の生物名を検索';
    input.setAttribute('aria-label','生物名の絞り込み');
    input.style.cssText='width:100%;padding:12px;border:1px solid #b1ccd4;border-radius:8px;margin:10px 0';
    container.appendChild(input);
    const list=elem('div');container.appendChild(list);
    let displayed=PAGE;
    function draw(){
      empty(list);
      const query=input.value.trim();
      const filtered=doc.labels.filter(function(x){return x.recorded_name.includes(query)});
      filtered.slice(0,displayed).forEach(function(x){
        const d=elem('div',undefined,'src');
        d.appendChild(elem('strong',x.recorded_name));
        d.appendChild(elem('span',' （'+x.year_min+'〜'+x.year_max+'年、記録 '+x.historical_contexts+'件）','muted'));
        const citations=elem('div');
        x.source_evidence.forEach(function(s){
          if(typeof s.source_url==='string'&&s.source_url.startsWith('https://')){
            const link=elem('a','原資料');link.href=s.source_url;
            link.target='_blank';link.rel='noopener noreferrer';link.style.marginRight='10px';
            citations.appendChild(link)
          }
        });
        d.appendChild(citations);list.appendChild(d)
      });
      list.appendChild(elem('p','該当 '+filtered.length.toLocaleString()+'表記／表示 '+Math.min(displayed,filtered.length).toLocaleString()+'表記','muted'));
      if(displayed<filtered.length){
        const more=elem('button','さらに35件表示','rehome');more.type='button';
        more.addEventListener('click',function(){displayed+=PAGE;draw()});list.appendChild(more)
      }
    }
    input.addEventListener('input',function(){displayed=PAGE;draw()});
    draw();
  }).catch(function(err){
    if(token!==requestToken||state.river!==key||state.group!==category)return;
    empty(container);container.appendChild(elem('p','全件データを読み込めませんでした。アーカイブを展開してWebサーバーで開いてください。','muted'));
    container.appendChild(elem('p',String(err),'muted'))
  })
}
function paint(){crumb();"""

def render(navigation,output):
    m=importlib.util.spec_from_file_location("atlas_original_preview",OLD)
    lib=importlib.util.module_from_spec(m);m.loader.exec_module(lib)
    source=lib.TEMPLATE
    start=source.find(START);end=source.find(END,start)
    if start<0 or end<0:raise ValueError("Original two-row biology preview has changed")
    html=source[:start]+REPLACEMENT+source[end+len(END):]
    d=json.loads(Path(navigation).read_text(encoding="utf-8"))
    if len(d["prefectures"])!=47 or len(d["rivers"])!=428 or len(d["prefecture_watershed_entries"])!=80:
        raise ValueError("Unexpected previous validated navigation data")
    js=json.dumps(d,ensure_ascii=False,separators=(",",":"))
    js=js.replace("<","\\u003c").replace(">","\\u003e").replace("&","\\u0026")
    html=html.replace("__DATA__",js)
    if "<iframe" in html or "fetch(path" not in html or "__DATA__" in html:
        raise ValueError("Unsafe or incomplete static viewer")
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(html,encoding="utf-8")
    print(json.dumps({"file":str(output),"initial_html_bytes":output.stat().st_size,
        "prefecture_choices":47,"watershed_entries":80,
        "all_names_not_initially_embedded":True,"lazy_category_fetch":True},ensure_ascii=False))
    return html

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--navigation",default=str(NAV))
    p.add_argument("--out",required=True)
    a=p.parse_args();render(a.navigation,a.out)
