#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, os, re, urllib.request
SITE='https://tsurikue.com'; POST_ID=2902; SLUG='lexus-ux-rear-seat'; UA='tsurikue-audit-rear-seat-20260907/1.0'
GULLIVER='[blog_parts id="2843"]'; CTN_BANNER='[blog_parts id="2846"]'; CTN_BUTTON='[blog_parts id="2184"]'
TOKEN=re.compile(r'<!--\s+/?wp:[\s\S]*?-->'); OPEN=re.compile(r'<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->'); CLOSE=re.compile(r'<!--\s+/wp:([\w\-/]+)\s+-->')
def auth():
    raw=f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode(); return 'Basic '+base64.b64encode(raw).decode()
def req(url):
    r=urllib.request.Request(url,headers={'Authorization':auth(),'Accept':'application/json','User-Agent':UA})
    with urllib.request.urlopen(r,timeout=60) as resp:return json.loads(resp.read().decode())
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
    for m in re.finditer(r'<!-- wp:(heading|paragraph|shortcode)[\s\S]*?<!-- /wp:\1 -->',c):
        b=m.group(0); kind=m.group(1)
        if kind=='shortcode':
            text=re.sub(r'<!--[\s\S]*?-->','',b).strip(); out.append(('SHORT',text)); continue
        text=re.sub(r'<!--[\s\S]*?-->','',b); text=re.sub(r'<br\s*/?>',' ',text); text=re.sub(r'<[^>]+>',' ',text); text=re.sub(r'\s+',' ',text).strip()
        out.append(('H' if kind=='heading' else 'P',text))
    return out
def main():
    row=req(f'{SITE}/wp-json/wp/v2/posts/{POST_ID}?context=edit'); c=raw(row,'content')
    assert row['id']==POST_ID and row['slug']==SLUG and row['status']=='publish'
    blocks=readable(c); keys=('後席','後部座席','大人','4人','家族','中古','ガリバー','乗り換','査定','売れ','CTN','まとめ')
    rel=[(k,t) for k,t in blocks if any(x in t for x in keys) or (k=='SHORT' and any(x in t for x in ('2843','2846','2184')))]
    print('# lexus-ux-rear-seat funnel audit (GET only)')
    print('- wordpress_write_count: **0**')
    print(f"- post_id: **{row['id']}** / slug: **{row['slug']}** / status: **{row['status']}** / featured_media: **{row['featured_media']}**")
    print(f"- title: {raw(row,'title')}")
    print(f"- content_sha256: `{hashlib.sha256(c.encode()).hexdigest()}` / chars: **{len(c)}**")
    print(f"- Gutenberg problems: **{problems(c)}**")
    print(f"- Gulliver: **{c.count(GULLIVER)}** / CTN banner: **{c.count(CTN_BANNER)}** / CTN button: **{c.count(CTN_BUTTON)}** / CTN text: **{c.count('CTN')}**")
    print('## Relevant vicinity')
    for k,t in rel[:90]: print(f'- **{k}** {t}')
    print('## Last 35 readable blocks')
    for k,t in blocks[-35:]: print(f'- **{k}** {t}')
if __name__=='__main__': main()
