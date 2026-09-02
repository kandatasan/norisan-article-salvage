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
PREVIEW_SLUG = 'odekake-v2-preview'
TITLE = 'おでかけ｜広島・江田島・山口・山陰'
MARKER = 'tsurikue-category-hub:v2:outing-region-accordion-preview'
SCRIPT_MARKER = 'tq-outing-auto-index:v2'
HERO_URL = 'https://tsurikue.com/wp-content/uploads/2026/05/img_4588.jpg'
OUTING_CATEGORY_SLUG = 'sightseeing-leisure'
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
        'User-Agent': 'tsurikue-outing-v2-preview/1.0',
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


def clean_title(value):
    if isinstance(value, dict):
        value = value.get('rendered') or value.get('raw') or ''
    value = re.sub(r'<[^>]+>', '', value or '')
    return html.unescape(value).strip()


def page_state(page):
    content = raw_field(page, 'content')
    return {
        'id': int(page.get('id') or 0),
        'slug': page.get('slug'),
        'status': page.get('status'),
        'title': clean_title(page.get('title')),
        'content_sha256': hashlib.sha256(content.encode()).hexdigest(),
    }


def get_live_page():
    row, _ = req(
        f'/pages/{LIVE_PAGE_ID}?context=edit&_fields=id,slug,status,title,content,link'
    )
    if row.get('id') != LIVE_PAGE_ID or row.get('slug') != LIVE_SLUG or row.get('status') != 'publish':
        raise RuntimeError('LIVE_PAGE_IDENTITY_MISMATCH ' + json.dumps(page_state(row), ensure_ascii=False))
    return row


def all_terms(endpoint):
    rows, _ = req(f'/{endpoint}?context=edit&per_page=100&hide_empty=false&_fields=id,name,slug,parent,count,link')
    return rows


def exact_term(rows, slug, label):
    matches = [row for row in rows if row.get('slug') == slug]
    if len(matches) != 1:
        raise RuntimeError(f'{label}_TERM_IDENTITY_FAILED {slug} ' + json.dumps(matches, ensure_ascii=False))
    return matches[0]


def region_posts(category_id, tag_id):
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
    out = []
    for post in posts:
        title = html.escape(clean_title(post.get('title')))
        url = html.escape(post.get('link') or '', quote=True)
        if not title or not url:
            raise RuntimeError('INVALID_FALLBACK_POST ' + json.dumps(post, ensure_ascii=False))
        out.append(f'<li><a href="{url}">{title}</a></li>')
    return '\n'.join(out)


def build_desired():
    categories = all_terms('categories')
    outing = exact_term(categories, OUTING_CATEGORY_SLUG, 'OUTING_CATEGORY')
    if int(outing.get('id') or 0) != 7:
        raise RuntimeError('OUTING_CATEGORY_ID_CHANGED ' + json.dumps(outing, ensure_ascii=False))

    tags = all_terms('tags')
    tag_by_slug = {row.get('slug'): row for row in tags}
    needed_slugs = [slug for _, slug in REGIONS.values()] + list(PURPOSE_TAGS)
    missing = [slug for slug in needed_slugs if slug not in tag_by_slug]
    if missing:
        raise RuntimeError('MISSING_REQUIRED_TAGS ' + json.dumps(missing, ensure_ascii=False))

    groups = {}
    for key, (name, slug) in REGIONS.items():
        term = tag_by_slug[slug]
        rows = region_posts(int(outing['id']), int(term['id']))
        if not rows:
            raise RuntimeError(f'EMPTY_REGION_GROUP {key}')
        groups[key] = {'name': name, 'slug': slug, 'tag': term, 'posts': rows}

    tpl = (ROOT / 'content.template.html').read_text(encoding='utf-8')
    replacements = {
        '{{OUTING_CATEGORY_ID}}': str(int(outing['id'])),
        '{{HIROSHIMA_TAG_ID}}': str(int(groups['hiroshima']['tag']['id'])),
        '{{ETAJIMA_TAG_ID}}': str(int(groups['etajima']['tag']['id'])),
        '{{YAMAGUCHI_TAG_ID}}': str(int(groups['yamaguchi']['tag']['id'])),
        '{{SANIN_TAG_ID}}': str(int(groups['sanin']['tag']['id'])),
        '{{HIROSHIMA_COUNT}}': str(len(groups['hiroshima']['posts'])),
        '{{ETAJIMA_COUNT}}': str(len(groups['etajima']['posts'])),
        '{{YAMAGUCHI_COUNT}}': str(len(groups['yamaguchi']['posts'])),
        '{{SANIN_COUNT}}': str(len(groups['sanin']['posts'])),
        '{{HIROSHIMA_ITEMS}}': list_items(groups['hiroshima']['posts']),
        '{{ETAJIMA_ITEMS}}': list_items(groups['etajima']['posts']),
        '{{YAMAGUCHI_ITEMS}}': list_items(groups['yamaguchi']['posts']),
        '{{SANIN_ITEMS}}': list_items(groups['sanin']['posts']),
    }
    for token, value in replacements.items():
        tpl = tpl.replace(token, value)
    unresolved = [token for token in replacements if token in tpl]
    if unresolved:
        raise RuntimeError('UNRESOLVED_TEMPLATE_PLACEHOLDER ' + json.dumps(unresolved))

    source = {
        'outing_category': {'id': int(outing['id']), 'slug': outing['slug'], 'count': int(outing.get('count') or 0)},
        'regions': {
            key: {
                'tag_id': int(value['tag']['id']),
                'tag_slug': value['slug'],
                'posts': len(value['posts']),
            }
            for key, value in groups.items()
        },
        'purpose_tags': {
            slug: {'id': int(tag_by_slug[slug]['id']), 'name': tag_by_slug[slug]['name']}
            for slug in PURPOSE_TAGS
        },
    }
    return tpl, source


def checks(raw, rendered):
    exact_placeholders = [
        '{{OUTING_CATEGORY_ID}}',
        '{{HIROSHIMA_TAG_ID}}', '{{ETAJIMA_TAG_ID}}', '{{YAMAGUCHI_TAG_ID}}', '{{SANIN_TAG_ID}}',
        '{{HIROSHIMA_COUNT}}', '{{ETAJIMA_COUNT}}', '{{YAMAGUCHI_COUNT}}', '{{SANIN_COUNT}}',
        '{{HIROSHIMA_ITEMS}}', '{{ETAJIMA_ITEMS}}', '{{YAMAGUCHI_ITEMS}}', '{{SANIN_ITEMS}}',
    ]
    return {
        'marker_once': raw.count(MARKER) == 1,
        'single_custom_html': raw.count('<!-- wp:html -->') == 1,
        'four_details': raw.count('<!-- wp:details ') == 4,
        'script_raw': SCRIPT_MARKER in raw and '<script>' in raw,
        'script_rendered': SCRIPT_MARKER in rendered and '<script>' in rendered,
        'hero': HERO_URL in raw and '今日は、どこ行く？' in raw,
        'region_labels': all(label in raw for label in ['>広島 <', '>江田島 <', '>山口 <', '>山陰 <']),
        'region_fallback_lists': all(raw.count(f'tq-auto-{key}') >= 2 for key in REGIONS),
        'purpose_native_buttons': raw.count('<!-- wp:buttons ') >= 2 and all(f'https://tsurikue.com/tag/{slug}/' in raw for slug in PURPOSE_TAGS),
        'swell_post_list': '<!-- wp:loos/post-list' in raw and '"catID":"7"' in raw and '"listCount":6' in raw,
        'archive_link': 'https://tsurikue.com/category/sightseeing-leisure/' in raw,
        'no_100vw': '100vw' not in raw,
        'no_negative_viewport_margin': '50% - 50vw' not in raw and 'margin-left:calc(50%' not in raw,
        'no_exact_placeholders': not any(token in raw for token in exact_placeholders),
        'no_emoji': not bool(re.search('[\U0001F300-\U0001FAFF]', raw)),
    }


def find_preview_pages():
    params = urllib.parse.urlencode({
        'context': 'edit',
        'slug': PREVIEW_SLUG,
        'status': 'any',
        'per_page': 100,
        '_fields': 'id,slug,status,title,content,link',
    })
    rows, _ = req('/pages?' + params)
    return rows


before_public = count_public()
live_before = get_live_page()
live_state_before = page_state(live_before)
desired, source = build_desired()
pre_checks = checks(desired, desired)
if not all(pre_checks.values()):
    raise RuntimeError('DESIRED_STRUCTURE_FAILED ' + json.dumps(pre_checks, ensure_ascii=False))

existing = find_preview_pages()
if len(existing) > 1:
    raise RuntimeError('AMBIGUOUS_PREVIEW_PAGES ' + json.dumps([page_state(p) for p in existing], ensure_ascii=False))

action = None
if existing:
    preview = existing[0]
    preview_raw = raw_field(preview, 'content')
    if preview.get('status') != 'draft':
        raise RuntimeError('PREVIEW_NOT_DRAFT ' + json.dumps(page_state(preview), ensure_ascii=False))
    if MARKER not in preview_raw:
        raise RuntimeError('UNRELATED_PREVIEW_SLUG_REFUSED ' + json.dumps(page_state(preview), ensure_ascii=False))
    req(f"/pages/{preview['id']}", method='POST', data={'title': TITLE, 'content': desired})
    preview_id = int(preview['id'])
    action = 'UPDATED_OUTING_V2_PREVIEW'
else:
    created, _ = req('/pages', method='POST', data={
        'title': TITLE,
        'slug': PREVIEW_SLUG,
        'content': desired,
        'status': 'draft',
    })
    preview_id = int(created.get('id') or 0)
    if not preview_id:
        raise RuntimeError('PREVIEW_CREATE_RETURNED_NO_ID')
    action = 'CREATED_OUTING_V2_PREVIEW'

final, _ = req(f'/pages/{preview_id}?context=edit&_fields=id,slug,status,title,content,link')
final_raw = raw_field(final, 'content')
final_rendered = (final.get('content') or {}).get('rendered') or ''
final_checks = checks(final_raw, final_rendered)
if final.get('status') != 'draft' or final.get('slug') != PREVIEW_SLUG or clean_title(final.get('title')) != TITLE:
    raise RuntimeError('FINAL_PREVIEW_IDENTITY_FAILED ' + json.dumps(page_state(final), ensure_ascii=False))
if not all(final_checks.values()):
    raise RuntimeError('FINAL_PREVIEW_STRUCTURE_FAILED ' + json.dumps(final_checks, ensure_ascii=False))

live_after = get_live_page()
live_state_after = page_state(live_after)
if live_state_after != live_state_before:
    raise RuntimeError('LIVE_OUTING_PAGE_CHANGED ' + json.dumps({'before': live_state_before, 'after': live_state_after}, ensure_ascii=False))

after_public = count_public()
if after_public != before_public:
    raise RuntimeError('PUBLIC_COUNTS_CHANGED ' + json.dumps({'before': before_public, 'after': after_public}, ensure_ascii=False))

report = {
    'ok': True,
    'action': action,
    'preview': {
        'id': preview_id,
        'slug': final['slug'],
        'status': final['status'],
        'title': clean_title(final.get('title')),
        'link': final.get('link'),
        'content_sha256': hashlib.sha256(final_raw.encode()).hexdigest(),
    },
    'live_page_unchanged': live_state_after == live_state_before,
    'live_page': live_state_after,
    'source': source,
    'checks': final_checks,
    'public_before': before_public,
    'public_after': after_public,
    'wordpress_write_count': writes,
    'publish_count': 0,
    'delete_count': 0,
    'block_counts': {
        'html': final_raw.count('<!-- wp:html -->'),
        'details': final_raw.count('<!-- wp:details '),
        'buttons': final_raw.count('<!-- wp:button'),
        'swell_post_list': final_raw.count('<!-- wp:loos/post-list'),
    },
}
print(json.dumps(report, ensure_ascii=False, indent=2))
