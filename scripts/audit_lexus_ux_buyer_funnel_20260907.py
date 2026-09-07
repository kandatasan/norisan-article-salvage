#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, os, re, urllib.request
SITE='https://tsurikue.com'; POST_ID=2881; SLUG='lexus-ux-buyer'; UA='tsurikue-audit-lexus-ux-buyer-20260907/1.0'
CTN_BANNER='[blog_parts id="2846"]'; CTN_BUTTON='[blog_parts id="2184"]'; GULLIVER='[blog_parts id="2843"]'
TOKEN=re.compile(r'<!--\s+/?wp:[\s\S]*?-->'); OPEN=re.compile(r'<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->'); CLOSE=re.compile(r'<!--\s+/wp:([\w\-/]+)\s+-->')
BLOCK=re.compile(r'<!--\s+wp:(paragraph|heading|shortcode)(?:\s+\{.*?\})?\s*-->([\s\S]*?)<!--\s+/wp:\1\s+-->'); TAG=re.compile(r'<[^>]+>')
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
    s=s.replace('<br>',' / ').replace('<br/>',' / ').replace('<br />',' / '); return re.sub(r'\s+',' ',html.unescape(TAG.sub('',s))).strip()
def blocks(c):
    out=[]
    for m in BLOCK.finditer(c):
        kind=m.group(1);body=m.group(2).strip();text=body if kind=='shortcode' else clean(body)
        if text:out.append(('SHORT' if kind=='shortcode' else ('H' if kind=='heading' else 'P'),text))
    return out
def main():
    row=get(); c=raw(row,'content'); assert row['id']==POST_ID and row['slug']==SLUG and row['status']=='publish'
    print('# lexus-ux-buyer funnel audit (GET only)')
    print('- wordpress_write_count: **0**')
    print(f'- post_id: **{POST_ID}** / status: **{row["status"]}** / featured_media: **{row.get("featured_media")}**')
    print(f'- title: {raw(row,"title")}')
    print(f'- content_sha256: `{hashlib.sha256(c.encode()).hexdigest()}` / chars: **{len(c)}**')
    print(f'- Gutenberg problems: **{problems(c)}**')
    print(f'- Gulliver: **{c.count(GULLIVER)}** / CTN banner: **{c.count(CTN_BANNER)}** / CTN button: **{c.count(CTN_BUTTON)}** / CTN text: **{c.count("CTN")}**')
    b=blocks(c); needles=('2843','2846','2184','中古','買う','購入','価格','下取り','買取','売れる','相場','後悔','向いて')
    hits=[i for i,(_,t) in enumerate(b) if any(n in t for n in needles)]
    print('## CTA / buying vicinity')
    shown=set()
    for hit in hits:
        for i in range(max(0,hit-2),min(len(b),hit+3)):
            if i in shown:continue
            shown.add(i);label,text=b[i];print(f'- **{label}** {text}')
        print('-')
    print('## Last 30 readable blocks')
    for label,text in b[-30:]:print(f'- **{label}** {text}')
if __name__=='__main__':main()
