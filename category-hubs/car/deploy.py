import base64
import json
import os
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = 'https://tsurikue.com/wp-json/wp/v2'
CAR_CATEGORY_IDS = (10, 11)
EXPECTED_CATEGORIES = {
    10: {'slug': 'car', 'parent': 0},
    11: {'slug': 'car-goods-wash', 'parent': 10},
}
HERO_MEDIA_ID = 2507
SLUG = 'car-guide'
TITLE = 'クルマ｜レクサスUXの購入・後悔・維持・売却を実体験で紹介'
STATUS = 'draft'
MARKER = '<!-- tsurikue-category-hub:v1:car-blocks -->'
CATEGORY_FILTER_PLACEHOLDER = '__CAR_CATEGORY_FILTER__'
HERO_URL_PLACEHOLDER = '__CAR_HERO_URL__'
HERO_ID_PLACEHOLDER = '__CAR_HERO_ID__'
HERE = pathlib.Path(__file__).resolve().parent
SOURCE = HERE / 'content.html'

user = os.environ['TSURIKUE_WP_USER']
password = os.environ['TSURIKUE_WP_APP_PASSWORD']
token = base64.b64encode(f'{user}:{password}'.encode()).decode()
HEADERS = {
    'Authorization': 'Basic ' + token,
    'Accept': 'application/json',
    'Content-Type': 'application/json; charset=utf-8',
    'User-Agent': 'tsurikue-car-hub-deploy/1.0',
}


def request(path, method='GET', payload=None, attempts=3, timeout=40):
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


def verify_categories():
    found = []
    for category_id in CAR_CATEGORY_IDS:
        category = request(
            f'/categories/{category_id}?context=edit&_fields=id,slug,parent,name,count',
            attempts=3,
            timeout=40,
        )
        expected = EXPECTED_CATEGORIES[category_id]
        checks = {
            'id': category.get('id') == category_id,
            'slug': category.get('slug') == expected['slug'],
            'parent': category.get('parent') == expected['parent'],
        }
        if not all(checks.values()):
            raise RuntimeError(
                'CAR_CATEGORY_VERIFY_FAILED '
                + json.dumps({
                    'expected_id': category_id,
                    'actual': category,
                    'checks': checks,
                }, ensure_ascii=False)
            )
        found.append({
            'id': category.get('id'),
            'slug': category.get('slug'),
            'parent': category.get('parent'),
            'count': category.get('count'),
        })
    print('CAR_CATEGORIES_VERIFIED ' + json.dumps(found, ensure_ascii=False))
    return found


def image_url_is_live(url):
    if not str(url).startswith('https://tsurikue.com/wp-content/uploads/'):
        return False
    headers = {
        'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
        'Referer': 'https://tsurikue.com/',
        'User-Agent': 'tsurikue-car-hero-check/1.0',
    }
    req = urllib.request.Request(str(url), headers=headers, method='GET')
    try:
        with urllib.request.urlopen(req, timeout=40) as response:
            content_type = response.headers.get('Content-Type', '')
            sample = response.read(1024)
            return response.status < 400 and content_type.startswith('image/') and bool(sample)
    except Exception:
        return False


def find_hero_media():
    media = request(
        f'/media/{HERO_MEDIA_ID}?context=edit'
        '&_fields=id,source_url,slug,alt_text,title,mime_type,date,media_details',
        attempts=3,
        timeout=40,
    )
    source_url = str(media.get('source_url') or '')
    dimensions = media.get('media_details') or {}
    checks = {
        'id': media.get('id') == HERO_MEDIA_ID,
        'image': str(media.get('mime_type') or '').startswith('image/'),
        'source_url': bool(source_url),
        'expected_file': 'IMG_2012' in source_url or 'img_2012' in source_url.lower(),
        'width': int(dimensions.get('width') or 0) >= 1600,
        'height': int(dimensions.get('height') or 0) >= 1000,
        'live': image_url_is_live(source_url),
    }
    if not all(checks.values()):
        raise RuntimeError(
            'CAR_HERO_MEDIA_VERIFY_FAILED '
            + json.dumps({'media': media, 'checks': checks}, ensure_ascii=False)
        )
    selected = {
        'id': int(media['id']),
        'source_url': source_url,
        'slug': str(media.get('slug') or ''),
        'width': int(dimensions.get('width') or 0),
        'height': int(dimensions.get('height') or 0),
    }
    print('CAR_HERO_MEDIA_FOUND ' + json.dumps(selected, ensure_ascii=False))
    return selected


def category_filter_json():
    return json.dumps(
        [{'id': category_id} for category_id in CAR_CATEGORY_IDS],
        ensure_ascii=False,
        separators=(',', ':'),
    )


def build_content(hero_media):
    content = SOURCE.read_text(encoding='utf-8')
    if MARKER not in content:
        raise RuntimeError('SOURCE_MARKER_MISSING')

    expected_counts = {
        CATEGORY_FILTER_PLACEHOLDER: 1,
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

    content = content.replace(CATEGORY_FILTER_PLACEHOLDER, category_filter_json())
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
    filter_json = category_filter_json()
    required_links = (
        '/lexus-ux-review/',
        '/ux-koukai/',
        '/lexus-ux-used/',
        '/ux-resale/',
        '/lexus-spindle-grille-carwash/',
        '/category/car/',
    )
    checks = {
        'marker': MARKER in content,
        'category_filter': f'"categories":{filter_json}' in content,
        'latest_block': 'wp:latest-posts' in content,
        'hero': 'クルマで、<br>どこまで行こう。' in content,
        'hero_image_url': hero_url in content,
        'hero_image_id': (
            f'"id":{hero_id}' in content
            and f'wp-image-{hero_id}' in content
        ),
        'hero_alt': '青空の下に停まる白いレクサスUX' in content,
        'hero_tokens_resolved': (
            HERO_URL_PLACEHOLDER not in content
            and HERO_ID_PLACEHOLDER not in content
        ),
        'category_token_resolved': CATEGORY_FILTER_PLACEHOLDER not in content,
        'required_links': all(link in content for link in required_links),
        'temp_nav_absent': 'tq-global-site-nav-ref' not in content,
        'custom_menu_absent': 'TQ SITEWIDE HOLIDAY MENU' not in content,
    }
    if not all(checks.values()):
        raise RuntimeError(
            'VERIFY_CONTENT_FAILED ' + json.dumps(checks, ensure_ascii=False)
        )
    return checks


def find_pages(status):
    query = urllib.parse.urlencode({
        'slug': SLUG,
        'status': status,
        'context': 'edit',
        'per_page': 5,
        '_fields': 'id,slug,status,title,content,link',
    })
    return request('/pages?' + query, attempts=3, timeout=40)


def find_existing():
    drafts = find_pages('draft')
    published = find_pages('publish')
    if published:
        raise RuntimeError(
            'REFUSE_PUBLISHED_CAR_PAGE ids='
            + repr([page.get('id') for page in published])
        )
    if len(drafts) > 1:
        raise RuntimeError(
            'MULTIPLE_CAR_DRAFTS_FOUND ids='
            + repr([page.get('id') for page in drafts])
        )
    return drafts[0] if drafts else None


def main():
    categories = verify_categories()
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
            'レクサスUXを購入し、1万km以上乗って売却するまでの実体験から、'
            '価格、後悔、内装、後席、荷室、リセール、洗車をまとめたクルマカテゴリーの入口です。'
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
            timeout=50,
        )
        action = 'UPDATED'
    else:
        page = request(
            '/pages',
            method='POST',
            payload=payload,
            attempts=1,
            timeout=50,
        )
        page_id = page.get('id')
        action = 'CREATED'

    if not page_id:
        raise RuntimeError('PAGE_ID_MISSING_FROM_POST_RESPONSE')
    if page.get('slug') != SLUG or page.get('status') != STATUS:
        raise RuntimeError(
            'POST_RESPONSE_VERIFY_FAILED '
            + json.dumps({
                'id': page.get('id'),
                'slug': page.get('slug'),
                'status': page.get('status'),
            }, ensure_ascii=False)
        )

    check = request(
        f'/pages/{page_id}?context=edit&_fields=id,slug,status,title,content,link',
        attempts=3,
        timeout=40,
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
        'car_categories': categories,
        'hero_media': hero_media,
        'temporary_nav': 'absent',
        'checks': checks,
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
