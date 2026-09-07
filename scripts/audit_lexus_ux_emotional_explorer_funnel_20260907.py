#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, os, re, urllib.request
SITE='https://tsurikue.com'; POST_ID=3570
UA='tsurikue-audit-lexus-ux-emotional-explorer-20260907/1.0'
GULLIVER='[blog_parts id="2843"]'; CTN_BANNER='[blog_parts id="2846"]'; CTN_BUTTON='[blog_parts id="2184"]'
KEYS=('Emotional Explorer','エモーショナル','特別仕様','中古','200万円','300万円','価格','買う','購入','売却','査定','今の車','乗り換え','まとめ','ガリバー','CTN')
def auth():
    raw=f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode(); return 'Basic '+base64.b64encode(raw).decode()
def get():
    req=urllib.request.Request(f'{SITE}/wp-json/wp/v2/posts/{POST_ID}?context=edit',headers={'Authorization':auth(),'Accept':'application/json','User-Agent':UA})
    with urllib.request.urlopen(req,timeout=60) as r:return json.loads(r.read().decode())
def raw(row,key):
    v=row.get(key) or {}; return (v.get('raw') or v.get('rendered') or '') if isinstance(v,dict) else str(v)
TOKEN=re.compile(r'<!--\s+/?wp:[\s\S]*?-->'); OPEN=re.compile(r'<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->'); CLOSE=re.compile(r'<!--\s+/wp:([\w\-/]+)\s+-->')
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
def textify(s):
    s=re.sub(r'<!--.*?-->',' ',s,flags=re.S); s=re.sub(r'<br\s*/?>',' ',s,flags=re.I); s=re.sub(r'<[^>]+>',' ',s); s=html.unescape(s)
    return re.sub(r'\s+',' ',s).strip()
def blocks(c):
    out=[]
    pats=[('H',r'<!--\s+wp:heading(?:\s+\{.*?\})?\s*-->([\s\S]*?)<!--\s+/wp:heading\s+-->'),('P',r'<!--\s+wp:paragraph(?:\s+\{.*?\})?\s*-->([\s\S]*?)<!--\s+/wp:paragraph\s+-->'),('SHORT',r'<!--\s+wp:shortcode\s*-->([\s\S]*?)<!--\s+/wp:shortcode\s+-->')]
    spans=[]
    for kind,pat in pats:
        for m in re.finditer(pat,c):spans.append((m.start(),kind,textify(m.group(1))))
    for _,kind,t in sorted(spans):
        if t:out.append((kind,t))
    return out
def main():
    row=get(); c=raw(row,'content'); bs=blocks(c)
    print('# lexus-ux-emotional-explorer funnel audit (GET only)')
    print('- wordpress_write_count: **0**')
    print(f"- post_id: **{row['id']}** / slug: **{row['slug']}** / status: **{row['status']}** / featured_media: **{row['featured_media']}**")
    print(f"- title: {raw(row,'title')}")
    print(f"- content_sha256: `{hashlib.sha256(c.encode()).hexdigest()}` / chars: **{len(c)}**")
    print(f'- Gutenberg problems: **{problems(c)}**')
    print(f'- Gulliver: **{c.count(GULLIVER)}** / CTN banner: **{c.count(CTN_BANNER)}** / CTN button: **{c.count(CTN_BUTTON)}** / CTN text: **{c.count("CTN")}**')
    print('## Relevant vicinity')
    idxs=[i for i,(_,t) in enumerate(bs) if any(k in t for k in KEYS)]
    shown=set()
    for i in idxs:
        for j in range(max(0,i-1),min(len(bs),i+2)):
            if j in shown: continue
            shown.add(j); kind,t=bs[j]
            print(f'- **{kind}** {t[:700]}')
        print('- ---')
    print('## Last 35 readable blocks')
    for kind,t in bs[-35:]: print(f'- **{kind}** {t[:700]}')
if __name__=='__main__': main()
