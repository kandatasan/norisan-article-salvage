#!/usr/bin/env python3
from __future__ import annotations
import base64, json, os, re, urllib.parse, urllib.request

SITE='https://tsurikue.com'
USER=os.environ['TSURIKUE_WP_USER']
APP=os.environ['TSURIKUE_WP_APP_PASSWORD']
AUTH='Basic '+base64.b64encode(f'{USER}:{APP}'.encode()).decode()
H={'Authorization':AUTH,'Accept':'application/json','User-Agent':'tsurikue-outing-hero-media-audit/1.0'}


def get(path, params=None):
    if params:
        path += '?' + urllib.parse.urlencode(params)
    req=urllib.request.Request(SITE+path,headers=H,method='GET')
    with urllib.request.urlopen(req,timeout=60) as r:
        return json.loads(r.read().decode()),dict(r.headers)

rows=[]
page=1
while page<=60:
    batch,headers=get('/wp-json/wp/v2/media',{
        'context':'edit','per_page':100,'page':page,'orderby':'date','order':'desc',
        '_fields':'id,date,slug,source_url,mime_type,media_details,title'
    })
    rows.extend(batch)
    total_pages=int(headers.get('X-WP-TotalPages',page))
    if page>=total_pages: break
    page+=1

matches=[]
for row in rows:
    hay=' '.join([str(row.get('slug') or ''),str(row.get('source_url') or ''),json.dumps(row.get('title') or {},ensure_ascii=False)])
    if re.search(r'(?:img[-_ ]?)?8005(?:[^0-9]|$)',hay,re.I):
        details=row.get('media_details') or {}
        matches.append({
            'id':row.get('id'),'date':row.get('date'),'slug':row.get('slug'),'source_url':row.get('source_url'),
            'mime_type':row.get('mime_type'),'width':details.get('width'),'height':details.get('height'),'title':row.get('title')
        })

page3154,_=get('/wp-json/wp/v2/pages/3154',{'context':'edit','_fields':'id,slug,status,title,content,link'})
raw=(page3154.get('content') or {}).get('raw') or ''
print(json.dumps({
    'mode':'READ_ONLY','media_scanned':len(rows),'img_8005_matches':matches,
    'outing_page':{'id':page3154.get('id'),'slug':page3154.get('slug'),'status':page3154.get('status'),'link':page3154.get('link')},
    'current_hero_4588':'img_4588.jpg' in raw,'current_hero_8005':'8005' in raw,
    'wordpress_write_count':0
},ensure_ascii=False,indent=2))
