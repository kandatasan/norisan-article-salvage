#!/usr/bin/env python3
from __future__ import annotations
import base64, html, json, os, re, urllib.parse, urllib.request

SITE='https://tsurikue.com'; UA='tsurikue-verify-lbx-regret-20260908/1.0'
SLUG='lexus-lbx-regret'
TITLE='レクサスLBXは後悔する？試乗して感じた3つの欠点を元UXオーナーが本音レビュー'
FEATURED=1728; CATEGORIES=[10]; TAGS=[36,37,42]
G='[blog_parts id="2843"]'; B='[blog_parts id="2846"]'; C='[blog_parts id="2184"]'
BODY_MEDIA=[1513,1504,2223,1506,1509]
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
    check((r.get('categories') or [])==CATEGORIES,'parent car category only',checks)
    check(11 not in (r.get('categories') or []),'no Lexus UX child category',checks)
    check(sorted(r.get('tags') or [])==sorted(TAGS),'tags exact',checks)
    check('<h1' not in c.lower(),'no body h1',checks)
    check(problems(c)==0,'Gutenberg balanced',checks)
    check(c.count(G)==1,'Gulliver count 1',checks)
    check(c.count(B)==1,'CTN banner count 1',checks)
    check(c.count(C)==1,'CTN button count 1',checks)
    check('420万円' in c and '460万円' in c and '550万円' in c,'current LBX prices present',checks)
    check('助手席は6Wayマニュアルシート' in c,'current seat equipment present',checks)
    check('運転しやすっ！' in c,'drive firsthand present',checks)
    check('お金に余裕がある人がスクーター感覚で乗るクルマ' in c,'old personality line preserved',checks)
    check('ヒザだけでなくスネ' in c,'rear-seat firsthand present',checks)
    check('UXより外の音が入りやすく' in c,'ride/quietness firsthand present',checks)
    check('LBXを所有したわけではない' in c,'ownership transparency present',checks)
    check('427万円' in c,'CTN sale firsthand present',checks)
    check('/lexus-ux-vs-lbx/' in c,'UX vs LBX internal link',checks)
    check('/lexus-ux-rear-seat/' in c,'UX rear-seat internal link',checks)
    check('/lexus-ux-used/' in c,'used UX internal link',checks)
    check('/lexus-ux250h-used-vs-ux300h/' in c,'used-vs-new UX internal link',checks)
    check('lexus.jp/models/lbx/' in c,'official LBX link present',checks)
    check('イカプラ' not in c and 'MOTA' not in c,'obsolete affiliate removed',checks)
    for mid in BODY_MEDIA: check(f'wp-image-{mid}' in c,f'media {mid} present',checks)
    q2=urllib.parse.urlencode({'status':'publish','per_page':1,'_fields':'id'})
    _,h=req(f'{SITE}/wp-json/wp/v2/posts?{q2}')
    print('# New Lexus LBX regret draft verification')
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
