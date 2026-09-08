#!/usr/bin/env python3
from __future__ import annotations
import base64, json, os, urllib.parse, urllib.request

SITE='https://tsurikue.com'; POST_ID=3608; SLUG='lexus-lbx-regret'
TITLE='レクサスLBXは後悔する？試乗して感じた3つの欠点を元UXオーナーが本音レビュー'
G='[blog_parts id="2843"]'; B='[blog_parts id="2846"]'; C='[blog_parts id="2184"]'

def auth():
    u=os.environ['TSURIKUE_WP_USER']; p=os.environ['TSURIKUE_WP_APP_PASSWORD']
    return 'Basic '+base64.b64encode(f'{u}:{p}'.encode()).decode()

def req(url):
    r=urllib.request.Request(url,headers={'Authorization':auth(),'Accept':'application/json','User-Agent':'tsurikue-verify-lbx-current-info/1.0'})
    with urllib.request.urlopen(r,timeout=90) as resp: return json.loads(resp.read().decode())

def raw(row,key):
    v=row.get(key) or {}; return (v.get('raw') or v.get('rendered') or '') if isinstance(v,dict) else str(v)

def main():
    q=urllib.parse.urlencode({'context':'edit','_fields':'id,slug,status,title,content,categories,featured_media,tags'})
    r=req(f'{SITE}/wp-json/wp/v2/posts/{POST_ID}?{q}'); c=raw(r,'content')
    checks=[]
    def ck(x,n):
        assert x,n; checks.append(n)
    ck(r['id']==POST_ID,'id exact'); ck(r['slug']==SLUG,'slug exact'); ck(r['status']=='draft','draft')
    ck(raw(r,'title')==TITLE,'title exact'); ck(r.get('categories')==[10],'car category only'); ck(r.get('featured_media')==1728,'featured preserved')
    ck('以前のLBXは460万円スタート' not in c,'old price framing absent')
    ck('つまり、今は「LBXは最低でも460万円」' not in c,'stale contrast absent')
    ck('現在の価格・装備は' not in c,'current meta wording absent')
    ck('LBXの2WD（FF）は、Elegantの420万円からBespoke Buildの550万円まで。' in c,'current price lead present')
    ck('価格・装備は<a href="https://lexus.jp/models/lbx/"' in c,'official-link wording present')
    ck(c.count(G)==1 and c.count(B)==1 and c.count(C)==1,'CTA counts preserved')
    ck('以前使った一括査定のような大量の電話もなく' in c,'personal appraisal comparison preserved')
    print('# LBX regret current-info verification')
    print('- result: **SUCCESS**')
    print(f'- all checks passed: **{len(checks)}/{len(checks)}**')
    print('- post_id: **3608**')
    print('- status: **draft**')
    print('- categories: **[10] (クルマのみ)**')
    print('- wordpress_write_count: **0**')

if __name__=='__main__': main()
