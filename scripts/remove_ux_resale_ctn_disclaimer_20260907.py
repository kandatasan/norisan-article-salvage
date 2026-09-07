#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, os, urllib.request

SITE_URL='https://tsurikue.com'
POST_ID=2222
EXPECTED_SLUG='ux-resale'
EXPECTED_STATUS='publish'
EXPECTED_TITLE='レクサスUXのリセールは？616万円で購入し427万円で売却した記録'
EXPECTED_FEATURED_MEDIA=2223
EXPECTED_SHA='7dd85f21d943c2ba76cf88ee3a1378460232410ebd5acb0b2f21d87776551bda'
REMOVE='''<!-- wp:paragraph -->
<p><strong>ちなみに、納車から約3か月ごろの500万円前後はCTNの査定ではありません。</strong><br>私がCTNを使ったのは約2年後、実際にUXを売ると決めたときです。</p>
<!-- /wp:paragraph -->

'''

def auth_header(user,password):
    token=base64.b64encode(f'{user}:{password}'.encode()).decode()
    return f'Basic {token}'

def req(url,auth,method='GET',payload=None):
    data=None
    headers={'Accept':'application/json','Authorization':auth,'User-Agent':'tsurikue-ux-resale-cleanup/1.0'}
    if payload is not None:
        data=json.dumps(payload,ensure_ascii=False).encode('utf-8')
        headers['Content-Type']='application/json; charset=utf-8'
    r=urllib.request.Request(url,data=data,headers=headers,method=method)
    with urllib.request.urlopen(r,timeout=60) as resp:
        return json.loads(resp.read().decode('utf-8')), dict(resp.headers)

def raw(row,key):
    v=row.get(key) or {}
    return v.get('raw') or v.get('rendered') or '' if isinstance(v,dict) else str(v)

def sha(s): return hashlib.sha256(s.encode('utf-8')).hexdigest()

def main():
    auth=auth_header(os.environ['TSURIKUE_WP_USER'],os.environ['TSURIKUE_WP_APP_PASSWORD'])
    before,_=req(f'{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}?context=edit',auth)
    content=raw(before,'content')
    assert before.get('slug')==EXPECTED_SLUG
    assert before.get('status')==EXPECTED_STATUS
    assert raw(before,'title')==EXPECTED_TITLE
    assert before.get('featured_media')==EXPECTED_FEATURED_MEDIA
    assert sha(content)==EXPECTED_SHA, sha(content)
    assert content.count(REMOVE)==1
    public_before=int(req(f'{SITE_URL}/wp-json/wp/v2/posts?status=publish&per_page=1&_fields=id',auth)[1].get('X-WP-Total','0'))
    fixed=content.replace(REMOVE,'',1)
    assert '500万円前後はCTNの査定ではありません' not in fixed
    assert '一括査定サービス' in fixed
    req(f'{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}',auth,'POST',{'content':fixed})
    after,_=req(f'{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}?context=edit',auth)
    after_content=raw(after,'content')
    public_after=int(req(f'{SITE_URL}/wp-json/wp/v2/posts?status=publish&per_page=1&_fields=id',auth)[1].get('X-WP-Total','0'))
    assert after.get('slug')==EXPECTED_SLUG
    assert after.get('status')==EXPECTED_STATUS
    assert raw(after,'title')==EXPECTED_TITLE
    assert after.get('featured_media')==EXPECTED_FEATURED_MEDIA
    assert public_before==public_after
    assert '500万円前後はCTNの査定ではありません' not in after_content
    print('# UX resale wording cleanup')
    print('- result: **SUCCESS**')
    print('- wording: explicit CTN/non-CTN disclaimer removed')
    print('- generic wording: **一括査定サービス** retained')
    print(f'- status: **{before.get("status")} → {after.get("status")}**')
    print(f'- public posts: **{public_before} → {public_after}**')
    print('- payload: **content only**')

if __name__=='__main__':
    main()
