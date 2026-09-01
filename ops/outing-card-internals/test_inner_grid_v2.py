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
OUT = Path('outing-card-inner-grid-v2.json')
BEFORE_SHOT = Path('outing-card-inner-grid-v2-before-1440.png')
AFTER_SHOT = Path('outing-card-inner-grid-v2-after-1440.png')

# SWELL inserts .wp-block-group__inner-container inside Group blocks.
# The existing PC card CSS already gives that wrapper the correct grid columns,
# but the outer Group is also a grid, so the wrapper itself is constrained to
# the first fixed-width track. The minimal fix is to make only the OUTER card
# a normal block and let the existing inner wrapper own the grid.
CANDIDATE_CSS = r'''
/* tq-outing-pc-card-inner-grid-fix:v2 test */
@media(min-width:861px){
  .tq-out .tq-out-trip-card,
  .tq-out .tq-out-route-card{
    display:block!important;
    grid-template-columns:none!important;
    width:100%!important;
    min-width:0!important;
    max-width:none!important;
  }
  .tq-out .tq-out-trip-card>.wp-block-group__inner-container,
  .tq-out .tq-out-route-card>.wp-block-group__inner-container{
    width:100%!important;
    min-width:0!important;
    max-width:none!important;
  }
  .tq-out .tq-out-trip-copy,
  .tq-out .tq-out-route-copy{
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
    width:Math.round(r.width*100)/100,
    height:Math.round(r.height*100)/100,
    left:Math.round(r.left*100)/100,
    right:Math.round(r.right*100)/100,
    display:cs.display,
    grid:cs.gridTemplateColumns,
    widthCss:cs.width,
    minWidth:cs.minWidth,
    maxWidth:cs.maxWidth,
  };
}
const trip=[...document.querySelectorAll('.tq-out-trip-card')].slice(0,4).map(el=>({
  card:box(el),
  inner:box(el.querySelector(':scope>.wp-block-group__inner-container')),
  badge:box(el.querySelector('.tq-out-trip-badge')),
  copy:box(el.querySelector('.tq-out-trip-copy')),
  heading:box(el.querySelector('h3')),
  text:box(el.querySelector('.tq-out-trip-text')),
}));
const route=[...document.querySelectorAll('.tq-out-route-card')].slice(0,3).map(el=>({
  card:box(el),
  inner:box(el.querySelector(':scope>.wp-block-group__inner-container')),
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
  trip,route
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
        'old_card_fix': CARD_FIX_START in content,
        'shell_fix': NEW_FIX_START in content,
    }
    if not all(source_checks.values()):
        raise RuntimeError('SOURCE_CHECK_FAILED '+json.dumps(source_checks,ensure_ascii=False))

    d=make_driver()
    try:
        d.get(PUBLIC_URL+'?card_inner_v2='+str(int(time.time())))
        time.sleep(3)
        before=d.execute_script(MEASURE)
        shot(d,BEFORE_SHOT)
        d.execute_script("const s=document.createElement('style');s.id='tq-card-inner-v2-test';s.textContent=arguments[0];document.head.appendChild(s);",CANDIDATE_CSS)
        time.sleep(.5)
        after=d.execute_script(MEASURE)
        shot(d,AFTER_SHOT)
    finally:
        d.quit()

    checks={
        'trip_count_4': len(after['trip']) == 4,
        'route_count_3': len(after['route']) == 3,
        'trip_outer_block': all(x['card']['display']=='block' for x in after['trip']),
        'trip_inner_grid': all(x['inner']['display']=='grid' and len(x['inner']['grid'].split())==2 for x in after['trip']),
        'trip_copy_wide': all(x['copy']['width'] >= 380 for x in after['trip']),
        'trip_heading_wide': all(x['heading']['width'] >= 380 for x in after['trip']),
        'trip_cards_short': all(x['card']['height'] <= 260 for x in after['trip']),
        'route_outer_block': all(x['card']['display']=='block' for x in after['route']),
        'route_inner_grid': all(x['inner']['display']=='grid' and len(x['inner']['grid'].split())==3 for x in after['route']),
        'route_copy_wide': all(x['copy']['width'] >= 850 for x in after['route']),
        'route_heading_wide': all(x['heading']['width'] >= 850 for x in after['route']),
        'route_cards_short': all(x['card']['height'] <= 190 for x in after['route']),
        'no_horizontal_overflow': after['scrollWidth'] == after['clientWidth'],
    }
    result={'source_checks':source_checks,'checks':checks,'candidate_css':CANDIDATE_CSS,'before':before,'after':after}
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'source_checks':source_checks,'checks':checks,'before':before,'after':after},ensure_ascii=False))
    if not all(checks.values()):
        raise RuntimeError('INNER_GRID_V2_FAILED '+json.dumps(checks,ensure_ascii=False))

if __name__=='__main__':
    main()
