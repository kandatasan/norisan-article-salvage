#!/usr/bin/env python3
import json, pathlib, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

ROOT=pathlib.Path.cwd()
URL='https://tsurikue.com/odekake/'
EXPECTED_HERO='https://tsurikue.com/wp-content/uploads/2026/09/img_2419.jpg'
opts=Options()
opts.add_argument('--headless=new')
opts.add_argument('--no-sandbox')
opts.add_argument('--disable-dev-shm-usage')
opts.add_argument('--force-device-scale-factor=1')
d=webdriver.Chrome(options=opts)
checks={}; metrics={}
try:
    for label,w,h in [('desktop',1440,1200),('mobile',390,1000)]:
        d.set_window_size(w,h)
        ready=False
        for attempt in range(6):
            d.get(URL+f'?tq_outing_v6={int(time.time())}-{label}-{attempt}')
            time.sleep(1.3+attempt*.25)
            if d.find_elements('css selector','.tq-outing-v3 .tq-hero'):
                ready=True; break
        checks[label+'_loaded']=ready
        if not ready: continue
        root=d.find_element('css selector','.tq-outing-v3')
        hero=d.find_element('css selector','.tq-outing-v3 .tq-hero')
        hero_img=d.find_element('css selector','.tq-outing-v3 .tq-hero .wp-block-cover__image-background')
        h1=d.find_element('css selector','.tq-outing-v3 .tq-hero h1')
        intro=d.find_element('css selector','.tq-outing-v3 .tq-choose-intro')
        choose=d.find_element('css selector','.tq-outing-v3 .tq-choose')
        post=d.find_element('css selector','.post_content')
        inner=d.find_element('css selector','.l-mainContent__inner')
        client=d.execute_script('return document.documentElement.clientWidth')
        scroll=d.execute_script('return document.documentElement.scrollWidth')
        auto=d.execute_script('return document.documentElement.dataset.tqOutingAuto || ""')
        geo=d.execute_script('''
          const els=arguments;
          const p=(el)=>{const r=el.getBoundingClientRect(),s=getComputedStyle(el);return {top:r.top,bottom:r.bottom,left:r.left,right:r.right,width:r.width,height:r.height,marginTop:s.marginTop,marginBottom:s.marginBottom,paddingTop:s.paddingTop,paddingBottom:s.paddingBottom};};
          return {root:p(els[0]),hero:p(els[1]),intro:p(els[2]),choose:p(els[3]),post:p(els[4]),inner:p(els[5])};
        ''',root,hero,intro,choose,post,inner)
        lines=[x.strip() for x in h1.text.splitlines() if x.strip()]
        src=(hero_img.get_attribute('src') or '').split('?')[0]
        metrics[label]={
            'client_width':client,'scroll_width':scroll,'geo':geo,
            'inner_to_hero':round(float(geo['hero']['top'])-float(geo['inner']['top']),2),
            'hero_to_intro':round(float(geo['intro']['top'])-float(geo['hero']['bottom']),2),
            'post_margin_top':geo['post']['marginTop'],'hero_margin_bottom':geo['hero']['marginBottom'],'choose_padding_top':geo['choose']['paddingTop'],
            'h1_lines':lines,'hero_src':src,'auto_state':auto,
        }
        checks[label+'_dolphin']=src==EXPECTED_HERO
        checks[label+'_heading_two_lines']=lines==['今日は、','どこ行く？']
        checks[label+'_post_margin_zero']=float(str(geo['post']['marginTop']).replace('px',''))<=0.5
        checks[label+'_hero_margin_zero']=float(str(geo['hero']['marginBottom']).replace('px',''))<=0.5
        target=32 if label=='desktop' else 24
        checks[label+'_choose_padding']=abs(float(str(geo['choose']['paddingTop']).replace('px',''))-target)<=1
        checks[label+'_top_gap_compact']=metrics[label]['inner_to_hero'] <= (55 if label=='desktop' else 45)
        checks[label+'_hero_to_intro_compact']=metrics[label]['hero_to_intro'] <= (36 if label=='desktop' else 28)
        checks[label+'_no_overflow']=scroll<=client+8
        checks[label+'_five_accordions']=len(d.find_elements('css selector','.tq-outing-v3 .tq-accordion'))==5
        checks[label+'_auto_ready']=auto=='ready'
        if label=='mobile':
            checks['mobile_centered']=abs(float(geo['root']['left'])-(client-float(geo['root']['right'])))<=3
        d.save_screenshot(str(ROOT/f'outing-v6-{label}.png'))
finally:
    d.quit()
result={'url':URL,'checks':checks,'metrics':metrics}
(ROOT/'outing-v6-render.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
if not checks or not all(checks.values()): raise RuntimeError('OUTING_V6_RENDER_FAILED '+json.dumps(result,ensure_ascii=False))
print(json.dumps(result,ensure_ascii=False))
