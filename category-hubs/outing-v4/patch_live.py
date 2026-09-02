#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, os, pathlib, re, time, urllib.parse, urllib.request

BASE='https://tsurikue.com/wp-json/wp/v2'
PAGE_ID=3154
SLUG='odekake'
TITLE='おでかけ'
EXPECTED_SHA='8df6d9b039fba9ad05d5b85851e4b6ef388a527de21adbe7ca3461827318402b'
OLD_HERO='https://tsurikue.com/wp-content/uploads/2026/05/img_4588.jpg'
NEW_HERO='https://tsurikue.com/wp-content/uploads/2026/09/img_2419.jpg'
OLD_H1='<h1 class="wp-block-heading">今日は、どこ行く？</h1>'
NEW_H1='<h1 class="wp-block-heading">今日は、<br>どこ行く？</h1>'
FIX_MARK='/* tq-outing-hero-fix:v4:dolphin-centered */'
FOCAL_JSON_RE=re.compile(r'"focalPoint"\s*:\s*\{\s*"x"\s*:\s*"?([0-9.]+)"?\s*,\s*"y"\s*:\s*"?([0-9.]+)"?\s*\}')
STYLE_POS_RE=re.compile(r'style="object-position:[^"]+"')
DATA_POS_RE=re.compile(r'data-object-position="[^"]+"')
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode()
OUT=pathlib.Path(os.environ.get('TQ_OUTING_V4_RESULT_PATH','/tmp/outing-v4-result.json'))
writes=0

CSS='''/* tq-outing-hero-fix:v4:dolphin-centered */
.tq-outing-v3.alignfull{
  margin-left:auto!important;
  margin-right:auto!important;
}
.tq-outing-v3 .tq-hero{
  margin-left:auto!important;
  margin-right:auto!important;
}
'''


def req(path,method='GET',data=None,retries=4):
    global writes
    headers={'Authorization':AUTH,'Accept':'application/json','User-Agent':'tsurikue-outing-v4-live-fix/1.2'}
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
def focal_json_ok(text):
    matches=FOCAL_JSON_RE.findall(text)
    if len(matches)!=1:
        return False
    x,y=map(float,matches[0])
    return abs(x-0.58)<=0.005 and abs(y-0.45)<=0.005


def checks(text, rendered_text=''):
    return {
        'fix_marker_once': text.count(FIX_MARK)==1,
        'dolphin_url_twice': text.count(NEW_HERO)==2,
        'old_hero_gone': OLD_HERO not in text,
        'forced_heading_once': text.count(NEW_H1)==1,
        'old_heading_gone': OLD_H1 not in text,
        'focal_json_numeric': focal_json_ok(text),
        'focal_style': 'style="object-position:58% 45%"' in text,
        'focal_data': 'data-object-position="58% 45%"' in text,
        'center_rule': '.tq-outing-v3.alignfull{' in text and 'margin-left:auto!important' in text and 'margin-right:auto!important' in text,
        'five_details': text.count('class="wp-block-details tq-accordion ') == 5,
        'far_group': 'ちょっと遠くへ' in text,
        'no_viewport_hacks': not any(x in text for x in ['100vw','100dvw','50vw','50dvw']),
        'rendered_dolphin': (not rendered_text) or (NEW_HERO in rendered_text and '今日は、<br>どこ行く？' in rendered_text),
    }

before_counts=counts()
before=page(); before_raw=raw(before)
state={'id':before.get('id'),'slug':before.get('slug'),'status':before.get('status'),'title':clean_title(before),'sha256':sha(before_raw)}
if state != {'id':PAGE_ID,'slug':SLUG,'status':'publish','title':TITLE,'sha256':EXPECTED_SHA}:
    raise RuntimeError('OUTING_V4_STALE_OR_IDENTITY_REFUSED '+json.dumps(state,ensure_ascii=False))
if before_raw.count(OLD_HERO)!=2 or before_raw.count(OLD_H1)!=1:
    raise RuntimeError('OUTING_V4_EXPECTED_HERO_COPY_NOT_FOUND')
if FIX_MARK in before_raw:
    raise RuntimeError('OUTING_V4_ALREADY_PRESENT')
if before_raw.count('<style>')<1:
    raise RuntimeError('OUTING_V4_STYLE_INSERTION_POINT_MISSING')
if len(FOCAL_JSON_RE.findall(before_raw))!=1:
    raise RuntimeError('OUTING_V4_FOCAL_JSON_COUNT_MISMATCH')
if len(STYLE_POS_RE.findall(before_raw))!=1 or len(DATA_POS_RE.findall(before_raw))!=1:
    raise RuntimeError('OUTING_V4_FOCAL_INLINE_COUNT_MISMATCH')

patched=before_raw
patched=patched.replace('<style>','<style>\n'+CSS,1)
patched=patched.replace(OLD_HERO,NEW_HERO)
patched=patched.replace(OLD_H1,NEW_H1)
patched,n_json=FOCAL_JSON_RE.subn('"focalPoint":{"x":0.58,"y":0.45}',patched,count=1)
patched,n_style=STYLE_POS_RE.subn('style="object-position:58% 45%"',patched,count=1)
patched,n_data=DATA_POS_RE.subn('data-object-position="58% 45%"',patched,count=1)
if (n_json,n_style,n_data)!=(1,1,1):
    raise RuntimeError('OUTING_V4_FOCAL_REPLACE_FAILED')
pre=checks(patched)
if not all(pre.values()):
    raise RuntimeError('OUTING_V4_PREWRITE_CHECK_FAILED '+json.dumps(pre,ensure_ascii=False))

req(f'/pages/{PAGE_ID}',method='POST',data={'content':patched})
after=page(); after_raw=raw(after); post=checks(after_raw,rendered(after))
identity=(after.get('id')==PAGE_ID and after.get('slug')==SLUG and after.get('status')=='publish' and clean_title(after)==TITLE)
if not identity or not all(post.values()):
    req(f'/pages/{PAGE_ID}',method='POST',data={'content':before_raw})
    raise RuntimeError('OUTING_V4_POSTWRITE_FAILED_ROLLED_BACK '+json.dumps({'identity':identity,'checks':post},ensure_ascii=False))
after_counts=counts()
if after_counts!=before_counts:
    req(f'/pages/{PAGE_ID}',method='POST',data={'content':before_raw})
    raise RuntimeError('OUTING_V4_PUBLIC_COUNTS_CHANGED_ROLLED_BACK')

report={
    'ok':True,'action':'LIVE_OUTING_V4_DOLPHIN_CENTER_HEADING',
    'before':state,
    'after':{'id':after.get('id'),'slug':after.get('slug'),'status':after.get('status'),'title':clean_title(after),'sha256':sha(after_raw)},
    'checks':post,'public_before':before_counts,'public_after':after_counts,
    'wordpress_write_count':writes,'publish_transition_count':0,'delete_count':0
}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
