from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'outing-pc-layout-fix'))
from apply import CARD_FIX_START, NEW_FIX_START, PAGE_ID, get_page, raw  # noqa: E402

PUBLIC_URL='https://tsurikue.com/odekake/'
OUT=Path('outing-card-inner-grid-v3.json')
BEFORE_SHOT=Path('outing-card-inner-grid-v3-before-1440.png')
AFTER_SHOT=Path('outing-card-inner-grid-v3-after-1440.png')

CANDIDATE_CSS=r'''
/* tq-outing-pc-card-inner-grid-fix:v3 test */
@media(min-width:861px){
  body:has(.tq-out) .tq-out .tq-out-trip-card,
  body:has(.tq-out) .tq-out .tq-out-route-card{
    display:block!important;
    grid-template-columns:none!important;
    width:100%!important;
    min-width:0!important;
    max-width:none!important;
  }
  body:has(.tq-out) .tq-out .tq-out-trip-card>.wp-block-group__inner-container{
    display:grid!important;
    grid-template-columns:82px minmax(0,1fr)!important;
    gap:18px!important;
    align-items:center!important;
    width:100%!important;
    min-width:0!important;
    max-width:none!important;
  }
  body:has(.tq-out) .tq-out .tq-out-route-card>.wp-block-group__inner-container{
    display:grid!important;
    grid-template-columns:145px minmax(0,1fr) auto!important;
    gap:24px!important;
    align-items:center!important;
    width:100%!important;
    min-width:0!important;
    max-width:none!important;
  }
  body:has(.tq-out) .tq-out .tq-out-trip-copy,
  body:has(.tq-out) .tq-out .tq-out-route-copy{
    display:block!important;
    width:100%!important;
    min-width:0!important;
    max-width:none!important;
    margin:0!important;
    padding:0!important;
  }
}
'''

MEASURE=r'''
function box(el){if(!el)return null;const r=el.getBoundingClientRect(),c=getComputedStyle(el);return{width:+r.width.toFixed(2),height:+r.height.toFixed(2),left:+r.left.toFixed(2),right:+r.right.toFixed(2),display:c.display,grid:c.gridTemplateColumns,widthCss:c.width,minWidth:c.minWidth,maxWidth:c.maxWidth}}
const trip=[...document.querySelectorAll('.tq-out-trip-card')].slice(0,4).map(el=>({card:box(el),inner:box(el.querySelector(':scope>.wp-block-group__inner-container')),badge:box(el.querySelector('.tq-out-trip-badge')),copy:box(el.querySelector('.tq-out-trip-copy')),heading:box(el.querySelector('h3')),text:box(el.querySelector('.tq-out-trip-text'))}));
const route=[...document.querySelectorAll('.tq-out-route-card')].slice(0,3).map(el=>({card:box(el),inner:box(el.querySelector(':scope>.wp-block-group__inner-container')),label:box(el.querySelector('.tq-out-route-label')),copy:box(el.querySelector('.tq-out-route-copy')),heading:box(el.querySelector('h3')),text:box(el.querySelector('.tq-out-route-text')),arrow:box(el.querySelector('.tq-out-route-arrow'))}));
return{clientWidth:document.documentElement.clientWidth,scrollWidth:document.documentElement.scrollWidth,tripGrid:box(document.querySelector('.tq-out-trip-grid')),routeList:box(document.querySelector('.tq-out-route-list')),trip,route};
'''

def driver():
    o=Options();o.add_argument('--headless=new');o.add_argument('--no-sandbox');o.add_argument('--disable-dev-shm-usage');o.add_argument('--disable-gpu');o.add_argument('--window-size=1440,1200');o.add_argument('--force-device-scale-factor=1')
    d=webdriver.Chrome(options=o);d.set_window_size(1440,1200);return d

def shot(d,p):
    h=min(int(d.execute_script('return document.documentElement.scrollHeight')),12000);d.set_window_size(1440,max(1200,h));time.sleep(.3);d.save_screenshot(str(p));d.set_window_size(1440,1200)

def main():
    page,_=get_page();content=raw(page,'content')
    source={'id':page.get('id')==PAGE_ID,'publish':page.get('status')=='publish','old_card_fix':CARD_FIX_START in content,'shell_fix':NEW_FIX_START in content}
    if not all(source.values()):raise RuntimeError('SOURCE '+json.dumps(source,ensure_ascii=False))
    d=driver()
    try:
        d.get(PUBLIC_URL+'?inner_v3='+str(int(time.time())));time.sleep(3);before=d.execute_script(MEASURE);shot(d,BEFORE_SHOT)
        d.execute_script("const s=document.createElement('style');s.id='tq-inner-v3';s.textContent=arguments[0];document.head.appendChild(s);",CANDIDATE_CSS);time.sleep(.5)
        after=d.execute_script(MEASURE);shot(d,AFTER_SHOT)
    finally:d.quit()
    checks={
      'trip_count':len(after['trip'])==4,'route_count':len(after['route'])==3,
      'trip_outer_block':all(x['card']['display']=='block' for x in after['trip']),
      'trip_inner_grid':all(x['inner']['display']=='grid' and len(x['inner']['grid'].split())==2 for x in after['trip']),
      'trip_copy_wide':all(x['copy']['width']>=390 for x in after['trip']),
      'trip_heading_wide':all(x['heading']['width']>=390 for x in after['trip']),
      'trip_height':all(x['card']['height']<=250 for x in after['trip']),
      'route_outer_block':all(x['card']['display']=='block' for x in after['route']),
      'route_inner_grid':all(x['inner']['display']=='grid' and len(x['inner']['grid'].split())==3 for x in after['route']),
      'route_copy_wide':all(x['copy']['width']>=850 for x in after['route']),
      'route_heading_wide':all(x['heading']['width']>=850 for x in after['route']),
      'route_height':all(x['card']['height']<=190 for x in after['route']),
      'no_overflow':after['scrollWidth']==after['clientWidth']}
    OUT.write_text(json.dumps({'source':source,'checks':checks,'css':CANDIDATE_CSS,'before':before,'after':after},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'source':source,'checks':checks,'after':after},ensure_ascii=False))
    if not all(checks.values()):raise RuntimeError('V3_FAILED '+json.dumps(checks,ensure_ascii=False))

if __name__=='__main__':main()
