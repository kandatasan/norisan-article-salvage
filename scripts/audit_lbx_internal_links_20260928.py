#!/usr/bin/env python3
from __future__ import annotations
import base64, json, os, re, urllib.parse, urllib.request
from html import unescape

SITE='https://tsurikue.com'
UA='tsurikue-audit-lbx-links-20260928/1.0'
SLUGS=[
 'lexus-lbx-price',
 'lexus-lbx-interior',
 'lexus-lbx-options',
 'lexus-lbx-cheap',
 'lexus-lbx-regret',
 'lexus-ux-vs-lbx',
]
HREF_RE=re.compile(r'href=["\']https://tsurikue\.com/([^"\'#?]+?)/?["\']',re.I)
SHORTCODE_RE=re.compile(r'\[blog_parts\s+id=["\']?(\d+)["\']?\]',re.I)

def auth():
    u=os.environ.get('TSURIKUE_WP_USER'); p=os.environ.get('TSURIKUE_WP_APP_PASSWORD')
    if not u or not p: raise SystemExit('BLOCKED_MISSING_SECRETS')
    return 'Basic '+base64.b64encode(f'{u}:{p}'.encode()).decode()

def req(url):
    r=urllib.request.Request(url,headers={'Authorization':auth(),'Accept':'application/json','User-Agent':UA})
    with urllib.request.urlopen(r,timeout=60) as resp:
        return json.loads(resp.read().decode()),dict(resp.headers)

def get_slug(slug):
    q=urllib.parse.urlencode({'context':'edit','slug':slug,'status':'any','per_page':10,'_fields':'id,slug,status,title,content,featured_media,categories,tags'})
    rows,_=req(f'{SITE}/wp-json/wp/v2/posts?{q}')
    if len(rows)!=1: raise RuntimeError(f'{slug}: expected 1 row, got {len(rows)}')
    return rows[0]

def raw(row,key):
    v=row.get(key) or {}
    return (v.get('raw') or v.get('rendered') or '') if isinstance(v,dict) else str(v)

def main():
    rows={s:get_slug(s) for s in SLUGS}
    print('# Lexus LBX internal-link audit (GET only)')
    print('- wordpress_write_count: **0**')
    print('\n## Target posts')
    for s,r in rows.items():
        c=raw(r,'content')
        aff=SHORTCODE_RE.findall(c)
        print(f"- {s}: id={r['id']} status={r['status']} title={unescape(raw(r,'title'))!r} chars={len(c)} affiliate_blocks={aff}")

    print('\n## Current cluster link matrix')
    header='| From | ' + ' | '.join(SLUGS) + ' |'
    sep='|---|' + '|'.join(['---:']*len(SLUGS)) + '|'
    print(header); print(sep)
    for s,r in rows.items():
        links=HREF_RE.findall(raw(r,'content'))
        vals=[]
        for t in SLUGS:
            vals.append(str(sum(1 for x in links if x.strip('/').casefold()==t.casefold())))
        print('| '+s+' | '+' | '.join(vals)+' |')

    print('\n## Outgoing internal links within cluster')
    for s,r in rows.items():
        links=[x.strip('/') for x in HREF_RE.findall(raw(r,'content'))]
        counts={t:links.count(t) for t in SLUGS if links.count(t)}
        print(f'- {s}: {counts}')

    print('\n## Suggested high-value relationships')
    desired={
      'lexus-lbx-price':['lexus-lbx-interior','lexus-lbx-options','lexus-lbx-cheap','lexus-lbx-regret','lexus-ux-vs-lbx'],
      'lexus-lbx-interior':['lexus-lbx-price','lexus-lbx-options'],
      'lexus-lbx-options':['lexus-lbx-price','lexus-lbx-interior','lexus-lbx-cheap'],
      'lexus-lbx-cheap':['lexus-lbx-price','lexus-lbx-options'],
      'lexus-lbx-regret':['lexus-lbx-price','lexus-lbx-interior','lexus-ux-vs-lbx'],
      'lexus-ux-vs-lbx':['lexus-lbx-price','lexus-lbx-regret'],
    }
    for s,targets in desired.items():
        links=[x.strip('/') for x in HREF_RE.findall(raw(rows[s],'content'))]
        missing=[t for t in targets if t not in links]
        print(f'- {s}: missing={missing}')

    _,h=req(f"{SITE}/wp-json/wp/v2/posts?{urllib.parse.urlencode({'status':'publish','per_page':1,'_fields':'id'})}")
    print(f'\n- published_posts: **{h.get("X-WP-Total","?")}**')

if __name__=='__main__': main()
