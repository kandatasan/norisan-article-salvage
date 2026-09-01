from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'outing-pc-layout-fix'))
from apply import CARD_FIX_START, NEW_FIX_START, PAGE_ID, get_page, raw  # noqa: E402

PUBLIC_URL = 'https://tsurikue.com/odekake/'
OUT = Path('outing-card-internals-test.json')
BEFORE_SHOT = Path('outing-card-internals-before-1440.png')
AFTER_SHOT = Path('outing-card-internals-after-flex-1440.png')

CANDIDATE_CSS = r'''
/* tq-outing-pc-card-flex-fix:v1 test */
@media(min-width:861px){
  .tq-out .tq-out-trip-card,
  .tq-out .tq-out-trip-card>.wp-block-group__inner-container{
    display:flex!important;
    grid-template-columns:none!important;
    align-items:center!important;
    gap:18px!important;
    width:100%!important;
    min-width:0!important;
    max-width:none!important;
  }
  .tq-out .tq-out-trip-card>.wp-block-group__inner-container{
    flex:1 1 auto!important;
  }
  .tq-out .tq-out-trip-card .tq-out-trip-badge{
    flex:0 0 72px!important;
    width:72px!important;
    min-width:72px!important;
    max-width:72px!important;
    writing-mode:horizontal-tb!important;
  }
  .tq-out .tq-out-trip-card .tq-out-trip-copy{
    flex:1 1 0!important;
    width:auto!important;
    min-width:0!important;
    max-width:none!important;
    display:block!important;
    writing-mode:horizontal-tb!important;
  }
  .tq-out .tq-out-trip-card .tq-out-trip-copy>*{
    width:auto!important;
    min-width:0!important;
    max-width:none!important;
    margin-left:0!important;
    margin-right:0!important;
    writing-mode:horizontal-tb!important;
    white-space:normal!important;
    word-break:normal!important;
  }

  .tq-out .tq-out-route-card,
  .tq-out .tq-out-route-card>.wp-block-group__inner-container{
    display:flex!important;
    grid-template-columns:none!important;
    align-items:center!important;
    gap:24px!important;
    width:100%!important;
    min-width:0!important;
    max-width:none!important;
  }
  .tq-out .tq-out-route-card>.wp-block-group__inner-container{
    flex:1 1 auto!important;
  }
  .tq-out .tq-out-route-card .tq-out-route-label{
    flex:0 0 145px!important;
    width:145px!important;
    min-width:145px!important;
    max-width:145px!important;
    writing-mode:horizontal-tb!important;
  }
  .tq-out .tq-out-route-card .tq-out-route-copy{
    flex:1 1 0!important;
    width:auto!important;
    min-width:0!important;
    max-width:none!important;
    display:block!important;
    writing-mode:horizontal-tb!important;
  }
  .tq-out .tq-out-route-card .tq-out-route-copy>*{
    width:auto!important;
    min-width:0!important;
    max-width:none!important;
    margin-left:0!important;
    margin-right:0!important;
    writing-mode:horizontal-tb!important;
    white-space:normal!important;
    word-break:normal!important;
  }
  .tq-out .tq-out-route-card .tq-out-route-arrow{
    flex:0 0 auto!important;
    width:auto!important;
    min-width:0!important;
    max-width:none!important;
  }
}
'''

MEASURE = r'''
function box(el){
  if(!el) return null;
  const r=el.getBoundingClientRect(), cs=getComputedStyle(el);
  return {
    tag:el.tagName,
    cls:String(el.className||''),
    left:Math.round(r.left*100)/100,
    right:Math.round(r.right*100)/100,
    width:Math.round(r.width*100)/100,
    height:Math.round(r.height*100)/100,
    display:cs.display,
    minWidth:cs.minWidth,
    maxWidth:cs.maxWidth,
    widthCss:cs.width,
    grid:cs.gridTemplateColumns,
    flex:cs.flex,
    justifySelf:cs.justifySelf,
    writingMode:cs.writingMode,
    whiteSpace:cs.whiteSpace,
    wordBreak:cs.wordBreak,
  };
}
function tree(sel){
  const el=document.querySelector(sel);
  if(!el) return null;
  return {
    self:box(el),
    html:el.outerHTML.slice(0,2200),
    children:[...el.children].map(ch=>({
      self:box(ch),
      children:[...ch.children].map(g=>box(g)),
    })),
  };
}
const trip=[...document.querySelectorAll('.tq-out-trip-card')].slice(0,4).map(el=>({
  card:box(el),
  directChildren:[...el.children].map(box),
  badge:box(el.querySelector('.tq-out-trip-badge')),
  copy:box(el.querySelector('.tq-out-trip-copy')),
  label:box(el.querySelector('.tq-out-trip-label')),
  heading:box(el.querySelector('h3')),
  text:box(el.querySelector('.tq-out-trip-text')),
}));
const route=[...document.querySelectorAll('.tq-out-route-card')].slice(0,3).map(el=>({
  card:box(el),
  directChildren:[...el.children].map(box),
  label:box(el.querySelector('.tq-out-route-label')),
  copy:box(el.querySelector('.tq-out-route-copy')),
  heading:box(el.querySelector('h3')),
  text:box(el.querySelector('.tq-out-route-text')),
  arrow:box(el.querySelector('.tq-out-route-arrow')),
}));
return {
  clientWidth:document.documentElement.clientWidth,
  scrollWidth:document.documentElement.scrollWidth,
  tripGrid:box(document.querySelector('.tq-out-trip-grid')),
  routeList:box(document.querySelector('.tq-out-route-list')),
  trip,
  route,
  sampleTripTree:tree('.tq-out-trip-card'),
  sampleRouteTree:tree('.tq-out-route-card'),
};
'''


def make_driver():
    options=Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1440,1200')
    options.add_argument('--force-device-scale-factor=1')
    d=webdriver.Chrome(options=options)
    d.set_window_size(1440,1200)
    return d


def shot(driver, path: Path):
    h=min(int(driver.execute_script('return document.documentElement.scrollHeight')),12000)
    driver.set_window_size(1440,max(1200,h))
    time.sleep(.4)
    driver.save_screenshot(str(path))
    driver.set_window_size(1440,1200)


def main():
    page,_=get_page()
    content=raw(page,'content')
    source_checks={
        'id': page.get('id') == PAGE_ID,
        'status_publish': page.get('status') == 'publish',
        'existing_card_fix': CARD_FIX_START in content,
        'shell_fix': NEW_FIX_START in content,
    }
    if not all(source_checks.values()):
        raise RuntimeError('SOURCE_CHECK_FAILED '+json.dumps(source_checks,ensure_ascii=False))

    d=make_driver()
    try:
        d.get(PUBLIC_URL+'?card_diag='+str(int(time.time())))
        time.sleep(3)
        before=d.execute_script(MEASURE)
        shot(d,BEFORE_SHOT)
        d.execute_script("const s=document.createElement('style');s.id='tq-card-flex-test';s.textContent=arguments[0];document.head.appendChild(s);",CANDIDATE_CSS)
        time.sleep(.5)
        after=d.execute_script(MEASURE)
        shot(d,AFTER_SHOT)
    finally:
        d.quit()

    checks={
        'trip_count_4': len(after['trip']) == 4,
        'route_count_3': len(after['route']) == 3,
        'trip_copy_wide': all((x['copy'] or {}).get('width',0) >= 330 for x in after['trip']),
        'trip_heading_wide': all((x['heading'] or {}).get('width',0) >= 300 for x in after['trip']),
        'trip_cards_reasonable_height': all((x['card'] or {}).get('height',9999) <= 260 for x in after['trip']),
        'route_copy_wide': all((x['copy'] or {}).get('width',0) >= 650 for x in after['route']),
        'route_heading_wide': all((x['heading'] or {}).get('width',0) >= 600 for x in after['route']),
        'route_cards_reasonable_height': all((x['card'] or {}).get('height',9999) <= 190 for x in after['route']),
        'no_horizontal_overflow': after['scrollWidth'] == after['clientWidth'],
        'trip_text_horizontal': all((x['copy'] or {}).get('writingMode') == 'horizontal-tb' for x in after['trip']),
        'route_text_horizontal': all((x['copy'] or {}).get('writingMode') == 'horizontal-tb' for x in after['route']),
    }
    result={'source_checks':source_checks,'checks':checks,'candidate_css':CANDIDATE_CSS,'before':before,'after':after}
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({
        'source_checks':source_checks,
        'checks':checks,
        'before_trip':before['trip'],
        'after_trip':after['trip'],
        'before_route':before['route'],
        'after_route':after['route'],
    },ensure_ascii=False))
    if not all(checks.values()):
        raise RuntimeError('CANDIDATE_FIX_FAILED '+json.dumps(checks,ensure_ascii=False))


if __name__=='__main__':
    main()
