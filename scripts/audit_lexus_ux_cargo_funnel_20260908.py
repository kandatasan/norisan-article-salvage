#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, os, re, urllib.request
SITE='https://tsurikue.com'; POST_ID=2907; SLUG='lexus-ux-cargo'
UA='tsurikue-audit-lexus-ux-cargo-20260908/1.0'
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
def readable(c):
    out=[]
    for m in re.finditer(r'<!--\s+wp:(heading|paragraph|shortcode)[\s\S]*?<!--\s+/wp:\1\s+-->',c):
        b=m.group(0)
        if 'wp:heading' in b: typ='H'
        elif 'wp:shortcode' in b: typ='SHORT'
        else: typ='P'
        txt=re.sub(r'<[^>]+>',' ',b); txt=re.sub(r'<!--.*?-->',' ',txt,flags=re.S); txt=re.sub(r'\s+',' ',txt).strip()
        out.append((typ,txt))
    return out
def main():
    row=get(); c=raw(row,'content')
    assert row['id']==POST_ID and row['slug']==SLUG and row['status']=='publish'
    blocks=readable(c)
    print('# lexus-ux-cargo funnel audit (GET only)')
    print('- wordpress_write_count: **0**')
    print(f'- post_id: **{POST_ID}** / slug: **{row["slug"]}** / status: **{row["status"]}** / featured_media: **{row["featured_media"]}**')
    print(f'- title: {raw(row,"title")}')
    print(f'- content_sha256: `{hashlib.sha256(c.encode()).hexdigest()}` / chars: **{len(c)}**')
    print(f'- Gutenberg problems: **{problems(c)}**')
    print(f'- Gulliver: **{c.count(GULLIVER)}** / CTN banner: **{c.count(CTN_BANNER)}** / CTN button: **{c.count(CTN_BUTTON)}** / CTN text: **{c.count("CTN")}**')
    keys=('荷室','ラゲッジ','ゴルフ','スーツケース','旅行','中古','ガリバー','乗り換え','売却','査定','予算','まとめ','結論')
    print('## Relevant vicinity')
    for i,(typ,txt) in enumerate(blocks):
        if any(k in txt for k in keys):
            for j in range(max(0,i-2),min(len(blocks),i+3)):
                t,x=blocks[j]; print(f'- **{t}** {x}')
            print('- ---')
    print('## Last 35 readable blocks')
    for typ,txt in blocks[-35:]: print(f'- **{typ}** {txt}')
if __name__=='__main__': main()
