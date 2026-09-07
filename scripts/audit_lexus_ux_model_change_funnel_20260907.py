#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, os, re, urllib.request
SITE='https://tsurikue.com'; POST_ID=2975; UA='tsurikue-audit-lexus-ux-model-change-20260907/1.0'
GULLIVER='[blog_parts id="2843"]'; CTN_BANNER='[blog_parts id="2846"]'; CTN_BUTTON='[blog_parts id="2184"]'
TOKEN=re.compile(r'<!--\s+/?wp:[\s\S]*?-->'); OPEN=re.compile(r'<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->'); CLOSE=re.compile(r'<!--\s+/wp:([\w\-/]+)\s+-->')
BLOCK=re.compile(r'<!--\s+wp:(paragraph|heading|shortcode)(?:\s+\{.*?\})?\s*-->([\s\S]*?)<!--\s+/wp:\1\s+-->')
TAG=re.compile(r'<[^>]+>'); WS=re.compile(r'\s+')
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
def readable(text):
    out=[]
    for kind,body in BLOCK.findall(text):
        txt=WS.sub(' ',TAG.sub(' ',body)).strip()
        if not txt: continue
        label='H' if kind=='heading' else ('SHORT' if kind=='shortcode' else 'P')
        out.append((label,txt))
    return out
def main():
    row=get(); c=raw(row,'content'); blocks=readable(c)
    print('# lexus-ux-model-change funnel audit (GET only)')
    print('- wordpress_write_count: **0**')
    print(f"- post_id: **{row['id']}** / slug: **{row['slug']}** / status: **{row['status']}** / featured_media: **{row['featured_media']}**")
    print(f"- title: {raw(row,'title')}")
    print(f"- content_sha256: `{hashlib.sha256(c.encode()).hexdigest()}` / chars: **{len(c)}**")
    print(f"- Gutenberg problems: **{problems(c)}**")
    print(f"- Gulliver: **{c.count(GULLIVER)}** / CTN banner: **{c.count(CTN_BANNER)}** / CTN button: **{c.count(CTN_BUTTON)}** / CTN text: **{c.count('CTN')}**")
    kws=('モデルチェンジ','フルモデルチェンジ','待つ','買う','購入','中古','250h','300h','査定','売る','売却','下取り','予算','ガリバー','CTN','まとめ')
    print('## Relevant vicinity')
    for i,(label,txt) in enumerate(blocks):
        if any(k in txt for k in kws):
            lo=max(0,i-1); hi=min(len(blocks),i+2)
            for l,t in blocks[lo:hi]: print(f'- **{l}** {t[:500]}')
            print('- ---')
    print('## Last 35 readable blocks')
    for l,t in blocks[-35:]: print(f'- **{l}** {t[:500]}')
if __name__=='__main__': main()
