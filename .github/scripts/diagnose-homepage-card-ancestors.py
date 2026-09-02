#!/usr/bin/env python3
import json,time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

URL='https://tsurikue.com/'
opts=Options(); opts.add_argument('--headless=new'); opts.add_argument('--no-sandbox'); opts.add_argument('--disable-dev-shm-usage'); opts.add_argument('--force-device-scale-factor=1')
d=webdriver.Chrome(options=opts)
try:
    d.set_window_size(1440,1200)
    d.get(URL+'?tq_card_ancestor_audit='+str(int(time.time())))
    time.sleep(2)
    card=d.find_element('css selector','.tq4-cat--outing')
    anchor=card.find_element('css selector','h3 a')
    chain=d.execute_script('''
      const card=arguments[0], a=arguments[1];
      const out=[]; let el=a;
      while(el){
        const cs=getComputedStyle(el), r=el.getBoundingClientRect();
        out.push({tag:el.tagName,cls:el.className||'',position:cs.position,zIndex:cs.zIndex,overflow:cs.overflow,overflowX:cs.overflowX,overflowY:cs.overflowY,pointerEvents:cs.pointerEvents,display:cs.display,rect:{x:r.x,y:r.y,w:r.width,h:r.height}});
        if(el===card) break;
        el=el.parentElement;
      }
      const cr=card.getBoundingClientRect();
      const pts=[[.08,.10],[.5,.5],[.92,.88]].map(([px,py])=>{
        const x=cr.left+cr.width*px,y=cr.top+cr.height*py;
        const e=document.elementFromPoint(x,y);
        return {x,y,tag:e&&e.tagName,cls:e&&e.className,html:e&&e.outerHTML.slice(0,300)};
      });
      return {chain:out,points:pts};
    ''',card,anchor)
    print(json.dumps(chain,ensure_ascii=False,indent=2))
finally:
    d.quit()
