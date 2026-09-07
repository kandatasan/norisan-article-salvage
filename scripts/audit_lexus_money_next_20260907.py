#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, os, re, urllib.request
SITE='https://tsurikue.com'; UA='tsurikue-audit-lexus-money-next-20260907/1.0'
TARGETS=[
    (2962,'lexus-ux-discount','レクサスUXは値引きできる？値引き0円だった実体験と安く買う方法'),
    (2240,'ux-mitsumori','レクサスUXの見積もり公開｜総額616万円で選んだ特別仕様車とオプション'),
]
CTN_BANNER='[blog_parts id="2846"]'; CTN_BUTTON='[blog_parts id="2184"]'; GULLIVER='[blog_parts id="2843"]'
TOKEN=re.compile(r'<!--\s+/?wp:[\s\S]*?-->'); OPEN=re.compile(r'<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->'); CLOSE=re.compile(r'<!--\s+/wp:([\w\-/]+)\s+-->')
BLOCK=re.compile(r'<!--\s+wp:(paragraph|heading|shortcode)(?:\s+\{.*?\})?\s*-->([\s\S]*?)<!--\s+/wp:\1\s+-->'); TAG=re.compile(r'<[^>]+>')
def auth():
    raw=f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode(); return 'Basic '+base64.b64encode(raw).decode()
def get(pid):
    req=urllib.request.Request(f'{SITE}/wp-json/wp/v2/posts/{pid}?context=edit',headers={'Authorization':auth(),'Accept':'application/json','User-Agent':UA})
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
def emit(pid,slug,title):
    row=get(pid);c=raw(row,'content'); assert row['id']==pid and row['slug']==slug and row['status']=='publish' and raw(row,'title')==title
    print(f'## {slug}')
    print(f'- post_id: **{pid}** / status: **publish** / featured_media: **{row.get("featured_media")}**')
    print(f'- content_sha256: `{hashlib.sha256(c.encode()).hexdigest()}` / chars: **{len(c)}**')
    print(f'- Gutenberg problems: **{problems(c)}** / image blocks: **{len(re.findall(r"<!--\\s+wp:image\\b",c))}**')
    print(f'- Gulliver: **{c.count(GULLIVER)}** / CTN banner: **{c.count(CTN_BANNER)}** / CTN button: **{c.count(CTN_BUTTON)}** / CTN text: **{c.count("CTN")}**')
    b=blocks(c); needles=('CTN','2846','2184','2843','50万円','75万円','25万円','427万円','値引き','高く売','電話','上位3社')
    hits=[i for i,(_,t) in enumerate(b) if any(n in t for n in needles)]
    print('### CTA vicinity')
    shown=set()
    for hit in hits:
        for i in range(max(0,hit-2),min(len(b),hit+3)):
            if i in shown:continue
            shown.add(i);label,text=b[i];print(f'- **{label}** {text}')
    print('### Last 22 readable blocks')
    for label,text in b[-22:]:print(f'- **{label}** {text}')
    print()
def main():
    print('# Lexus money articles audit (GET only)');print('- wordpress_write_count: **0**');print()
    for t in TARGETS:emit(*t)
if __name__=='__main__':main()
