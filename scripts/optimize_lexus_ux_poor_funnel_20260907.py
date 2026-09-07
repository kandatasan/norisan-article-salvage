#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, os, re, urllib.request
SITE='https://tsurikue.com'; POST_ID=2874; SLUG='lexus-ux-poor'
TITLE='レクサスUXは貧乏・見栄っ張りに見える？実際に所有して感じたこと'
FEATURED=2507; EXPECTED_SHA='0f89ca01250cdc3b5cff48887d3375a0b0f03df4a0192647dcf8ae61b111c63b'
UA='tsurikue-optimize-lexus-ux-poor-20260907/1.0'
GULLIVER='[blog_parts id="2843"]'; CTN_BANNER='[blog_parts id="2846"]'; CTN_BUTTON='[blog_parts id="2184"]'
MARKER='<!-- tsurikue-ctn-poor-funnel:20260907 -->'
TOKEN=re.compile(r'<!--\s+/?wp:[\s\S]*?-->'); OPEN=re.compile(r'<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->'); CLOSE=re.compile(r'<!--\s+/wp:([\w\-/]+)\s+-->')
INSERT='''<!-- tsurikue-ctn-poor-funnel:20260907 -->
<!-- wp:paragraph -->
<p>実際にUXを手放したときに使ったCTNは、最大15社で査定し、やり取りするのは高額査定の上位3社だけ。<br><strong>私のときはカーセブンとネクステージの2社から連絡が来て、電話が少なくて快適でした。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>無理して新車に寄せる前に、まずは「今の車、いくらになる？」を見ておく。</strong></p>
<!-- /wp:paragraph -->'''
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
def insert_before_ctn(content):
    assert content.count(CTN_BUTTON)==1
    pos=content.index(CTN_BUTTON); start=content.rfind('<!-- wp:shortcode -->',0,pos)
    assert start>=0
    return content[:start]+INSERT+'\n\n'+content[start:]
def main():
    pub0=public_count(); row=get(); identity(row); c=raw(row,'content')
    assert hashlib.sha256(c.encode()).hexdigest()==EXPECTED_SHA and problems(c)==0 and MARKER not in c
    assert c.count(GULLIVER)==1 and c.count(CTN_BANNER)==0 and c.count(CTN_BUTTON)==1 and c.count('CTN')==0
    fixed=insert_before_ctn(c)
    assert problems(fixed)==0 and fixed.count(GULLIVER)==1 and fixed.count(CTN_BANNER)==0 and fixed.count(CTN_BUTTON)==1
    assert fixed.count(MARKER)==1 and '電話が少なくて快適でした' in fixed and '今の車、いくらになる？' in fixed
    req(f'{SITE}/wp-json/wp/v2/posts/{POST_ID}',method='POST',payload={'content':fixed})
    after=get(); identity(after); ac=raw(after,'content'); assert ac==fixed and problems(ac)==0
    pub1=public_count(); assert pub0==pub1
    print('# lexus-ux-poor funnel optimization')
    print('- result: **SUCCESS**')
    print(f'- public posts: **{pub0} → {pub1}**')
    print('- WordPress payload: **content only**')
    print('- status: **publish → publish** / featured_media: **2507 → 2507**')
    print('- Gulliver: **1 → 1** / CTN banner: **0 → 0** / CTN button: **1 → 1**')
    print('- Gutenberg problems after: **0**')
    print('- added: **CTN top-3 + actual two-company/low-phone-volume note + poor-article microcopy only**')
if __name__=='__main__':main()
