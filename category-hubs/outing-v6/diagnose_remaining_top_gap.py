#!/usr/bin/env python3
import json, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

URL='https://tsurikue.com/odekake/'

def snap(driver, sel):
    return driver.execute_script('''
const e=document.querySelector(arguments[0]); if(!e) return null;
const r=e.getBoundingClientRect(), s=getComputedStyle(e);
const kids=[...e.children].map(c=>{const q=c.getBoundingClientRect(),cs=getComputedStyle(c);return {tag:c.tagName,cls:c.className,id:c.id,text:(c.innerText||'').trim().slice(0,120),top:q.top,bottom:q.bottom,height:q.height,display:cs.display,marginTop:cs.marginTop,marginBottom:cs.marginBottom,paddingTop:cs.paddingTop,paddingBottom:cs.paddingBottom};});
return {tag:e.tagName,cls:e.className,id:e.id,top:r.top,bottom:r.bottom,height:r.height,marginTop:s.marginTop,marginBottom:s.marginBottom,paddingTop:s.paddingTop,paddingBottom:s.paddingBottom,before:{content:getComputedStyle(e,'::before').content,display:getComputedStyle(e,'::before').display,height:getComputedStyle(e,'::before').height,marginTop:getComputedStyle(e,'::before').marginTop,marginBottom:getComputedStyle(e,'::before').marginBottom},after:{content:getComputedStyle(e,'::after').content,display:getComputedStyle(e,'::after').display,height:getComputedStyle(e,'::after').height,marginTop:getComputedStyle(e,'::after').marginTop,marginBottom:getComputedStyle(e,'::after').marginBottom},children:kids};
''', sel)

def run(w,h):
    o=Options(); o.add_argument('--headless=new'); o.add_argument('--no-sandbox'); o.add_argument('--disable-dev-shm-usage'); o.add_argument(f'--window-size={w},{h}')
    d=webdriver.Chrome(options=o)
    try:
        d.get(URL); time.sleep(3)
        return {
          'viewport':d.execute_script('return {w:innerWidth,h:innerHeight,scrollW:document.documentElement.scrollWidth}'),
          'header':snap(d,'#header'),
          'content':snap(d,'#content'),
          'main':snap(d,'#main_content'),
          'inner':snap(d,'.l-mainContent__inner'),
          'post':snap(d,'.post_content'),
          'root':snap(d,'.tq-outing-v3'),
          'hero':snap(d,'.tq-outing-v3 .tq-hero'),
        }
    finally:d.quit()

out={'desktop':run(1425,1057),'mobile':run(375,857)}
print(json.dumps(out,ensure_ascii=False,indent=2))
