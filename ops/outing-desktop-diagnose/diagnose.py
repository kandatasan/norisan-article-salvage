from __future__ import annotations

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


def wp_get_page() -> dict:
    user = os.environ['TSURIKUE_WP_USER']
    password = os.environ['TSURIKUE_WP_APP_PASSWORD']
    import base64
    token = base64.b64encode(f'{user}:{password}'.encode()).decode()
    url = f'{BASE}/pages/{PAGE_ID}?context=edit&_fields=id,slug,status,title,content,link,modified,featured_media'
    req = urllib.request.Request(url, headers={
        'Authorization': f'Basic {token}',
        'Accept': 'application/json',
        'User-Agent': 'tsurikue-outing-layout-diagnostic/1.0',
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def raw(obj: dict, key: str) -> str:
    value = obj.get(key)
    if isinstance(value, dict):
        return value.get('raw') or value.get('rendered') or ''
    return str(value or '')


def main() -> None:
    page = wp_get_page()
    content = raw(page, 'content')

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

        js = r'''
        const selectors = [
          '.tq-out',
          '.tq-out-hero',
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
          if (r.width > 0 && (r.left < -2 || r.right > innerWidth + 2)) {
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
        layout = driver.execute_script(js)

        # Capture a tall desktop screenshot for human inspection.
        full_h = min(int(driver.execute_script('return document.documentElement.scrollHeight')), 12000)
        driver.set_window_size(1440, max(1200, full_h))
        time.sleep(0.5)
        driver.save_screenshot(str(SHOT))

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
                'has_v1_marker': '<!-- tsurikue-category-hub:v1:outing -->' in content,
                'has_v2_marker': '<!-- tsurikue-category-hub:v2:outing-blocks -->' in content,
                'custom_html_blocks': content.count('<!-- wp:html -->'),
                'group_blocks': content.count('<!-- wp:group'),
            },
            'layout_1440': layout,
        }
        OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        driver.quit()


if __name__ == '__main__':
    main()
