from __future__ import annotations

import base64
import collections
import hashlib
import json
import os
import pathlib
import re
import urllib.error
import urllib.request

BASE = 'https://tsurikue.com/wp-json/wp/v2'
PAGE_ID = 3154
SLUG = 'odekake'
STATUS = 'publish'
TITLE = 'おでかけ｜広島・山口・中国地方の観光・ドライブ・旅行'
EXPECTED_CURRENT_SHA256 = '74cb29217bb7f3d89257d6f7f19b360efc2e1502425776054ceb3b5b2d1d15e2'
V1_MARKER = '<!-- tsurikue-category-hub:v1:outing -->'
V2_MARKER = '<!-- tsurikue-category-hub:v2:outing-blocks -->'
CARD_FIX_START = '<!-- tq-outing-pc-card-width-fix:v1 start -->'
CARD_FIX_END = '<!-- tq-outing-pc-card-width-fix:v1 end -->'
NEW_FIX_START = '/* tq-outing-pc-shell-align-fix:v1 start */'
NEW_FIX_END = '/* tq-outing-pc-shell-align-fix:v1 end */'

FIX_CSS = r'''

/* tq-outing-pc-shell-align-fix:v1 start */
@media(min-width:861px){
  body:has(.tq-out) .post_content{
    padding-left:0!important;
    padding-right:0!important;
  }
  .tq-out.wp-block-group{
    left:0!important;
    right:auto!important;
    width:100%!important;
    max-width:none!important;
    margin-left:0!important;
    margin-right:0!important;
  }
  .tq-out .tq-out-section,
  .tq-out .tq-out-latest,
  .tq-out .tq-out-final{
    left:auto!important;
    right:auto!important;
    width:100%!important;
    max-width:none!important;
    margin-left:0!important;
    margin-right:0!important;
  }
  .tq-out .tq-out-hero{
    left:0!important;
    right:auto!important;
    width:100%!important;
    max-width:none!important;
    margin-left:0!important;
    margin-right:0!important;
    padding-left:0!important;
    padding-right:0!important;
  }
  .tq-out .tq-out-hero>.wp-block-cover__inner-container{
    width:100%!important;
    max-width:none!important;
  }
  .tq-out .tq-out-hero-inner{
    width:min(1160px,calc(100% - 32px))!important;
    max-width:none!important;
    margin-left:auto!important;
    margin-right:auto!important;
  }
}
/* tq-outing-pc-shell-align-fix:v1 end */
'''

BEFORE_PATH = pathlib.Path('outing-pc-layout-before.html')
AFTER_PATH = pathlib.Path('outing-pc-layout-after.html')


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def raw(obj: dict, key: str) -> str:
    value = obj.get(key)
    if isinstance(value, dict):
        return value.get('raw') or value.get('rendered') or ''
    return str(value or '')


def headers() -> dict[str, str]:
    user = os.environ['TSURIKUE_WP_USER']
    password = os.environ['TSURIKUE_WP_APP_PASSWORD']
    token = base64.b64encode(f'{user}:{password}'.encode()).decode()
    return {
        'Authorization': 'Basic ' + token,
        'Accept': 'application/json',
        'Content-Type': 'application/json; charset=utf-8',
        'User-Agent': 'tsurikue-outing-pc-layout-fix/1.0',
    }


def request(path: str, *, method: str = 'GET', payload: dict | None = None):
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers())
    try:
        with urllib.request.urlopen(req, timeout=40) as response:
            body = response.read().decode('utf-8')
            return json.loads(body), response.headers
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace')
        raise RuntimeError(f'WP_HTTP_{exc.code}: {body[:800]}') from exc


def get_page():
    return request(f'/pages/{PAGE_ID}?context=edit&_fields=id,slug,status,title,content,link,modified,featured_media')


def get_public_total(kind: str) -> int:
    _, hdr = request(f'/{kind}?status=publish&per_page=1&_fields=id')
    return int(hdr.get('X-WP-Total', '0'))


def block_counts(content: str) -> dict[str, int]:
    names = re.findall(r'<!--\s+wp:([a-zA-Z0-9_/-]+)', content)
    return dict(sorted(collections.Counter(names).items()))


def hrefs(content: str) -> dict[str, int]:
    vals = re.findall(r'href=["\']([^"\']+)["\']', content)
    return dict(sorted(collections.Counter(vals).items()))


def image_sources(content: str) -> dict[str, int]:
    vals = re.findall(r'(?:src|url)=["\']([^"\']+)["\']', content)
    return dict(sorted(collections.Counter(vals).items()))


def identity_checks(page: dict) -> dict[str, bool]:
    return {
        'id': page.get('id') == PAGE_ID,
        'slug': page.get('slug') == SLUG,
        'status_publish': page.get('status') == STATUS,
        'title': raw(page, 'title') == TITLE,
    }


def require_all(label: str, checks: dict[str, bool], extra: dict | None = None):
    if not all(checks.values()):
        payload = {'checks': checks}
        if extra:
            payload.update(extra)
        raise RuntimeError(label + ' ' + json.dumps(payload, ensure_ascii=False))


def structural_checks(content: str, before_counts: dict[str, int] | None = None) -> dict[str, bool]:
    counts = block_counts(content)
    checks = {
        'v1_marker': content.count(V1_MARKER) == 1,
        'v2_marker': content.count(V2_MARKER) == 1,
        'card_fix_start': content.count(CARD_FIX_START) == 1,
        'card_fix_end': content.count(CARD_FIX_END) == 1,
        'custom_html_two': counts.get('html', 0) == 2,
        'groups_present': counts.get('group', 0) >= 50,
        'hero_present': 'tq-out-hero' in content,
        'choose_grid_present': 'tq-out-choose-grid' in content,
        'local_grid_present': 'tq-out-local-grid' in content,
        'trip_grid_present': 'tq-out-trip-grid' in content,
        'route_list_present': 'tq-out-route-list' in content,
        'latest_present': 'tq-out-latest' in content,
    }
    if before_counts is not None:
        checks['all_block_counts_unchanged'] = counts == before_counts
    return checks


def patch_content(content: str) -> str:
    if NEW_FIX_START in content or NEW_FIX_END in content:
        raise RuntimeError('REFUSE_PATCH_MARKER_ALREADY_PRESENT')
    start = content.find(CARD_FIX_START)
    end = content.find(CARD_FIX_END)
    if start < 0 or end < 0 or end <= start:
        raise RuntimeError('REFUSE_PC_CARD_FIX_BLOCK_NOT_FOUND')
    segment = content[start:end]
    style_close_rel = segment.rfind('</style>')
    if style_close_rel < 0:
        raise RuntimeError('REFUSE_PC_CARD_FIX_STYLE_CLOSE_NOT_FOUND')
    insert_at = start + style_close_rel
    return content[:insert_at] + FIX_CSS + content[insert_at:]


def main() -> None:
    public_before = {'posts': get_public_total('posts'), 'pages': get_public_total('pages')}
    page, _ = get_page()
    identity_before = identity_checks(page)
    require_all('REFUSE_PAGE_IDENTITY_MISMATCH', identity_before)

    current = raw(page, 'content')
    current_hash = sha256_text(current)
    before_counts = block_counts(current)
    before_structure = structural_checks(current)
    require_all('REFUSE_CURRENT_STRUCTURE_MISMATCH', before_structure, {
        'current_hash': current_hash,
        'block_counts': before_counts,
    })

    BEFORE_PATH.write_text(current, encoding='utf-8')

    if NEW_FIX_START in current or NEW_FIX_END in current:
        existing_checks = structural_checks(current, before_counts)
        existing_checks.update({
            'new_fix_start_once': current.count(NEW_FIX_START) == 1,
            'new_fix_end_once': current.count(NEW_FIX_END) == 1,
            'desktop_media_scope': '@media(min-width:861px)' in current,
        })
        require_all('EXISTING_FIX_VERIFY_FAILED', existing_checks)
        action = 'VERIFIED_EXISTING_OUTING_PC_LAYOUT_FIX'
        write_count = 0
        final = page
        final_content = current
    else:
        if current_hash != EXPECTED_CURRENT_SHA256:
            raise RuntimeError('REFUSE_LIVE_CONTENT_CHANGED ' + json.dumps({
                'expected_sha256': EXPECTED_CURRENT_SHA256,
                'actual_sha256': current_hash,
                'modified': page.get('modified'),
            }, ensure_ascii=False))

        patched = patch_content(current)
        prewrite_checks = structural_checks(patched, before_counts)
        prewrite_checks.update({
            'new_fix_start_once': patched.count(NEW_FIX_START) == 1,
            'new_fix_end_once': patched.count(NEW_FIX_END) == 1,
            'hrefs_preserved': hrefs(patched) == hrefs(current),
            'image_sources_preserved': image_sources(patched) == image_sources(current),
            'only_expected_growth': len(patched) == len(current) + len(FIX_CSS),
        })
        require_all('PATCH_CONSERVATION_FAILED', prewrite_checks)

        # Intentionally send content only. Do not send status/title/slug.
        updated, _ = request(f'/pages/{PAGE_ID}', method='POST', payload={'content': patched})
        require_all('UPDATE_RESPONSE_IDENTITY_FAILED', identity_checks(updated))
        action = 'UPDATED_PUBLISHED_OUTING_PC_LAYOUT_CSS'
        write_count = 1

        final, _ = get_page()
        final_content = raw(final, 'content')

    identity_after = identity_checks(final)
    require_all('FINAL_PAGE_IDENTITY_FAILED', identity_after)
    final_structure = structural_checks(final_content, before_counts)
    final_structure.update({
        'new_fix_start_once': final_content.count(NEW_FIX_START) == 1,
        'new_fix_end_once': final_content.count(NEW_FIX_END) == 1,
        'desktop_media_scope': '@media(min-width:861px)' in final_content,
        'post_padding_rule': 'body:has(.tq-out) .post_content' in final_content,
        'root_alignment_rule': '.tq-out.wp-block-group' in final_content,
        'hero_alignment_rule': '.tq-out .tq-out-hero{' in final_content,
        'hero_inner_rule': '.tq-out .tq-out-hero-inner{' in final_content,
        'hrefs_preserved': hrefs(final_content) == hrefs(current),
        'image_sources_preserved': image_sources(final_content) == image_sources(current),
    })
    require_all('FINAL_CONTENT_VERIFY_FAILED', final_structure, {
        'final_sha256': sha256_text(final_content),
        'final_block_counts': block_counts(final_content),
    })

    AFTER_PATH.write_text(final_content, encoding='utf-8')
    public_after = {'posts': get_public_total('posts'), 'pages': get_public_total('pages')}
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
        'link': final.get('link'),
        'wordpress_write_count': write_count,
        'publish_count': 0,
        'delete_count': 0,
        'public_before': public_before,
        'public_after': public_after,
        'current_sha256': current_hash,
        'final_sha256': sha256_text(final_content),
        'custom_html_blocks': block_counts(final_content).get('html', 0),
        'group_blocks': block_counts(final_content).get('group', 0),
        'identity_before': identity_before,
        'identity_after': identity_after,
        'before_structure': before_structure,
        'final_structure': final_structure,
        'existing_pc_card_fix_preserved': CARD_FIX_START in final_content and CARD_FIX_END in final_content,
        'new_pc_shell_fix_present': NEW_FIX_START in final_content and NEW_FIX_END in final_content,
    }
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
