#!/usr/bin/env python3
from __future__ import annotations
import base64, html, json, os, re, urllib.parse, urllib.request

SITE='https://tsurikue.com'; UA='tsurikue-verify-lbx-used-20260929/1.0'
SLUG='lexus-lbx-used'
TITLE='レクサスLBXの中古車は狙い目？新車との価格差・CPO・選び方を本音で解説'
FEATURED=1513; CATEGORIES=[10]; TAGS=[36,37,42]
BODY_MEDIA=[1509,1504]
GULLIVER='[blog_parts id="2843"]'
TOKEN=re.compile(r'<!--\s+/?wp:[\s\S]*?-->'); OPEN=re.compile(r'<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->'); CLOSE=re.compile(r'<!--\s+/wp:([\w\-/]+)\s+-->')

def auth():
    u=os.environ.get('TSURIKUE_WP_USER'); p=os.environ.get('TSURIKUE_WP_APP_PASSWORD')
    if not u or not p: raise SystemExit('BLOCKED_MISSING_SECRETS')
    return 'Basic '+base64.b64encode(f'{u}:{p}'.encode()).decode()

def req(url):
    r=urllib.request.Request(url,headers={'Authorization':auth(),'Accept':'application/json','User-Agent':UA})
    with urllib.request.urlopen(r,timeout=60) as resp: return json.loads(resp.read().decode()),dict(resp.headers)

def raw(row,key):
    v=row.get(key) or {}; return (v.get('raw') or v.get('rendered') or '') if isinstance(v,dict) else str(v)

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

def check(cond,name,checks):
    if not cond: raise AssertionError(name)
    checks.append(name)

def main():
    q=urllib.parse.urlencode({'context':'edit','slug':SLUG,'status':'any','per_page':10,'_fields':'id,slug,status,title,content,featured_media,categories,tags,excerpt'})
    rows,_=req(f'{SITE}/wp-json/wp/v2/posts?{q}')
    checks=[]
    check(len(rows)==1,'unique slug',checks); r=rows[0]; c=raw(r,'content')
    check(r.get('status')=='draft','status draft',checks)
    check(r.get('slug')==SLUG,'slug exact',checks)
    check(html.unescape(raw(r,'title'))==TITLE,'title exact',checks)
    check(int(r.get('featured_media') or 0)==FEATURED,'featured exact',checks)
    check((r.get('categories') or [])==CATEGORIES,'car category only',checks)
    check(sorted(r.get('tags') or [])==sorted(TAGS),'tags exact',checks)
    check('<h1' not in c.lower(),'no body h1',checks)
    check(problems(c)==0,'Gutenberg balanced',checks)
    check(c.count(GULLIVER)==1,'Gulliver block count 1',checks)
    check('[blog_parts id="2184"]' not in c and '[blog_parts id="2846"]' not in c,'no CTN blocks',checks)
    for phrase,name in [
      ('229台','market listing count'),
      ('373.9万円〜798万円','market range'),
      ('42台／444.8万円〜','CPO snapshot'),
      ('Relaxが<strong>379万円〜528.9万円</strong>','Relax used range'),
      ('差は81万円','Relax gap caveated'),
      ('485万6,300円','personal new build comparator'),
      ('2年・走行距離無制限','CPO warranty wording'),
      ('/lexus-lbx-price/','price link'),
      ('/lexus-lbx-interior/','interior link'),
      ('/lexus-lbx-options/','options link'),
      ('/lexus-lbx-regret/','regret link'),
      ('/lexus-lbx-cheap/','cheap link'),
      ('/lexus-ux-vs-lbx/','UX comparison link'),
      ('欲しくない仕様が80万円安いより、欲しい仕様が少し高い方がいい。','human voice line'),
      ('中古を買うことが目的じゃなく、欲しいLBXを納得できる金額で買うのが目的','humanized thesis'),
      ('/lexus-ux-used/','used UX link')]:
        check(phrase in c,name,checks)
    check('MOTA' not in c and 'イカプラ' not in c and '普通に' not in c,'forbidden expressions absent',checks)
    check('全員に中古をすすめたいわけではありません' not in c,'defensive phrase removed',checks)
    check('ここでも条件確認は必要です' not in c,'AI safety phrasing removed',checks)
    for mid in BODY_MEDIA: check(f'wp-image-{mid}' in c,f'media {mid} present',checks)
    q2=urllib.parse.urlencode({'status':'publish','per_page':1,'_fields':'id'})
    _,h=req(f'{SITE}/wp-json/wp/v2/posts?{q2}')
    print('# New Lexus LBX used-car draft verification')
    print('- result: **SUCCESS**')
    print('- wordpress_write_count: **0**')
    print(f'- post_id: **{r["id"]}**')
    print('- status: **draft**')
    print(f'- all checks passed: **{len(checks)}/{len(checks)}**')
    print('- Gutenberg problems: **0**')
    print('- Gulliver: **1** / CTN: **0**')
    print(f'- WordPress media: featured **{FEATURED}** + body **{",".join(map(str,BODY_MEDIA))}**')
    print('- categories: **[10] (クルマのみ)**')
    print(f'- published_posts: **{h.get("X-WP-Total","?")}**')

if __name__=='__main__': main()
