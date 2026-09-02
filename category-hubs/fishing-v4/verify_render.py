#!/usr/bin/env python3
import base64, json, os, pathlib, re, time, urllib.request
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

BASE='https://tsurikue.com/wp-json/wp/v2'
PAGE_ID=3316
ROOT=pathlib.Path.cwd()
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode()

def get_json(url, auth=False):
    headers={'User-Agent':'tsurikue-fishing-v4-render/1.0'}
    if auth: headers['Authorization']=AUTH
    req=urllib.request.Request(url,headers=headers)
    with urllib.request.urlopen(req,timeout=45) as r:return json.load(r)

p=get_json(f'{BASE}/pages/{PAGE_ID}?context=edit&_fields=id,slug,status,content',True)
if p['slug']!='fishing-guide' or p['status']!='draft': raise RuntimeError('DRAFT_IDENTITY_FAILED')
rendered=p['content']['rendered']
if 'tq-fishing-auto-index:v4' not in rendered or '<script>' not in rendered: raise RuntimeError('AUTO_INDEX_SCRIPT_NOT_RENDERED')
if 'p-postList' not in rendered: raise RuntimeError('SWELL_POST_LIST_NOT_RENDERED')

home=urllib.request.urlopen(urllib.request.Request('https://tsurikue.com/',headers={'User-Agent':'Mozilla/5.0'}),timeout=45).read().decode('utf-8','ignore')
styles='\n'.join(re.findall(r'<link[^>]+rel=["\'][^"\']*stylesheet[^"\']*["\'][^>]+>',home,re.I))
html='<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'+styles+'<style>body{margin:0;background:#fff;font-family:"Noto Sans CJK JP",sans-serif}</style></head><body class="page page-template-default"><main>'+rendered+'</main></body></html>'
path=ROOT/'fishing-v4-rendered.html'; path.write_text(html,encoding='utf-8')

opts=Options(); opts.add_argument('--headless=new'); opts.add_argument('--no-sandbox'); opts.add_argument('--disable-dev-shm-usage'); opts.add_argument('--force-device-scale-factor=1'); opts.add_argument('--disable-web-security')
d=webdriver.Chrome(options=opts)
checks={};metrics={}
try:
    for label,w,h in [('desktop',1440,1200),('mobile',390,1000)]:
        d.set_window_size(w,h); d.get(path.resolve().as_uri())
        WebDriverWait(d,12).until(lambda x: x.execute_script("return document.documentElement.dataset.tqFishingAuto || ''") in ('ready','fallback'))
        state=d.execute_script("return document.documentElement.dataset.tqFishingAuto")
        hero=d.find_element('css selector','.tq-hero')
        h1=d.find_element('css selector','.tq-hero h1')
        details=d.find_elements('css selector','.tq-accordion')
        latest=d.find_element('css selector','.p-postList')
        sw=d.execute_script('return document.documentElement.scrollWidth');cw=d.execute_script('return document.documentElement.clientWidth')
        count=lambda k:d.find_element('css selector',f'[data-count="{k}"]').text
        list_count=lambda k:len(d.find_elements('css selector',f'.tq-auto-{k} li'))
        metrics[label]={
            'auto_state':state,'scroll_width':sw,'client_width':cw,'hero_height':round(hero.rect['height'],1),
            'h1_font':float(h1.value_of_css_property('font-size').replace('px','')),
            'details':len(details),'latest_width':round(latest.rect['width'],1),
            'counts':{k:count(k) for k in ('howto','experiment','diary','wild')},
            'list_counts':{k:list_count(k) for k in ('howto','experiment','diary','wild')},
        }
        checks[label+'_auto_ready']=state=='ready'
        checks[label+'_hero_copy']=h1.text=='今日は、なに釣る？'
        checks[label+'_four_accordions']=len(details)==4
        checks[label+'_counts_match']=all(count(k)==str(list_count(k))+'記事' for k in ('howto','experiment','diary','wild'))
        checks[label+'_groups_nonempty']=all(list_count(k)>0 for k in ('howto','experiment','diary','wild'))
        checks[label+'_known_howto']=bool(d.find_elements('css selector','.tq-auto-howto a[href*="sabiki-beginner"]'))
        checks[label+'_known_experiment']=bool(d.find_elements('css selector','.tq-auto-experiment a[href*="gulpalivepowder"]'))
        checks[label+'_known_diary']=bool(d.find_elements('css selector','.tq-auto-diary a[href*="aoriika-nikki"]'))
        checks[label+'_wild_six_or_more']=list_count('wild')>=6
        checks[label+'_latest']=latest.rect['width']>200
        checks[label+'_no_overflow']=sw<=cw+10
        if label=='desktop': checks['desktop_h1_48']=47.5<=metrics[label]['h1_font']<=48.5
        else: checks['mobile_h1_34']=33.5<=metrics[label]['h1_font']<=34.5
        d.save_screenshot(str(ROOT/f'fishing-v4-{label}-closed.png'))
        if label=='desktop':
            d.find_element('css selector','.tq-accordion-howto summary').click();time.sleep(.4)
            checks['desktop_open_list_visible']=d.find_element('css selector','.tq-auto-howto').rect['height']>100
            d.save_screenshot(str(ROOT/'fishing-v4-desktop-open.png'))
finally:
    d.quit()
if not all(checks.values()): raise RuntimeError('RENDER_CHECK_FAILED '+json.dumps({'checks':checks,'metrics':metrics},ensure_ascii=False))
out={'page_id':PAGE_ID,'status':'draft','checks':checks,'metrics':metrics}
(ROOT/'fishing-v4-render-check.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False))