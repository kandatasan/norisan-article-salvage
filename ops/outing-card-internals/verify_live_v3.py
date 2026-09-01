from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'outing-pc-layout-fix'))
from apply import NEW_FIX_END, NEW_FIX_START, PAGE_ID, get_page, raw  # noqa: E402
from apply_live_v3 import FIX_END, FIX_START  # noqa: E402

PUBLIC_URL='https://tsurikue.com/odekake/'
OUT=Path('outing-card-inner-grid-live-verify.json')
DESKTOP_SHOT=Path('outing-card-inner-grid-live-desktop-1440.png')
MOBILE_SHOT=Path('outing-card-inner-grid-live-mobile-390.png')

MEASURE=r'''
function box(el){if(!el)return null;const r=el.getBoundingClientRect(),c=getComputedStyle(el);return{width:+r.width.toFixed(2),height:+r.height.toFixed(2),left:+r.left.toFixed(2),right:+r.right.toFixed(2),display:c.display,grid:c.gridTemplateColumns,paddingLeft:c.paddingLeft,paddingRight:c.paddingRight}}
const trip=[...document.querySelectorAll('.tq-out-trip-card')].slice(0,4).map(el=>({card:box(el),inner:box(el.querySelector(':scope>.wp-block-group__inner-container')),copy:box(el.querySelector('.tq-out-trip-copy')),heading:box(el.querySelector('h3'))}));
const route=[...document.querySelectorAll('.tq-out-route-card')].slice(0,3).map(el=>({card:box(el),inner:box(el.querySelector(':scope>.wp-block-group__inner-container')),copy:box(el.querySelector('.tq-out-route-copy')),heading:box(el.querySelector('h3'))}));
return{clientWidth:document.documentElement.clientWidth,scrollWidth:document.documentElement.scrollWidth,post:box(document.querySelector('.post_content')),root:box(document.querySelector('.tq-out')),hero:box(document.querySelector('.tq-out-hero')),heroInner:box(document.querySelector('.tq-out-hero-inner')),tripGrid:box(document.querySelector('.tq-out-trip-grid')),routeList:box(document.querySelector('.tq-out-route-list')),trip,route};
'''

def make_driver(w,h):
    o=Options();o.add_argument('--headless=new');o.add_argument('--no-sandbox');o.add_argument('--disable-dev-shm-usage');o.add_argument('--disable-gpu');o.add_argument(f'--window-size={w},{h}');o.add_argument('--force-device-scale-factor=1')
    d=webdriver.Chrome(options=o);d.set_window_size(w,h);return d

def load(d,label):
    d.get(PUBLIC_URL+'?'+urlencode({'live_card_verify':f'{int(time.time())}-{label}'}));time.sleep(3);return d.execute_script(MEASURE)

def shot(d,path,w):
    h=min(int(d.execute_script('return document.documentElement.scrollHeight')),12000);d.set_window_size(w,max(900,h));time.sleep(.3);d.save_screenshot(str(path))

def main():
    page,_=get_page();content=raw(page,'content')
    content_checks={'id':page.get('id')==PAGE_ID,'publish':page.get('status')=='publish','shell_fix_once':content.count(NEW_FIX_START)==1 and content.count(NEW_FIX_END)==1,'card_fix_once':content.count(FIX_START)==1 and content.count(FIX_END)==1,'desktop_scope':'@media(min-width:861px)' in content}
    if not all(content_checks.values()):raise RuntimeError('CONTENT_CHECK_FAILED '+json.dumps(content_checks,ensure_ascii=False))

    d=make_driver(1440,1200)
    try:
        desktop=load(d,'desktop');client=desktop['clientWidth']
        desktop_checks={
          'root_full':abs(desktop['root']['left'])<=1 and abs(desktop['root']['right']-client)<=1,
          'hero_full':abs(desktop['hero']['left'])<=1 and abs(desktop['hero']['right']-client)<=1,
          'hero_inner_centered':abs((desktop['heroInner']['left']+desktop['heroInner']['right'])/2-client/2)<=2,
          'trip_count':len(desktop['trip'])==4,'route_count':len(desktop['route'])==3,
          'trip_outer_block':all(x['card']['display']=='block' for x in desktop['trip']),
          'trip_inner_grid':all(x['inner']['display']=='grid' and len(x['inner']['grid'].split())==2 for x in desktop['trip']),
          'trip_copy_wide':all(x['copy']['width']>=390 for x in desktop['trip']),
          'trip_heading_wide':all(x['heading']['width']>=390 for x in desktop['trip']),
          'trip_height':all(x['card']['height']<=250 for x in desktop['trip']),
          'route_outer_block':all(x['card']['display']=='block' for x in desktop['route']),
          'route_inner_grid':all(x['inner']['display']=='grid' and len(x['inner']['grid'].split())==3 for x in desktop['route']),
          'route_copy_wide':all(x['copy']['width']>=850 for x in desktop['route']),
          'route_heading_wide':all(x['heading']['width']>=850 for x in desktop['route']),
          'route_height':all(x['card']['height']<=190 for x in desktop['route']),
          'no_overflow':desktop['scrollWidth']==client}
        shot(d,DESKTOP_SHOT,1440)
    finally:d.quit()

    m=make_driver(390,844)
    try:
        mobile=load(m,'mobile');mc=mobile['clientWidth']
        mobile_checks={'root_present':mobile['root'] is not None and mobile['root']['width']>0,'hero_present':mobile['hero'] is not None and mobile['hero']['width']>0,'trip_present':len(mobile['trip'])==4,'route_present':len(mobile['route'])==3,'no_overflow':mobile['scrollWidth']==mc}
        shot(m,MOBILE_SHOT,390)
    finally:m.quit()

    checks={'content':content_checks,'desktop':desktop_checks,'mobile':mobile_checks}
    if not all(all(v.values()) for v in checks.values()):raise RuntimeError('LIVE_VERIFY_FAILED '+json.dumps(checks,ensure_ascii=False))
    result={'post_id':PAGE_ID,'status':page.get('status'),'checks':checks,'desktop':desktop,'mobile':mobile}
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'post_id':PAGE_ID,'status':page.get('status'),'checks':checks,'desktop_summary':{'trip':desktop['trip'],'route':desktop['route']},'mobile_summary':{'clientWidth':mobile['clientWidth'],'scrollWidth':mobile['scrollWidth']}},ensure_ascii=False))

if __name__=='__main__':main()
