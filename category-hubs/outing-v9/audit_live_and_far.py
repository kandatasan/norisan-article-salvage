#!/usr/bin/env python3
import base64, html, json, os, pathlib, re, time, urllib.parse, urllib.request
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

BASE='https://tsurikue.com/wp-json/wp/v2'
PAGE_ID=3154
OUT=pathlib.Path('/tmp/outing-v9-audit.json')
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode()

def req(path):
    r=urllib.request.Request(BASE+path,headers={'Authorization':AUTH,'Accept':'application/json','User-Agent':'tsurikue-outing-v9-audit/1.0'})
    with urllib.request.urlopen(r,timeout=60) as x:
        return json.loads(x.read().decode()),dict(x.headers.items())

def clean(s): return html.unescape(re.sub(r'<[^>]+>','',s or '')).strip()

def browser(url,width=390,height=844):
    o=Options(); o.add_argument('--headless=new'); o.add_argument('--no-sandbox'); o.add_argument('--disable-dev-shm-usage'); o.add_argument(f'--window-size={width},{height}')
    d=webdriver.Chrome(options=o); d.get(url); time.sleep(4)
    try:
        return d.execute_script(r'''
const q=s=>document.querySelector(s), r=e=>e?e.getBoundingClientRect():null;
const hero=q('.tq-outing-v3.tq-hero')||q('.tq-outing-v3 .tq-hero');
const post=q('.post_content');
const root=q('div.wp-block-group.tq-outing-v3:not(.tq-hero)');
const nav=q('.p-spHeadMenu')||q('.l-header__bar')||q('.l-header__gnav')||q('.p-globalNav');
const header=q('#header');
const content=q('#content');
const main=q('#main_content')||q('main');
const chain=[]; let e=hero;
while(e && chain.length<10){const cs=getComputedStyle(e), rr=r(e); chain.push({tag:e.tagName,cls:e.className||'',id:e.id||'',top:rr&&rr.top,bottom:rr&&rr.bottom,height:rr&&rr.height,marginTop:cs.marginTop,paddingTop:cs.paddingTop,position:cs.position,display:cs.display}); e=e.parentElement;}
const children=post?Array.from(post.children).map((x,i)=>({i,tag:x.tagName,cls:x.className||'',display:getComputedStyle(x).display,top:r(x).top,height:r(x).height})):[];
return {url:location.href,clientW:document.documentElement.clientWidth,scrollW:document.documentElement.scrollWidth,header:r(header),nav:r(nav),content:r(content),main:r(main),post:r(post),hero:r(hero),root:r(root),heroClass:hero&&hero.className,heroParent:hero&&hero.parentElement&&hero.parentElement.className,heroInsideRoot:root?root.querySelectorAll('.tq-hero').length:null,children,chain,h1:hero&&hero.querySelector('h1')?hero.querySelector('h1').innerText:null,img:hero&&hero.querySelector('img')?(hero.querySelector('img').currentSrc||hero.querySelector('img').src):null,auto:document.documentElement.dataset.tqOutingAuto||null};
''')
    finally: d.quit()

page,_=req(f'/pages/{PAGE_ID}?context=edit&_fields=id,slug,status,title,content,modified')
raw=page['content']['raw']

# Find far tag by exact name, then audit all posts using it.
tags,_=req('/tags?search='+urllib.parse.quote('ちょっと遠くへ')+'&per_page=100&_fields=id,name,slug,count')
far=next((t for t in tags if t['name']=='ちょっと遠くへ'),None)
far_posts=[]
if far:
    far_posts,_=req(f"/posts?status=publish&tags={far['id']}&per_page=100&_fields=id,slug,link,title,categories,tags")

# Find published posts whose title/content search matches 高知.
kochi_posts,_=req('/posts?status=publish&search='+urllib.parse.quote('高知')+'&per_page=100&_fields=id,slug,link,title,categories,tags')

# Resolve category and tag names used by relevant posts.
cat_ids=sorted({i for p in far_posts+kochi_posts for i in p.get('categories',[])})
tag_ids=sorted({i for p in far_posts+kochi_posts for i in p.get('tags',[])})
cats=[]
for i in cat_ids:
    try: c,_=req(f'/categories/{i}?_fields=id,name,slug,parent,count'); cats.append(c)
    except Exception as e: cats.append({'id':i,'error':str(e)})
resolved_tags=[]
for i in tag_ids:
    try: t,_=req(f'/tags/{i}?_fields=id,name,slug,count'); resolved_tags.append(t)
    except Exception as e: resolved_tags.append({'id':i,'error':str(e)})

# Determine whether live auto-index still requires the outing category.
auto_lines=[line.strip() for line in raw.splitlines() if '/posts?' in line and 'tags=' in line]

normal=browser('https://tsurikue.com/odekake/')
busted=browser('https://tsurikue.com/odekake/?tq_cache_audit=20260903')

report={
 'page':{'id':page['id'],'slug':page['slug'],'status':page['status'],'modified':page.get('modified')},
 'raw_structure':{'standalone_marker':'tq-outing-structure:v8:standalone-hero' in raw,'hero_before_root':raw.find('<!-- wp:cover ')>=0 and raw.find('<!-- wp:cover ')<raw.find('<!-- wp:group {"className":"tq-outing-v3"'),'auto_query_lines':auto_lines},
 'far_tag':far,
 'far_posts':[{'id':p['id'],'slug':p['slug'],'title':clean(p['title']['rendered']),'link':p['link'],'categories':p['categories'],'tags':p['tags']} for p in far_posts],
 'kochi_posts':[{'id':p['id'],'slug':p['slug'],'title':clean(p['title']['rendered']),'link':p['link'],'categories':p['categories'],'tags':p['tags']} for p in kochi_posts],
 'categories':cats,'resolved_tags':resolved_tags,
 'render':{'normal':normal,'cache_busted':busted}
}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
