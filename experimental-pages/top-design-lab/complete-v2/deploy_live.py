#!/usr/bin/env python3
import base64
import hashlib
import html
import json
import os
import pathlib
import re
import time
import urllib.parse
import urllib.request

BASE='https://tsurikue.com/wp-json/wp/v2'
PAGE_ID=2983
MARKER='<!-- tsurikue-experimental-page:v1:top-design-lab -->'
PATCH='/* TQ TOP CARD RESPONSE + HUB LINKS v2 */'
EXPECTED_OLD_SHA='8d01e3c0e8d4d5d37f65d380c092e0f071db8dfbeee9d52759088e569788ea93'
ROOT=pathlib.Path(__file__).resolve().parents[1]
CONTENT_PATH=ROOT/'content.html'
CONFIG_PATH=ROOT/'config.json'
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode()
writes=0


def req(path,method='GET',data=None,retries=4):
    global writes
    headers={'Authorization':AUTH,'Accept':'application/json','User-Agent':'tsurikue-home-complete-v2/1.0'}
    body=None
    if data is not None:
        body=json.dumps(data,ensure_ascii=False).encode('utf-8')
        headers['Content-Type']='application/json; charset=utf-8'
    last=None
    for i in range(retries):
        try:
            request=urllib.request.Request(BASE+path,data=body,headers=headers,method=method)
            with urllib.request.urlopen(request,timeout=60) as response:
                raw=response.read(); total=response.headers.get('X-WP-Total')
                if method not in ('GET','HEAD'): writes+=1
                return json.loads(raw.decode('utf-8')),total
        except Exception as exc:
            last=exc
            if i+1==retries: raise
            time.sleep(2*(i+1))
    raise last


def raw_field(page): return (page.get('content') or {}).get('raw') or ''
def rendered_field(page): return (page.get('content') or {}).get('rendered') or ''
def sha(text): return hashlib.sha256(text.encode()).hexdigest()
def clean(value):
    if isinstance(value,dict): value=value.get('raw') or value.get('rendered') or ''
    return html.unescape(re.sub(r'<[^>]+>','',value or '')).strip()


def get_page():
    q=urllib.parse.urlencode({'context':'edit','_fields':'id,slug,status,title,content,link'})
    row,_=req(f'/pages/{PAGE_ID}?{q}')
    return row


def count_public():
    _,posts=req('/posts?status=publish&per_page=1&_fields=id')
    _,pages=req('/pages?status=publish&per_page=1&_fields=id')
    return {'posts':int(posts or 0),'pages':int(pages or 0)}


def check_hub(slug):
    q=urllib.parse.urlencode({'context':'edit','slug':slug,'status':'publish','per_page':10,'_fields':'id,slug,status,title,link'})
    rows,_=req('/pages?'+q)
    if len(rows)!=1 or rows[0].get('status')!='publish':
        raise RuntimeError('HUB_PAGE_NOT_PUBLISHED '+slug+' '+json.dumps(rows,ensure_ascii=False))
    return {'id':int(rows[0]['id']),'slug':rows[0]['slug'],'title':clean(rows[0].get('title')),'link':rows[0].get('link')}


def checks(raw,rendered):
    targets=['/odekake/','/gourmet-guide/','/fishing-guide/','/car-guide/']
    old=['/category/sightseeing-leisure/','/category/gourmet/','/category/fishing/','/category/car/']
    return {
        'marker':MARKER in raw,
        'response_patch_once':raw.count(PATCH)==1,
        'four_cards':all(x in raw for x in ['tq4-cat--outing','tq4-cat--gourmet','tq4-cat--fishing','tq4-cat--car']),
        'hub_links':all(f'href="{x}"' in raw for x in targets),
        'old_category_links_gone':not any(x in raw for x in old),
        'stretched_anchor_css':'h3 a::after' in raw and 'position:absolute' in raw and 'inset:0' in raw,
        'touch_response':'touch-action:manipulation' in raw and 'a:active::after' in raw,
        'no_viewport_hack':all(x not in raw for x in ['100vw','100dvw','50vw','50dvw']),
        'rendered_marker':PATCH in rendered,
        'status_safe_copy':'休日、' in raw and '今日はどれ？' in raw,
    }

cfg=json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
desired=CONTENT_PATH.read_text(encoding='utf-8')
desired_sha=sha(desired)
if cfg.get('homepage_revision')!='complete-v2-card-response-hub-links':
    raise RuntimeError('CANONICAL_REVISION_MISMATCH')
if cfg.get('expected_current_content_sha256')!=desired_sha:
    raise RuntimeError('CANONICAL_SHA_MISMATCH')
pre=checks(desired,desired)
if not all(pre.values()): raise RuntimeError('DESIRED_CHECK_FAILED '+json.dumps(pre,ensure_ascii=False))

hubs={s:check_hub(s) for s in ['odekake','gourmet-guide','fishing-guide','car-guide']}
before_counts=count_public()
before=get_page(); before_raw=raw_field(before)
before_state={'id':before.get('id'),'slug':before.get('slug'),'status':before.get('status'),'title':clean(before.get('title')),'sha256':sha(before_raw)}
if before.get('id')!=PAGE_ID or before.get('status')!='publish' or MARKER not in before_raw:
    raise RuntimeError('LIVE_HOME_IDENTITY_FAILED '+json.dumps(before_state,ensure_ascii=False))

written=False
if sha(before_raw)==desired_sha and PATCH in before_raw:
    action='VERIFIED_EXISTING_HOME_COMPLETE_V2'
else:
    if sha(before_raw)!=EXPECTED_OLD_SHA:
        raise RuntimeError('STALE_HOME_REFUSED '+json.dumps({'expected':EXPECTED_OLD_SHA,'actual':sha(before_raw)},ensure_ascii=False))
    req(f'/pages/{PAGE_ID}',method='POST',data={'content':desired})
    written=True; action='UPDATED_LIVE_HOME_COMPLETE_V2'

after=get_page(); after_raw=raw_field(after); after_rendered=rendered_field(after)
after_state={'id':after.get('id'),'slug':after.get('slug'),'status':after.get('status'),'title':clean(after.get('title')),'sha256':sha(after_raw)}
final_checks=checks(after_raw,after_rendered)
identity_ok=(after.get('id')==PAGE_ID and after.get('status')=='publish' and after.get('slug')==before.get('slug') and clean(after.get('title'))==clean(before.get('title')))
if not identity_ok or sha(after_raw)!=desired_sha or not all(final_checks.values()):
    if written: req(f'/pages/{PAGE_ID}',method='POST',data={'content':before_raw})
    raise RuntimeError('LIVE_HOME_VERIFY_FAILED_ROLLED_BACK '+json.dumps({'identity_ok':identity_ok,'state':after_state,'checks':final_checks},ensure_ascii=False))

after_counts=count_public()
if after_counts!=before_counts:
    if written: req(f'/pages/{PAGE_ID}',method='POST',data={'content':before_raw})
    raise RuntimeError('PUBLIC_COUNTS_CHANGED_ROLLED_BACK '+json.dumps({'before':before_counts,'after':after_counts},ensure_ascii=False))

report={
    'ok':True,'action':action,'page':after_state,'before_sha256':before_state['sha256'],'desired_sha256':desired_sha,
    'hubs':hubs,'checks':final_checks,'public_before':before_counts,'public_after':after_counts,
    'wordpress_write_count':writes,'live_write_count':1 if written else 0,'publish_transition_count':0,'delete_count':0,
}
out=os.environ.get('TQ_HOME_RESULT_PATH')
if out: pathlib.Path(out).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
