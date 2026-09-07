#!/usr/bin/env python3
from __future__ import annotations
import base64, json, os, re, time, urllib.parse, urllib.request

SITE='https://tsurikue.com'
UA='tsurikue-audit-new-ux250h-vs-ux300h-20260908/1.0'
POST_IDS=[2329,2948,2975,2870,3570,2517]


def auth():
    raw=f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()
    return 'Basic '+base64.b64encode(raw).decode()


def get_json(url, timeout=60):
    last=None
    for n in range(3):
        try:
            req=urllib.request.Request(url,headers={'Authorization':auth(),'Accept':'application/json','User-Agent':UA})
            with urllib.request.urlopen(req,timeout=timeout) as r:
                return json.loads(r.read().decode()),dict(r.headers)
        except Exception as e:
            last=e
            if n<2: time.sleep(3*(n+1))
    raise last


def raw(row,key):
    v=row.get(key) or {}
    return (v.get('raw') or v.get('rendered') or '') if isinstance(v,dict) else str(v)


def media_ids(content):
    ids=set(int(x) for x in re.findall(r'wp-image-(\d+)',content))
    ids.update(int(x) for x in re.findall(r'<!--\s*wp:image\s+\{[^}]*"id"\s*:\s*(\d+)',content))
    return sorted(ids)


def plain(s):
    return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',s or '')).strip()


def main():
    print('# Audit: new UX250h used vs UX300h new draft (GET only)')
    print('- wordpress_write_count: **0**')
    all_media=[]
    cats=set(); tags=set()
    for pid in POST_IDS:
        q=urllib.parse.urlencode({'context':'edit','_fields':'id,slug,status,title,content,featured_media,categories,tags,link'})
        row,_=get_json(f'{SITE}/wp-json/wp/v2/posts/{pid}?{q}')
        content=raw(row,'content')
        mids=media_ids(content)
        if row.get('featured_media'): mids=[int(row['featured_media'])]+[x for x in mids if x!=int(row['featured_media'])]
        cats.update(row.get('categories') or []); tags.update(row.get('tags') or [])
        print(f"\n## {pid} {row.get('slug')} — {plain(raw(row,'title'))}")
        print(f"- status: {row.get('status')} / featured_media: {row.get('featured_media')} / categories: {row.get('categories')} / tags: {row.get('tags')}")
        print(f"- media ids from post: {mids}")
        for mid in mids[:12]:
            try:
                q=urllib.parse.urlencode({'context':'edit','_fields':'id,status,source_url,alt_text,caption,description,media_details'})
                m,_=get_json(f'{SITE}/wp-json/wp/v2/media/{mid}?{q}',timeout=45)
                url=m.get('source_url') or ''
                alt=plain(m.get('alt_text') or '')
                cap=plain(raw(m,'caption'))
                desc=plain(raw(m,'description'))
                w=(m.get('media_details') or {}).get('width'); h=(m.get('media_details') or {}).get('height')
                print(f"  - media {mid}: {w}x{h} alt=`{alt}` caption=`{cap}` url={url}")
                all_media.append((mid,pid,url,alt,cap,desc,w,h))
            except Exception as e:
                print(f"  - media {mid}: ERROR {e}")

    print('\n## Category metadata')
    for cid in sorted(cats):
        q=urllib.parse.urlencode({'context':'edit','_fields':'id,name,slug,parent,count'})
        c,_=get_json(f'{SITE}/wp-json/wp/v2/categories/{cid}?{q}',timeout=45)
        print(f"- category {cid}: {c.get('name')} / slug={c.get('slug')} / parent={c.get('parent')} / count={c.get('count')}")

    print('\n## Tag metadata')
    for tid in sorted(tags):
        q=urllib.parse.urlencode({'context':'edit','_fields':'id,name,slug,count'})
        t,_=get_json(f'{SITE}/wp-json/wp/v2/tags/{tid}?{q}',timeout=45)
        print(f"- tag {tid}: {t.get('name')} / slug={t.get('slug')} / count={t.get('count')}")

    print('\n## Slug collision checks')
    for slug in ['lexus-ux250h-vs-ux300h','lexus-ux250h-used-vs-ux300h','lexus-ux-buy-now']:
        q=urllib.parse.urlencode({'context':'edit','slug':slug,'status':'any','per_page':10,'_fields':'id,slug,status,title'})
        rows,_=get_json(f'{SITE}/wp-json/wp/v2/posts?{q}',timeout=45)
        print(f'- {slug}: {[(r.get("id"),r.get("status"),plain(raw(r,"title"))) for r in rows]}')

    # General media-library search for UX/300h labels, plus recent image attachments.
    print('\n## Media library searches')
    for term in ['UX','300h','250h','レクサス']:
        q=urllib.parse.urlencode({'context':'edit','search':term,'media_type':'image','per_page':30,'orderby':'date','order':'desc','_fields':'id,date,source_url,alt_text,caption,media_details'})
        rows,_=get_json(f'{SITE}/wp-json/wp/v2/media?{q}',timeout=45)
        print(f'### search={term} results={len(rows)}')
        for m in rows[:20]:
            w=(m.get('media_details') or {}).get('width'); h=(m.get('media_details') or {}).get('height')
            print(f"- {m.get('id')} {m.get('date')} {w}x{h} alt=`{plain(m.get('alt_text') or '')}` caption=`{plain(raw(m,'caption'))}` url={m.get('source_url')}")

if __name__=='__main__': main()
