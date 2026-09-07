#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, os, re, urllib.request
SITE='https://tsurikue.com'; POST_ID=3570; SLUG='lexus-ux-emotional-explorer'
TITLE='レクサスUXの特別仕様車エモーショナルエクスプローラーはお得？実際に選んだ理由'
FEATURED=2223; EXPECTED_SHA='9814d016b4ba613495fd7f22f35c8c9589031abe0a082e7a665492d919b1ca15'
UA='tsurikue-optimize-emotional-explorer-20260907/1.0'
GULLIVER='[blog_parts id="2843"]'; CTN_BANNER='[blog_parts id="2846"]'; CTN_BUTTON='[blog_parts id="2184"]'
MARKER='<!-- tsurikue-ctn-emotional-explorer-funnel:20260907 -->'
ANCHOR='今すぐ買うと決めていなくても、まず候補があるか見てから考える。<br>台数が限られる特別仕様車なら、そのくらいから始めてもいいと思います。'
INSERT='''\n<!-- tsurikue-ctn-emotional-explorer-funnel:20260907 -->\n<!-- wp:paragraph -->\n<p>Emotional Explorerのように条件の合う1台を探す中古車は、<strong>買う車の価格だけでなく、今の車がいくらで売れるか</strong>も乗り換え予算に効きます。<br>私がUXを売却するときに使ったCTNは、最大15社で査定し、やり取りするのは高額査定の上位3社だけ。実際に私へ連絡が来たのはカーセブンとネクステージの2社で、電話が少なくて快適でした。</p>\n<!-- /wp:paragraph -->\n<!-- wp:shortcode -->\n[blog_parts id="2846"]\n<!-- /wp:shortcode -->\n<!-- wp:paragraph -->\n<p><strong>欲しい1台が見つかったときに動けるよう、今の車の値段も見ておく。</strong></p>\n<!-- /wp:paragraph -->\n<!-- wp:shortcode -->\n[blog_parts id="2184"]\n<!-- /wp:shortcode -->'''
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
    assert c.count(GULLIVER)==1 and c.count(CTN_BANNER)==0 and c.count(CTN_BUTTON)==0 and c.count('CTN')==0
    assert c.count(ANCHOR)==1
    fixed=c.replace(ANCHOR,ANCHOR+INSERT,1)
    assert fixed.count(GULLIVER)==1 and fixed.count(CTN_BANNER)==1 and fixed.count(CTN_BUTTON)==1 and problems(fixed)==0
    assert fixed.count(MARKER)==1 and 'カーセブンとネクステージの2社' in fixed and '電話が少なくて快適でした' in fixed
    req(f'{SITE}/wp-json/wp/v2/posts/{POST_ID}',method='POST',payload={'content':fixed})
    after=get(); identity(after); ac=raw(after,'content'); assert ac==fixed and problems(ac)==0
    pub1=public_count(); assert pub0==pub1
    print('# lexus-ux-emotional-explorer funnel optimization')
    print('- result: **SUCCESS**')
    print(f'- public posts: **{pub0} → {pub1}**')
    print('- WordPress payload: **content only**')
    print('- status: **publish → publish** / featured_media: **2223 → 2223**')
    print('- Gulliver: **1 → 1** / CTN banner: **0 → 1** / CTN button: **0 → 1**')
    print('- Gutenberg problems after: **0**')
    print('- article body: **unchanged; only a CTN funnel block was inserted before the existing summary section**')
if __name__=='__main__': main()
