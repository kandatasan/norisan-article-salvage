#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, os, re, urllib.request

SITE='https://tsurikue.com'
UA='tsurikue-fix-final-ux-funnels-20260908/1.0'
G='[blog_parts id="2843"]'; B='[blog_parts id="2846"]'; C='[blog_parts id="2184"]'
TOKEN=re.compile(r'<!--\s+/?wp:[\s\S]*?-->'); OPEN=re.compile(r'<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->'); CLOSE=re.compile(r'<!--\s+/wp:([\w\-/]+)\s+-->')

def auth():
    raw=f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode(); return 'Basic '+base64.b64encode(raw).decode()

def req(url,method='GET',payload=None):
    headers={'Authorization':auth(),'Accept':'application/json','User-Agent':UA}; data=None
    if payload is not None:
        data=json.dumps(payload,ensure_ascii=False).encode(); headers['Content-Type']='application/json; charset=utf-8'
    r=urllib.request.Request(url,data=data,headers=headers,method=method)
    with urllib.request.urlopen(r,timeout=60) as resp:return json.loads(resp.read().decode()),dict(resp.headers)

def get(pid): return req(f'{SITE}/wp-json/wp/v2/posts/{pid}?context=edit')[0]

def raw(row,key):
    v=row.get(key) or {}; return (v.get('raw') or v.get('rendered') or '') if isinstance(v,dict) else str(v)

def public_count():
    _,h=req(f'{SITE}/wp-json/wp/v2/posts?status=publish&per_page=1&_fields=id'); return int(h.get('X-WP-Total',0))

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

def assert_id(row,pid,slug,title,featured):
    assert row['id']==pid and row['slug']==slug and row['status']=='publish' and row['featured_media']==featured
    assert raw(row,'title')==title

def main():
    pub0=public_count()

    # 1) ux-resale: remove only the premature first CTN pitch/banner; keep the two high-intent CTN banners.
    pid=2222; slug='ux-resale'; title='レクサスUXのリセールは？616万円で購入し427万円で売却した記録'; featured=2223
    expected_sha='0e7d6b97bc30434db63e97f0b50156e09b5833f5a76e04baaa2550d7e30599ab'
    row=get(pid); assert_id(row,pid,slug,title,featured); c=raw(row,'content')
    assert hashlib.sha256(c.encode()).hexdigest()==expected_sha and problems(c)==0
    assert c.count(G)==0 and c.count(B)==3 and c.count(C)==1
    old='''<!-- wp:paragraph -->\n<p>最初の好奇心査定で「査定先によって、ここまで金額が違うのか」と知っていたので、実際の売却でも1社だけでは決めませんでした。<br>CTNは最大15社で査定し、高額査定の上位3社とやり取りする仕組みです。</p>\n<!-- /wp:paragraph -->\n\n<!-- wp:shortcode -->\n[blog_parts id="2846"]\n<!-- /wp:shortcode -->'''
    new='''<!-- wp:paragraph -->\n<p>最初の好奇心査定で「査定先によって、ここまで金額が違うのか」と知っていたので、実際の売却でも1社だけでは決めませんでした。</p>\n<!-- /wp:paragraph -->'''
    assert c.count(old)==1
    fixed=c.replace(old,new,1)
    assert fixed.count(B)==2 and fixed.count(C)==1 and problems(fixed)==0
    req(f'{SITE}/wp-json/wp/v2/posts/{pid}',method='POST',payload={'content':fixed})
    after=get(pid); assert_id(after,pid,slug,title,featured); ac=raw(after,'content'); assert ac==fixed and problems(ac)==0

    # 2) ux-koukai: correct only the appraisal timing references from ~5 months to ~3 months.
    pid=2517; slug='ux-koukai'; title='レクサスUXはひどい？616万円で買って後悔した欠点と満足している理由'; featured=2208
    expected_sha='aaf3a72d5515df9647254945f953e5b6934c05b051d9de4c336e47eef775fbc7'
    row=get(pid); assert_id(row,pid,slug,title,featured); c=raw(row,'content')
    assert hashlib.sha256(c.encode()).hexdigest()==expected_sha and problems(c)==0
    assert c.count('5か月')==4
    replacements=[
      ('納車約5か月・5,000km','納車約3か月・5,000km'),
      ('査定時点：納車約5か月後・走行距離約5,000km','査定時点：納車約3か月後・走行距離約5,000km'),
      ('納車から約5か月、走行距離約5,000km','納車から約3か月、走行距離約5,000km'),
      ('納車約5か月、走行距離約5,000kmの時点','納車約3か月、走行距離約5,000kmの時点'),
    ]
    fixed=c
    for old,new in replacements:
        assert fixed.count(old)==1
        fixed=fixed.replace(old,new,1)
    assert fixed.count('5か月')==0 and fixed.count('3か月')>=4 and problems(fixed)==0
    assert fixed.count(G)==1 and fixed.count(B)==1 and fixed.count(C)==2
    req(f'{SITE}/wp-json/wp/v2/posts/{pid}',method='POST',payload={'content':fixed})
    after=get(pid); assert_id(after,pid,slug,title,featured); ac=raw(after,'content'); assert ac==fixed and problems(ac)==0

    pub1=public_count(); assert pub0==pub1
    print('# Final Lexus UX funnel fixes')
    print('- result: **SUCCESS**')
    print(f'- public posts: **{pub0} → {pub1}**')
    print('- WordPress payloads: **content only**')
    print('- `ux-resale`: CTN banner **3 → 2**; removed only premature first pitch/banner')
    print('- `ux-koukai`: appraisal timing **約5か月 → 約3か月** in 4 appraisal-related references')
    print('- statuses/titles/featured media preserved; Gutenberg problems: **0**')

if __name__=='__main__': main()
