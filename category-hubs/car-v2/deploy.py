#!/usr/bin/env python3
import base64
import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = 'https://tsurikue.com/wp-json/wp/v2'
CAR_ID = 10
LEGACY_WASH_ID = 11
LIVE_CAR_PAGE_ID = 3294
PREVIEW_SLUG = 'car-guide-v2-preview'
MARKER = 'tsurikue-category-hub:v2:car-model-first-preview'
UX_POST_IDS = [2975,2962,2956,2948,2907,2902,2897,2886,2881,2874,2870,2222,2517,2186,2329,2240,2530]
GENERIC_CAR_POST_ID = 2575
ALL_STATUSES = 'publish,draft,pending,private,future'

USER = os.environ.get('TSURIKUE_WP_USER')
PASS = os.environ.get('TSURIKUE_WP_APP_PASSWORD')
if not USER or not PASS:
    raise SystemExit('Missing TSURIKUE_WP_USER / TSURIKUE_WP_APP_PASSWORD')
TOKEN = base64.b64encode(f'{USER}:{PASS}'.encode()).decode()
HEADERS = {
    'Authorization': 'Basic ' + TOKEN,
    'Accept': 'application/json',
    'Content-Type': 'application/json; charset=utf-8',
    'User-Agent': 'tsurikue-car-model-first-v2/1.0',
}

def req(method, path, data=None):
    body = None if data is None else json.dumps(data, ensure_ascii=False).encode('utf-8')
    r = urllib.request.Request(BASE + path, data=body, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(r, timeout=50) as x:
            raw = x.read().decode('utf-8')
            return (json.loads(raw) if raw else None), dict(x.headers)
    except urllib.error.HTTPError as e:
        detail = e.read().decode('utf-8', errors='replace')
        raise RuntimeError(f'{method} {path} -> HTTP {e.code}: {detail[:1200]}') from e

def get(path): return req('GET', path)[0]
def post(path, data): return req('POST', path, data)[0]

def q(path, **params):
    return get(path + '?' + urllib.parse.urlencode(params))

def raw_content(item):
    return ((item.get('content') or {}).get('raw') or '')

def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def public_count(kind):
    _, headers = req('GET', f'/{kind}?status=publish&per_page=1&_fields=id')
    return int(headers.get('X-WP-Total', '0'))

def find_category(slug):
    items = q('/categories', slug=slug, context='edit', per_page=20, _fields='id,name,slug,parent,count,link')
    return items[0] if items else None

def ensure_car_parent():
    car = find_category('car')
    if not car or car['id'] != CAR_ID or car['parent'] != 0:
        raise SystemExit('CAR_PARENT_MISMATCH ' + repr(car))
    return car

def ensure_ux_category():
    existing = find_category('lexus-ux')
    if existing:
        if existing['parent'] != CAR_ID:
            raise SystemExit('LEXUS_UX_PARENT_MISMATCH ' + repr(existing))
        return existing
    legacy = get(f'/categories/{LEGACY_WASH_ID}?context=edit&_fields=id,name,slug,parent,count,link')
    if legacy['parent'] != CAR_ID:
        raise SystemExit('LEGACY_WASH_PARENT_MISMATCH ' + repr(legacy))
    if legacy['slug'] not in ('car-goods-wash', 'lexus-ux'):
        raise SystemExit('LEGACY_CATEGORY_UNEXPECTED ' + repr(legacy))
    updated = post(f'/categories/{LEGACY_WASH_ID}', {
        'name': 'レクサスUX',
        'slug': 'lexus-ux',
        'parent': CAR_ID,
        'description': 'レクサスUXの購入・使い勝手・本音・売却など、実体験を中心にまとめています。',
    })
    return updated

def ensure_fj_category():
    existing = find_category('landcruiser-fj')
    if existing:
        if existing['parent'] != CAR_ID:
            raise SystemExit('FJ_PARENT_MISMATCH ' + repr(existing))
        return existing
    return post('/categories', {
        'name': 'ランドクルーザーFJ',
        'slug': 'landcruiser-fj',
        'parent': CAR_ID,
        'description': 'ランドクルーザーFJの納車後レビュー・使い勝手・遊び方などをまとめるカテゴリです。',
    })

def post_edit(post_id):
    return get(f'/posts/{post_id}?context=edit&_fields=id,slug,status,title,categories,link')

def set_categories(post_id, wanted_add=(), wanted_remove=()):
    item = post_edit(post_id)
    cats = set(item.get('categories') or [])
    cats.update(wanted_add)
    cats.difference_update(wanted_remove)
    new = sorted(cats)
    if new != sorted(item.get('categories') or []):
        post(f'/posts/{post_id}', {'categories': new})
        changed = True
    else:
        changed = False
    after = post_edit(post_id)
    if sorted(after.get('categories') or []) != new:
        raise SystemExit(f'CATEGORY_WRITE_VERIFY_FAILED post={post_id} expected={new} actual={after.get("categories")}')
    return {'id': post_id, 'slug': after['slug'], 'status': after['status'], 'categories': after['categories'], 'changed': changed}

def active_posts_for_category(cat_id):
    out=[]
    page=1
    while True:
        items=q('/posts', categories=cat_id, context='edit', status=ALL_STATUSES, per_page=100, page=page,
                _fields='id,slug,status,title,categories,link')
        out.extend(items)
        if len(items)<100: break
        page += 1
    return out

def render_template(ux_id, fj_id):
    path = Path(__file__).with_name('content.template.html')
    text = path.read_text(encoding='utf-8')
    text = text.replace('{{UX_CATEGORY_ID}}', str(ux_id)).replace('{{FJ_CATEGORY_ID}}', str(fj_id))
    if '{{' in text or '}}' in text:
        raise SystemExit('UNRESOLVED_TEMPLATE_PLACEHOLDER')
    return text

def find_preview_page():
    items = q('/pages', slug=PREVIEW_SLUG, context='edit', status='publish,draft,pending,private,future,trash', per_page=20,
              _fields='id,slug,status,title,content,link')
    if len(items) > 1:
        raise SystemExit('PREVIEW_PAGE_NOT_UNIQUE ' + repr([(x['id'],x['status']) for x in items]))
    return items[0] if items else None

def upsert_preview(content):
    page = find_preview_page()
    title = 'クルマ｜レクサスUX・ランドクルーザーFJ'
    if page:
        if page['status'] != 'draft':
            raise SystemExit('PREVIEW_PAGE_NOT_DRAFT ' + repr((page['id'],page['status'])))
        if MARKER in raw_content(page) and raw_content(page) == content and page['title']['raw'] == title:
            return page, False
        updated = post(f"/pages/{page['id']}", {'title': title, 'content': content, 'status': 'draft'})
        return updated, True
    created = post('/pages', {'title': title, 'slug': PREVIEW_SLUG, 'content': content, 'status': 'draft'})
    return created, True

def verify_preview(page_id, ux_id, fj_id):
    page = get(f'/pages/{page_id}?context=edit&_fields=id,slug,status,title,content,link')
    raw = raw_content(page)
    checks = {
        'status_draft': page['status'] == 'draft',
        'slug_preview': page['slug'] == PREVIEW_SLUG,
        'marker': MARKER in raw,
        'one_custom_html': raw.count('<!-- wp:html -->') == 1,
        'two_details': raw.count('<!-- wp:details') == 2,
        'two_latest_posts': raw.count('<!-- wp:latest-posts') == 2,
        'swell_latest': '<!-- wp:loos/post-list' in raw and '"catID":"10"' in raw,
        'ux_filter': f'"categories":[{ux_id}]' in raw,
        'fj_filter': f'"categories":[{fj_id}]' in raw,
        'no_placeholder': '{{' not in raw and '}}' not in raw,
        'hero': 'IMG_2012.jpeg' in raw,
        'model_first_copy': 'どのクルマを見る？' in raw and 'レクサスUX' in raw and 'ランドクルーザーFJ' in raw,
    }
    if not all(checks.values()):
        raise SystemExit('PREVIEW_VERIFY_FAILED ' + json.dumps(checks, ensure_ascii=False))
    return page, checks

def main():
    before_counts = {'posts': public_count('posts'), 'pages': public_count('pages')}
    car = ensure_car_parent()
    live_before = get(f'/pages/{LIVE_CAR_PAGE_ID}?context=edit&_fields=id,slug,status,title,content,link')
    if live_before['slug'] != 'car-guide' or live_before['status'] != 'publish':
        raise SystemExit('LIVE_CAR_PAGE_UNEXPECTED ' + repr((live_before['id'],live_before['slug'],live_before['status'])))
    live_before_sha = sha(raw_content(live_before))

    ux = ensure_ux_category()
    fj = ensure_fj_category()
    ux_id, fj_id = ux['id'], fj['id']

    migrations=[]
    for pid in UX_POST_IDS:
        migrations.append(set_categories(pid, wanted_add=(CAR_ID, ux_id)))
    migrations.append(set_categories(GENERIC_CAR_POST_ID, wanted_add=(CAR_ID,), wanted_remove=(ux_id,)))

    ux_posts = active_posts_for_category(ux_id)
    ux_ids = {p['id'] for p in ux_posts}
    expected_ux = set(UX_POST_IDS)
    unexpected = sorted(ux_ids - expected_ux)
    missing = sorted(expected_ux - ux_ids)
    if unexpected or missing:
        raise SystemExit('UX_CATEGORY_MEMBERSHIP_MISMATCH ' + repr({'unexpected':unexpected,'missing':missing}))
    if GENERIC_CAR_POST_ID in ux_ids:
        raise SystemExit('GENERIC_CAR_ARTICLE_STILL_IN_UX')

    content = render_template(ux_id, fj_id)
    preview, preview_written = upsert_preview(content)
    preview_id = preview['id']
    preview_after, preview_checks = verify_preview(preview_id, ux_id, fj_id)

    live_after = get(f'/pages/{LIVE_CAR_PAGE_ID}?context=edit&_fields=id,slug,status,title,content,link')
    live_after_sha = sha(raw_content(live_after))
    if live_after['status'] != 'publish' or live_after_sha != live_before_sha:
        raise SystemExit('LIVE_CAR_PAGE_CHANGED')

    ux_after = get(f'/categories/{ux_id}?context=edit&_fields=id,name,slug,parent,count,link')
    fj_after = get(f'/categories/{fj_id}?context=edit&_fields=id,name,slug,parent,count,link')
    if (ux_after['name'],ux_after['slug'],ux_after['parent']) != ('レクサスUX','lexus-ux',CAR_ID):
        raise SystemExit('UX_CATEGORY_VERIFY_FAILED ' + repr(ux_after))
    if (fj_after['name'],fj_after['slug'],fj_after['parent']) != ('ランドクルーザーFJ','landcruiser-fj',CAR_ID):
        raise SystemExit('FJ_CATEGORY_VERIFY_FAILED ' + repr(fj_after))
    if find_category('car-goods-wash') is not None:
        raise SystemExit('LEGACY_WASH_SLUG_STILL_EXISTS')

    after_counts = {'posts': public_count('posts'), 'pages': public_count('pages')}
    if before_counts != after_counts:
        raise SystemExit('PUBLIC_COUNTS_CHANGED ' + repr({'before':before_counts,'after':after_counts}))

    result = {
        'ok': True,
        'public_counts_before': before_counts,
        'public_counts_after': after_counts,
        'live_car_page': {'id': LIVE_CAR_PAGE_ID, 'status': live_after['status'], 'sha_unchanged': live_after_sha == live_before_sha},
        'taxonomy': {
            'car': {'id': car['id'], 'slug': car['slug']},
            'lexus_ux': {'id': ux_after['id'], 'slug': ux_after['slug'], 'count': ux_after['count']},
            'landcruiser_fj': {'id': fj_after['id'], 'slug': fj_after['slug'], 'count': fj_after['count']},
            'legacy_wash_slug_exists': False,
        },
        'migration_writes': sum(1 for m in migrations if m['changed']),
        'migration_results': migrations,
        'preview': {'id': preview_id, 'slug': preview_after['slug'], 'status': preview_after['status'], 'written': preview_written, 'checks': preview_checks},
    }
    print('CAR_MODEL_FIRST_V2_AUDIT ' + json.dumps(result, ensure_ascii=False))

if __name__ == '__main__':
    main()
