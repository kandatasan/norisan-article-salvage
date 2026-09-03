#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, os, pathlib, re, time, urllib.parse, urllib.request

BASE='https://tsurikue.com/wp-json/wp/v2'
PAGE_ID=3154
SLUG='odekake'
TITLE='おでかけ'
EXPECTED_SHA='bc9bef266ff65ddefb39b8fe4b81766345d905e9e7d98a3a97dbd7e8d29591e0'
V5_MARK='/* tq-outing-hero-fix:v5:dolphin-native-width */'
V6_MARK='/* tq-outing-spacing:v6:compact-vertical */'
DOLPHIN='https://tsurikue.com/wp-content/uploads/2026/09/img_2419.jpg'
H1='<h1 class="wp-block-heading">今日は、<br>どこ行く？</h1>'
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode()
OUT=pathlib.Path(os.environ.get('TQ_OUTING_V6_RESULT_PATH','/tmp/outing-v6-result.json'))
writes=0

CSS='''\n/* tq-outing-spacing:v6:compact-vertical */
body.page-id-3154 .post_content{margin-top:0!important}
.tq-outing-v3 .tq-hero{margin-bottom:0!important}
.tq-outing-v3 .tq-choose{padding-top:32px!important}
@media(max-width:760px){.tq-outing-v3 .tq-choose{padding-top:24px!important}}
'''

def req(path,method='GET',data=None,retries=4):
    global writes
    headers={'Authorization':AUTH,'Accept':'application/json','User-Agent':'tsurikue-outing-v6-spacing/1.0'}
    body=None
    if data is not None:
        body=json.dumps(data,ensure_ascii=False).encode('utf-8')
        headers['Content-Type']='application/json; charset=utf-8'
    last=None
    for i in range(retries):
        try:
            r=urllib.request.Request(BASE+path,data=body,headers=headers,method=method)
            with urllib.request.urlopen(r,timeout=60) as resp:
                raw=resp.read(); total=resp.headers.get('X-WP-Total')
                if method not in ('GET','HEAD'): writes+=1
                return json.loads(raw.decode()), total
        except Exception as e:
            last=e
            if i+1==retries: raise
            time.sleep(2*(i+1))
    raise last

def page():
    q=urllib.parse.urlencode({'context':'edit','_fields':'id,slug,status,title,content,link'})
    row,_=req(f'/pages/{PAGE_ID}?{q}')
    return row

def raw(row): return (row.get('content') or {}).get('raw') or ''
def rendered(row): return (row.get('content') or {}).get('rendered') or ''
def sha(text): return hashlib.sha256(text.encode()).hexdigest()
def clean_title(row):
    x=(row.get('title') or {}).get('raw') or (row.get('title') or {}).get('rendered') or ''
    return html.unescape(re.sub(r'<[^>]+>','',x)).strip()
def counts():
    _,p=req('/posts?status=publish&per_page=1&_fields=id')
    _,g=req('/pages?status=publish&per_page=1&_fields=id')
    return {'posts':int(p or 0),'pages':int(g or 0)}
def checks(text, rendered_text=''):
    return {
        'v5_marker_once':text.count(V5_MARK)==1,
        'v6_marker_once':text.count(V6_MARK)==1,
        'dolphin_twice':text.count(DOLPHIN)==2,
        'heading_once':text.count(H1)==1,
        'post_margin_rule':'body.page-id-3154 .post_content{margin-top:0!important}' in text,
        'hero_margin_rule':'.tq-outing-v3 .tq-hero{margin-bottom:0!important}' in text,
        'choose_desktop_rule':'.tq-outing-v3 .tq-choose{padding-top:32px!important}' in text,
        'choose_mobile_rule':'@media(max-width:760px){.tq-outing-v3 .tq-choose{padding-top:24px!important}}' in text,
        'five_details':text.count('class="wp-block-details tq-accordion ') == 5,
        'far_group':'ちょっと遠くへ' in text,
        'no_viewport_hacks':not any(x in text for x in ['100vw','100dvw','50vw','50dvw']),
        'rendered_ok':(not rendered_text) or (DOLPHIN in rendered_text and '今日は、<br>どこ行く？' in rendered_text),
    }

before_counts=counts(); before=page(); before_raw=raw(before)
state={'id':before.get('id'),'slug':before.get('slug'),'status':before.get('status'),'title':clean_title(before),'sha256':sha(before_raw)}
expected={'id':PAGE_ID,'slug':SLUG,'status':'publish','title':TITLE,'sha256':EXPECTED_SHA}
if state!=expected: raise RuntimeError('OUTING_V6_STALE_OR_IDENTITY_REFUSED '+json.dumps(state,ensure_ascii=False))
if before_raw.count(V5_MARK)!=1 or V6_MARK in before_raw: raise RuntimeError('OUTING_V6_MARKER_REFUSED')
if before_raw.count(DOLPHIN)!=2 or before_raw.count(H1)!=1: raise RuntimeError('OUTING_V6_CURRENT_HERO_REFUSED')
if before_raw.count('</style>')<1: raise RuntimeError('OUTING_V6_STYLE_END_MISSING')

patched=before_raw.replace('</style>',CSS+'\n</style>',1)
pre=checks(patched)
if not all(pre.values()): raise RuntimeError('OUTING_V6_PREWRITE_FAILED '+json.dumps(pre,ensure_ascii=False))

req(f'/pages/{PAGE_ID}',method='POST',data={'content':patched})
after=page(); after_raw=raw(after); post=checks(after_raw,rendered(after))
identity=(after.get('id')==PAGE_ID and after.get('slug')==SLUG and after.get('status')=='publish' and clean_title(after)==TITLE)
if not identity or not all(post.values()):
    req(f'/pages/{PAGE_ID}',method='POST',data={'content':before_raw})
    raise RuntimeError('OUTING_V6_POSTWRITE_FAILED_ROLLED_BACK '+json.dumps({'identity':identity,'checks':post},ensure_ascii=False))
after_counts=counts()
if after_counts!=before_counts:
    req(f'/pages/{PAGE_ID}',method='POST',data={'content':before_raw})
    raise RuntimeError('OUTING_V6_COUNTS_CHANGED_ROLLED_BACK')
report={'ok':True,'action':'LIVE_OUTING_V6_COMPACT_VERTICAL_SPACING','before':state,'after':{'id':after.get('id'),'slug':after.get('slug'),'status':after.get('status'),'title':clean_title(after),'sha256':sha(after_raw)},'checks':post,'public_before':before_counts,'public_after':after_counts,'wordpress_write_count':writes,'publish_transition_count':0,'delete_count':0}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
