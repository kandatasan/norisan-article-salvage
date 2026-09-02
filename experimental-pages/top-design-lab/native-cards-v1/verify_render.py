#!/usr/bin/env python3
import json, pathlib, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

ROOT=pathlib.Path.cwd(); URL='https://tsurikue.com/'
TARGETS=['/odekake/','/gourmet-guide/','/fishing-guide/','/car-guide/']
opts=Options(); opts.add_argument('--headless=new'); opts.add_argument('--no-sandbox'); opts.add_argument('--disable-dev-shm-usage'); opts.add_argument('--force-device-scale-factor=1')
d=webdriver.Chrome(options=opts)
checks={}; metrics={}
try:
  for label,w,h in [('desktop',1440,1200),('mobile',390,1000)]:
    d.set_window_size(w,h); ready=False
    for attempt in range(6):
      d.get(URL+f'?tq_native_cards_v1={int(time.time())}-{label}-{attempt}'); time.sleep(1.3+attempt*.25)
      if len(d.find_elements('css selector','.tq4-native-card'))==4: ready=True; break
    checks[label+'_loaded']=ready
    if not ready: continue
    h1=d.find_element('css selector','.tq4 .tq4-hero h1')
    cards=d.find_elements('css selector','.tq4-native-card')
    imgs=[c.find_element('css selector','figure.tq4-native-image a img') for c in cards]
    image_links=[c.find_element('css selector','figure.tq4-native-image a') for c in cards]
    title_links=[c.find_element('css selector','h3 a') for c in cards]
    hrefs=[a.get_attribute('href') for a in image_links]
    title_hrefs=[a.get_attribute('href') for a in title_links]
    direct_hits=[]; image_loaded=[]
    for img,a in zip(imgs,image_links):
      d.execute_script("arguments[0].scrollIntoView({block:'center',inline:'center'});",img); time.sleep(.15)
      hit=d.execute_script('''
        const img=arguments[0], link=arguments[1], r=img.getBoundingClientRect();
        const el=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);
        const anchor=el && el.closest ? el.closest('a') : null;
        return !!anchor && anchor===link;
      ''',img,a)
      direct_hits.append(bool(hit)); image_loaded.append(bool(d.execute_script('return arguments[0].complete && arguments[0].naturalWidth>0 && arguments[0].naturalHeight>0',img)))
    rects=[c.rect for c in cards]
    scroll=d.execute_script('return document.documentElement.scrollWidth'); client=d.execute_script('return document.documentElement.clientWidth')
    metrics[label]={'scroll_width':scroll,'client_width':client,'hrefs':hrefs,'title_hrefs':title_hrefs,'direct_image_hits':direct_hits,'image_loaded':image_loaded,'card_rects':[{'x':round(r['x'],1),'y':round(r['y'],1),'w':round(r['width'],1),'h':round(r['height'],1)} for r in rects]}
    checks[label+'_hero']='休日、' in h1.text and 'なにして遊ぶ？' in h1.text
    checks[label+'_four_native_cards']=len(cards)==4
    checks[label+'_image_links']=all(href.endswith(t) for href,t in zip(hrefs,TARGETS))
    checks[label+'_title_links']=all(href.endswith(t) for href,t in zip(title_hrefs,TARGETS))
    checks[label+'_direct_image_hit']=all(direct_hits)
    checks[label+'_images_loaded']=all(image_loaded)
    checks[label+'_no_old_cover_cards']=len(d.find_elements('css selector','.tq4-cat--outing,.tq4-cat--gourmet,.tq4-cat--fishing,.tq4-cat--car'))==0
    checks[label+'_no_overflow']=scroll<=client+8
    if label=='desktop': checks['desktop_four_columns']=max(abs(rects[i]['y']-rects[0]['y']) for i in range(4))<4
    else: checks['mobile_two_columns']=abs(rects[0]['y']-rects[1]['y'])<4 and rects[2]['y']>rects[0]['y']+rects[0]['height']-4
    d.save_screenshot(str(ROOT/f'homepage-native-cards-v1-{label}.png'))
finally:
  d.quit()
result={'url':URL,'checks':checks,'metrics':metrics}
(ROOT/'homepage-native-cards-v1-render.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
if not checks or not all(checks.values()): raise RuntimeError('NATIVE_CARD_RENDER_FAILED '+json.dumps(result,ensure_ascii=False))
print(json.dumps(result,ensure_ascii=False))
