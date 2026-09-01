import base64
import hashlib
import json
import os
import pathlib
import urllib.error
import urllib.parse
import urllib.request

BASE = 'https://tsurikue.com/wp-json/wp/v2'
PAGE_ID = 3289
SLUG = 'gourmet-guide'
STATUS = 'draft'
TITLE = 'グルメ｜広島・旅先で実際に食べたラーメン・ご当地グルメ'
MARKER_V1 = '<!-- tsurikue-category-hub:v1:gourmet-blocks -->'
MARKER_V2 = '<!-- tsurikue-category-hub:v2:gourmet-editor-blocks -->'
EXPECTED_CURRENT_SHA256 = '7319af82faa013d428b9a33aa410dbdc7a82f5f450acc448dd4f8012d533ac20'
EXPECTED_TEMPLATE_SHA256 = '5b5b17ff228a3985e63b58c14217b43607fd2372f55789d2c5adfd5eb1993205'
EXPECTED_NEW_SHA256 = 'c113e197086fc84096d34c644b4ae0b51ffa821b5664227caf19c67bf814ee55'
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
    'User-Agent': 'tsurikue-gourmet-block-editor/2.0',
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


def validate_source(content):
    checks = {
        'v1_marker': MARKER_V1 in content,
        'v2_marker': MARKER_V2 in content,
        'single_custom_html_block': content.count('<!-- wp:html -->') == 1 and content.count('<!-- /wp:html -->') == 1,
        'balanced_groups': content.count('<!-- wp:group') == content.count('<!-- /wp:group -->'),
        'balanced_headings': content.count('<!-- wp:heading') == content.count('<!-- /wp:heading -->'),
        'hero_id': f'"id":{HERO_MEDIA_ID}' in content and f'wp-image-{HERO_MEDIA_ID}' in content,
        'hero_url': HERO_URL in content,
        'latest_category': '"categories":[{"id":9}]' in content,
        'main_card_block': 'className":"tq-gourmet-card tq-gourmet-card--main"' in content,
        'choice_grid_block': 'className":"tq-gourmet-choose-grid"' in content,
        'button_block': 'className":"tq-gourmet-final-button"' in content,
        'legacy_choice_html_absent': '<div class="tq-gourmet-choose-grid"><div' not in content,
        'legacy_full_card_anchor_absent': '<a class="tq-gourmet-card' not in content,
        'old_hero_absent': 'img_4017.jpg' not in content,
        'archive_link': 'https://tsurikue.com/category/gourmet/' in content,
    }
    if not all(checks.values()):
        raise RuntimeError('SOURCE_VALIDATION_FAILED ' + json.dumps(checks, ensure_ascii=False))
    source_hash = sha256_text(content)
    if source_hash != EXPECTED_NEW_SHA256:
        raise RuntimeError(f'SOURCE_HASH_MISMATCH expected={EXPECTED_NEW_SHA256} actual={source_hash}')
    return checks


def validate_media():
    media, _ = request(f'/media/{HERO_MEDIA_ID}?context=edit&_fields=id,source_url,mime_type,slug')
    checks = {
        'id': media.get('id') == HERO_MEDIA_ID,
        'url': media.get('source_url') == HERO_URL,
        'image': str(media.get('mime_type') or '').startswith('image/'),
    }
    if not all(checks.values()):
        raise RuntimeError('HERO_MEDIA_MISMATCH ' + json.dumps({'media': media, 'checks': checks}, ensure_ascii=False))
    return checks


def validate_current(page):
    current_content = raw(page, 'content')
    checks = {
        'id': page.get('id') == PAGE_ID,
        'slug': page.get('slug') == SLUG,
        'status': page.get('status') == STATUS,
        'title': raw(page, 'title') == TITLE,
        'marker': MARKER_V1 in current_content,
        'expected_current_hash': sha256_text(current_content) == EXPECTED_CURRENT_SHA256,
    }
    if not all(checks.values()):
        raise RuntimeError('REFUSE_CURRENT_PAGE_MISMATCH ' + json.dumps({
            'checks': checks,
            'actual_hash': sha256_text(current_content),
            'id': page.get('id'),
            'slug': page.get('slug'),
            'status': page.get('status'),
            'title': raw(page, 'title'),
        }, ensure_ascii=False))
    return checks


def main():
    template = SOURCE.read_text(encoding='utf-8')
    template_hash = sha256_text(template)
    if template_hash != EXPECTED_TEMPLATE_SHA256:
        raise RuntimeError(f'TEMPLATE_HASH_MISMATCH expected={EXPECTED_TEMPLATE_SHA256} actual={template_hash}')
    source = apply_mobile_consistency_fix(template)
    source_checks = validate_source(source)
    media_checks = validate_media()

    public_before = {
        'posts': get_public_total('posts'),
        'pages': get_public_total('pages'),
    }

    page, _ = request(
        f'/pages/{PAGE_ID}?context=edit&_fields=id,slug,status,title,content,link'
    )
    current_checks = validate_current(page)

    updated, _ = request(
        f'/pages/{PAGE_ID}',
        method='POST',
        payload={'content': source},
    )
    if updated.get('id') != PAGE_ID or updated.get('slug') != SLUG or updated.get('status') != STATUS:
        raise RuntimeError('UPDATE_RESPONSE_MISMATCH ' + json.dumps({
            'id': updated.get('id'), 'slug': updated.get('slug'), 'status': updated.get('status')
        }, ensure_ascii=False))

    final, _ = request(
        f'/pages/{PAGE_ID}?context=edit&_fields=id,slug,status,title,content,link'
    )
    final_content = raw(final, 'content')
    final_hash = sha256_text(final_content)
    final_checks = {
        'id': final.get('id') == PAGE_ID,
        'slug': final.get('slug') == SLUG,
        'status': final.get('status') == STATUS,
        'title': raw(final, 'title') == TITLE,
        'new_hash': final_hash == EXPECTED_NEW_SHA256,
        'v1_marker': MARKER_V1 in final_content,
        'v2_marker': MARKER_V2 in final_content,
        'custom_html_blocks': final_content.count('<!-- wp:html -->') == 1,
        'legacy_full_card_anchor_absent': '<a class="tq-gourmet-card' not in final_content,
    }
    if not all(final_checks.values()):
        raise RuntimeError('FINAL_VERIFY_FAILED ' + json.dumps({
            'checks': final_checks,
            'actual_hash': final_hash,
        }, ensure_ascii=False))

    public_after = {
        'posts': get_public_total('posts'),
        'pages': get_public_total('pages'),
    }
    if public_before != public_after:
        raise RuntimeError('PUBLIC_COUNTS_CHANGED ' + json.dumps({
            'before': public_before, 'after': public_after
        }, ensure_ascii=False))

    result = {
        'action': 'UPDATED_GOURMET_TO_BLOCK_EDITOR',
        'post_id': PAGE_ID,
        'slug': SLUG,
        'status': final.get('status'),
        'title': raw(final, 'title'),
        'preview_link': f'https://tsurikue.com/?page_id={PAGE_ID}&preview=true',
        'featured_media': 'unchanged',
        'confirmed_media_checked': HERO_MEDIA_ID,
        'public_before': public_before,
        'public_after': public_after,
        'source_checks': source_checks,
        'media_checks': media_checks,
        'current_checks': current_checks,
        'final_checks': final_checks,
        'before_custom_html_blocks': 5,
        'after_custom_html_blocks': 1,
    }
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
