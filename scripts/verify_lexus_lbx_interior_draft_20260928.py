#!/usr/bin/env python3
from __future__ import annotations
import base64, html, json, os, re, urllib.parse, urllib.request

SITE='https://tsurikue.com'; UA='tsurikue-verify-lbx-interior-20260928/1.0'
SLUG='lexus-lbx-interior'
TITLE='レクサスLBXの内装を実車レビュー｜Relax・Coolの違いとActive・Elegantも比較'
FEATURED=1509; CATEGORIES=[10]; TAGS=[36,37,42]
BODY_MEDIA=[1509,1504]
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
    check(int(r.get('featured_media') or 0)==FEATURED,'featured interior exact',checks)
    check((r.get('categories') or [])==CATEGORIES,'car category only',checks)
    check(sorted(r.get('tags') or [])==sorted(TAGS),'tags exact',checks)
    check('<h1' not in c.lower(),'no body h1',checks)
    check(problems(c)==0,'Gutenberg balanced',checks)
    check('[blog_parts' not in c,'no affiliate blog parts',checks)
    for phrase,name in [
        ('RelaxとCoolの内装を実車で見比べた','firsthand Relax Cool section'),
        ('Active・Elegant','current lineup section'),
        ('サドルタン','saddle tan present'),
        ('セミアニリン本革','seat material present'),
        ('シートベンチレーション','comfort limitation present'),
        ('/lexus-lbx-regret/','regret internal link'),
        ('/lexus-ux-vs-lbx/','UX comparison internal link'),
        ('/lexus-lbx-options/','options internal link'),
        ('/lexus-lbx-cheap/','cheap-buying internal link')]:
        check(phrase in c,name,checks)
    check('MOTA' not in c and 'イカプラ' not in c,'obsolete affiliate absent',checks)
    check('普通に' not in c,'forbidden expression absent',checks)
    for mid in BODY_MEDIA: check(f'wp-image-{mid}' in c,f'media {mid} present',checks)
    q2=urllib.parse.urlencode({'status':'publish','per_page':1,'_fields':'id'})
    _,h=req(f'{SITE}/wp-json/wp/v2/posts?{q2}')
    print('# New Lexus LBX interior draft verification')
    print('- result: **SUCCESS**')
    print('- wordpress_write_count: **0**')
    print(f'- post_id: **{r["id"]}**')
    print('- status: **draft**')
    print(f'- all checks passed: **{len(checks)}/{len(checks)}**')
    print('- Gutenberg problems: **0**')
    print('- affiliate blog parts: **0**')
    print(f'- WordPress media: featured **{FEATURED}** + body **{",".join(map(str,BODY_MEDIA))}**')
    print('- categories: **[10] (クルマのみ)**')
    print(f'- published_posts: **{h.get("X-WP-Total","?")}**')

if __name__=='__main__': main()
