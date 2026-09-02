#!/usr/bin/env python3
import base64,json,os,pathlib,re,time,urllib.request
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

BASE='https://tsurikue.com/wp-json/wp/v2'
PAGE_ID=3350
MARKER='tsurikue-category-hub:v3:car-current-improved'
ROOT=pathlib.Path.cwd()
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode()

def get_json(url,auth=False):
    headers={'User-Agent':'tsurikue-car-current-v3-render/1.0'}
    if auth: headers['Authorization']=AUTH
    req=urllib.request.Request(url,headers=headers)
    with urllib.request.urlopen(req,timeout=45) as r:return json.load(r)

p=get_json(f'{BASE}/pages/{PAGE_ID}?context=edit&_fields=id,slug,status,content',True)
if p['slug']!='car-guide-v2-preview' or p['status']!='draft': raise RuntimeError('DRAFT_IDENTITY_FAILED')
rendered=p['content']['rendered']
if MARKER not in rendered: raise RuntimeError('MARKER_NOT_RENDERED')
if 'p-postList' not in rendered: raise RuntimeError('SWELL_POST_LIST_NOT_RENDERED')
if 'ランドクルーザーFJ' in rendered: raise RuntimeError('FJ_COPY_RENDERED')

home=urllib.request.urlopen(urllib.request.Request('https://tsurikue.com/',headers={'User-Agent':'Mozilla/5.0'}),timeout=45).read().decode('utf-8','ignore')
styles='\n'.join(re.findall(r'<link[^>]+rel=["\'][^"\']*stylesheet[^"\']*["\'][^>]+>',home,re.I))
html='<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'+styles+'<style>body{margin:0;background:#fff;font-family:"Noto Sans CJK JP",sans-serif}</style></head><body class="page page-template-default"><main>'+rendered+'</main></body></html>'
path=ROOT/'car-current-v3-rendered.html';path.write_text(html,encoding='utf-8')

opts=Options();opts.add_argument('--headless=new');opts.add_argument('--no-sandbox');opts.add_argument('--disable-dev-shm-usage');opts.add_argument('--force-device-scale-factor=1')
d=webdriver.Chrome(options=opts)
checks={};metrics={}
try:
    for label,w,h in [('desktop',1440,1200),('mobile',390,1000)]:
        d.set_window_size(w,h);d.get(path.resolve().as_uri());time.sleep(.8)
        hero=d.find_element('css selector','.tq-hero')
        h1=d.find_element('css selector','.tq-hero h1')
        picks=d.find_elements('css selector','.tq-pick')
        stats=d.find_elements('css selector','.tq-stat')
        details=d.find_elements('css selector','.tq-accordion')
        latest=d.find_element('css selector','.p-postList')
        sw=d.execute_script('return document.documentElement.scrollWidth');cw=d.execute_script('return document.documentElement.clientWidth')
        pick_rects=[x.rect for x in picks]
        metrics[label]={
            'scroll_width':sw,'client_width':cw,'hero_height':round(hero.rect['height'],1),
            'h1_font':float(h1.value_of_css_property('font-size').replace('px','')),
            'picks':len(picks),'stats':len(stats),'details':len(details),'latest_width':round(latest.rect['width'],1),
            'pick_rects':[{'x':round(r['x'],1),'y':round(r['y'],1),'w':round(r['width'],1),'h':round(r['height'],1)} for r in pick_rects],
        }
        checks[label+'_hero_copy']='クルマで、' in h1.text and 'どこまで行こう。' in h1.text
        checks[label+'_four_picks']=len(picks)==4
        checks[label+'_four_stats']=len(stats)==4
        checks[label+'_four_accordions']=len(details)==4
        checks[label+'_known_links']=all(bool(d.find_elements('css selector',f'a[href="{href}"]')) for href in [
            'https://tsurikue.com/lexus-ux-review/','https://tsurikue.com/ux-koukai/','https://tsurikue.com/lexus-ux-used/','https://tsurikue.com/ux-resale/'
        ])
        checks[label+'_no_fj']='ランドクルーザーFJ' not in d.find_element('tag name','body').text
        checks[label+'_latest']=latest.rect['width']>200
        checks[label+'_no_overflow']=sw<=cw+10
        if label=='desktop':
            checks['desktop_two_column_picks']=abs(pick_rects[0]['y']-pick_rects[1]['y'])<3 and abs(pick_rects[0]['width']-pick_rects[1]['width'])<5
            checks['desktop_h1_size']=50<=metrics[label]['h1_font']<=70
        else:
            checks['mobile_one_column_picks']=pick_rects[1]['y']>pick_rects[0]['y']+pick_rects[0]['height']-3 and pick_rects[0]['width']>330
            checks['mobile_h1_size']=38<=metrics[label]['h1_font']<=40
        d.save_screenshot(str(ROOT/f'car-current-v3-{label}-closed.png'))
        if label=='desktop':
            d.find_element('css selector','.tq-accordion summary').click();time.sleep(.35)
            checks['desktop_open_list_visible']=d.find_element('css selector','.tq-link-list').rect['height']>100
            d.save_screenshot(str(ROOT/'car-current-v3-desktop-open.png'))
finally:
    d.quit()

if not all(checks.values()): raise RuntimeError('RENDER_CHECK_FAILED '+json.dumps({'checks':checks,'metrics':metrics},ensure_ascii=False))
out={'page_id':PAGE_ID,'status':'draft','checks':checks,'metrics':metrics}
(ROOT/'car-current-v3-render-check.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False))
