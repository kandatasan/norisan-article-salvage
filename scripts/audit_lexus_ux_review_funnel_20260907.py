#!/usr/bin/env python3
import base64, hashlib, json, os, re, urllib.request
SITE='https://tsurikue.com'; POST_ID=2870
UA='tsurikue-audit-lexus-ux-review-20260907/1.0'
GULLIVER='[blog_parts id="2843"]'; CTN_BANNER='[blog_parts id="2846"]'; CTN_BUTTON='[blog_parts id="2184"]'
TOKEN=re.compile(r'<!--\s+/?wp:[\s\S]*?-->'); OPEN=re.compile(r'<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->'); CLOSE=re.compile(r'<!--\s+/wp:([\w\-/]+)\s+-->')
BLOCK=re.compile(r'<!--\s+wp:(paragraph|heading|shortcode)(?:\s+\{.*?\})?\s*-->([\s\S]*?)<!--\s+/wp:\1\s+-->')
TAG=re.compile(r'<[^>]+>')
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
    for m in BLOCK.finditer(text):
        kind=m.group(1); body=m.group(2).strip()
        if kind=='shortcode': s=' '.join(body.split())
        else:
            s=TAG.sub(' ',body); s=re.sub(r'\s+',' ',s).strip()
        if s: out.append((kind,s))
    return out
def main():
    row=get(); c=raw(row,'content'); blocks=readable(c)
    print('# lexus-ux-review funnel audit (GET only)')
    print('- wordpress_write_count: **0**')
    print(f"- post_id: **{row['id']}** / slug: **{row['slug']}** / status: **{row['status']}** / featured_media: **{row['featured_media']}**")
    print(f"- title: {raw(row,'title')}")
    print(f"- content_sha256: `{hashlib.sha256(c.encode()).hexdigest()}` / chars: **{len(c)}**")
    print(f"- Gutenberg problems: **{problems(c)}**")
    print(f"- Gulliver: **{c.count(GULLIVER)}** / CTN banner: **{c.count(CTN_BANNER)}** / CTN button: **{c.count(CTN_BUTTON)}** / CTN text: **{c.count('CTN')}**")
    keys=('中古','予算','価格','値引','見積','下取り','査定','売る','売却','乗り換え','買う','購入','リセール','総額')
    idx=[i for i,(_,s) in enumerate(blocks) if any(k in s for k in keys) or GULLIVER in s or CTN_BUTTON in s or CTN_BANNER in s]
    show=set()
    for i in idx:
        for j in range(max(0,i-2),min(len(blocks),i+3)):show.add(j)
    print('## Relevant vicinity')
    for i in sorted(show):
        kind,s=blocks[i]; label={'paragraph':'P','heading':'H','shortcode':'SHORT'}[kind]
        print(f'- **{label}** {s}')
    print('## Last 35 readable blocks')
    for kind,s in blocks[-35:]:
        label={'paragraph':'P','heading':'H','shortcode':'SHORT'}[kind]
        print(f'- **{label}** {s}')
if __name__=='__main__':main()
