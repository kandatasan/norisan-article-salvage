#!/usr/bin/env python3
import json, pathlib, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

ROOT=pathlib.Path.cwd()
URL='https://tsurikue.com/'
TARGETS=['/odekake/','/gourmet-guide/','/fishing-guide/','/car-guide/']
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
      d.get(URL+f'?tq_native_overlay_v2={int(time.time())}-{label}-{attempt}')
      time.sleep(1.3+attempt*.25)
      if len(d.find_elements('css selector','.tq4-native-card'))==4:
        ready=True; break
    checks[label+'_loaded']=ready
    if not ready: continue

    cards=d.find_elements('css selector','.tq4-native-card')
    image_links=[c.find_element('css selector','figure.tq4-native-image a') for c in cards]
    imgs=[c.find_element('css selector','figure.tq4-native-image img') for c in cards]
    bodies=[c.find_element('css selector','.tq4-native-body') for c in cards]
    titles=[c.find_element('css selector','h3') for c in cards]
    hrefs=[a.get_attribute('href') for a in image_links]
    point_hits=[]; image_loaded=[]; overlay_metrics=[]

    for c,img,a,body,title in zip(cards,imgs,image_links,bodies,titles):
      d.execute_script("arguments[0].scrollIntoView({block:'center',inline:'center'});",c)
      time.sleep(.12)
      hits=d.execute_script('''
        const card=arguments[0], link=arguments[1]; const r=card.getBoundingClientRect();
        const pts=[[.50,.18],[.50,.52],[.50,.86]];
        return pts.map(([px,py])=>{
          const el=document.elementFromPoint(r.left+r.width*px,r.top+r.height*py);
          const anchor=el && el.closest ? el.closest('a') : null;
          return !!anchor && anchor===link;
        });
      ''',c,a)
      point_hits.append(hits)
      image_loaded.append(bool(d.execute_script('return arguments[0].complete && arguments[0].naturalWidth>0 && arguments[0].naturalHeight>0',img)))
      overlay_metrics.append(d.execute_script('''
        const c=arguments[0],img=arguments[1],body=arguments[2],title=arguments[3];
        const cr=c.getBoundingClientRect(), ir=img.getBoundingClientRect(), br=body.getBoundingClientRect();
        const bs=getComputedStyle(body), ts=getComputedStyle(title), aft=getComputedStyle(c,'::after');
        return {
          cardH:cr.height,imgH:ir.height,bodyTop:br.top-cr.top,bodyBottom:cr.bottom-br.bottom,
          bodyPosition:bs.position,bodyPointer:bs.pointerEvents,titleColor:ts.color,
          afterPointer:aft.pointerEvents,afterBackground:aft.backgroundImage
        };
      ''',c,img,body,title))

    rects=[c.rect for c in cards]
    scroll=d.execute_script('return document.documentElement.scrollWidth')
    client=d.execute_script('return document.documentElement.clientWidth')
    metrics[label]={
      'scroll_width':scroll,'client_width':client,'hrefs':hrefs,
      'three_point_image_hits':point_hits,'image_loaded':image_loaded,
      'overlay':overlay_metrics,
      'card_rects':[{'x':round(r['x'],1),'y':round(r['y'],1),'w':round(r['width'],1),'h':round(r['height'],1)} for r in rects]
    }
    checks[label+'_four_cards']=len(cards)==4
    checks[label+'_links']=all(href.endswith(t) for href,t in zip(hrefs,TARGETS))
    checks[label+'_image_hits_through_text']=all(all(row) for row in point_hits)
    checks[label+'_images_loaded']=all(image_loaded)
    checks[label+'_overlay_absolute']=all(x['bodyPosition']=='absolute' and x['bodyBottom']<3 for x in overlay_metrics)
    checks[label+'_overlay_clickthrough']=all(x['bodyPointer']=='none' and x['afterPointer']=='none' for x in overlay_metrics)
    checks[label+'_white_titles']=all(x['titleColor']=='rgb(255, 255, 255)' for x in overlay_metrics)
    checks[label+'_gradient']=all('gradient' in x['afterBackground'] for x in overlay_metrics)
    checks[label+'_text_on_image']=all(abs(x['cardH']-x['imgH'])<4 and x['bodyTop']>0 and x['bodyTop']<x['cardH'] for x in overlay_metrics)
    checks[label+'_no_overflow']=scroll<=client+8
    if label=='desktop':
      checks['desktop_four_columns']=max(abs(rects[i]['y']-rects[0]['y']) for i in range(4))<4
    else:
      checks['mobile_two_columns']=abs(rects[0]['y']-rects[1]['y'])<4 and rects[2]['y']>rects[0]['y']+rects[0]['height']-4
    d.save_screenshot(str(ROOT/f'homepage-native-overlay-v2-{label}.png'))
finally:
  d.quit()

result={'url':URL,'checks':checks,'metrics':metrics}
(ROOT/'homepage-native-overlay-v2-render.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
if not checks or not all(checks.values()):
  raise RuntimeError('NATIVE_OVERLAY_RENDER_FAILED '+json.dumps(result,ensure_ascii=False))
print(json.dumps(result,ensure_ascii=False))
