from __future__ import annotations

import json
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from diagnose import FIX_CSS, MEASURE_JS, PUBLIC_URL, raw, wp_get_page

EXTRA_CSS = r'''
/* TQ OUTING PC SHELL ALIGN FIX v3 root + hero correction */
.tq-out.wp-block-group{left:auto!important;right:auto!important}
.tq-out .tq-out-hero{left:0!important;right:auto!important;width:100%!important;max-width:none!important;margin-left:0!important;margin-right:0!important;padding-left:0!important;padding-right:0!important}
'''
OUT = Path('outing-desktop-proposal-v2.json')
SHOT = Path('outing-desktop-proposal-v2-1440.png')


def main() -> None:
    page = wp_get_page()
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
        driver.execute_script(
            "const s=document.createElement('style');s.id='tq-outing-pc-shell-align-proposal-v3';s.textContent=arguments[0];document.head.appendChild(s);",
            FIX_CSS + EXTRA_CSS,
        )
        time.sleep(0.5)
        after = driver.execute_script(MEASURE_JS)

        full_h = min(int(driver.execute_script('return document.documentElement.scrollHeight')), 12000)
        driver.set_window_size(1440, max(1200, full_h))
        time.sleep(0.4)
        driver.save_screenshot(str(SHOT))

        client = after['document']['clientWidth']
        root = after['selectors']['.tq-out']
        hero = after['selectors']['.tq-out-hero']
        hero_inner = after['selectors']['.tq-out-hero-inner']
        post = after['selectors']['.post_content']
        checks = {
            'identity_publish': page.get('id') == 3154 and page.get('slug') == 'odekake' and page.get('status') == 'publish',
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
        result = {
            'checks': checks,
            'page': {'id': page.get('id'), 'slug': page.get('slug'), 'status': page.get('status'), 'title': raw(page, 'title')},
            'before_selected': {k: before['selectors'][k] for k in ['.post_content','.tq-out','.tq-out-hero','.tq-out-hero > .wp-block-cover__inner-container','.tq-out-hero-inner']},
            'after_selected': {k: after['selectors'][k] for k in ['.post_content','.tq-out','.tq-out-hero','.tq-out-hero > .wp-block-cover__inner-container','.tq-out-hero-inner','.tq-out-choose-grid','.tq-out-local-grid','.tq-out-trip-grid']},
            'client_width': client,
            'overflow_after': after['overflowElements'],
            'css': FIX_CSS + EXTRA_CSS,
        }
        OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not all(checks.values()):
            raise RuntimeError('PROPOSAL_V3_FAILED ' + json.dumps(checks, ensure_ascii=False))
    finally:
        driver.quit()


if __name__ == '__main__':
    main()
