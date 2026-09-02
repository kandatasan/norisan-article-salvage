#!/usr/bin/env python3
import json
import pathlib
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

ROOT = pathlib.Path.cwd()
URL = 'https://tsurikue.com/odekake/'
MARKER_CLASS = '.tq-outing-v3'

opts = Options()
opts.add_argument('--headless=new')
opts.add_argument('--no-sandbox')
opts.add_argument('--disable-dev-shm-usage')
opts.add_argument('--force-device-scale-factor=1')
driver = webdriver.Chrome(options=opts)
checks = {}
metrics = {}

try:
    for label, width, height in [('desktop', 1440, 1200), ('mobile', 390, 1000)]:
        driver.set_window_size(width, height)
        ready = False
        for attempt in range(5):
            driver.get(URL + f'?tq_outing_v3_audit={int(time.time())}-{label}-{attempt}')
            time.sleep(1.4 + attempt * .4)
            if driver.find_elements('css selector', MARKER_CLASS):
                ready = True
                break
        checks[label + '_v3_loaded'] = ready
        if not ready:
            continue

        hero = driver.find_element('css selector', '.tq-outing-v3 .tq-hero')
        h1 = driver.find_element('css selector', '.tq-outing-v3 .tq-hero h1')
        details = driver.find_elements('css selector', '.tq-outing-v3 .tq-accordion')
        purpose = driver.find_elements('css selector', '.tq-outing-v3 .tq-purpose-link-button')
        latest = driver.find_element('css selector', '.tq-outing-v3 .p-postList')
        far_list = driver.find_elements('css selector', '.tq-outing-v3 .tq-auto-far li')
        body_text = driver.find_element('tag name', 'body').text
        scroll_width = driver.execute_script('return document.documentElement.scrollWidth')
        client_width = driver.execute_script('return document.documentElement.clientWidth')
        auto_state = driver.execute_script('return document.documentElement.dataset.tqOutingAuto || ""')

        metrics[label] = {
            'scroll_width': scroll_width,
            'client_width': client_width,
            'hero_height': round(hero.rect['height'], 1),
            'h1_font': float(h1.value_of_css_property('font-size').replace('px', '')),
            'details': len(details),
            'purpose_links': len(purpose),
            'far_items': len(far_list),
            'latest_width': round(latest.rect['width'], 1),
            'auto_state': auto_state,
        }
        checks[label + '_hero_copy'] = h1.text.strip() == '今日は、どこ行く？'
        checks[label + '_five_accordions'] = len(details) == 5
        checks[label + '_far_label'] = 'ちょっと遠くへ' in body_text
        checks[label + '_far_has_posts'] = len(far_list) >= 1
        checks[label + '_four_purpose_links'] = len(purpose) == 4
        checks[label + '_latest'] = latest.rect['width'] > 200
        checks[label + '_no_overflow'] = scroll_width <= client_width + 10
        checks[label + '_auto_index_ready'] = auto_state == 'ready'
        if label == 'desktop':
            checks['desktop_h1_size'] = 45 <= metrics[label]['h1_font'] <= 55
        else:
            checks['mobile_h1_size'] = 32 <= metrics[label]['h1_font'] <= 36

        driver.save_screenshot(str(ROOT / f'outing-v3-{label}-closed.png'))
        if label == 'desktop':
            details[-1].find_element('css selector', 'summary').click()
            time.sleep(.35)
            open_height = driver.find_element('css selector', '.tq-outing-v3 .tq-auto-far').rect['height']
            checks['desktop_far_open_visible'] = open_height > 20
            driver.save_screenshot(str(ROOT / 'outing-v3-desktop-far-open.png'))
finally:
    driver.quit()

result = {'url': URL, 'checks': checks, 'metrics': metrics}
(ROOT / 'outing-v3-render-check.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
if not checks or not all(checks.values()):
    raise RuntimeError('OUTING_V3_RENDER_CHECK_FAILED ' + json.dumps(result, ensure_ascii=False))
print(json.dumps(result, ensure_ascii=False))
