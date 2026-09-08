#!/usr/bin/env python3
from __future__ import annotations
import base64, json, os, urllib.parse, urllib.request

SITE='https://tsurikue.com'
UA='tsurikue-audit-lbx-options-20260908/1.0'
SLUGS=['lexus-lbx-options','lbx-options','lexus-lbx-option','lbx-option']
SEARCHES=['レクサスLBX オプション','LBX オプション','LBX 見積もり']
MEDIA_TERMS=['3110','4492','4494','4510','4513']
RELATED_SLUGS=['lexus-lbx-regret','lexus-ux-vs-lbx']

def auth():
    u=os.environ.get('TSURIKUE_WP_USER'); p=os.environ.get('TSURIKUE_WP_APP_PASSWORD')
    if not u or not p: raise SystemExit('BLOCKED_MISSING_SECRETS')
    return 'Basic '+base64.b64encode(f'{u}:{p}'.encode()).decode()

def req(url):
    r=urllib.request.Request(url,headers={'Authorization':auth(),'Accept':'application/json','User-Agent':UA})
    with urllib.request.urlopen(r,timeout=60) as resp:
        return json.loads(resp.read().decode()),dict(resp.headers)

def q(path, params):
    return req(f"{SITE}{path}?{urllib.parse.urlencode(params)}")[0]

def main():
    print('# Audit: Lexus LBX options new draft (GET only)')
    print('- wordpress_write_count: **0**')
    print('\n## Slug collision checks')
    for slug in SLUGS:
        rows=q('/wp-json/wp/v2/posts',{'context':'edit','slug':slug,'status':'any','per_page':20,'_fields':'id,slug,status,title'})
        out=[(r['id'],r['slug'],r['status'],(r.get('title') or {}).get('rendered','')) for r in rows]
        print(f'- `{slug}`: {out}')
    print('\n## Search collisions')
    for s in SEARCHES:
        rows=q('/wp-json/wp/v2/posts',{'context':'edit','search':s,'status':'any','per_page':30,'_fields':'id,slug,status,title'})
        out=[(r['id'],r['slug'],r['status'],(r.get('title') or {}).get('rendered','')) for r in rows]
        print(f'- search `{s}`: {out}')
    print('\n## Related posts')
    for slug in RELATED_SLUGS:
        rows=q('/wp-json/wp/v2/posts',{'context':'edit','slug':slug,'status':'any','per_page':5,'_fields':'id,slug,status,title,featured_media,categories,tags,content'})
        for r in rows:
            c=(r.get('content') or {}).get('raw') or (r.get('content') or {}).get('rendered','')
            print(f"- {r['id']} {r['slug']} — status={r['status']} featured={r.get('featured_media')} categories={r.get('categories')} tags={r.get('tags')} chars={len(c)}")
    print('\n## Media searches')
    seen=set()
    for term in MEDIA_TERMS:
        rows=q('/wp-json/wp/v2/media',{'context':'edit','search':term,'per_page':50,'_fields':'id,slug,title,alt_text,caption,source_url,media_type,mime_type,media_details'})
        print(f'### search={term} results={len(rows)}')
        for r in rows:
            if r['id'] in seen: continue
            seen.add(r['id'])
            title=(r.get('title') or {}).get('rendered',''); cap=(r.get('caption') or {}).get('rendered','')
            md=r.get('media_details') or {}
            print(f"- {r['id']}: slug=`{r.get('slug')}` title=`{title}` alt=`{r.get('alt_text','')}` caption=`{cap}` size={md.get('width')}x{md.get('height')} url={r.get('source_url')}")
    print('\n## Category/tag metadata')
    for kind,ids in [('categories',[10,11]),('tags',[36,37,42])]:
        for i in ids:
            row,_=req(f'{SITE}/wp-json/wp/v2/{kind}/{i}?context=edit')
            print(f'- {kind[:-1]} {i}: name={row.get("name")} slug={row.get("slug")} parent={row.get("parent")} count={row.get("count")}')
    _,h=req(f"{SITE}/wp-json/wp/v2/posts?{urllib.parse.urlencode({'status':'publish','per_page':1,'_fields':'id'})}")
    print(f'\n- published_posts: **{h.get("X-WP-Total","?")}**')

if __name__=='__main__': main()
