#!/usr/bin/env python3
import json,time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
URL='https://tsurikue.com/odekake/'
def run(w,h):
 o=Options();o.add_argument('--headless=new');o.add_argument('--no-sandbox');o.add_argument('--disable-dev-shm-usage');o.add_argument(f'--window-size={w},{h}');d=webdriver.Chrome(options=o)
 try:
  d.get(URL);time.sleep(4)
  return d.execute_script('''
const q=s=>document.querySelector(s), r=e=>e&&e.getBoundingClientRect();
const H=q('#header'), C=q('#content'), T=q('.c-pageTitle'), P=q('.post_content'), R=q('.tq-outing-v3'), X=q('.tq-hero'), I=q('.tq-choose-intro');
const hs=r(H),cs=r(C),ts=r(T),ps=r(P),rs=r(R),xs=r(X),is=r(I);
return {headerBottom:hs.bottom,contentTop:cs.top,contentPaddingTop:getComputedStyle(C).paddingTop,titleDisplay:getComputedStyle(T).display,titleHeight:ts.height,postTop:ps.top,rootTop:rs.top,heroTop:xs.top,heroBottom:xs.bottom,introTop:is.top,scrollW:document.documentElement.scrollWidth,clientW:document.documentElement.clientWidth,src:q('.tq-hero img').currentSrc||q('.tq-hero img').src,h1:[...q('.tq-hero h1').getClientRects()].length,text:q('.tq-hero h1').innerText};''')
 finally:d.quit()
res={'desktop':run(1425,1057),'mobile':run(375,857)}
checks={
'desktop_title_hidden':res['desktop']['titleDisplay']=='none' and res['desktop']['titleHeight']==0,
'mobile_title_hidden':res['mobile']['titleDisplay']=='none' and res['mobile']['titleHeight']==0,
'desktop_top_compact':res['desktop']['heroTop']-res['desktop']['headerBottom']<=70,
'mobile_top_compact':res['mobile']['heroTop']-res['mobile']['headerBottom']<=48,
'desktop_pad':res['desktop']['contentPaddingTop']=='24px','mobile_pad':res['mobile']['contentPaddingTop']=='8px',
'desktop_no_overflow':res['desktop']['scrollW']<=res['desktop']['clientW']+2,'mobile_no_overflow':res['mobile']['scrollW']<=res['mobile']['clientW']+2,
'dolphin':all('img_2419.jpg' in res[k]['src'] for k in ['desktop','mobile']),
'heading':all(res[k]['text'].splitlines()==['今日は、','どこ行く？'] for k in ['desktop','mobile'])}
out={'checks':checks,'metrics':res};print(json.dumps(out,ensure_ascii=False,indent=2));
if not all(checks.values()): raise SystemExit('VERIFY_FAILED')
