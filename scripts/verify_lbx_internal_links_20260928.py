#!/usr/bin/env python3
from __future__ import annotations
import base64, json, os, re, urllib.parse, urllib.request

SITE='https://tsurikue.com'
UA='tsurikue-verify-lbx-links-20260928/1.0'
SLUGS=['lexus-lbx-price','lexus-lbx-interior','lexus-lbx-options','lexus-lbx-cheap','lexus-lbx-regret','lexus-ux-vs-lbx']
URL_RE=re.compile(r'https://tsurikue\.com/([^/"?#]+?)/')
SHORTCODE_RE=re.compile(r'\[blog_parts\s+id=["\']?(\d+)["\']?\]',re.I)
EXPECTED_AFF={
 'lexus-lbx-price':['2184'],
 'lexus-lbx-interior':[],
 'lexus-lbx-options':['2184','2843','2846'],
 'lexus-lbx-cheap':['2846','2843'],
 'lexus-lbx-regret':['2184','2843','2846'],
 'lexus-ux-vs-lbx':['2184','2843','2846'],
}
MUST={
 'lexus-lbx-price':['lexus-lbx-interior','lexus-lbx-options','lexus-lbx-cheap','lexus-lbx-regret','lexus-ux-vs-lbx'],
 'lexus-lbx-interior':['lexus-lbx-price','lexus-lbx-options'],
 'lexus-lbx-options':['lexus-lbx-price','lexus-lbx-interior','lexus-lbx-cheap'],
 'lexus-lbx-cheap':['lexus-lbx-price','lexus-lbx-options'],
 'lexus-lbx-regret':['lexus-lbx-price','lexus-lbx-interior','lexus-ux-vs-lbx'],
 'lexus-ux-vs-lbx':['lexus-lbx-price','lexus-lbx-regret'],
}

def auth():
    u=os.environ.get('TSURIKUE_WP_USER'); p=os.environ.get('TSURIKUE_WP_APP_PASSWORD')
    if not u or not p: raise SystemExit('BLOCKED_MISSING_SECRETS')
    return 'Basic '+base64.b64encode(f'{u}:{p}'.encode()).decode()

def req(url):
    r=urllib.request.Request(url,headers={'Authorization':auth(),'Accept':'application/json','User-Agent':UA})
    with urllib.request.urlopen(r,timeout=60) as resp:
        return json.loads(resp.read().decode()),dict(resp.headers)

def raw(row,key):
    v=row.get(key) or {}
    return (v.get('raw') or v.get('rendered') or '') if isinstance(v,dict) else str(v)

def get(slug):
    q=urllib.parse.urlencode({'context':'edit','slug':slug,'status':'any','per_page':10,'_fields':'id,slug,status,content'})
    rows,_=req(f'{SITE}/wp-json/wp/v2/posts?{q}')
    assert len(rows)==1
    return rows[0]

def main():
    rows={s:get(s) for s in SLUGS}
    for s,r in rows.items():
        assert r.get('status')=='publish'
        c=raw(r,'content')
        assert SHORTCODE_RE.findall(c)==EXPECTED_AFF[s], (s,SHORTCODE_RE.findall(c))
        for t in MUST[s]:
            assert f'https://tsurikue.com/{t}/' in c, (s,t)

    print('# Lexus LBX internal-link verification')
    print('- result: **SUCCESS**')
    print('- wordpress_write_count: **0**')
    print('- target posts: **6/6 publish**')
    print('- affiliate blocks: **unchanged**')
    print('\n## Verified routing')
    for s in SLUGS:
        c=raw(rows[s],'content')
        found=[t for t in SLUGS if t!=s and f'https://tsurikue.com/{t}/' in c]
        print(f'- {s}: {found}')
    q=urllib.parse.urlencode({'status':'publish','per_page':1,'_fields':'id'})
    _,h=req(f'{SITE}/wp-json/wp/v2/posts?{q}')
    print(f'\n- published_posts: **{h.get("X-WP-Total","?")}**')

if __name__=='__main__': main()
