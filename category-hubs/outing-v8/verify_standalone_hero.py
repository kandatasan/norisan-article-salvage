#!/usr/bin/env python3
import json, pathlib, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

URL='https://tsurikue.com/odekake/?tq_audit=v8'
DOLPHIN='https://tsurikue.com/wp-content/uploads/2026/09/img_2419.jpg'
OUT=pathlib.Path('/tmp/outing-v8-render.json')

def driver(width,height):
    o=Options(); o.add_argument('--headless=new'); o.add_argument('--no-sandbox'); o.add_argument('--disable-dev-shm-usage'); o.add_argument(f'--window-size={width},{height}')
    d=webdriver.Chrome(options=o); d.get(URL); time.sleep(4); return d

def metrics(d):
    return d.execute_script(r'''
const q=s=>document.querySelector(s);
const hero=q('.tq-outing-v3.tq-hero');
const group=q('div.wp-block-group.tq-outing-v3:not(.tq-hero)');
const post=q('.post_content');
const header=q('#header');
const title=q('.c-pageTitle');
const intro=q('.tq-choose-intro');
const h1=hero && hero.querySelector('h1');
const img=hero && hero.querySelector('.wp-block-cover__image-background');
const children=post ? Array.from(post.children).map((el,i)=>({i,tag:el.tagName,cls:el.className||'',display:getComputedStyle(el).display})) : [];
const r=e=>e?e.getBoundingClientRect():null;
return {
 clientW:document.documentElement.clientWidth,scrollW:document.documentElement.scrollWidth,
 hero:r(hero),group:r(group),post:r(post),header:r(header),intro:r(intro),
 titleDisplay:title?getComputedStyle(title).display:null,titleHeight:title?r(title).height:null,
 heroClass:hero?hero.className:null,
 heroInGroup:group?group.querySelectorAll('.tq-hero').length:null,
 heroParentClass:hero&&hero.parentElement?hero.parentElement.className:null,
 firstVisibleChild:(children.find(x=>x.display!=='none')||null),
 children,
 h1Text:h1?h1.innerText.trim():null,h1Font:h1?getComputedStyle(h1).fontSize:null,
 imgSrc:img?img.currentSrc||img.src:null,
 details:document.querySelectorAll('details.tq-accordion').length,
 auto:document.documentElement.dataset.tqOutingAuto||null
};
''')

def run(width,height):
    d=driver(width,height)
    try: return metrics(d)
    finally: d.quit()

desktop=run(1440,1000); mobile=run(500,850)

def ok(m,mode):
    hero=m['hero']; header=m['header']; group=m['group']; post=m['post']
    gap=(hero['top']-header['bottom']) if hero and header else 999
    checks={
      'hero_exists':bool(hero),
      'group_exists':bool(group),
      'hero_not_inside_group':m['heroInGroup']==0,
      'hero_is_first_visible_post_child':bool(m['firstVisibleChild'] and 'tq-hero' in m['firstVisibleChild']['cls']),
      'hero_parent_is_post':bool(m['heroParentClass'] is not None and 'post_content' in m['heroParentClass']),
      'dolphin':m['imgSrc']==DOLPHIN,
      'heading':m['h1Text']=='今日は、\nどこ行く？',
      'title_hidden':m['titleDisplay']=='none' and (m['titleHeight'] or 0)==0,
      'five_details':m['details']==5,
      'no_overflow':m['scrollW']<=m['clientW']+2,
      'top_gap_not_worse':gap <= (70 if mode=='desktop' else 50),
      'hero_width_sane':bool(hero and post and hero['width']<=post['width']+2 and hero['width']>=post['width']-4),
      'auto_index':m['auto'] in ('ready','fallback'),
    }
    if mode=='mobile': checks['mobile_h1_size']=float(m['h1Font'].replace('px',''))<=36.5
    return checks,gap

dc,dgap=ok(desktop,'desktop'); mc,mgap=ok(mobile,'mobile')
checks={**{'desktop_'+k:v for k,v in dc.items()},**{'mobile_'+k:v for k,v in mc.items()}}
report={'checks':checks,'gaps':{'desktop':dgap,'mobile':mgap},'metrics':{'desktop':desktop,'mobile':mobile}}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
if not all(checks.values()): raise SystemExit(1)
