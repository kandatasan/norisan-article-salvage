#!/usr/bin/env python3
import base64
import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

BASE='https://tsurikue.com/wp-json/wp/v2'
LIVE_PAGE_ID=3294
PREVIEW_PAGE_ID=3350
LIVE_SLUG='car-guide'
PREVIEW_SLUG='car-guide-v2-preview'
LIVE_EXPECTED_SHA='b41eaca8ad5f570e063c12715d1622cbdf7ffee25af8fc0baf93682d6f5c9b02'
MARKER='tsurikue-category-hub:v3:car-current-improved'
ALLOWED_PREVIEW_MARKERS=(
    'tsurikue-category-hub:v2:car-model-first-preview',
    MARKER,
)

USER=os.environ.get('TSURIKUE_WP_USER')
PASS=os.environ.get('TSURIKUE_WP_APP_PASSWORD')
if not USER or not PASS:
    raise SystemExit('Missing TSURIKUE_WP_USER / TSURIKUE_WP_APP_PASSWORD')
TOKEN=base64.b64encode(f'{USER}:{PASS}'.encode()).decode()
HEADERS={
    'Authorization':'Basic '+TOKEN,
    'Accept':'application/json',
    'Content-Type':'application/json; charset=utf-8',
    'User-Agent':'tsurikue-car-current-v3/1.0',
}

def req(method,path,data=None):
    body=None if data is None else json.dumps(data,ensure_ascii=False).encode('utf-8')
    r=urllib.request.Request(BASE+path,data=body,headers=HEADERS,method=method)
    try:
        with urllib.request.urlopen(r,timeout=50) as x:
            raw=x.read().decode('utf-8')
            return (json.loads(raw) if raw else None),dict(x.headers)
    except urllib.error.HTTPError as e:
        detail=e.read().decode('utf-8',errors='replace')
        raise RuntimeError(f'{method} {path} -> HTTP {e.code}: {detail[:1200]}') from e

def get(path): return req('GET',path)[0]
def post(path,data): return req('POST',path,data)[0]
def raw_content(item): return ((item.get('content') or {}).get('raw') or '')
def sha(text): return hashlib.sha256(text.encode('utf-8')).hexdigest()

def public_count(kind):
    _,h=req('GET',f'/{kind}?status=publish&per_page=1&_fields=id')
    return int(h.get('X-WP-Total','0'))

def page_edit(page_id):
    return get(f'/pages/{page_id}?context=edit&_fields=id,slug,status,title,content,link')

def main():
    before={'posts':public_count('posts'),'pages':public_count('pages')}

    live_before=page_edit(LIVE_PAGE_ID)
    live_raw_before=raw_content(live_before)
    live_sha_before=sha(live_raw_before)
    if (live_before['slug'],live_before['status'])!=(LIVE_SLUG,'publish'):
        raise SystemExit('LIVE_PAGE_IDENTITY_FAILED '+repr((live_before['slug'],live_before['status'])))
    if live_sha_before!=LIVE_EXPECTED_SHA:
        raise SystemExit('LIVE_PAGE_STALE_SOURCE_GUARD '+live_sha_before)

    preview_before=page_edit(PREVIEW_PAGE_ID)
    if (preview_before['slug'],preview_before['status'])!=(PREVIEW_SLUG,'draft'):
        raise SystemExit('PREVIEW_PAGE_IDENTITY_FAILED '+repr((preview_before['slug'],preview_before['status'])))
    preview_raw_before=raw_content(preview_before)
    if not any(m in preview_raw_before for m in ALLOWED_PREVIEW_MARKERS):
        raise SystemExit('PREVIEW_MARKER_GUARD_FAILED')

    template=Path(__file__).with_name('content.template.html').read_text(encoding='utf-8')
    if template.count(MARKER)!=1:
        raise SystemExit('SOURCE_MARKER_COUNT_FAILED')
    if 'ランドクルーザーFJ' in template or 'landcruiser-fj' in template:
        raise SystemExit('FJ_COPY_MUST_NOT_APPEAR')

    title='クルマ｜レクサスUX（現行改善版）'
    write_needed=(preview_raw_before!=template or preview_before['title']['raw']!=title)
    if write_needed:
        post(f'/pages/{PREVIEW_PAGE_ID}',{'title':title,'content':template,'status':'draft'})

    preview_after=page_edit(PREVIEW_PAGE_ID)
    raw=raw_content(preview_after)
    checks={
        'draft':preview_after['status']=='draft',
        'slug':preview_after['slug']==PREVIEW_SLUG,
        'marker_once':raw.count(MARKER)==1,
        'one_custom_html':raw.count('<!-- wp:html -->')==1,
        'four_details':raw.count('<!-- wp:details ')==4,
        'four_top_picks':raw.count('class="tq-pick"')==4,
        'four_stats':raw.count('class="tq-stat"')==4,
        'swell_latest':'<!-- wp:loos/post-list' in raw and '"catID":"10"' in raw,
        'hero':'IMG_2012.jpeg' in raw and 'クルマで、<br>どこまで行こう。' in raw,
        'ux_review':'https://tsurikue.com/lexus-ux-review/' in raw,
        'ux_regret':'https://tsurikue.com/ux-koukai/' in raw,
        'ux_used':'https://tsurikue.com/lexus-ux-used/' in raw,
        'ux_resale':'https://tsurikue.com/ux-resale/' in raw,
        'archive':'https://tsurikue.com/category/car/' in raw,
        'no_fj':'ランドクルーザーFJ' not in raw and 'landcruiser-fj' not in raw,
        'no_old_duplicate_heading':'実際に乗って、いま伝えたいこと。' not in raw,
    }
    if not all(checks.values()):
        raise SystemExit('PREVIEW_VERIFY_FAILED '+json.dumps(checks,ensure_ascii=False))

    blocks={k:len(re.findall(r'<!--\s+wp:'+re.escape(k)+r'\b',raw)) for k in ('html','group','cover','heading','paragraph','details','list','buttons','button','loos/post-list')}

    live_after=page_edit(LIVE_PAGE_ID)
    live_sha_after=sha(raw_content(live_after))
    if live_after['status']!='publish' or live_sha_after!=live_sha_before:
        raise SystemExit('LIVE_PAGE_CHANGED')

    after={'posts':public_count('posts'),'pages':public_count('pages')}
    if before!=after:
        raise SystemExit('PUBLIC_COUNTS_CHANGED '+repr({'before':before,'after':after}))

    out={
        'ok':True,
        'page_id':PREVIEW_PAGE_ID,
        'slug':preview_after['slug'],
        'status':preview_after['status'],
        'written':write_needed,
        'preview_sha':sha(raw),
        'live_page':{'id':LIVE_PAGE_ID,'status':live_after['status'],'sha':live_sha_after,'unchanged':live_sha_after==live_sha_before},
        'public_before':before,
        'public_after':after,
        'checks':checks,
        'block_counts':blocks,
    }
    print(json.dumps(out,ensure_ascii=False))

if __name__=='__main__':
    main()
