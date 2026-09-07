#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, os, re, urllib.request
SITE='https://tsurikue.com'; POST_ID=2329; SLUG='ux300h'
TITLE='レクサスUX300hを試乗｜UX250hオーナーが比較して感じた3つの違い'
FEATURED=2330; EXPECTED_SHA='45cb5b90dbe97e91d8da11a0eb3f2503930e96cd1ddb62f9d8ad5e098ca27cd5'
UA='tsurikue-optimize-ux300h-20260907/1.1'
GULLIVER='[blog_parts id="2843"]'; CTN_BANNER='[blog_parts id="2846"]'; CTN_BUTTON='[blog_parts id="2184"]'
MARKER='<!-- tsurikue-ctn-ux300h-funnel:20260907 -->'
OLD_TEXT='乗り換えなら、今の車がいくらで売れるかも確認しておくと予算を組みやすくなります。'
NEW_TEXT='UX300hと中古UX250hの価格差を比べるのと同じくらい、乗り換えなら<strong>今の車がいくらで売れるか</strong>も予算に効きます。<br>実際に私がCTNを使ったときは、連絡が来たのは2社だけ。高額査定の上位3社だけとやり取りする仕組みなので、電話が少なくて快適でした。'
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
    assert c.count(OLD_TEXT)==1
    fixed=c.replace(OLD_TEXT,MARKER+NEW_TEXT,1)
    assert fixed.count(GULLIVER)==1 and fixed.count(CTN_BANNER)==1 and fixed.count(CTN_BUTTON)==1 and problems(fixed)==0
    assert fixed.count(MARKER)==1 and '連絡が来たのは2社だけ' in fixed and '電話が少なくて快適でした' in fixed
    req(f'{SITE}/wp-json/wp/v2/posts/{POST_ID}',method='POST',payload={'content':fixed})
    after=get(); identity(after); ac=raw(after,'content'); assert ac==fixed and problems(ac)==0
    pub1=public_count(); assert pub0==pub1
    print('# ux300h funnel optimization')
    print('- result: **SUCCESS**')
    print(f'- public posts: **{pub0} → {pub1}**')
    print('- WordPress payload: **content only**')
    print('- status: **publish → publish** / featured_media: **2330 → 2330**')
    print('- Gulliver: **1 → 1** / CTN banner: **1 → 1** / CTN button: **1 → 1**')
    print('- Gutenberg problems after: **0**')
    print('- article body: **unchanged except the text inside the existing CTN bridge paragraph**')
if __name__=='__main__': main()
