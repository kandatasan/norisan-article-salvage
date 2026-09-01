import base64
import json
import os
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = 'https://tsurikue.com/wp-json/wp/v2'
CATEGORY_ID = 9
SLUG = 'gourmet-guide'
TITLE = 'グルメ｜広島・旅先で実際に食べたラーメン・ご当地グルメ'
STATUS = 'draft'
MARKER = '<!-- tsurikue-category-hub:v1:gourmet-blocks -->'
CATEGORY_CATEGORY_PLACEHOLDER = '__GOURMET_CATEGORY_ID__'
HERO_URL_CATEGORY_PLACEHOLDER = '__GOURMET_HERO_URL__'
HERO_ID_CATEGORY_PLACEHOLDER = '__GOURMET_HERO_ID__'
HERO_MATCH = '7358'
HERE = pathlib.Path(__file__).resolve().parent
SOURCE = HERE / 'content.html'

user = os.environ['TSURIKUE_WP_USER']
password = os.environ['TSURIKUE_WP_APP_PASSWORD']
token = base64.b64encode(f'{user}:{password}'.encode()).decode()
HEADERS = {
    'Authorization': 'Basic ' + token,
    'Accept': 'application/json',
    'Content-Type': 'application/json; charset=utf-8',
    'User-Agent': 'tsurikue-gourmet-hub-deploy/1.4',
}


def request(path, method='GET', payload=None, attempts=3, timeout=35):
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode('utf-8')
    last = None
    for attempt in range(1, attempts + 1):
        req = urllib.request.Request(BASE + path, data=data, headers=HEADERS, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = response.read().decode('utf-8')
                return json.loads(body) if body else None
        except urllib.error.HTTPError as error:
            body = error.read().decode('utf-8', 'replace')
            if error.code >= 500 and attempt < attempts:
                last = error
                time.sleep(4 * attempt)
                continue
            raise RuntimeError(f'HTTP {error.code} {method} {path}: {body[:800]}') from error
        except Exception as error:
            last = error
            if attempt < attempts:
                time.sleep(4 * attempt)
    raise RuntimeError(
        f'REQUEST_FAILED {method} {path}: {type(last).__name__}: {last}'
    )


def raw(obj, field):
    value = obj.get(field) or {}
    return value.get('raw') or value.get('rendered') or ''


def scalar_text(value):
    if isinstance(value, dict):
        return ' '.join(str(part) for part in value.values() if part)
    return '' if value is None else str(value)


def hero_media_matches(item):
    fields = (
        item.get('source_url'),
        item.get('slug'),
        item.get('alt_text'),
        item.get('title'),
        item.get('caption'),
    )
    haystack = ' '.join(scalar_text(field) for field in fields).lower()
    mime_type = str(item.get('mime_type') or '')
    return HERO_MATCH in haystack and mime_type.startswith('image/')


def image_url_is_live(url):
    if not str(url).startswith('https://tsurikue.com/wp-content/uploads/'):
        return False
    headers = {
        'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
        'Referer': 'https://tsurikue.com/',
        'User-Agent': 'tsurikue-gourmet-hero-check/1.0',
    }
    req = urllib.request.Request(str(url), headers=headers, method='GET')
    try:
        with urllib.request.urlopen(req, timeout=35) as response:
            content_type = response.headers.get('Content-Type', '')
            sample = response.read(1024)
            return response.status < 400 and content_type.startswith('image/') and bool(sample)
    except Exception:
        return False


def find_hero_media():
    fields = 'id,source_url,slug,alt_text,title,caption,mime_type,date'
    queries = [
        urllib.parse.urlencode({
            'context': 'edit',
            'slug': 'img_7358',
            'per_page': 20,
            '_fields': fields,
        }),
        urllib.parse.urlencode({
            'context': 'edit',
            'search': HERO_MATCH,
            'per_page': 100,
            'orderby': 'date',
            'order': 'desc',
            '_fields': fields,
        }),
        urllib.parse.urlencode({
            'context': 'edit',
            'per_page': 100,
            'orderby': 'date',
            'order': 'desc',
            '_fields': fields,
        }),
    ]

    candidates = {}
    errors = []
    for query in queries:
        try:
            items = request('/media?' + query, attempts=3, timeout=40)
        except Exception as error:
            errors.append(f'{type(error).__name__}: {error}')
            continue
        for item in items:
            if hero_media_matches(item) and item.get('id') and item.get('source_url'):
                candidates[item['id']] = item

    ordered = sorted(
        candidates.values(),
        key=lambda item: (str(item.get('date') or ''), int(item.get('id') or 0)),
        reverse=True,
    )
    for item in ordered:
        if image_url_is_live(item['source_url']):
            selected = {
                'id': int(item['id']),
                'source_url': str(item['source_url']),
                'slug': str(item.get('slug') or ''),
                'date': str(item.get('date') or ''),
            }
            print('GOURMET_HERO_MEDIA_FOUND ' + json.dumps(selected, ensure_ascii=False))
            return selected

    raise RuntimeError(
        'IMG_7358_MEDIA_NOT_FOUND_OR_NOT_LIVE '
        + json.dumps({
            'candidate_ids': [item.get('id') for item in ordered],
            'errors': errors,
        }, ensure_ascii=False)
    )


def build_content(hero_media):
    content = SOURCE.read_text(encoding='utf-8')
    if MARKER not in content:
        raise RuntimeError('SOURCE_MARKER_MISSING')

    expected_counts = {
        CATEGORY_PLACEHOLDER: 1,
        HERO_URL_PLACEHOLDER: 2,
        HERO_ID_PLACEHOLDER: 2,
    }
    actual_counts = {
        token: content.count(token)
        for token in expected_counts
    }
    if actual_counts != expected_counts:
        raise RuntimeError(
            'PLACEHOLDER_COUNTS_INVALID '
            + json.dumps(actual_counts, ensure_ascii=False)
        )

    content = content.replace(CATEGORY_PLACEHOLDER, str(CATEGORY_ID))
    content = content.replace(HERO_URL_PLACEHOLDER, hero_media['source_url'])
    content = content.replace(HERO_ID_PLACEHOLDER, str(hero_media['id']))
    unresolved = [
        token for token in expected_counts
        if token in content
    ]
    if unresolved:
        raise RuntimeError('UNRESOLVED_TEMPLATE_TOKENS ' + repr(unresolved))

    forbidden = (
        'tq-global-site-nav-ref',
        'TQ HEADER DRAWER PROTOTYPE',
        'TQ HEADER NAV PROTOTYPE',
        'TQ SITEWIDE HOLIDAY MENU',
    )
    remains = [marker for marker in forbidden if marker in content]
    if remains:
        raise RuntimeError('CUSTOM_NAV_MARKER_IN_SOURCE ' + repr(remains))

    return content

def verify_content(content, hero_media):
    hero_id = int(hero_media['id'])
    hero_url = str(hero_media['source_url'])
    checks = {
        'marker': MARKER in content,
        'category_id': f'"categories":[{CATEGORY_ID}]' in content,
        'latest_block': 'wp:latest-posts' in content,
        'hero': '今日は、<br>なに食べる？' in content,
        'hero_image_url': hero_url in content,
        'hero_image_id': (
            f'"id":{hero_id}' in content
            and f'wp-image-{hero_id}' in content
        ),
        'hero_filename': HERO_MATCH in hero_url.lower(),
        'hero_alt': '皿に盛られた霜降りの焼肉' in content,
        'old_hero_absent': 'img_4017.jpg' not in content,
        'hero_tokens_resolved': (
            HERO_URL_PLACEHOLDER not in content
            and HERO_ID_PLACEHOLDER not in content
        ),
        'archive_link': '/category/gourmet/' in content,
        'temp_nav_absent': 'tq-global-site-nav-ref' not in content,
        'custom_menu_absent': 'TQ SITEWIDE HOLIDAY MENU' not in content,
    }
    if not all(checks.values()):
        raise RuntimeError(
            'VERIFY_CONTENT_FAILED ' + json.dumps(checks, ensure_ascii=False)
        )
    return checks

def find_existing():
    query = urllib.parse.urlencode({
        'slug': SLUG,
        'status': 'draft',
        'context': 'edit',
        'per_page': 2,
        '_fields': 'id,slug,status,title,content,link',
    })
    try:
        pages = request('/pages?' + query, attempts=2, timeout=30)
    except Exception as error:
        # Never create when the duplicate check is uncertain.
        raise RuntimeError(
            f'EXISTING_PAGE_LOOKUP_FAILED_REFUSE_CREATE: {error}'
        ) from error

    if len(pages) > 1:
        raise RuntimeError(
            'MULTIPLE_GOURMET_DRAFTS_FOUND ids=' + repr([page.get('id') for page in pages])
        )
    return pages[0] if pages else None


def main():
    hero_media = find_hero_media()
    content = build_content(hero_media)
    verify_content(content, hero_media)
    existing = find_existing()

    payload = {
        'title': TITLE,
        'slug': SLUG,
        'status': STATUS,
        'content': content,
        'excerpt': (
            '広島の街グルメや旅先で実際に食べたラーメン、肉、海鮮、'
            'ご当地グルメから、次に食べたいものを探せるつりくえ！のグルメ入口です。'
        ),
    }

    if existing:
        page_id = existing.get('id')
        if existing.get('slug') != SLUG or existing.get('status') != STATUS:
            raise RuntimeError(
                f'REFUSE_WRONG_PAGE id={page_id} slug={existing.get("slug")} '
                f'status={existing.get("status")}'
            )
        if MARKER not in raw(existing, 'content'):
            raise RuntimeError(f'REFUSE_OVERWRITE_UNRELATED_PAGE id={page_id}')
        page = request(
            f'/pages/{page_id}',
            method='POST',
            payload=payload,
            attempts=3,
            timeout=45,
        )
        action = 'UPDATED'
    else:
        # A create request is intentionally not retried: after an ambiguous timeout,
        # the next workflow run will perform the slug lookup before writing again.
        page = request('/pages', method='POST', payload=payload, attempts=1, timeout=45)
        page_id = page.get('id')
        action = 'CREATED'

    if not page_id:
        raise RuntimeError('PAGE_ID_MISSING_FROM_POST_RESPONSE')
    if page.get('slug') != SLUG or page.get('status') != STATUS:
        raise RuntimeError(
            'POST_RESPONSE_VERIFY_FAILED ' + json.dumps(
                {
                    'id': page.get('id'),
                    'slug': page.get('slug'),
                    'status': page.get('status'),
                },
                ensure_ascii=False,
            )
        )

    check = request(
        f'/pages/{page_id}?context=edit&_fields=id,slug,status,title,content,link',
        attempts=2,
        timeout=30,
    )
    checks = verify_content(raw(check, 'content'), hero_media)
    checks.update({
        'id': check.get('id') == page_id,
        'slug': check.get('slug') == SLUG,
        'status': check.get('status') == STATUS,
    })
    if not all(checks.values()):
        raise RuntimeError(
            'FINAL_VERIFY_FAILED ' + json.dumps(checks, ensure_ascii=False)
        )

    print(json.dumps({
        'action': action,
        'page_id': page_id,
        'slug': SLUG,
        'status': check.get('status'),
        'title': raw(check, 'title'),
        'preview_link': f'https://tsurikue.com/?page_id={page_id}&preview=true',
        'gourmet_category_id': CATEGORY_ID,
        'temporary_nav': 'absent',
        'hero_media': hero_media,
        'checks': checks,
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
