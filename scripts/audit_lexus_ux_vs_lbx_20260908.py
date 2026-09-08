#!/usr/bin/env python3
from __future__ import annotations
import base64, json, os, urllib.parse, urllib.request

SITE='https://tsurikue.com'
UA='tsurikue-audit-ux-vs-lbx-20260908/1.0'
SLUGS=['lexus-ux-vs-lbx','lexus-ux-lbx','ux-vs-lbx','lexus-lbx-vs-ux']
SEARCHES=['レクサスUX LBX','LBX']
MEDIA_TERMS=['3110','3099','3089','3087','3105','3106','3129','LBX','lbx']
RELATED_SLUGS=['lexus-ux-review','lexus-ux-size','lexus-ux-rear-seat','lexus-ux-cargo','lexus-ux-used','lexus-ux250h-used-vs-ux300h','lexus-ux-vs-nx']


def auth():
    u=os.environ.get('TSURIKUE_WP_USER'); p=os.environ.get('TSURIKUE_WP_APP_PASSWORD')
    if not u or not p: raise SystemExit('BLOCKED_MISSING_SECRETS')
    return 'Basic '+base64.b64encode(f'{u}:{p}'.encode()).decode()


def req(url):
    r=urllib.request.Request(url,headers={'Authorization':auth(),'Accept':'application/json','User-Agent':UA})
    with urllib.request.urlopen(r,timeout=60) as resp:
        return json.loads(resp.read().decode())


def q(path, params):
    return req(f"{SITE}{path}?{urllib.parse.urlencode(params)}")


def main():
    print('# Audit: Lexus UX vs LBX new draft (GET only)')
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
        rows=q('/wp-json/wp/v2/media',{'context':'edit','search':term,'per_page':50,'_fields':'id,slug,title,alt_text,caption,source_url,media_type,mime_type'})
        print(f'### search={term} results={len(rows)}')
        for r in rows:
            if r['id'] in seen: continue
            seen.add(r['id'])
            title=(r.get('title') or {}).get('rendered',''); cap=(r.get('caption') or {}).get('rendered','')
            print(f"- {r['id']}: slug=`{r.get('slug')}` title=`{title}` alt=`{r.get('alt_text','')}` caption=`{cap}` url={r.get('source_url')}")
    print('\n## Category/tag metadata')
    for kind,ids in [('categories',[10,11]),('tags',[36,37,42])]:
        for i in ids:
            row=req(f'{SITE}/wp-json/wp/v2/{kind}/{i}?context=edit')
            print(f'- {kind[:-1]} {i}: name={row.get("name")} slug={row.get("slug")} parent={row.get("parent")} count={row.get("count")}')

if __name__=='__main__': main()
