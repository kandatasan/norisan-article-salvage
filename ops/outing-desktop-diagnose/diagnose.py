from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.request
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

PAGE_ID = 3154
BASE = 'https://tsurikue.com/wp-json/wp/v2'
PUBLIC_URL = 'https://tsurikue.com/odekake/?layout_diag=20260901'
OUT = Path('outing-desktop-diagnostic.json')
SHOT = Path('outing-desktop-1440.png')
PROPOSAL_SHOT = Path('outing-desktop-proposal-1440.png')
LIVE_CONTENT = Path('outing-live-content.html')

FIX_CSS = r'''
/* TQ OUTING PC SHELL ALIGN FIX v1 */
body:has(.tq-out) .post_content{padding-left:0!important;padding-right:0!important}
.tq-out.wp-block-group{width:100%!important;max-width:none!important;margin-left:0!important;margin-right:0!important}
.tq-out>.alignfull,
.tq-out .tq-out-section,
.tq-out .tq-out-latest,
.tq-out .tq-out-final{left:auto!important;right:auto!important;width:100%!important;max-width:none!important;margin-left:0!important;margin-right:0!important}
.tq-out .tq-out-hero{padding-left:0!important;padding-right:0!important}
.tq-out .tq-out-hero>.wp-block-cover__inner-container{width:100%!important;max-width:none!important}
.tq-out .tq-out-hero-inner{width:min(1160px,calc(100% - 32px))!important;max-width:none!important;margin-left:auto!important;margin-right:auto!important}
'''

MEASURE_JS = r'''
const selectors = [
  '.tq-out',
  '.tq-out-hero',
  '.tq-out-hero > .wp-block-cover__inner-container',
  '.tq-out-hero-inner',
  '.tq-out-wrap',
  '.tq-out-head',
  '.tq-out-choose-grid',
  '.tq-out-local-grid',
  '.tq-out-trip-grid',
  '.tq-out-route-list',
  '.tq-out-latest',
  '.tq-out-latest-list',
  '.tq-out-final',
  '.tq-out-final-inner',
  '.l-content',
  '.l-mainContent',
  '.post_content'
];
const info = {};
for (const sel of selectors) {
  const el = document.querySelector(sel);
  if (!el) { info[sel] = null; continue; }
  const r = el.getBoundingClientRect();
  const cs = getComputedStyle(el);
  info[sel] = {
    tag: el.tagName,
    className: el.className,
    left: Math.round(r.left*100)/100,
    right: Math.round(r.right*100)/100,
    top: Math.round(r.top*100)/100,
    width: Math.round(r.width*100)/100,
    height: Math.round(r.height*100)/100,
    display: cs.display,
    position: cs.position,
    leftCss: cs.left,
    rightCss: cs.right,
    maxWidth: cs.maxWidth,
    widthCss: cs.width,
    marginLeft: cs.marginLeft,
    marginRight: cs.marginRight,
    paddingLeft: cs.paddingLeft,
    paddingRight: cs.paddingRight,
    gridTemplateColumns: cs.gridTemplateColumns,
    gap: cs.gap,
    overflowX: cs.overflowX,
  };
}
const over = [];
for (const el of document.querySelectorAll('body *')) {
  const r = el.getBoundingClientRect();
  if (r.width > 0 && (r.left < -2 || r.right > document.documentElement.clientWidth + 2)) {
    const cs = getComputedStyle(el);
    if (cs.position === 'fixed') continue;
    over.push({
      tag: el.tagName,
      className: String(el.className || '').slice(0,180),
      left: Math.round(r.left), right: Math.round(r.right), width: Math.round(r.width),
      display: cs.display,
    });
    if (over.length >= 50) break;
  }
}
const children = {};
for (const sel of ['.tq-out-choose-grid','.tq-out-local-grid','.tq-out-trip-grid','.tq-out-route-list']) {
  const el = document.querySelector(sel);
  children[sel] = el ? [...el.children].slice(0,8).map(ch => {
    const r=ch.getBoundingClientRect(); const cs=getComputedStyle(ch);
    return {tag:ch.tagName,className:String(ch.className||''),left:Math.round(r.left),right:Math.round(r.right),width:Math.round(r.width),display:cs.display};
  }) : [];
}
return {
  href: location.href,
  title: document.title,
  viewport: {innerWidth, innerHeight, dpr: devicePixelRatio},
  document: {
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
    bodyScrollWidth: document.body.scrollWidth,
    scrollHeight: document.documentElement.scrollHeight,
  },
  selectors: info,
  children,
  overflowElements: over,
};
'''


def wp_get_page() -> dict:
    user = os.environ['TSURIKUE_WP_USER']
    password = os.environ['TSURIKUE_WP_APP_PASSWORD']
    import base64
    token = base64.b64encode(f'{user}:{password}'.encode()).decode()
    url = f'{BASE}/pages/{PAGE_ID}?context=edit&_fields=id,slug,status,title,content,link,modified,featured_media'
    req = urllib.request.Request(url, headers={
        'Authorization': f'Basic {token}',
        'Accept': 'application/json',
        'User-Agent': 'tsurikue-outing-layout-diagnostic/1.2',
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def raw(obj: dict, key: str) -> str:
    value = obj.get(key)
    if isinstance(value, dict):
        return value.get('raw') or value.get('rendered') or ''
    return str(value or '')


def screenshot(driver, path: Path) -> None:
    full_h = min(int(driver.execute_script('return document.documentElement.scrollHeight')), 12000)
    driver.set_window_size(1440, max(1200, full_h))
    time.sleep(0.4)
    driver.save_screenshot(str(path))
    driver.set_window_size(1440, 1200)


def main() -> None:
    page = wp_get_page()
    content = raw(page, 'content')
    LIVE_CONTENT.write_text(content, encoding='utf-8')
    content_sha256 = hashlib.sha256(content.encode('utf-8')).hexdigest()

    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1440,1200')
    options.add_argument('--force-device-scale-factor=1')
    driver = webdriver.Chrome(options=options)
    try:
        driver.set_window_size(1440, 1200)
        driver.get(PUBLIC_URL)
        time.sleep(3)

        before = driver.execute_script(MEASURE_JS)
        screenshot(driver, SHOT)

        driver.execute_script(
            "const s=document.createElement('style');s.id='tq-outing-pc-shell-align-proposal';s.textContent=arguments[0];document.head.appendChild(s);",
            FIX_CSS,
        )
        time.sleep(0.5)
        after = driver.execute_script(MEASURE_JS)
        screenshot(driver, PROPOSAL_SHOT)

        client = after['document']['clientWidth']
        root = after['selectors']['.tq-out']
        hero = after['selectors']['.tq-out-hero']
        hero_inner = after['selectors']['.tq-out-hero-inner']
        post = after['selectors']['.post_content']
        checks = {
            'post_padding_zero': post['paddingLeft'] == '0px' and post['paddingRight'] == '0px',
            'root_full_width': abs(root['left']) <= 1 and abs(root['right'] - client) <= 1,
            'hero_full_width': abs(hero['left']) <= 1 and abs(hero['right'] - client) <= 1,
            'hero_inner_centered': abs((hero_inner['left'] + hero_inner['right']) / 2 - client / 2) <= 2,
            'hero_inner_expected_width': 1120 <= hero_inner['width'] <= 1161,
            'choice_grid_still_4_columns': len(after['selectors']['.tq-out-choose-grid']['gridTemplateColumns'].split()) == 4,
            'local_grid_still_3_columns': len(after['selectors']['.tq-out-local-grid']['gridTemplateColumns'].split()) == 3,
            'trip_grid_still_2_columns': len(after['selectors']['.tq-out-trip-grid']['gridTemplateColumns'].split()) == 2,
            'no_document_horizontal_overflow': after['document']['scrollWidth'] == client,
        }
        if not all(checks.values()):
            raise RuntimeError('PROPOSAL_LAYOUT_CHECK_FAILED ' + json.dumps(checks, ensure_ascii=False))

        result = {
            'wordpress': {
                'id': page.get('id'),
                'slug': page.get('slug'),
                'status': page.get('status'),
                'title': raw(page, 'title'),
                'link': page.get('link'),
                'modified': page.get('modified'),
                'featured_media': page.get('featured_media'),
                'content_bytes': len(content.encode('utf-8')),
                'content_sha256': content_sha256,
                'has_v1_marker': '<!-- tsurikue-category-hub:v1:outing -->' in content,
                'has_v2_marker': '<!-- tsurikue-category-hub:v2:outing-blocks -->' in content,
                'custom_html_blocks': content.count('<!-- wp:html -->'),
                'group_blocks': content.count('<!-- wp:group'),
                'pc_card_fix_marker': 'tq-outing-pc-card-width-fix:v1' in content,
            },
            'proposal_css': FIX_CSS,
            'proposal_checks': checks,
            'layout_1440_before': before,
            'layout_1440_after_runtime_fix': after,
        }
        OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        driver.quit()


if __name__ == '__main__':
    main()
