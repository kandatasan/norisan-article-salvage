#!/usr/bin/env python3
from __future__ import annotations
import base64, html, json, os, re, urllib.parse, urllib.request

SITE='https://tsurikue.com'; UA='tsurikue-verify-lbx-options-20260908/1.0'
SLUG='lexus-lbx-options'
TITLE='レクサスLBXのおすすめオプションは？ディーラー見積もりから必要・不要を本音で整理'
FEATURED=1700; CATEGORIES=[10]; TAGS=[36,37,42]
G='[blog_parts id="2843"]'; B='[blog_parts id="2846"]'; C='[blog_parts id="2184"]'
BODY_MEDIA=[1513,1673,1671,1509]
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
    check(int(r.get('featured_media') or 0)==FEATURED,'featured estimate exact',checks)
    check((r.get('categories') or [])==CATEGORIES,'car category only',checks)
    check(sorted(r.get('tags') or [])==sorted(TAGS),'tags exact',checks)
    check('<h1' not in c.lower(),'no body h1',checks)
    check(problems(c)==0,'Gutenberg balanced',checks)
    check(c.count(G)==1,'Gulliver count 1',checks)
    check(c.count(B)==1,'CTN banner count 1',checks)
    check(c.count(C)==1,'CTN button count 1',checks)
    for phrase,name in [
        ('256,300円','option total present'),('485万6,300円','Relax total present'),
        ('502万1,300円','Sonic Copper total present'),('510万8,200円','Mark Levinson total present'),
        ('カラーヘッドアップディスプレイ','HUD present'),('Advanced Park','Advanced Park present'),
        ('駐車時イベント録画','parking event recording present'),('427万円','CTN firsthand present'),
        ('/lexus-lbx-regret/','LBX regret internal link'),('/lexus-ux-vs-lbx/','UX LBX comparison link')]:
        check(phrase in c,name,checks)
    check('以前のLBX' not in c and 'LBXは最低でも460万円' not in c,'no stale historical framing',checks)
    check('イカプラ' not in c and 'MOTA' not in c,'obsolete affiliate absent',checks)
    for mid in BODY_MEDIA: check(f'wp-image-{mid}' in c,f'media {mid} present',checks)
    q2=urllib.parse.urlencode({'status':'publish','per_page':1,'_fields':'id'})
    _,h=req(f'{SITE}/wp-json/wp/v2/posts?{q2}')
    print('# New Lexus LBX options draft verification')
    print('- result: **SUCCESS**')
    print('- wordpress_write_count: **0**')
    print(f'- post_id: **{r["id"]}**')
    print('- status: **draft**')
    print(f'- all checks passed: **{len(checks)}/{len(checks)}**')
    print('- Gutenberg problems: **0**')
    print('- CTA counts: Gulliver **1** / CTN banner **1** / CTN button **1**')
    print(f'- WordPress media: featured **{FEATURED}** + body **{",".join(map(str,BODY_MEDIA))}**')
    print('- categories: **[10] (クルマのみ)**')
    print(f'- published_posts: **{h.get("X-WP-Total","?")}**')

if __name__=='__main__': main()
