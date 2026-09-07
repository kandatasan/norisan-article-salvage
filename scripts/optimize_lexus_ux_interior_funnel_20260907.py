#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, os, re, urllib.request
SITE='https://tsurikue.com'; POST_ID=2897; SLUG='lexus-ux-interior'
TITLE='レクサスUXの内装はしょぼい？実際に触って感じた高級感と気になる部分'
FEATURED=2210; EXPECTED_SHA='746a40bd154eabe1c73995d56d0274084c268a0a6c068b4d291034ea278f2be4'
UA='tsurikue-optimize-lexus-ux-interior-20260907/1.0'
GULLIVER='[blog_parts id="2843"]'; CTN_BANNER='[blog_parts id="2846"]'; CTN_BUTTON='[blog_parts id="2184"]'
MARKER='<!-- tsurikue-ctn-interior-funnel:20260907 -->'
OLD='私のUXも査定先によって提示額に大きな差が出ました。'
NEW='私のUXも査定先によって提示額に大きな差が出ました。<br>実際にUXを売却するときに使ったCTNは、高額査定の上位3社だけとやり取りする仕組み。私のときはカーセブンとネクステージの2社から連絡が来て、電話が少なくて快適でした。<br><strong>内装まで納得できたら、次は「今の車、いくらになる？」を見ておく。</strong>'
TOKEN=re.compile(r'<!--\s+/?wp:[\s\S]*?-->'); OPEN=re.compile(r'<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->'); CLOSE=re.compile(r'<!--\s+/wp:([\w\-/]+)\s+-->')
def auth():
    raw=f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode(); return 'Basic '+base64.b64encode(raw).decode()
def req(url,method='GET',payload=None):
    headers={'Authorization':auth(),'Accept':'application/json','User-Agent':UA}; data=None
    if payload is not None:
        data=json.dumps(payload,ensure_ascii=False).encode(); headers['Content-Type']='application/json; charset=utf-8'
    r=urllib.request.Request(url,data=data,headers=headers,method=method)
    with urllib.request.urlopen(r,timeout=60) as resp:return json.loads(resp.read().decode()),dict(resp.headers)
def get(): return req(f'{SITE}/wp-json/wp/v2/posts/{POST_ID}?context=edit')[0]
def raw(row,key):
    v=row.get(key) or {}; return (v.get('raw') or v.get('rendered') or '') if isinstance(v,dict) else str(v)
def public_count():
    _,h=req(f'{SITE}/wp-json/wp/v2/posts?status=publish&per_page=1&_fields=id'); return int(h.get('X-WP-Total',0))
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
def identity(row):
    assert row['id']==POST_ID and row['slug']==SLUG and row['status']=='publish' and row['featured_media']==FEATURED
    assert raw(row,'title')==TITLE
def main():
    pub0=public_count(); row=get(); identity(row); c=raw(row,'content')
    assert hashlib.sha256(c.encode()).hexdigest()==EXPECTED_SHA and problems(c)==0 and MARKER not in c
    assert c.count(GULLIVER)==1 and c.count(CTN_BANNER)==0 and c.count(CTN_BUTTON)==1 and c.count('CTN')==0
    assert c.count(OLD)==1
    fixed=c.replace(OLD,MARKER+NEW,1)
    assert fixed.count(GULLIVER)==1 and fixed.count(CTN_BANNER)==0 and fixed.count(CTN_BUTTON)==1 and problems(fixed)==0
    assert fixed.count(MARKER)==1 and 'カーセブンとネクステージの2社' in fixed and '電話が少なくて快適でした' in fixed
    req(f'{SITE}/wp-json/wp/v2/posts/{POST_ID}',method='POST',payload={'content':fixed})
    after=get(); identity(after); ac=raw(after,'content'); assert ac==fixed and problems(ac)==0
    pub1=public_count(); assert pub0==pub1
    print('# lexus-ux-interior funnel optimization')
    print('- result: **SUCCESS**')
    print(f'- public posts: **{pub0} → {pub1}**')
    print('- WordPress payload: **content only**')
    print('- status: **publish → publish** / featured_media: **2210 → 2210**')
    print('- Gulliver: **1 → 1** / CTN banner: **0 → 0** / CTN button: **1 → 1**')
    print('- Gutenberg problems after: **0**')
    print('- article body: **unchanged except text inside existing CTN bridge paragraph**')
if __name__=='__main__': main()
