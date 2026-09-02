#!/usr/bin/env python3
import base64
import hashlib
import html
import json
import os
import pathlib
import re
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = 'https://tsurikue.com/wp-json/wp/v2'
LIVE_PAGE_ID = 3154
LIVE_SLUG = 'odekake'
LIVE_TITLE = 'おでかけ'
EXPECTED_OLD_LIVE_SHA = 'd687663011b34078b0e53b8f3b3639d32efd41f097427325d604d9af283d9b34'
PREVIEW_PAGE_ID = 3361
PREVIEW_SLUG = 'odekake-v2-preview'
PREVIEW_TITLE = 'おでかけ｜広島・江田島・山口・山陰・ちょっと遠くへ'
OLD_PREVIEW_MARKER = 'tsurikue-category-hub:v2:outing-region-accordion-preview'
MARKER = 'tsurikue-category-hub:v3:outing-region-accordion-final'
SCRIPT_MARKER = 'tq-outing-auto-index:v3'
HERO_URL = 'https://tsurikue.com/wp-content/uploads/2026/05/img_4588.jpg'
OUTING_CATEGORY_SLUG = 'sightseeing-leisure'
FAR_TAG_NAME = 'ちょっと遠くへ'
REGIONS = {
    'hiroshima': ('広島', 'hiroshima'),
    'etajima': ('江田島', 'etajima'),
    'yamaguchi': ('山口', 'yamaguchi'),
    'sanin': ('山陰', 'sanin'),
}
PURPOSE_TAGS = {
    'road-trip': 'ドライブ',
    'stay': '宿泊',
    'family-outing': '子どもと遊ぶ',
    'experience-spot': '体験スポット',
}
ROOT = pathlib.Path(__file__).resolve().parent
USER = os.environ['TSURIKUE_WP_USER']
APP = os.environ['TSURIKUE_WP_APP_PASSWORD']
AUTH = 'Basic ' + base64.b64encode(f'{USER}:{APP}'.encode()).decode()
writes = 0


def req(path, method='GET', data=None, timeout=60, retries=4):
    global writes
    headers = {
        'Authorization': AUTH,
        'Accept': 'application/json',
        'User-Agent': 'tsurikue-outing-v3-live/1.0',
    }
    body = None
    if data is not None:
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        headers['Content-Type'] = 'application/json; charset=utf-8'
    last = None
    for i in range(retries):
        try:
            request = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read()
                total = response.headers.get('X-WP-Total')
                if method not in ('GET', 'HEAD'):
                    writes += 1
                return json.loads(raw.decode('utf-8')), total
        except (urllib.error.URLError, TimeoutError) as exc:
            last = exc
            if i + 1 == retries:
                raise
            time.sleep(2 * (i + 1))
    raise last


def count_public():
    _, posts = req('/posts?status=publish&per_page=1&_fields=id')
    _, pages = req('/pages?status=publish&per_page=1&_fields=id')
    return {'posts': int(posts or 0), 'pages': int(pages or 0)}


def raw_field(row, key):
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get('raw') or value.get('rendered') or ''
    return str(value)


def clean_text(value):
    if isinstance(value, dict):
        value = value.get('raw') or value.get('rendered') or ''
    value = re.sub(r'<[^>]+>', '', value or '')
    return html.unescape(value).strip()


def sha(raw):
    return hashlib.sha256(raw.encode()).hexdigest()


def page_state(page):
    raw = raw_field(page, 'content')
    return {
        'id': int(page.get('id') or 0),
        'slug': page.get('slug'),
        'status': page.get('status'),
        'title': clean_text(page.get('title')),
        'content_sha256': sha(raw),
    }


def get_page(page_id):
    row, _ = req(f'/pages/{page_id}?context=edit&_fields=id,slug,status,title,content,link')
    return row


def all_terms(endpoint):
    rows, _ = req(f'/{endpoint}?context=edit&per_page=100&hide_empty=false&_fields=id,name,slug,parent,count,link')
    return rows


def exact_slug(rows, slug, label):
    found = [row for row in rows if row.get('slug') == slug]
    if len(found) != 1:
        raise RuntimeError(f'{label}_TERM_IDENTITY_FAILED {slug} ' + json.dumps(found, ensure_ascii=False))
    return found[0]


def exact_name(rows, name, label):
    found = [row for row in rows if clean_text(row.get('name')) == name]
    if len(found) != 1:
        raise RuntimeError(f'{label}_TERM_NAME_FAILED {name} ' + json.dumps(found, ensure_ascii=False))
    return found[0]


def tagged_posts(category_id, tag_id):
    params = urllib.parse.urlencode({
        'categories': category_id,
        'tags': tag_id,
        'status': 'publish',
        'per_page': 100,
        'orderby': 'date',
        'order': 'desc',
        '_fields': 'id,slug,link,title,date',
    })
    rows, _ = req('/posts?' + params)
    return rows


def list_items(posts):
    items = []
    for post in posts:
        title = html.escape(clean_text(post.get('title')))
        url = html.escape(post.get('link') or '', quote=True)
        if not title or not url:
            raise RuntimeError('INVALID_FALLBACK_POST ' + json.dumps(post, ensure_ascii=False))
        items.append(f'<li><a href="{url}">{title}</a></li>')
    return '\n'.join(items)


def build_desired():
    categories = all_terms('categories')
    outing = exact_slug(categories, OUTING_CATEGORY_SLUG, 'OUTING_CATEGORY')
    if int(outing.get('id') or 0) != 7:
        raise RuntimeError('OUTING_CATEGORY_ID_CHANGED ' + json.dumps(outing, ensure_ascii=False))

    tags = all_terms('tags')
    tag_by_slug = {row.get('slug'): row for row in tags}
    required_slugs = [slug for _, slug in REGIONS.values()] + list(PURPOSE_TAGS)
    missing = [slug for slug in required_slugs if slug not in tag_by_slug]
    if missing:
        raise RuntimeError('MISSING_REQUIRED_TAGS ' + json.dumps(missing, ensure_ascii=False))

    far_tag = exact_name(tags, FAR_TAG_NAME, 'FAR_TAG')
    groups = {}
    for key, (name, slug) in REGIONS.items():
        term = tag_by_slug[slug]
        posts = tagged_posts(int(outing['id']), int(term['id']))
        if not posts:
            raise RuntimeError(f'EMPTY_REGION_GROUP {key}')
        groups[key] = {'name': name, 'tag': term, 'posts': posts}

    far_posts = tagged_posts(int(outing['id']), int(far_tag['id']))
    if not far_posts:
        raise RuntimeError('EMPTY_FAR_GROUP ' + json.dumps({'tag': far_tag}, ensure_ascii=False))
    groups['far'] = {'name': FAR_TAG_NAME, 'tag': far_tag, 'posts': far_posts}

    tpl = (ROOT / 'content.template.html').read_text(encoding='utf-8')
    replacements = {
        '{{OUTING_CATEGORY_ID}}': str(int(outing['id'])),
        '{{HIROSHIMA_TAG_ID}}': str(int(groups['hiroshima']['tag']['id'])),
        '{{ETAJIMA_TAG_ID}}': str(int(groups['etajima']['tag']['id'])),
        '{{YAMAGUCHI_TAG_ID}}': str(int(groups['yamaguchi']['tag']['id'])),
        '{{SANIN_TAG_ID}}': str(int(groups['sanin']['tag']['id'])),
        '{{FAR_TAG_ID}}': str(int(groups['far']['tag']['id'])),
        '{{HIROSHIMA_COUNT}}': str(len(groups['hiroshima']['posts'])),
        '{{ETAJIMA_COUNT}}': str(len(groups['etajima']['posts'])),
        '{{YAMAGUCHI_COUNT}}': str(len(groups['yamaguchi']['posts'])),
        '{{SANIN_COUNT}}': str(len(groups['sanin']['posts'])),
        '{{FAR_COUNT}}': str(len(groups['far']['posts'])),
        '{{HIROSHIMA_ITEMS}}': list_items(groups['hiroshima']['posts']),
        '{{ETAJIMA_ITEMS}}': list_items(groups['etajima']['posts']),
        '{{YAMAGUCHI_ITEMS}}': list_items(groups['yamaguchi']['posts']),
        '{{SANIN_ITEMS}}': list_items(groups['sanin']['posts']),
        '{{FAR_ITEMS}}': list_items(groups['far']['posts']),
    }
    for token, value in replacements.items():
        tpl = tpl.replace(token, value)
    unresolved = [token for token in replacements if token in tpl]
    if unresolved:
        raise RuntimeError('UNRESOLVED_TEMPLATE_PLACEHOLDER ' + json.dumps(unresolved))

    source = {
        'outing_category': {'id': int(outing['id']), 'count': int(outing.get('count') or 0)},
        'groups': {
            key: {
                'name': value['name'],
                'tag_id': int(value['tag']['id']),
                'tag_slug': value['tag'].get('slug'),
                'posts': len(value['posts']),
                'post_ids': [int(p['id']) for p in value['posts']],
            }
            for key, value in groups.items()
        },
    }
    return tpl, source


def checks(raw, rendered):
    exact_placeholders = [
        '{{OUTING_CATEGORY_ID}}',
        '{{HIROSHIMA_TAG_ID}}', '{{ETAJIMA_TAG_ID}}', '{{YAMAGUCHI_TAG_ID}}', '{{SANIN_TAG_ID}}', '{{FAR_TAG_ID}}',
        '{{HIROSHIMA_COUNT}}', '{{ETAJIMA_COUNT}}', '{{YAMAGUCHI_COUNT}}', '{{SANIN_COUNT}}', '{{FAR_COUNT}}',
        '{{HIROSHIMA_ITEMS}}', '{{ETAJIMA_ITEMS}}', '{{YAMAGUCHI_ITEMS}}', '{{SANIN_ITEMS}}', '{{FAR_ITEMS}}',
    ]
    return {
        'marker_once': raw.count(MARKER) == 1,
        'single_custom_html': raw.count('<!-- wp:html -->') == 1,
        'five_details': raw.count('<!-- wp:details ') == 5,
        'script_raw': SCRIPT_MARKER in raw and '<script>' in raw,
        'script_rendered': SCRIPT_MARKER in rendered and '<script>' in rendered,
        'hero': HERO_URL in raw and '今日は、どこ行く？' in raw,
        'region_labels': all(label in raw for label in ['>広島 <', '>江田島 <', '>山口 <', '>山陰 <', '>ちょっと遠くへ <']),
        'fallback_lists': all(raw.count(f'tq-auto-{key}') >= 2 for key in ['hiroshima','etajima','yamaguchi','sanin','far']),
        'purpose_native_buttons': raw.count('<!-- wp:buttons ') >= 2 and all(f'https://tsurikue.com/tag/{slug}/' in raw for slug in PURPOSE_TAGS),
        'swell_post_list': '<!-- wp:loos/post-list' in raw and '"catID":"7"' in raw and '"listCount":6' in raw,
        'archive_link': 'https://tsurikue.com/category/sightseeing-leisure/' in raw,
        'no_100vw': '100vw' not in raw,
        'no_negative_viewport_margin': '50% - 50vw' not in raw and 'margin-left:calc(50%' not in raw,
        'no_exact_placeholders': not any(token in raw for token in exact_placeholders),
        'no_emoji': not bool(re.search('[\U0001F300-\U0001FAFF]', raw)),
    }


before_public = count_public()
live_before = get_page(LIVE_PAGE_ID)
live_before_state = page_state(live_before)
if live_before_state['slug'] != LIVE_SLUG or live_before_state['status'] != 'publish' or live_before_state['title'] != LIVE_TITLE:
    raise RuntimeError('LIVE_PAGE_IDENTITY_MISMATCH ' + json.dumps(live_before_state, ensure_ascii=False))

preview_before = get_page(PREVIEW_PAGE_ID)
preview_before_state = page_state(preview_before)
if preview_before_state['slug'] != PREVIEW_SLUG or preview_before_state['status'] != 'draft':
    raise RuntimeError('PREVIEW_PAGE_IDENTITY_MISMATCH ' + json.dumps(preview_before_state, ensure_ascii=False))
preview_before_raw = raw_field(preview_before, 'content')
if MARKER not in preview_before_raw and OLD_PREVIEW_MARKER not in preview_before_raw:
    raise RuntimeError('PREVIEW_MARKER_MISMATCH ' + json.dumps(preview_before_state, ensure_ascii=False))

desired, source = build_desired()
pre_checks = checks(desired, desired)
if not all(pre_checks.values()):
    raise RuntimeError('DESIRED_STRUCTURE_FAILED ' + json.dumps(pre_checks, ensure_ascii=False))

# First make the existing preview the exact completed version and verify it as a draft.
if sha(preview_before_raw) != sha(desired) or MARKER not in preview_before_raw:
    req(f'/pages/{PREVIEW_PAGE_ID}', method='POST', data={'title': PREVIEW_TITLE, 'content': desired, 'status': 'draft'})
preview_final = get_page(PREVIEW_PAGE_ID)
preview_raw = raw_field(preview_final, 'content')
preview_rendered = (preview_final.get('content') or {}).get('rendered') or ''
preview_checks = checks(preview_raw, preview_rendered)
if page_state(preview_final)['status'] != 'draft' or not all(preview_checks.values()):
    raise RuntimeError('PREVIEW_FINAL_VERIFY_FAILED ' + json.dumps({'state': page_state(preview_final), 'checks': preview_checks}, ensure_ascii=False))

live_old_raw = raw_field(live_before, 'content')
live_written = False
if MARKER in live_old_raw:
    live_pre_checks = checks(live_old_raw, (live_before.get('content') or {}).get('rendered') or '')
    if not all(live_pre_checks.values()):
        raise RuntimeError('EXISTING_V3_LIVE_INVALID ' + json.dumps(live_pre_checks, ensure_ascii=False))
else:
    if live_before_state['content_sha256'] != EXPECTED_OLD_LIVE_SHA:
        raise RuntimeError('STALE_LIVE_REFUSED ' + json.dumps({'expected': EXPECTED_OLD_LIVE_SHA, 'actual': live_before_state['content_sha256']}, ensure_ascii=False))
    req(f'/pages/{LIVE_PAGE_ID}', method='POST', data={'content': desired})
    live_written = True

live_final = get_page(LIVE_PAGE_ID)
live_final_raw = raw_field(live_final, 'content')
live_final_rendered = (live_final.get('content') or {}).get('rendered') or ''
live_final_state = page_state(live_final)
live_checks = checks(live_final_raw, live_final_rendered)
identity_ok = live_final_state['id'] == LIVE_PAGE_ID and live_final_state['slug'] == LIVE_SLUG and live_final_state['status'] == 'publish' and live_final_state['title'] == LIVE_TITLE
if not identity_ok or not all(live_checks.values()):
    if live_written:
        req(f'/pages/{LIVE_PAGE_ID}', method='POST', data={'content': live_old_raw})
    raise RuntimeError('LIVE_FINAL_VERIFY_FAILED_ROLLED_BACK ' + json.dumps({'state': live_final_state, 'checks': live_checks}, ensure_ascii=False))

after_public = count_public()
if after_public != before_public:
    if live_written:
        req(f'/pages/{LIVE_PAGE_ID}', method='POST', data={'content': live_old_raw})
    raise RuntimeError('PUBLIC_COUNTS_CHANGED_ROLLED_BACK ' + json.dumps({'before': before_public, 'after': after_public}, ensure_ascii=False))

report = {
    'ok': True,
    'action': 'UPDATED_LIVE_OUTING_V3' if live_written else 'VERIFIED_EXISTING_LIVE_OUTING_V3',
    'live': live_final_state,
    'preview': page_state(preview_final),
    'source': source,
    'checks': live_checks,
    'public_before': before_public,
    'public_after': after_public,
    'wordpress_write_count': writes,
    'live_write_count': 1 if live_written else 0,
    'publish_transition_count': 0,
    'delete_count': 0,
    'old_live_content_sha256': live_before_state['content_sha256'],
    'new_live_content_sha256': live_final_state['content_sha256'],
    'block_counts': {
        'html': live_final_raw.count('<!-- wp:html -->'),
        'details': live_final_raw.count('<!-- wp:details '),
        'buttons': live_final_raw.count('<!-- wp:button'),
        'swell_post_list': live_final_raw.count('<!-- wp:loos/post-list'),
    },
}
path = os.environ.get('TQ_OUTING_RESULT_PATH')
if path:
    pathlib.Path(path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
