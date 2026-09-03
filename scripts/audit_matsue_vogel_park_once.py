#!/usr/bin/env python3
from __future__ import annotations
import base64, json, os, urllib.parse, urllib.request
from pathlib import Path

SITE='https://tsurikue.com'
OUT=Path('reports/matsue-vogel-park-audit')
TARGETS=['img_5120','img_5121','img_5123','img_5125','img_5129','img_5131','img_5132','img_5133','img_5135','img_5136','img_8011','img_8010','img_5144','img_5153','img_5160','img_5158']

def auth_header(u,p):
    return 'Basic '+base64.b64encode(f'{u}:{p}'.encode()).decode()

def get_json(url,auth):
    req=urllib.request.Request(url,headers={'Authorization':auth,'Accept':'application/json','User-Agent':'tsurikue-vogel-audit/1.0'})
    with urllib.request.urlopen(req,timeout=60) as r:
        return json.loads(r.read().decode()), dict(r.headers)

def all_rows(endpoint,auth,fields):
    rows=[]; page=1
    while True:
        q=urllib.parse.urlencode({'context':'edit','per_page':100,'page':page,'_fields':fields})
        batch,h=get_json(f'{SITE}/wp-json/wp/v2/{endpoint}?{q}',auth)
        rows.extend(batch)
        total_pages=int(h.get('X-WP-TotalPages','1'))
        if page>=total_pages: break
        page+=1
    return rows

def main():
    u=os.environ.get('TSURIKUE_WP_USER'); p=os.environ.get('TSURIKUE_WP_APP_PASSWORD')
    if not u or not p: raise SystemExit('BLOCKED_MISSING_SECRETS')
    a=auth_header(u,p)
    media=all_rows('media',a,'id,date,slug,source_url,title,caption,mime_type')
    found={}
    for t in TARGETS:
        matches=[]
        for m in media:
            hay=' '.join([str(m.get('slug') or ''),str(m.get('source_url') or ''),json.dumps(m.get('title') or {},ensure_ascii=False)]).casefold()
            if t in hay:
                matches.append({'id':m['id'],'slug':m.get('slug'),'source_url':m.get('source_url'),'mime_type':m.get('mime_type')})
        found[t]=matches
    posts=all_rows('posts',a,'id,slug,status,title,link,categories,tags')
    dup=[]
    for r in posts:
        hay=(r.get('slug') or '')+' '+json.dumps(r.get('title') or {},ensure_ascii=False)
        if 'フォーゲル' in hay or 'vogel' in hay.casefold(): dup.append(r)
    cats=all_rows('categories',a,'id,slug,name,parent,count')
    tags=all_rows('tags',a,'id,slug,name,count')
    report={'wordpress_write_count':0,'media_total':len(media),'media_matches':found,'possible_existing_posts':dup,'categories':cats,'tags':tags}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# Matsue Vogel Park audit','',f'- mode: **READ ONLY**',f'- wordpress_write_count: **0**',f'- media_total: **{len(media)}**','','## Media matches','']
    for t,m in found.items(): lines.append(f'- `{t}`: '+(json.dumps(m,ensure_ascii=False) if m else '**NOT FOUND**'))
    lines += ['','## Possible existing posts','',json.dumps(dup,ensure_ascii=False,indent=2),'','## Categories','',json.dumps(cats,ensure_ascii=False,indent=2),'','## Tags','',json.dumps(tags,ensure_ascii=False,indent=2)]
    (OUT/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
