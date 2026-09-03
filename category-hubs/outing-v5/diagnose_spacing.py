#!/usr/bin/env python3
import json, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

URL='https://tsurikue.com/odekake/'
opts=Options()
opts.add_argument('--headless=new')
opts.add_argument('--no-sandbox')
opts.add_argument('--disable-dev-shm-usage')
opts.add_argument('--force-device-scale-factor=1')
d=webdriver.Chrome(options=opts)
result={}
try:
    for label,w,h in [('desktop',1440,1200),('mobile',390,1000)]:
        d.set_window_size(w,h)
        d.get(URL+f'?tq_spacing_diag={int(time.time())}-{label}')
        time.sleep(2)
        root=d.find_element('css selector','.tq-outing-v3')
        hero=d.find_element('css selector','.tq-outing-v3 .tq-hero')
        choose=d.find_element('css selector','.tq-outing-v3 .tq-choose')
        data=d.execute_script('''
          const root=arguments[0], hero=arguments[1], choose=arguments[2];
          const pick=(el)=>{
            if(!el) return null;
            const r=el.getBoundingClientRect(), s=getComputedStyle(el);
            return {tag:el.tagName, id:el.id||'', cls:el.className||'', top:r.top,bottom:r.bottom,left:r.left,right:r.right,width:r.width,height:r.height,
              marginTop:s.marginTop,marginBottom:s.marginBottom,paddingTop:s.paddingTop,paddingBottom:s.paddingBottom,rowGap:s.rowGap,gap:s.gap,position:s.position,display:s.display};
          };
          const ancestors=[]; let el=root;
          for(let i=0;el && i<8;i++,el=el.parentElement) ancestors.push(pick(el));
          const header=document.querySelector('#header, .l-header, header');
          const main=document.querySelector('.l-mainContent');
          const inner=document.querySelector('.l-mainContent__inner');
          const post=document.querySelector('.post_content');
          return {viewport:{w:document.documentElement.clientWidth,h:innerHeight,scrollW:document.documentElement.scrollWidth},header:pick(header),main:pick(main),mainInner:pick(inner),post:pick(post),root:pick(root),hero:pick(hero),choose:pick(choose),ancestors};
        ''',root,hero,choose)
        data['gaps']={
            'header_to_hero': None if not data.get('header') else round(data['hero']['top']-data['header']['bottom'],2),
            'root_to_hero': round(data['hero']['top']-data['root']['top'],2),
            'hero_to_choose': round(data['choose']['top']-data['hero']['bottom'],2),
        }
        result[label]=data
finally:
    d.quit()
print(json.dumps(result,ensure_ascii=False,indent=2))
