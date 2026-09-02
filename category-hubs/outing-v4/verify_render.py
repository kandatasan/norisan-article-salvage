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
            d.get(URL+f'?tq_outing_v5={int(time.time())}-{label}-{attempt}')
            time.sleep(1.4+attempt*.3)
            if d.find_elements('css selector','.tq-outing-v3 .tq-hero'):
                ready=True; break
        checks[label+'_loaded']=ready
        if not ready: continue
        root=d.find_element('css selector','.tq-outing-v3')
        hero=d.find_element('css selector','.tq-outing-v3 .tq-hero')
        hero_img=d.find_element('css selector','.tq-outing-v3 .tq-hero .wp-block-cover__image-background')
        h1=d.find_element('css selector','.tq-outing-v3 .tq-hero h1')
        details=d.find_elements('css selector','.tq-outing-v3 .tq-accordion')
        purpose=d.find_elements('css selector','.tq-outing-v3 .tq-purpose-link-button')
        far=d.find_elements('css selector','.tq-outing-v3 .tq-auto-far li')
        client=d.execute_script('return document.documentElement.clientWidth')
        scroll=d.execute_script('return document.documentElement.scrollWidth')
        auto=d.execute_script('return document.documentElement.dataset.tqOutingAuto || ""')
        geo=d.execute_script('''
          const root=arguments[0], hero=arguments[1], parent=root.parentElement;
          const r=root.getBoundingClientRect(), h=hero.getBoundingClientRect(), p=parent.getBoundingClientRect();
          return {root:{left:r.left,right:r.right,width:r.width},hero:{left:h.left,right:h.right,width:h.width},parent:{left:p.left,right:p.right,width:p.width,cls:parent.className},rootClass:root.className};
        ''',root,hero)
        lines=[x.strip() for x in h1.text.splitlines() if x.strip()]
        src=hero_img.get_attribute('src') or ''
        object_position=hero_img.value_of_css_property('object-position')
        left_gutter=float(geo['root']['left']); right_gutter=float(client-geo['root']['right'])
        metrics[label]={'client_width':client,'scroll_width':scroll,'geometry':geo,'viewport_gutters':{'left':round(left_gutter,2),'right':round(right_gutter,2)},'hero_height':round(hero.rect['height'],2),'hero_src':src,'object_position':object_position,'h1_lines':lines,'h1_font':float(h1.value_of_css_property('font-size').replace('px','')),'details':len(details),'purpose_links':len(purpose),'far_items':len(far),'auto_state':auto}
        checks[label+'_dolphin_hero']=src.split('?')[0]==EXPECTED_HERO
        checks[label+'_heading_two_lines']=lines==['今日は、','どこ行く？']
        checks[label+'_no_alignfull_class']='alignfull' not in str(geo['rootClass']).split()
        checks[label+'_root_matches_parent']=abs(float(geo['root']['left'])-float(geo['parent']['left']))<=2 and abs(float(geo['root']['right'])-float(geo['parent']['right']))<=2 and abs(float(geo['root']['width'])-float(geo['parent']['width']))<=3
        checks[label+'_hero_matches_root']=abs(float(geo['hero']['left'])-float(geo['root']['left']))<=2 and abs(float(geo['hero']['width'])-float(geo['root']['width']))<=3
        checks[label+'_focal_point']=object_position.replace(' ','')=='58%45%'
        checks[label+'_five_accordions']=len(details)==5
        checks[label+'_four_purpose_links']=len(purpose)==4
        checks[label+'_far_has_posts']=len(far)>=1
        checks[label+'_auto_ready']=auto=='ready'
        checks[label+'_no_overflow']=scroll<=client+8
        if label=='desktop': checks['desktop_h1_size']=45<=metrics[label]['h1_font']<=55
        else:
            checks['mobile_h1_size']=32<=metrics[label]['h1_font']<=36
            checks['mobile_viewport_centered']=abs(left_gutter-right_gutter)<=3
        d.save_screenshot(str(ROOT/f'outing-v4-{label}.png'))
finally:
    d.quit()
result={'url':URL,'checks':checks,'metrics':metrics}
(ROOT/'outing-v4-render.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
if not checks or not all(checks.values()): raise RuntimeError('OUTING_V5_RENDER_FAILED '+json.dumps(result,ensure_ascii=False))
print(json.dumps(result,ensure_ascii=False))
