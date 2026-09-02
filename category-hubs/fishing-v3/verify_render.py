#!/usr/bin/env python3
import base64, json, os, pathlib, re, urllib.request, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
BASE='https://tsurikue.com/wp-json/wp/v2'
PAGE_ID=3316
ROOT=pathlib.Path.cwd()
USER=os.environ['TSURIKUE_WP_USER']
APP=os.environ['TSURIKUE_WP_APP_PASSWORD']
AUTH='Basic '+base64.b64encode(f'{USER}:{APP}'.encode()).decode()

def get_json(url, timeout=45):
    req=urllib.request.Request(url,headers={'Authorization':AUTH,'User-Agent':'tsurikue-fishing-render/1.0'})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return json.load(r)

p=get_json(f'{BASE}/pages/{PAGE_ID}?context=edit&_fields=id,slug,status,title,content,link')
if p['slug']!='fishing-guide' or p['status']!='draft':
    raise RuntimeError('DRAFT_IDENTITY_FAILED')
rendered=p['content']['rendered']
if 'p-postList' not in rendered:
    raise RuntimeError('SWELL_POST_LIST_NOT_RENDERED')

home=urllib.request.urlopen(urllib.request.Request('https://tsurikue.com/',headers={'User-Agent':'Mozilla/5.0'}),timeout=45).read().decode('utf-8','ignore')
styles=re.findall(r'<link[^>]+rel=["\'][^"\']*stylesheet[^"\']*["\'][^>]+>',home,re.I)
head='\n'.join(styles)
html='<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'+head+'<style>body{margin:0;background:#fff}.tq-test-shell{max-width:none;margin:0 auto}</style></head><body class="page page-template-default"><main class="tq-test-shell">'+rendered+'</main></body></html>'
path=ROOT/'fishing-hub-v3-rendered.html'
path.write_text(html,encoding='utf-8')

opts=Options()
opts.add_argument('--headless=new'); opts.add_argument('--no-sandbox'); opts.add_argument('--disable-dev-shm-usage'); opts.add_argument('--force-device-scale-factor=1')
d=webdriver.Chrome(options=opts)
checks={}; metrics={}
try:
    for label,w,h in [('desktop',1440,1200),('mobile',390,1000)]:
        d.set_window_size(w,h); d.get(path.as_uri()); time.sleep(2)
        sw=d.execute_script('return document.documentElement.scrollWidth')
        cw=d.execute_script('return document.documentElement.clientWidth')
        hero=d.find_element('css selector','.tq-fishing-hero')
        cards=d.find_elements('css selector','.tq-fishing-card')
        postlist=d.find_element('css selector','.p-postList')
        grid_cols=d.execute_script("return getComputedStyle(document.querySelector('.tq-fishing-grid')).gridTemplateColumns")
        metrics[label]={'scroll_width':sw,'client_width':cw,'hero_height':round(hero.rect['height'],1),'card_count':len(cards),'post_list_width':round(postlist.rect['width'],1),'first_grid_columns':grid_cols}
        checks[label+'_no_horizontal_overflow']=sw<=cw+10
        checks[label+'_hero_visible']=hero.rect['height']>350
        checks[label+'_cards_visible']=len(cards)>=9
        checks[label+'_swell_post_list_visible']=postlist.rect['width']>200
        h1=d.find_element('css selector','.tq-fishing-hero h1')
        h2=d.find_element('css selector','.tq-fishing-section-title')
        h3=d.find_element('css selector','.tq-fishing-card h3')
        checks[label+'_hero_title_visible']=h1.rect['height']>35 and h1.value_of_css_property('visibility')=='visible' and float(h1.value_of_css_property('opacity'))>0
        checks[label+'_section_title_visible']=h2.rect['height']>25 and h2.value_of_css_property('visibility')=='visible' and float(h2.value_of_css_property('opacity'))>0
        checks[label+'_card_title_visible']=h3.rect['height']>18 and h3.value_of_css_property('visibility')=='visible' and float(h3.value_of_css_property('opacity'))>0
        metrics[label]['text']={
            'h1':{'height':round(h1.rect['height'],1),'color':h1.value_of_css_property('color')},
            'h2':{'height':round(h2.rect['height'],1),'color':h2.value_of_css_property('color')},
            'h3':{'height':round(h3.rect['height'],1),'color':h3.value_of_css_property('color')}
        }
        if label=='mobile': checks['mobile_single_column']=len(grid_cols.split())==1
        else: checks['desktop_three_columns']=len(grid_cols.split())>=3
        d.save_screenshot(str(ROOT/f'fishing-hub-v3-{label}.png'))
finally:
    d.quit()
if not all(checks.values()): raise RuntimeError('RENDER_CHECK_FAILED '+json.dumps({'checks':checks,'metrics':metrics},ensure_ascii=False))
out={'page_id':PAGE_ID,'status':'draft','checks':checks,'metrics':metrics}
(ROOT/'fishing-hub-v3-render-check.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False))
