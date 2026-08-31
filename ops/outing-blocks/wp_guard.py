from __future__ import annotations

import base64
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

BASE = 'https://tsurikue.com/wp-json/wp/v2'
PAGE_ID = 3154
BACKUP = pathlib.Path('/tmp/tsurikue-outing-before-blocks.json')
OLD_MARKER = '<!-- tsurikue-category-hub:v1:outing -->'
BLOCK_MARKER = '<!-- tsurikue-category-hub:v2:outing-blocks -->'

user = os.environ['TSURIKUE_WP_USER']
pw = os.environ['TSURIKUE_WP_APP_PASSWORD']
token = base64.b64encode(f'{user}:{pw}'.encode()).decode()
HEADERS = {
    'Authorization': 'Basic ' + token,
    'Accept': 'application/json',
    'Content-Type': 'application/json; charset=utf-8',
    'User-Agent': 'tsurikue-outing-block-migration/1.0',
}


def request(path: str, method: str = 'GET', payload: dict | None = None):
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8') if payload is not None else None
    last = None
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request(BASE + path, data=data, headers=HEADERS, method=method)
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read().decode('utf-8'))
        except Exception as exc:
            last = exc
            print(f'WP_REQUEST_RETRY attempt={attempt}/3 method={method} path={path} error={type(exc).__name__}:{exc}')
            if attempt < 3:
                time.sleep(7 * attempt)
    raise RuntimeError(f'WP_REQUEST_FAILED method={method} path={path}: {last}')


def raw_content(page: dict) -> str:
    content = page.get('content') or {}
    return content.get('raw') or content.get('rendered') or ''


def fetch_page() -> dict:
    return request(f'/pages/{PAGE_ID}?context=edit&_fields=id,slug,status,title,content')


def validate_block_stack(content: str) -> None:
    pattern = re.compile(r'<!--\s*(/?)wp:([a-z0-9-]+)(?:\s+\{.*?\})?\s*(/?)-->', re.S | re.I)
    stack: list[str] = []
    for m in pattern.finditer(content):
        closing, name, self_close = m.group(1), m.group(2), m.group(3)
        if self_close:
            continue
        if closing:
            if not stack or stack[-1] != name:
                raise RuntimeError(f'BLOCK_STACK_MISMATCH closing={name} stack={stack[-5:]}')
            stack.pop()
        else:
            stack.append(name)
    if stack:
        raise RuntimeError(f'UNCLOSED_BLOCKS={stack[-10:]}')


def backup() -> None:
    page = fetch_page()
    content = raw_content(page)
    checks = {
        'id': page.get('id') == PAGE_ID,
        'slug': page.get('slug') == 'odekake',
        'draft': page.get('status') == 'draft',
        'old_marker': OLD_MARKER in content,
        'not_blockized_yet': BLOCK_MARKER not in content,
        'temporary_nav_absent': 'tq-global-site-nav-ref:v1' not in content,
    }
    print('OUTING_BLOCK_BACKUP_CHECKS=' + json.dumps(checks, ensure_ascii=False))
    if not all(checks.values()):
        raise SystemExit('BACKUP_GUARD_FAILED')
    BACKUP.write_text(json.dumps({
        'id': page.get('id'),
        'slug': page.get('slug'),
        'status': page.get('status'),
        'content': content,
    }, ensure_ascii=False), encoding='utf-8')
    print(f'OUTING_BLOCK_BACKUP_SAVED bytes={len(content.encode("utf-8"))}')


def verify() -> None:
    page = fetch_page()
    content = raw_content(page)
    validate_block_stack(content)
    checks = {
        'id': page.get('id') == PAGE_ID,
        'slug': page.get('slug') == 'odekake',
        'draft': page.get('status') == 'draft',
        'old_marker': OLD_MARKER in content,
        'block_marker': BLOCK_MARKER in content,
        'one_custom_html': content.count('<!-- wp:html -->') == 1,
        'group_blocks': content.count('<!-- wp:group ') >= 35,
        'heading_blocks': content.count('<!-- wp:heading') >= 18,
        'paragraph_blocks': content.count('<!-- wp:paragraph') >= 35,
        'cover_block': '<!-- wp:cover ' in content,
        'latest_block': '<!-- wp:latest-posts ' in content,
        'category_placeholder_resolved': '{{OUTING_CATEGORY_IDS}}' not in content,
        'legacy_main_absent': '<main class="tq-out">' not in content,
        'legacy_cards_absent': '<a class="tq-out-card' not in content and '<a class="tq-out-trip-card' not in content,
        'travel_wording': content.count('旅に出る') >= 2 and 'ちょっと遠くへ' not in content,
        'final_polish': '/* TQ OUTING FINAL POLISH v1 */' in content,
        'block_css': '/* TQ OUTING BLOCKS v1 */' in content,
        'temporary_nav_absent': 'tq-global-site-nav-ref:v1' not in content,
    }
    print('OUTING_BLOCK_WP_VERIFY=' + json.dumps(checks, ensure_ascii=False))
    if not all(checks.values()):
        raise SystemExit('WORDPRESS_BLOCK_VERIFY_FAILED')
    print('OUTING_GUTENBERG_BLOCKS_VERIFIED')


def restore() -> None:
    if not BACKUP.exists():
        print('OUTING_BLOCK_RESTORE_SKIPPED_NO_BACKUP')
        return
    before = json.loads(BACKUP.read_text(encoding='utf-8'))
    if before.get('id') != PAGE_ID or before.get('slug') != 'odekake' or before.get('status') != 'draft':
        raise SystemExit('BACKUP_METADATA_INVALID')
    result = request(f'/pages/{PAGE_ID}', method='POST', payload={
        'content': before['content'],
        'status': 'draft',
    })
    page = fetch_page()
    content = raw_content(page)
    checks = {
        'draft': page.get('status') == 'draft',
        'old_marker': OLD_MARKER in content,
        'block_marker_absent': BLOCK_MARKER not in content,
        'exact_content': content == before['content'],
    }
    print('OUTING_BLOCK_RESTORE=' + json.dumps(checks, ensure_ascii=False))
    if not all(checks.values()):
        raise SystemExit('RESTORE_VERIFY_FAILED')
    print('OUTING_BLOCK_ROLLBACK_COMPLETE')


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {'backup', 'verify', 'restore'}:
        raise SystemExit('usage: wp_guard.py backup|verify|restore')
    {'backup': backup, 'verify': verify, 'restore': restore}[sys.argv[1]]()


if __name__ == '__main__':
    main()
