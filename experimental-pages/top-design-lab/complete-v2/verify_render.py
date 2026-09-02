#!/usr/bin/env python3
import json
import pathlib
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

ROOT=pathlib.Path.cwd()
URL='https://tsurikue.com/'
TARGETS=['/odekake/','/gourmet-guide/','/fishing-guide/','/car-guide/']
CARD_CLASSES=['.tq4-cat--outing','.tq4-cat--gourmet','.tq4-cat--fishing','.tq4-cat--car']

opts=Options(); opts.add_argument('--headless=new'); opts.add_argument('--no-sandbox'); opts.add_argument('--disable-dev-shm-usage'); opts.add_argument('--force-device-scale-factor=1')
d=webdriver.Chrome(options=opts)
checks={}; metrics={}
try:
    for label,w,h in [('desktop',1440,1200),('mobile',390,1000)]:
        d.set_window_size(w,h)
        ready=False
        for attempt in range(6):
            d.get(URL+f'?tq_home_complete_v2={int(time.time())}-{label}-{attempt}')
            time.sleep(1.3+attempt*.3)
            if d.find_elements('css selector','.tq4') and d.find_elements('css selector','.tq4-cat'):
                ready=True; break
        checks[label+'_loaded']=ready
        if not ready: continue
        root=d.find_element('css selector','.tq4')
        h1=d.find_element('css selector','.tq4 .tq4-hero h1')
        cards=[d.find_element('css selector',x) for x in CARD_CLASSES]
        links=[c.find_element('css selector','h3 a') for c in cards]
        scroll=d.execute_script('return document.documentElement.scrollWidth')
        client=d.execute_script('return document.documentElement.clientWidth')
        hrefs=[a.get_attribute('href') for a in links]
        hit=[]; pseudo=[]
        for c,a,target in zip(cards,links,TARGETS):
            info=d.execute_script('''
                const card=arguments[0], link=arguments[1];
                const r=card.getBoundingClientRect();
                const pts=[[.08,.10],[.50,.50],[.92,.88]];
                const hits=pts.map(([px,py])=>{
                  const el=document.elementFromPoint(r.left+r.width*px,r.top+r.height*py);
                  const anchor=el && el.closest ? el.closest('a') : null;
                  return !!anchor && anchor===link;
                });
                const ps=getComputedStyle(link,'::after');
                return {hits:hits,pseudoWidth:parseFloat(ps.width)||0,pseudoHeight:parseFloat(ps.height)||0,cardWidth:r.width,cardHeight:r.height,content:ps.content,position:ps.position};
            ''',c,a)
            hit.append(all(info['hits']))
            pseudo.append(info)
        rects=[c.rect for c in cards]
        metrics[label]={
            'scroll_width':scroll,'client_width':client,'h1_font':float(h1.value_of_css_property('font-size').replace('px','')),
            'card_rects':[{'x':round(r['x'],1),'y':round(r['y'],1),'w':round(r['width'],1),'h':round(r['height'],1)} for r in rects],
            'hrefs':hrefs,'full_card_hit':hit,'pseudo':pseudo,
        }
        checks[label+'_hero']='休日、' in h1.text and 'なにして遊ぶ？' in h1.text
        checks[label+'_four_cards']=len(cards)==4
        checks[label+'_hub_hrefs']=all(href.endswith(target) for href,target in zip(hrefs,TARGETS))
        checks[label+'_full_card_hit']=all(hit)
        checks[label+'_pseudo_covers_card']=all(p['position']=='absolute' and p['pseudoWidth']>=p['cardWidth']-3 and p['pseudoHeight']>=p['cardHeight']-3 for p in pseudo)
        checks[label+'_no_overflow']=scroll<=client+8
        if label=='desktop':
            checks['desktop_four_columns']=max(abs(rects[i]['y']-rects[0]['y']) for i in range(4))<4
        else:
            checks['mobile_two_columns']=abs(rects[0]['y']-rects[1]['y'])<4 and rects[2]['y']>rects[0]['y']+rects[0]['height']-4
        d.save_screenshot(str(ROOT/f'homepage-complete-v2-{label}.png'))
finally:
    d.quit()

result={'url':URL,'checks':checks,'metrics':metrics}
(ROOT/'homepage-complete-v2-render-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
if not checks or not all(checks.values()): raise RuntimeError('HOME_COMPLETE_V2_RENDER_FAILED '+json.dumps(result,ensure_ascii=False))
print(json.dumps(result,ensure_ascii=False))
