#!/usr/bin/env python3
from __future__ import annotations
import base64, json, os, re, urllib.parse, urllib.request

SITE='https://tsurikue.com'
UA='tsurikue-live-lbx-links-state-20260928/1.0'
SLUGS=['lexus-lbx-price','lexus-lbx-interior','lexus-lbx-options','lexus-lbx-cheap','lexus-lbx-regret','lexus-ux-vs-lbx']
SHORTCODE_RE=re.compile(r'\[blog_parts\s+id=["\']?(\d+)["\']?\]',re.I)

def auth():
    u=os.environ.get('TSURIKUE_WP_USER'); p=os.environ.get('TSURIKUE_WP_APP_PASSWORD')
    if not u or not p: raise SystemExit('BLOCKED_MISSING_SECRETS')
    return 'Basic '+base64.b64encode(f'{u}:{p}'.encode()).decode()

def req(url):
    r=urllib.request.Request(url,headers={'Authorization':auth(),'Accept':'application/json','User-Agent':UA})
    with urllib.request.urlopen(r,timeout=60) as resp:
        return json.loads(resp.read().decode()),dict(resp.headers)

def raw(r,key):
    v=r.get(key) or {}
    return (v.get('raw') or v.get('rendered') or '') if isinstance(v,dict) else str(v)

def get(slug):
    q=urllib.parse.urlencode({'context':'edit','slug':slug,'status':'any','per_page':10,'_fields':'id,slug,status,title,content,featured_media,categories,tags'})
    rows,_=req(f'{SITE}/wp-json/wp/v2/posts?{q}')
    if len(rows)!=1: raise RuntimeError((slug,len(rows)))
    return rows[0]

def main():
    print('# Live LBX internal-link state (GET only)')
    print('- wordpress_write_count: **0**')
    rows={s:get(s) for s in SLUGS}
    for s,r in rows.items():
        c=raw(r,'content')
        targets=[t for t in SLUGS if t!=s and f'https://tsurikue.com/{t}/' in c]
        print(f"- {s}: id={r['id']} status={r['status']} cluster_targets={targets} affiliate={SHORTCODE_RE.findall(c)}")
        if s in ['lexus-lbx-options','lexus-lbx-regret','lexus-ux-vs-lbx']:
            start=f'<!-- tq-lexus-related-cards:v1:{s} -->'
            end='<!-- tq-lexus-related-cards:v1:end -->'
            i=c.find(start); j=c.find(end,i)
            if i>=0 and j>=0:
                block=c[i:j+len(end)]
                urls=re.findall(r'https://tsurikue\.com/([^/\s"<]+?)/',block)
                print(f"  related_cards={urls}")
            else:
                print('  related_cards=MARKER_MISSING')
    _,h=req(f"{SITE}/wp-json/wp/v2/posts?{urllib.parse.urlencode({'status':'publish','per_page':1,'_fields':'id'})}")
    print(f'- published_posts: **{h.get("X-WP-Total","?")}**')

if __name__=='__main__': main()
