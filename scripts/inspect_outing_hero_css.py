#!/usr/bin/env python3
import json,time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
SITE='https://tsurikue.com/odekake/'
o=Options(); o.add_argument('--headless=new'); o.add_argument('--no-sandbox'); o.add_argument('--disable-dev-shm-usage'); o.add_argument('--window-size=1440,1100')
d=webdriver.Chrome(options=o)
try:
    d.get(SITE+'?tq_hero_diag='+str(int(time.time()))); time.sleep(5)
    data=d.execute_script('''
const h=document.querySelector('.tq-outing-v3.tq-hero'); if(!h) return {error:'hero missing'};
const cs=getComputedStyle(h), r=h.getBoundingClientRect();
const p=h.parentElement, pr=p&&p.getBoundingClientRect(), pcs=p&&getComputedStyle(p);
const rules=[];
for(const ss of [...document.styleSheets]){
  let rr; try{rr=ss.cssRules}catch(e){continue}
  for(const rule of [...rr]){
    if(rule.type===CSSRule.STYLE_RULE && rule.selectorText){
      try{if(h.matches(rule.selectorText)) rules.push({selector:rule.selectorText,css:rule.style.cssText})}catch(e){}
    }
    if(rule.type===CSSRule.SUPPORTS_RULE || rule.type===CSSRule.MEDIA_RULE){
      for(const x of [...rule.cssRules]) if(x.selectorText){try{if(h.matches(x.selectorText)) rules.push({group:rule.conditionText||rule.media?.mediaText,selector:x.selectorText,css:x.style.cssText})}catch(e){}}
    }
  }
}
return {viewport:{w:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth},hero:{rect:{left:r.left,right:r.right,width:r.width},computed:{position:cs.position,left:cs.left,right:cs.right,width:cs.width,maxWidth:cs.maxWidth,marginLeft:cs.marginLeft,marginRight:cs.marginRight,transform:cs.transform}},parent:pr?{tag:p.tagName,cls:p.className,rect:{left:pr.left,right:pr.right,width:pr.width},computed:{position:pcs.position,width:pcs.width,paddingLeft:pcs.paddingLeft,paddingRight:pcs.paddingRight,overflow:pcs.overflow}}:null,rules};
''')
    print(json.dumps(data,ensure_ascii=False,indent=2))
finally:d.quit()
