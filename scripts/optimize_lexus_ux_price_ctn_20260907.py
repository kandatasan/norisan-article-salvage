#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, os, re, urllib.request

SITE='https://tsurikue.com'
POST_ID=2956
SLUG='lexus-ux-price'
TITLE='レクサスUXの価格はいくら？乗り出し価格とグレード別の違い'
FEATURED_MEDIA=2223
EXPECTED_SHA='1468c9f5f1e988080713f8283d9a0cafeb2e7d5e63d50ba93bfc7099acba407e'
UA='tsurikue-optimize-lexus-ux-price-ctn-20260907/1.0'
CTN_BANNER='[blog_parts id="2846"]'
CTN_BUTTON='[blog_parts id="2184"]'
GULLIVER='[blog_parts id="2843"]'
MARKER='<!-- tsurikue-ctn-price-funnel:20260907 -->'
TOKEN=re.compile(r'<!--\s+/?wp:[\s\S]*?-->')
OPEN=re.compile(r'<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->')
CLOSE=re.compile(r'<!--\s+/wp:([\w\-/]+)\s+-->')

INSERT='''<!-- tsurikue-ctn-price-funnel:20260907 -->
<!-- wp:paragraph -->
<p>車両価格やオプションで数万円を調整するのも、もちろん方法のひとつです。<br>でも私の場合は、<strong>前の車の売り方だけで25万円差が出ました。</strong><br>乗り換えでは「いくらで買うか」だけでなく、「今の車をいくらで売れるか」も見ておきたいところです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>実際にUXを売るときに使ったCTNは、最大15社で査定し、やり取りするのは高額査定の上位3社だけ。<br><strong>私のときは2社から連絡が来て、電話が少なくて快適でした。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>「今の車、いくらになる？」を先に見ておく。</strong></p>
<!-- /wp:paragraph -->'''

def auth():
    raw=f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()
    return 'Basic '+base64.b64encode(raw).decode()

def req(url,method='GET',payload=None):
    headers={'Authorization':auth(),'Accept':'application/json','User-Agent':UA}
    data=None
    if payload is not None:
        data=json.dumps(payload,ensure_ascii=False).encode(); headers['Content-Type']='application/json; charset=utf-8'
    r=urllib.request.Request(url,data=data,headers=headers,method=method)
    with urllib.request.urlopen(r,timeout=60) as resp:
        return json.loads(resp.read().decode()),dict(resp.headers)

def get(): return req(f'{SITE}/wp-json/wp/v2/posts/{POST_ID}?context=edit')[0]

def raw(row,key):
    v=row.get(key) or {}
    return (v.get('raw') or v.get('rendered') or '') if isinstance(v,dict) else str(v)

def count_public():
    _,h=req(f'{SITE}/wp-json/wp/v2/posts?status=publish&per_page=1&_fields=id')
    return int(h.get('X-WP-Total',0))

def problems(text):
    stack=[]
    for m in TOKEN.finditer(text):
        t=m.group(0); o=OPEN.fullmatch(t); c=CLOSE.fullmatch(t)
        if o:
            if not o.group(2): stack.append(o.group(1))
        elif c:
            if not stack or stack[-1]!=c.group(1): return 1
            stack.pop()
    return len(stack)

def identity(row):
    assert row['id']==POST_ID and row['slug']==SLUG and row['status']=='publish'
    assert raw(row,'title')==TITLE and row['featured_media']==FEATURED_MEDIA

def main():
    public_before=count_public(); row=get(); identity(row); c=raw(row,'content')
    assert hashlib.sha256(c.encode()).hexdigest()==EXPECTED_SHA
    assert problems(c)==0 and MARKER not in c
    assert c.count(GULLIVER)==1 and c.count(CTN_BANNER)==0 and c.count(CTN_BUTTON)==1 and c.count('CTN')==0
    anchor='必ず買取の方が高くなるわけではありません。'
    assert anchor in c and '前の車がディーラー下取り50万円、買取サービスでは75万円でした' in c
    pos=c.index(CTN_BUTTON)
    start=c.rfind('<!-- wp:shortcode -->',0,pos)
    assert start>=0
    fixed=c[:start]+INSERT+'\n\n'+c[start:]
    assert fixed.count(GULLIVER)==1 and fixed.count(CTN_BANNER)==0 and fixed.count(CTN_BUTTON)==1
    assert fixed.count(MARKER)==1 and problems(fixed)==0
    req(f'{SITE}/wp-json/wp/v2/posts/{POST_ID}',method='POST',payload={'content':fixed})
    after=get(); identity(after); ac=raw(after,'content')
    assert ac==fixed and problems(ac)==0
    public_after=count_public(); assert public_after==public_before
    print('# lexus-ux-price CTN optimization')
    print('- result: **SUCCESS**')
    print(f'- public posts: **{public_before} → {public_after}**')
    print('- WordPress payload: **content only**')
    print('- status: **publish → publish**')
    print('- featured_media: **2223 → 2223**')
    print('- Gulliver banner: **1 → 1** / CTN banner: **0 → 0** / CTN button: **1 → 1**')
    print('- Gutenberg problems after: **0**')
    print('- added: **buy-price + sell-price framing / 25万円 firsthand bridge / CTN top-3 + 2-call comfort note / microcopy**')

if __name__=='__main__': main()
