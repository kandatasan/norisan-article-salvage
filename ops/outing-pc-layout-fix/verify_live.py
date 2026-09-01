from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.parse import urlencode

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from apply import (
    CARD_FIX_END,
    CARD_FIX_START,
    NEW_FIX_END,
    NEW_FIX_START,
    PAGE_ID,
    SLUG,
    STATUS,
    TITLE,
    block_counts,
    get_page,
    raw,
)

PUBLIC_URL = 'https://tsurikue.com/odekake/'
OUT = Path('outing-pc-layout-live-verify.json')
DESKTOP_SHOT = Path('outing-pc-layout-live-desktop-1440.png')
MOBILE_SHOT = Path('outing-pc-layout-live-mobile-390.png')

MEASURE_JS = r'''
const selectors = [
  '.post_content',
  '.tq-out',
  '.tq-out-hero',
  '.tq-out-hero > .wp-block-cover__inner-container',
  '.tq-out-hero-inner',
  '.tq-out-choose-grid',
  '.tq-out-local-grid',
  '.tq-out-trip-grid',
  '.tq-out-route-list',
  '.tq-out-latest',
  '.tq-out-final'
];
const out = {};
for (const sel of selectors) {
  const el = document.querySelector(sel);
  if (!el) { out[sel] = null; continue; }
  const r = el.getBoundingClientRect();
  const cs = getComputedStyle(el);
  out[sel] = {
    left: Math.round(r.left * 100) / 100,
    right: Math.round(r.right * 100) / 100,
    width: Math.round(r.width * 100) / 100,
    height: Math.round(r.height * 100) / 100,
    paddingLeft: cs.paddingLeft,
    paddingRight: cs.paddingRight,
    marginLeft: cs.marginLeft,
    marginRight: cs.marginRight,
    leftCss: cs.left,
    rightCss: cs.right,
    maxWidth: cs.maxWidth,
    display: cs.display,
    gridTemplateColumns: cs.gridTemplateColumns,
  };
}
const client = document.documentElement.clientWidth;
const overflow = [];
for (const el of document.querySelectorAll('body *')) {
  const r = el.getBoundingClientRect();
  if (r.width > 0 && (r.left < -2 || r.right > client + 2)) {
    const cs = getComputedStyle(el);
    if (cs.position === 'fixed') continue;
    overflow.push({
      tag: el.tagName,
      className: String(el.className || '').slice(0, 160),
      left: Math.round(r.left),
      right: Math.round(r.right),
      width: Math.round(r.width),
      display: cs.display,
    });
    if (overflow.length >= 30) break;
  }
}
return {
  url: location.href,
  viewport: {innerWidth, innerHeight, dpr: devicePixelRatio},
  document: {
    clientWidth: client,
    scrollWidth: document.documentElement.scrollWidth,
    bodyScrollWidth: document.body.scrollWidth,
    scrollHeight: document.documentElement.scrollHeight,
  },
  selectors: out,
  overflowElements: overflow,
};
'''


def make_driver(width: int, height: int) -> webdriver.Chrome:
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument(f'--window-size={width},{height}')
    options.add_argument('--force-device-scale-factor=1')
    driver = webdriver.Chrome(options=options)
    driver.set_window_size(width, height)
    return driver


def load_and_measure(driver: webdriver.Chrome, label: str) -> dict:
    url = PUBLIC_URL + '?' + urlencode({'layout_verify': f'{int(time.time())}-{label}'})
    driver.get(url)
    time.sleep(3)
    return driver.execute_script(MEASURE_JS)


def save_full_screenshot(driver: webdriver.Chrome, path: Path, width: int, max_height: int = 12000) -> None:
    height = min(int(driver.execute_script('return document.documentElement.scrollHeight')), max_height)
    driver.set_window_size(width, max(900, height))
    time.sleep(0.4)
    driver.save_screenshot(str(path))


def count_columns(value: str) -> int:
    if not value or value == 'none':
        return 0
    return len(value.split())


def main() -> None:
    page, _ = get_page()
    content = raw(page, 'content')
    counts = block_counts(content)
    content_checks = {
        'id': page.get('id') == PAGE_ID,
        'slug': page.get('slug') == SLUG,
        'status_publish': page.get('status') == STATUS,
        'title': raw(page, 'title') == TITLE,
        'custom_html_two': counts.get('html', 0) == 2,
        'group_blocks_unchanged': counts.get('group', 0) == 51,
        'old_pc_card_fix_preserved': content.count(CARD_FIX_START) == 1 and content.count(CARD_FIX_END) == 1,
        'new_shell_fix_once': content.count(NEW_FIX_START) == 1 and content.count(NEW_FIX_END) == 1,
        'desktop_only_media_scope': '@media(min-width:861px)' in content,
    }
    if not all(content_checks.values()):
        raise RuntimeError('LIVE_CONTENT_CHECK_FAILED ' + json.dumps(content_checks, ensure_ascii=False))

    desktop_driver = make_driver(1440, 1200)
    try:
        desktop = load_and_measure(desktop_driver, 'desktop')
        client = desktop['document']['clientWidth']
        root = desktop['selectors']['.tq-out']
        hero = desktop['selectors']['.tq-out-hero']
        hero_inner = desktop['selectors']['.tq-out-hero-inner']
        post = desktop['selectors']['.post_content']
        desktop_checks = {
            'post_padding_zero': post['paddingLeft'] == '0px' and post['paddingRight'] == '0px',
            'root_full_width': abs(root['left']) <= 1 and abs(root['right'] - client) <= 1,
            'hero_full_width': abs(hero['left']) <= 1 and abs(hero['right'] - client) <= 1,
            'hero_inner_centered': abs((hero_inner['left'] + hero_inner['right']) / 2 - client / 2) <= 2,
            'hero_inner_1160': 1158 <= hero_inner['width'] <= 1161,
            'choose_grid_4_columns': count_columns(desktop['selectors']['.tq-out-choose-grid']['gridTemplateColumns']) == 4,
            'local_grid_3_columns': count_columns(desktop['selectors']['.tq-out-local-grid']['gridTemplateColumns']) == 3,
            'trip_grid_2_columns': count_columns(desktop['selectors']['.tq-out-trip-grid']['gridTemplateColumns']) == 2,
            'no_horizontal_overflow': desktop['document']['scrollWidth'] == client and not desktop['overflowElements'],
        }
        save_full_screenshot(desktop_driver, DESKTOP_SHOT, 1440)
    finally:
        desktop_driver.quit()

    mobile_driver = make_driver(390, 844)
    try:
        mobile = load_and_measure(mobile_driver, 'mobile')
        mobile_client = mobile['document']['clientWidth']
        mobile_root = mobile['selectors']['.tq-out']
        mobile_hero = mobile['selectors']['.tq-out-hero']
        mobile_checks = {
            'root_present': mobile_root is not None and mobile_root['width'] > 0,
            'hero_present': mobile_hero is not None and mobile_hero['width'] > 0,
            'no_horizontal_overflow': mobile['document']['scrollWidth'] == mobile_client,
            'no_large_left_escape': mobile_root['left'] >= -2 and mobile_hero['left'] >= -2,
            'no_large_right_escape': mobile_root['right'] <= mobile_client + 2 and mobile_hero['right'] <= mobile_client + 2,
        }
        save_full_screenshot(mobile_driver, MOBILE_SHOT, 390)
    finally:
        mobile_driver.quit()

    all_checks = {
        'content': content_checks,
        'desktop': desktop_checks,
        'mobile': mobile_checks,
    }
    if not all(all(group.values()) for group in all_checks.values()):
        raise RuntimeError('LIVE_LAYOUT_VERIFY_FAILED ' + json.dumps(all_checks, ensure_ascii=False))

    result = {
        'post_id': PAGE_ID,
        'slug': SLUG,
        'status': page.get('status'),
        'checks': all_checks,
        'desktop': desktop,
        'mobile': mobile,
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({
        'post_id': PAGE_ID,
        'slug': SLUG,
        'status': page.get('status'),
        'checks': all_checks,
        'desktop_summary': {
            'client_width': desktop['document']['clientWidth'],
            'root': desktop['selectors']['.tq-out'],
            'hero': desktop['selectors']['.tq-out-hero'],
            'hero_inner': desktop['selectors']['.tq-out-hero-inner'],
        },
        'mobile_summary': {
            'client_width': mobile['document']['clientWidth'],
            'scroll_width': mobile['document']['scrollWidth'],
        },
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
