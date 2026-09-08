#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, os, urllib.parse, urllib.request

SITE='https://tsurikue.com'
POST_ID=3608
SLUG='lexus-lbx-regret'
TITLE='レクサスLBXは後悔する？試乗して感じた3つの欠点を元UXオーナーが本音レビュー'
EXPECTED_SHA='561a3c6965ca230a6bd7043f64f4a74c46172010798f30ed4bf9b324243f5204'
OLD1='<p>以前のLBXは460万円スタートでしたが、現在はグレード追加によって価格帯が広がっています。</p>'
NEW1='<p>LBXの2WD（FF）は、Elegantの420万円からBespoke Buildの550万円まで。<br>グレードによって価格差があります。</p>'
OLD_BLOCK='''<!-- wp:paragraph -->\n<p>つまり、今は「LBXは最低でも460万円」というクルマではありません。<br>Elegantなら420万円から選べます。</p>\n<!-- /wp:paragraph -->\n\n'''
OLD2='現在の価格・装備は<a href="https://lexus.jp/models/lbx/"'
NEW2='価格・装備は<a href="https://lexus.jp/models/lbx/"'


def auth():
    u=os.environ['TSURIKUE_WP_USER']; p=os.environ['TSURIKUE_WP_APP_PASSWORD']
    return 'Basic '+base64.b64encode(f'{u}:{p}'.encode()).decode()

def req(url, method='GET', payload=None):
    headers={'Authorization':auth(),'Accept':'application/json','User-Agent':'tsurikue-fix-lbx-current-info/1.0'}
    data=None
    if payload is not None:
        data=json.dumps(payload,ensure_ascii=False).encode(); headers['Content-Type']='application/json; charset=utf-8'
    r=urllib.request.Request(url,data=data,headers=headers,method=method)
    with urllib.request.urlopen(r,timeout=90) as resp:
        return json.loads(resp.read().decode())

def raw(row,key):
    v=row.get(key) or {}
    return (v.get('raw') or v.get('rendered') or '') if isinstance(v,dict) else str(v)

def main():
    q=urllib.parse.urlencode({'context':'edit','_fields':'id,slug,status,title,content,categories,featured_media'})
    row=req(f'{SITE}/wp-json/wp/v2/posts/{POST_ID}?{q}')
    assert row['id']==POST_ID and row['slug']==SLUG and row['status']=='draft'
    assert raw(row,'title')==TITLE
    assert row.get('categories')==[10]
    content=raw(row,'content')
    assert hashlib.sha256(content.encode()).hexdigest()==EXPECTED_SHA
    assert content.count(OLD1)==1 and content.count(OLD_BLOCK)==1 and content.count(OLD2)==1
    fixed=content.replace(OLD1,NEW1,1).replace(OLD_BLOCK,'',1).replace(OLD2,NEW2,1)
    assert '以前のLBXは460万円スタート' not in fixed
    assert 'つまり、今は「LBXは最低でも460万円」' not in fixed
    assert '現在の価格・装備は' not in fixed
    assert NEW1 in fixed and NEW2 in fixed
    out=req(f'{SITE}/wp-json/wp/v2/posts/{POST_ID}',method='POST',payload={'content':fixed})
    assert out['id']==POST_ID and out['slug']==SLUG and out['status']=='draft'
    print('# LBX regret current-info copy fix')
    print('- result: **SUCCESS**')
    print('- post_id: **3608**')
    print('- status: **draft**')
    print('- changed: historical price framing removed; current-info wording retained')
    print('- wordpress_write_count: **1**')

if __name__=='__main__': main()
