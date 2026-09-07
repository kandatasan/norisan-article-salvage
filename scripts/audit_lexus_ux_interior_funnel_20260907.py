#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, os, re, urllib.request
SITE='https://tsurikue.com'; POST_ID=2897; UA='tsurikue-audit-lexus-ux-interior-20260907/1.0'
GULLIVER='[blog_parts id="2843"]'; CTN_BANNER='[blog_parts id="2846"]'; CTN_BUTTON='[blog_parts id="2184"]'
TOKEN=re.compile(r'<!--\s+/?wp:[\s\S]*?-->'); OPEN=re.compile(r'<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->'); CLOSE=re.compile(r'<!--\s+/wp:([\w\-/]+)\s+-->')
def auth():
    raw=f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode(); return 'Basic '+base64.b64encode(raw).decode()
def get():
    req=urllib.request.Request(f'{SITE}/wp-json/wp/v2/posts/{POST_ID}?context=edit',headers={'Authorization':auth(),'Accept':'application/json','User-Agent':UA})
    with urllib.request.urlopen(req,timeout=60) as r:return json.loads(r.read().decode())
def raw(row,key):
    v=row.get(key) or {}; return (v.get('raw') or v.get('rendered') or '') if isinstance(v,dict) else str(v)
def problems(text):
    stack=[]
    for m in TOKEN.finditer(text):
        t=m.group(0);o=OPEN.fullmatch(t);c=CLOSE.fullmatch(t)
        if o:
            if not o.group(2):stack.append(o.group(1))
        elif c:
            if not stack or stack[-1]!=c.group(1):return 1
            stack.pop()
    return len(stack)
def clean(s):
    s=re.sub(r'<!--.*?-->',' ',s,flags=re.S); s=re.sub(r'<[^>]+>',' ',s); return re.sub(r'\s+',' ',s).strip()
def blocks(c):
    pat=re.compile(r'<!-- wp:(heading|paragraph|shortcode)[^>]*-->(.*?)<!-- /wp:\1 -->',re.S)
    out=[]
    for typ,b in pat.findall(c):
        txt=clean(b)
        if txt: out.append(('H' if typ=='heading' else 'P' if typ=='paragraph' else 'SHORT',txt))
    return out
def main():
    row=get(); c=raw(row,'content'); b=blocks(c)
    print('# lexus-ux-interior funnel audit (GET only)')
    print('- wordpress_write_count: **0**')
    print(f"- post_id: **{row['id']}** / slug: **{row['slug']}** / status: **{row['status']}** / featured_media: **{row['featured_media']}**")
    print(f"- title: {raw(row,'title')}")
    print(f"- content_sha256: `{hashlib.sha256(c.encode()).hexdigest()}` / chars: **{len(c)}**")
    print(f"- Gutenberg problems: **{problems(c)}**")
    print(f"- Gulliver: **{c.count(GULLIVER)}** / CTN banner: **{c.count(CTN_BANNER)}** / CTN button: **{c.count(CTN_BUTTON)}** / CTN text: **{c.count('CTN')}**")
    kws=('内装','高級','前期','後期','300h','中古','ガリバー','CTN','乗り換','売','査定','まとめ','後席','質感')
    print('## Relevant vicinity')
    for i,(t,x) in enumerate(b):
        if any(k in x for k in kws):
            lo=max(0,i-1); hi=min(len(b),i+2)
            for tt,xx in b[lo:hi]: print(f'- **{tt}** {xx[:650]}')
            print('- ---')
    print('## Last 35 readable blocks')
    for t,x in b[-35:]: print(f'- **{t}** {x[:650]}')
if __name__=='__main__': main()
