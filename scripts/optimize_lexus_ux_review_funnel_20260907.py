#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, os, re, urllib.request
SITE='https://tsurikue.com'; POST_ID=2870; SLUG='lexus-ux-review'
TITLE='レクサスUXの評価・感想は？1万km以上乗った元オーナーが本音レビュー'
FEATURED=2231; EXPECTED_SHA='7b5d77b5a892f5eb202b6d14018fab1e23bdd8d8f6531ec86800d46f3942eb6f'
UA='tsurikue-optimize-lexus-ux-review-20260907/1.0'
GULLIVER='[blog_parts id="2843"]'; CTN_BANNER='[blog_parts id="2846"]'; CTN_BUTTON='[blog_parts id="2184"]'
MARKER='<!-- tsurikue-ctn-review-funnel:20260907 -->'
SHORT='''<!-- wp:shortcode -->\n[blog_parts id="2846"]\n<!-- /wp:shortcode -->'''
INSERT='''<!-- tsurikue-ctn-review-funnel:20260907 -->\n<!-- wp:paragraph -->\n<p>実際にUXを売却するときに使ったCTNは、やり取りするのが高額査定の上位3社だけ。<br><strong>私のときは2社から連絡が来て、電話が少なくて快適でした。</strong></p>\n<!-- /wp:paragraph -->\n\n'''
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
    assert c.count(GULLIVER)==1 and c.count(CTN_BANNER)==1 and c.count(CTN_BUTTON)==1 and c.count('CTN')==0
    assert c.count(SHORT)==1
    fixed=c.replace(SHORT,INSERT+SHORT,1)
    assert fixed.count(GULLIVER)==1 and fixed.count(CTN_BANNER)==1 and fixed.count(CTN_BUTTON)==1 and problems(fixed)==0
    assert fixed.count(MARKER)==1 and '私のときは2社から連絡が来て、電話が少なくて快適でした' in fixed
    req(f'{SITE}/wp-json/wp/v2/posts/{POST_ID}',method='POST',payload={'content':fixed})
    after=get(); identity(after); ac=raw(after,'content'); assert ac==fixed and problems(ac)==0
    pub1=public_count(); assert pub0==pub1
    print('# lexus-ux-review funnel optimization')
    print('- result: **SUCCESS**')
    print(f'- public posts: **{pub0} → {pub1}**')
    print('- WordPress payload: **content only**')
    print('- status: **publish → publish** / featured_media: **2231 → 2231**')
    print('- Gulliver: **1 → 1** / CTN banner: **1 → 1** / CTN button: **1 → 1**')
    print('- Gutenberg problems after: **0**')
    print('- article body: **unchanged except one compact CTN experience paragraph immediately before existing CTN banner**')
if __name__=='__main__':main()
