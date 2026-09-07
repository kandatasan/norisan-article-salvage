#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, os, re, urllib.request
SITE='https://tsurikue.com'; POST_ID=2886; UA='tsurikue-audit-lexus-ux-size-20260907/1.0'
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
def strip_tags(s):
    s=re.sub(r'<!--.*?-->',' ',s,flags=re.S); s=re.sub(r'<[^>]+>',' ',s); return re.sub(r'\s+',' ',html.unescape(s)).strip()
def blocks(c):
    out=[]
    pat=re.compile(r'<!--\s+wp:(heading|paragraph|shortcode)(?:\s+\{.*?\})?\s*-->([\s\S]*?)<!--\s+/wp:\1\s+-->')
    for m in pat.finditer(c):
        typ=m.group(1); body=m.group(2)
        if typ=='shortcode': txt=strip_tags(body); kind='SHORT'
        elif typ=='heading': txt=strip_tags(body); kind='H'
        else: txt=strip_tags(body); kind='P'
        if txt: out.append((kind,txt))
    return out
def main():
    row=get(); c=raw(row,'content'); b=blocks(c)
    print('# lexus-ux-size funnel audit (GET only)')
    print('- wordpress_write_count: **0**')
    print(f"- post_id: **{row['id']}** / slug: **{row['slug']}** / status: **{row['status']}** / featured_media: **{row['featured_media']}**")
    print(f"- title: {raw(row,'title')}")
    print(f"- content_sha256: `{hashlib.sha256(c.encode()).hexdigest()}` / chars: **{len(c)}**")
    print(f"- Gutenberg problems: **{problems(c)}**")
    print(f"- Gulliver: **{c.count(GULLIVER)}** / CTN banner: **{c.count(CTN_BANNER)}** / CTN button: **{c.count(CTN_BUTTON)}** / CTN text: **{c.count('CTN')}**")
    keys=('サイズ','全長','全幅','車幅','駐車','取り回し','運転','買う','購入','中古','ガリバー','査定','売る','売却','乗り換え','まとめ')
    idx=[]
    for i,(k,t) in enumerate(b):
        if any(x in t for x in keys): idx.extend(range(max(0,i-1),min(len(b),i+2)))
    seen=[]
    for i in idx:
        if i not in seen: seen.append(i)
    print('## Relevant vicinity')
    for i in seen[:100]:
        k,t=b[i]; print(f'- **{k}** {t}')
    print('## Last 35 readable blocks')
    for k,t in b[-35:]: print(f'- **{k}** {t}')
if __name__=='__main__': main()
