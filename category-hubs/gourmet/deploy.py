import base64
import hashlib
import json
import os
import pathlib
import urllib.error
import urllib.request

BASE = 'https://tsurikue.com/wp-json/wp/v2'
PAGE_ID = 3289
SLUG = 'gourmet-guide'
STATUS = 'draft'
TITLE = 'グルメ｜広島・旅先で実際に食べたラーメン・ご当地グルメ'
MARKER_V1 = '<!-- tsurikue-category-hub:v1:gourmet-blocks -->'
MARKER_V2 = '<!-- tsurikue-category-hub:v2:gourmet-editor-blocks -->'
EXPECTED_LEGACY_SHA256 = '7319af82faa013d428b9a33aa410dbdc7a82f5f450acc448dd4f8012d533ac20'
EXPECTED_TEMPLATE_SHA256 = '5b5b17ff228a3985e63b58c14217b43607fd2372f55789d2c5adfd5eb1993205'
HERO_MEDIA_ID = 3291
HERO_URL = 'https://tsurikue.com/wp-content/uploads/2026/09/img_7358.jpg'
HERE = pathlib.Path(__file__).resolve().parent
SOURCE = HERE / 'content.html'

user = os.environ['TSURIKUE_WP_USER']
password = os.environ['TSURIKUE_WP_APP_PASSWORD']
token = base64.b64encode(f'{user}:{password}'.encode()).decode()
HEADERS = {
    'Authorization': 'Basic ' + token,
    'Accept': 'application/json',
    'Content-Type': 'application/json; charset=utf-8',
    'User-Agent': 'tsurikue-gourmet-block-editor/2.1',
}


def normalize(text):
    return (text or '').replace('\r\n', '\n').replace('\r', '\n')


def sha256_text(text):
    return hashlib.sha256(normalize(text).encode('utf-8')).hexdigest()


def raw(obj, field):
    value = obj.get(field) or {}
    return value.get('raw') or value.get('rendered') or ''


def request(path, method='GET', payload=None, timeout=45):
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(BASE + path, data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode('utf-8')
            return (json.loads(body) if body else None), response.headers
    except urllib.error.HTTPError as error:
        body = error.read().decode('utf-8', 'replace')
        raise RuntimeError(f'HTTP {error.code} {method} {path}: {body[:1200]}') from error


def get_public_total(kind):
    _, headers = request(f'/{kind}?status=publish&per_page=1&_fields=id')
    total = headers.get('X-WP-Total')
    if total is None:
        raise RuntimeError(f'PUBLIC_TOTAL_HEADER_MISSING kind={kind}')
    return int(total)


def apply_mobile_consistency_fix(content):
    old = """  .tq-gourmet .tq-gourmet-grid{grid-template-columns:1fr!important}
  .tq-gourmet .tq-gourmet-card--main{grid-column:auto!important;min-height:290px}
  .tq-gourmet .tq-gourmet-final-actions,.tq-gourmet .tq-gourmet-final-button,.tq-gourmet .tq-gourmet-final-button .wp-block-button__link{width:100%}
}"""
    new = """  .tq-gourmet .tq-gourmet-choice h3{font-size:17px!important}
  .tq-gourmet .tq-gourmet-grid{grid-template-columns:1fr!important}
  .tq-gourmet .tq-gourmet-card--main{grid-column:auto!important;min-height:290px}
  .tq-gourmet .tq-gourmet-card h3,.tq-gourmet .tq-gourmet-card--main h3{font-size:26px!important}
  .tq-gourmet .tq-gourmet-final-actions,.tq-gourmet .tq-gourmet-final-button{width:100%}
  .tq-gourmet .tq-gourmet-final-button .wp-block-button__link{width:100%;margin-top:0!important}
}"""
    if old not in content:
        raise RuntimeError('MOBILE_FIX_ANCHOR_MISSING')
    return content.replace(old, new, 1)


def content_shape_checks(content):
    return {
        'v1_marker': MARKER_V1 in content,
        'v2_marker': MARKER_V2 in content,
        'single_custom_html_block': content.count('<!-- wp:html -->') == 1 and content.count('<!-- /wp:html -->') == 1,
        'balanced_groups': content.count('<!-- wp:group') == content.count('<!-- /wp:group -->'),
        'balanced_headings': content.count('<!-- wp:heading') == content.count('<!-- /wp:heading -->'),
        'native_groups_present': content.count('<!-- wp:group') >= 20,
        'native_headings_present': content.count('<!-- wp:heading') >= 10,
        'native_paragraphs_present': content.count('<!-- wp:paragraph') >= 20,
        'hero_id': f'"id":{HERO_MEDIA_ID}' in content and f'wp-image-{HERO_MEDIA_ID}' in content,
        'hero_url': HERO_URL in content,
        'latest_category': '"categories":[{"id":9}]' in content,
        'main_card_block': 'tq-gourmet-card tq-gourmet-card--main' in content,
        'choice_grid_block': 'tq-gourmet-choose-grid' in content,
        'button_block': 'tq-gourmet-final-button' in content,
        'legacy_choice_html_absent': '<div class="tq-gourmet-choose-grid"><div' not in content,
        'legacy_full_card_anchor_absent': '<a class="tq-gourmet-card' not in content,
        'old_hero_absent': 'img_4017.jpg' not in content,
        'ramen_link': 'https://tsurikue.com/higashihiroshima-ramen/' in content,
        'archive_link': 'https://tsurikue.com/category/gourmet/' in content,
        'mobile_choice_size': '.tq-gourmet .tq-gourmet-choice h3{font-size:17px!important}' in content,
        'mobile_card_size': '.tq-gourmet .tq-gourmet-card h3,.tq-gourmet .tq-gourmet-card--main h3{font-size:26px!important}' in content,
    }


def require_all(label, checks, extra=None):
    if not all(checks.values()):
        payload = {'checks': checks}
        if extra:
            payload.update(extra)
        raise RuntimeError(label + ' ' + json.dumps(payload, ensure_ascii=False))


def validate_media():
    media, _ = request(f'/media/{HERO_MEDIA_ID}?context=edit&_fields=id,source_url,mime_type,slug')
    checks = {
        'id': media.get('id') == HERO_MEDIA_ID,
        'url': media.get('source_url') == HERO_URL,
        'image': str(media.get('mime_type') or '').startswith('image/'),
    }
    require_all('HERO_MEDIA_MISMATCH', checks, {'media': media})
    return checks


def page_identity_checks(page):
    return {
        'id': page.get('id') == PAGE_ID,
        'slug': page.get('slug') == SLUG,
        'status': page.get('status') == STATUS,
        'title': raw(page, 'title') == TITLE,
    }


def get_page():
    page, _ = request(f'/pages/{PAGE_ID}?context=edit&_fields=id,slug,status,title,content,link')
    identity = page_identity_checks(page)
    require_all('REFUSE_PAGE_IDENTITY_MISMATCH', identity, {
        'id': page.get('id'),
        'slug': page.get('slug'),
        'status': page.get('status'),
        'title': raw(page, 'title'),
    })
    return page, identity


def main():
    template = SOURCE.read_text(encoding='utf-8')
    template_hash = sha256_text(template)
    if template_hash != EXPECTED_TEMPLATE_SHA256:
        raise RuntimeError(f'TEMPLATE_HASH_MISMATCH expected={EXPECTED_TEMPLATE_SHA256} actual={template_hash}')

    desired = apply_mobile_consistency_fix(template)
    desired_checks = content_shape_checks(desired)
    require_all('DESIRED_CONTENT_SHAPE_FAILED', desired_checks, {'desired_hash': sha256_text(desired)})
    media_checks = validate_media()

    public_before = {
        'posts': get_public_total('posts'),
        'pages': get_public_total('pages'),
    }

    page, identity_before = get_page()
    current = raw(page, 'content')
    current_hash = sha256_text(current)

    if MARKER_V2 in current:
        current_shape = content_shape_checks(current)
        require_all('EXISTING_V2_CONTENT_SHAPE_FAILED', current_shape, {'current_hash': current_hash})
        action = 'VERIFIED_EXISTING_GOURMET_BLOCK_EDITOR'
        write_count = 0
    else:
        legacy_checks = {
            'v1_marker': MARKER_V1 in current,
            'v2_absent': MARKER_V2 not in current,
            'legacy_hash': current_hash == EXPECTED_LEGACY_SHA256,
        }
        require_all('REFUSE_UNEXPECTED_LEGACY_CONTENT', legacy_checks, {'current_hash': current_hash})
        updated, _ = request(f'/pages/{PAGE_ID}', method='POST', payload={'content': desired})
        update_identity = page_identity_checks(updated)
        require_all('UPDATE_RESPONSE_IDENTITY_FAILED', update_identity)
        action = 'UPDATED_GOURMET_TO_BLOCK_EDITOR'
        write_count = 1

    final, identity_after = get_page()
    final_content = raw(final, 'content')
    final_hash = sha256_text(final_content)
    final_shape = content_shape_checks(final_content)
    require_all('FINAL_CONTENT_SHAPE_FAILED', final_shape, {'final_hash': final_hash})

    public_after = {
        'posts': get_public_total('posts'),
        'pages': get_public_total('pages'),
    }
    if public_before != public_after:
        raise RuntimeError('PUBLIC_COUNTS_CHANGED ' + json.dumps({
            'before': public_before,
            'after': public_after,
        }, ensure_ascii=False))

    result = {
        'action': action,
        'post_id': PAGE_ID,
        'slug': SLUG,
        'status': final.get('status'),
        'title': raw(final, 'title'),
        'preview_link': f'https://tsurikue.com/?page_id={PAGE_ID}&preview=true',
        'wordpress_write_count': write_count,
        'featured_media': 'unchanged',
        'confirmed_media_checked': HERO_MEDIA_ID,
        'public_before': public_before,
        'public_after': public_after,
        'current_content_sha256': current_hash,
        'final_content_sha256': final_hash,
        'custom_html_blocks': final_content.count('<!-- wp:html -->'),
        'native_group_blocks': final_content.count('<!-- wp:group'),
        'native_heading_blocks': final_content.count('<!-- wp:heading'),
        'native_paragraph_blocks': final_content.count('<!-- wp:paragraph'),
        'identity_before': identity_before,
        'identity_after': identity_after,
        'media_checks': media_checks,
        'final_shape_checks': final_shape,
        'migration_history': {
            'custom_html_before': 5,
            'custom_html_after': 1,
        },
    }
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
