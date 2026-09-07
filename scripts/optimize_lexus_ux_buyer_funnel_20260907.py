#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, os, re, urllib.request
SITE='https://tsurikue.com'; POST_ID=2881; SLUG='lexus-ux-buyer'
TITLE='レクサスUXを買う人はどんな人？年齢層・年収・向いている使い方を考える'
FEATURED=2223; EXPECTED_SHA='d32047b102fe41e480f8de372f57b3c7ea7611457d666121c83a2a3b48415c70'
UA='tsurikue-optimize-lexus-ux-buyer-20260907/1.0'
CTN_BANNER='[blog_parts id="2846"]'; CTN_BUTTON='[blog_parts id="2184"]'; GULLIVER='[blog_parts id="2843"]'
MARKER='<!-- tsurikue-ctn-buyer-funnel:20260907 -->'
TOKEN=re.compile(r'<!--\s+/?wp:[\s\S]*?-->'); OPEN=re.compile(r'<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->'); CLOSE=re.compile(r'<!--\s+/wp:([\w\-/]+)\s+-->')
OLD='''<!-- wp:paragraph -->
<p>私のUXも、査定する場所によって提示額に大きな差が出ました。</p>
<!-- /wp:paragraph -->'''
NEW='''<!-- tsurikue-ctn-buyer-funnel:20260907 -->
<!-- wp:paragraph -->
<p>私のUXも、査定する場所によって提示額に大きな差が出ました。<br>納車から約3か月ごろ、売るつもりはなく「これ、いくらになるんだろ？」という好奇心で査定したとき、ディーラーは約350万円。<br>一括査定サービスでは500万円前後の提示がありました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>査定額は時期や車の状態で変わります。<br>それでも、<strong>UXを買う前に今の車の価値を知っておくと、乗り換えに使える予算が見えやすくなります。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>その後、実際にUXを手放すときに使ったCTNは、最大15社で査定し、やり取りするのは高額査定の上位3社だけ。<br><strong>私のときは2社から連絡が来て、電話が少なくて快適でした。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>買う車を決める前に、「今の車、いくらになる？」を見ておく。</strong></p>
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
def main():
    pub0=public_count(); row=get(); identity(row); c=raw(row,'content')
    assert hashlib.sha256(c.encode()).hexdigest()==EXPECTED_SHA and problems(c)==0 and MARKER not in c
    assert c.count(GULLIVER)==1 and c.count(CTN_BANNER)==0 and c.count(CTN_BUTTON)==1 and c.count('CTN')==0
    assert c.count(OLD)==1
    fixed=c.replace(OLD,NEW,1)
    assert fixed.count(GULLIVER)==1 and fixed.count(CTN_BANNER)==0 and fixed.count(CTN_BUTTON)==1 and problems(fixed)==0
    assert fixed.count(MARKER)==1
    req(f'{SITE}/wp-json/wp/v2/posts/{POST_ID}',method='POST',payload={'content':fixed})
    after=get(); identity(after); ac=raw(after,'content'); assert ac==fixed and problems(ac)==0
    pub1=public_count(); assert pub0==pub1
    print('# lexus-ux-buyer funnel optimization')
    print('- result: **SUCCESS**')
    print(f'- public posts: **{pub0} → {pub1}**')
    print('- WordPress payload: **content only**')
    print('- status: **publish → publish** / featured_media: **2223 → 2223**')
    print('- Gulliver: **1 → 1** / CTN banner: **0 → 0** / CTN button: **1 → 1**')
    print('- Gutenberg problems after: **0**')
    print('- added: **3-month curiosity appraisal / buy-before-current-car-value framing / CTN top-3 + 2-call comfort / microcopy**')
if __name__=='__main__':main()
