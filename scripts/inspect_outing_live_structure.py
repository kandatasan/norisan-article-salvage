#!/usr/bin/env python3
import base64, html, json, os, re, urllib.parse, urllib.request
SITE='https://tsurikue.com'; BASE=SITE+'/wp-json/wp/v2'
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode()

def req(path):
    r=urllib.request.Request(BASE+path,headers={'Authorization':AUTH,'Accept':'application/json','User-Agent':'tsurikue-outing-inspect/1.0'})
    with urllib.request.urlopen(r,timeout=60) as x: return json.loads(x.read().decode())

def clean(v):
    if isinstance(v,dict): v=v.get('raw') or v.get('rendered') or ''
    return html.unescape(re.sub(r'<[^>]+>','',v or '')).strip()
q=urllib.parse.urlencode({'context':'edit','slug':'odekake','status':'publish','per_page':10,'_fields':'id,slug,status,title,content,link'})
rows=req('/pages?'+q)
if len(rows)!=1: raise SystemExit(f'PAGE_MATCHES={len(rows)}')
p=rows[0]; raw=(p.get('content') or {}).get('raw') or ''
classes=sorted(set(re.findall(r'class="([^"]+)"',raw)))
tq=sorted(set(re.findall(r'\btq-[A-Za-z0-9_-]+\b',raw)))
markers=[x for x in ['tq-outing-clean','tq-outing-v3','tq-outing-v4','tq-outing-v5','tq-outing-v6','tq-outing-v7','tq-outing-v8','tq-outing-v9','tq-outing-v10','tq-accordion','wp-block-details','wp-block-cover'] if x in raw]
snips=[]
for needle in ['tq-accordion','wp-block-details','ちょっと遠くへ','今日は、どこ行く？','今日は、<br>どこ行く？']:
    i=raw.find(needle)
    if i>=0: snips.append({'needle':needle,'snippet':raw[max(0,i-220):i+520]})
print(json.dumps({'page_id':p['id'],'title':clean(p['title']),'raw_length':len(raw),'details_tag_count':raw.count('<details'),'wp_details_count':raw.count('<!-- wp:details'),'cover_count':raw.count('<!-- wp:cover'),'markers':markers,'tq_tokens':tq[:120],'class_samples':classes[:80],'snippets':snips},ensure_ascii=False,indent=2))
