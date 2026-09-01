from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'outing-pc-layout-fix'))
from apply import (  # noqa: E402
    CARD_FIX_END,
    CARD_FIX_START,
    NEW_FIX_END,
    NEW_FIX_START,
    PAGE_ID,
    SLUG,
    STATUS,
    TITLE,
    block_counts,
    get_page,
    get_public_total,
    hrefs,
    identity_checks,
    image_sources,
    raw,
    request,
    require_all,
    sha256_text,
    structural_checks,
)

EXPECTED_CURRENT_SHA256 = 'a00d75705ff9dfc50de016d40496e47bf5087a82e43d6b4b0e7bb48a721f0e67'
FIX_START = '/* tq-outing-pc-card-inner-grid-fix:v3 start */'
FIX_END = '/* tq-outing-pc-card-inner-grid-fix:v3 end */'
BEFORE = Path('outing-card-inner-grid-live-before.html')
AFTER = Path('outing-card-inner-grid-live-after.html')

FIX_CSS = r'''

/* tq-outing-pc-card-inner-grid-fix:v3 start */
@media(min-width:861px){
  body:has(.tq-out) .tq-out .tq-out-trip-card,
  body:has(.tq-out) .tq-out .tq-out-route-card{
    display:block!important;
    grid-template-columns:none!important;
    width:100%!important;
    min-width:0!important;
    max-width:none!important;
  }
  body:has(.tq-out) .tq-out .tq-out-trip-card>.wp-block-group__inner-container{
    display:grid!important;
    grid-template-columns:82px minmax(0,1fr)!important;
    gap:18px!important;
    align-items:center!important;
    width:100%!important;
    min-width:0!important;
    max-width:none!important;
  }
  body:has(.tq-out) .tq-out .tq-out-route-card>.wp-block-group__inner-container{
    display:grid!important;
    grid-template-columns:145px minmax(0,1fr) auto!important;
    gap:24px!important;
    align-items:center!important;
    width:100%!important;
    min-width:0!important;
    max-width:none!important;
  }
  body:has(.tq-out) .tq-out .tq-out-trip-copy,
  body:has(.tq-out) .tq-out .tq-out-route-copy{
    display:block!important;
    width:100%!important;
    min-width:0!important;
    max-width:none!important;
    margin:0!important;
    padding:0!important;
  }
}
/* tq-outing-pc-card-inner-grid-fix:v3 end */
'''


def patch(content: str) -> str:
    if FIX_START in content or FIX_END in content:
        raise RuntimeError('REFUSE_CARD_FIX_ALREADY_PRESENT')
    start = content.find(CARD_FIX_START)
    end = content.find(CARD_FIX_END)
    if start < 0 or end < 0 or end <= start:
        raise RuntimeError('REFUSE_PC_CARD_BLOCK_MISSING')
    segment = content[start:end]
    close_rel = segment.rfind('</style>')
    if close_rel < 0:
        raise RuntimeError('REFUSE_STYLE_CLOSE_MISSING')
    insert_at = start + close_rel
    return content[:insert_at] + FIX_CSS + content[insert_at:]


def main() -> None:
    public_before = {'posts': get_public_total('posts'), 'pages': get_public_total('pages')}
    page, _ = get_page()
    identity_before = identity_checks(page)
    require_all('REFUSE_IDENTITY', identity_before)

    current = raw(page, 'content')
    current_sha = sha256_text(current)
    before_counts = block_counts(current)
    before_structure = structural_checks(current)
    before_structure.update({
        'shell_fix_start_once': current.count(NEW_FIX_START) == 1,
        'shell_fix_end_once': current.count(NEW_FIX_END) == 1,
        'card_fix_absent': FIX_START not in current and FIX_END not in current,
        'custom_html_two': before_counts.get('html', 0) == 2,
        'group_51': before_counts.get('group', 0) == 51,
    })
    require_all('REFUSE_STRUCTURE', before_structure, {'sha256': current_sha, 'counts': before_counts})
    BEFORE.write_text(current, encoding='utf-8')

    if current_sha != EXPECTED_CURRENT_SHA256:
        raise RuntimeError('REFUSE_LIVE_CONTENT_CHANGED ' + json.dumps({
            'expected_sha256': EXPECTED_CURRENT_SHA256,
            'actual_sha256': current_sha,
            'modified': page.get('modified'),
        }, ensure_ascii=False))

    patched = patch(current)
    pre = structural_checks(patched, before_counts)
    pre.update({
        'shell_fix_preserved': patched.count(NEW_FIX_START) == 1 and patched.count(NEW_FIX_END) == 1,
        'new_fix_once': patched.count(FIX_START) == 1 and patched.count(FIX_END) == 1,
        'desktop_only': '@media(min-width:861px)' in FIX_CSS,
        'trip_outer_block_rule': 'body:has(.tq-out) .tq-out .tq-out-trip-card' in FIX_CSS,
        'trip_inner_grid_rule': 'grid-template-columns:82px minmax(0,1fr)!important' in FIX_CSS,
        'route_inner_grid_rule': 'grid-template-columns:145px minmax(0,1fr) auto!important' in FIX_CSS,
        'hrefs_preserved': hrefs(patched) == hrefs(current),
        'images_preserved': image_sources(patched) == image_sources(current),
        'exact_growth': len(patched) == len(current) + len(FIX_CSS),
    })
    require_all('PATCH_CONSERVATION_FAILED', pre)

    # Content only. Do not send status/title/slug.
    updated, _ = request(f'/pages/{PAGE_ID}', method='POST', payload={'content': patched})
    require_all('UPDATE_IDENTITY_FAILED', identity_checks(updated))

    final, _ = get_page()
    final_content = raw(final, 'content')
    identity_after = identity_checks(final)
    require_all('FINAL_IDENTITY_FAILED', identity_after)

    final_checks = structural_checks(final_content, before_counts)
    final_checks.update({
        'shell_fix_preserved': final_content.count(NEW_FIX_START) == 1 and final_content.count(NEW_FIX_END) == 1,
        'new_fix_once': final_content.count(FIX_START) == 1 and final_content.count(FIX_END) == 1,
        'hrefs_preserved': hrefs(final_content) == hrefs(current),
        'images_preserved': image_sources(final_content) == image_sources(current),
        'custom_html_two': block_counts(final_content).get('html', 0) == 2,
        'group_51': block_counts(final_content).get('group', 0) == 51,
    })
    require_all('FINAL_CONSERVATION_FAILED', final_checks)
    AFTER.write_text(final_content, encoding='utf-8')

    public_after = {'posts': get_public_total('posts'), 'pages': get_public_total('pages')}
    if public_after != public_before:
        raise RuntimeError('REFUSE_PUBLIC_COUNTS_CHANGED ' + json.dumps({'before': public_before, 'after': public_after}))

    print(json.dumps({
        'action': 'UPDATED_PUBLISHED_OUTING_CARD_INNER_GRID_CSS',
        'post_id': PAGE_ID,
        'slug': SLUG,
        'status': STATUS,
        'title': TITLE,
        'wordpress_write_count': 1,
        'publish_count': 0,
        'delete_count': 0,
        'public_before': public_before,
        'public_after': public_after,
        'current_sha256': current_sha,
        'final_sha256': sha256_text(final_content),
        'identity_before': identity_before,
        'identity_after': identity_after,
        'before_structure': before_structure,
        'final_checks': final_checks,
        'custom_html_blocks': block_counts(final_content).get('html', 0),
        'group_blocks': block_counts(final_content).get('group', 0),
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
