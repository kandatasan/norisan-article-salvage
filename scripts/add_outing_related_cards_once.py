#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

SITE = 'https://tsurikue.com'
BASE = SITE + '/wp-json/wp/v2'
CONFIG = Path('outing-related-cards/links.json')
UA = 'tsurikue-outing-related-cards-20260909/1.0'
MARK_PREFIX = '<!-- tq-outing-related-cards:v1:'
MARK_SUFFIX = '<!-- tq-outing-related-cards:v1:end -->'
TOKEN = re.compile(r'<!--\s+/?wp:[\s\S]*?-->')
OPEN = re.compile(r'<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->')
CLOSE = re.compile(r'<!--\s+/wp:([\w\-/]+)\s+-->')


def auth_header() -> str:
    user = os.environ.get('TSURIKUE_WP_USER')
    pw = os.environ.get('TSURIKUE_WP_APP_PASSWORD')
    if not user or not pw:
        raise RuntimeError('BLOCKED_MISSING_SECRETS')
    token = base64.b64encode(f'{user}:{pw}'.encode()).decode()
    return 'Basic ' + token


def req(url: str, method: str = 'GET', payload=None, timeout: int = 60):
    headers = {
        'Authorization': auth_header(),
        'Accept': 'application/json',
        'User-Agent': UA,
    }
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        headers['Content-Type'] = 'application/json; charset=utf-8'
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
        if not body:
            return None, dict(response.headers)
        return json.loads(body.decode('utf-8')), dict(response.headers)


def raw_field(row, key: str) -> str:
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get('raw') or value.get('rendered') or ''
    return str(value)


def clean_title(row) -> str:
    return html.unescape(re.sub(r'<[^>]+>', '', raw_field(row, 'title'))).strip()


def public_counts() -> dict:
    out = {}
    for endpoint in ('posts', 'pages'):
        q = urllib.parse.urlencode({'status': 'publish', 'per_page': 1, '_fields': 'id'})
        _, headers = req(f'{BASE}/{endpoint}?{q}', timeout=45)
        out[endpoint] = int(headers.get('X-WP-Total', '0'))
    out['total'] = out['posts'] + out['pages']
    return out


def get_post(post_id: int) -> dict:
    q = urllib.parse.urlencode({
        'context': 'edit',
        '_fields': 'id,slug,status,title,content,link,categories,modified',
    })
    row, _ = req(f'{BASE}/posts/{post_id}?{q}')
    return row


def gb_problems(text: str) -> int:
    stack = []
    bad = 0
    for m in TOKEN.finditer(text):
        token = m.group(0)
        op = OPEN.fullmatch(token)
        cl = CLOSE.fullmatch(token)
        if op:
            if not op.group(2):
                stack.append(op.group(1))
        elif cl:
            if not stack or stack[-1] != cl.group(1):
                bad += 1
            else:
                stack.pop()
    return bad + len(stack)


def marker_for(slug: str) -> str:
    return f'{MARK_PREFIX}{slug} -->'


def embed_block(url: str) -> str:
    return (
        f'<!-- wp:embed {{"url":"{url}"}} -->\n'
        f'<figure class="wp-block-embed"><div class="wp-block-embed__wrapper">\n'
        f'{url}\n'
        f'</div></figure>\n'
        f'<!-- /wp:embed -->'
    )


def section_block(slug: str, title: str, target_urls: list[str]) -> str:
    embeds = '\n\n'.join(embed_block(url) for url in target_urls)
    return (
        f'{marker_for(slug)}\n'
        f'<!-- wp:heading {{"level":3}} -->\n'
        f'<h3 class="wp-block-heading">{title}</h3>\n'
        f'<!-- /wp:heading -->\n\n'
        f'{embeds}\n'
        f'{MARK_SUFFIX}'
    )


def append_section(raw: str, slug: str, title: str, target_urls: list[str]) -> tuple[str, bool]:
    mark = marker_for(slug)
    if mark in raw:
        if raw.count(mark) != 1 or raw.count(MARK_SUFFIX) < 1:
            raise RuntimeError(f'{slug}: marker exists in an invalid state')
        for url in target_urls:
            if url not in raw:
                raise RuntimeError(f'{slug}: marker exists but target URL missing: {url}')
        return raw, False

    if title in raw:
        raise RuntimeError(f'{slug}: heading text already exists without marker; refusing duplicate append')

    block = section_block(slug, title, target_urls)
    new = raw.rstrip() + '\n\n' + block + '\n'
    return new, True


def validate_row(row: dict, expected: dict, eligible_category_ids: set[int], source: bool) -> None:
    if row.get('id') != expected['id']:
        raise RuntimeError(f'{expected["slug"]}: id mismatch {row.get("id")} != {expected["id"]}')
    if row.get('slug') != expected['slug']:
        raise RuntimeError(f'{expected["id"]}: slug mismatch {row.get("slug")} != {expected["slug"]}')
    if row.get('status') != 'publish':
        raise RuntimeError(f'{expected["slug"]}: expected publish, got {row.get("status")}')
    if clean_title(row) != expected['title']:
        raise RuntimeError(f'{expected["slug"]}: title changed: {clean_title(row)!r}')
    if row.get('link') != expected['url']:
        raise RuntimeError(f'{expected["slug"]}: link mismatch {row.get("link")} != {expected["url"]}')
    if source and not (set(row.get('categories') or []) & eligible_category_ids):
        raise RuntimeError(f'{expected["slug"]}: source category mismatch, categories={row.get("categories")}')


def public_html(url: str) -> str:
    sep = '&' if '?' in url else '?'
    request = urllib.request.Request(
        url + sep + 'tq_related_cards=1',
        headers={'User-Agent': UA},
        method='GET',
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        if getattr(response, 'status', 200) != 200:
            raise RuntimeError(f'public GET failed: {url} status={response.status}')
        return response.read().decode('utf-8', 'ignore')


def rollback(written: list[tuple[dict, str]]) -> list[str]:
    errors = []
    for source, old_raw in reversed(written):
        try:
            updated, _ = req(
                f'{BASE}/posts/{source["id"]}',
                method='POST',
                payload={'content': old_raw},
            )
            if updated.get('status') != 'publish':
                raise RuntimeError(f'rollback status={updated.get("status")}')
            check = get_post(source['id'])
            if raw_field(check, 'content') != old_raw:
                raise RuntimeError('rollback content mismatch')
        except Exception as exc:
            errors.append(f'{source["slug"]}: {exc}')
    return errors


def main() -> None:
    cfg = json.loads(CONFIG.read_text(encoding='utf-8'))
    if cfg.get('version') != 1:
        raise RuntimeError('unsupported config version')

    section_title = cfg['section_title']
    eligible_category_ids = set(cfg['eligible_category_ids'])
    sources = cfg['sources']
    if len(sources) != 29:
        raise RuntimeError(f'expected 29 source entries, got {len(sources)}')

    source_ids = [x['source']['id'] for x in sources]
    source_slugs = [x['source']['slug'] for x in sources]
    if len(set(source_ids)) != len(source_ids) or len(set(source_slugs)) != len(source_slugs):
        raise RuntimeError('duplicate source id/slug in config')

    for entry in sources:
        source = entry['source']
        targets = entry['targets']
        if not 2 <= len(targets) <= 3:
            raise RuntimeError(f'{source["slug"]}: target count must be 2 or 3')
        ids = [x['id'] for x in targets]
        slugs = [x['slug'] for x in targets]
        if len(set(ids)) != len(ids) or len(set(slugs)) != len(slugs):
            raise RuntimeError(f'{source["slug"]}: duplicate target')
        if source['id'] in ids or source['slug'] in slugs:
            raise RuntimeError(f'{source["slug"]}: self link in target set')

    before_counts = public_counts()

    expected_by_id = {}
    for entry in sources:
        expected_by_id[entry['source']['id']] = entry['source']
        for target in entry['targets']:
            expected_by_id[target['id']] = target

    rows = {}
    for post_id, expected in expected_by_id.items():
        row = get_post(post_id)
        validate_row(row, expected, eligible_category_ids, source=False)
        rows[post_id] = row

    planned = []
    for entry in sources:
        source = entry['source']
        row = rows[source['id']]
        validate_row(row, source, eligible_category_ids, source=True)
        old_raw = raw_field(row, 'content')
        if not old_raw:
            raise RuntimeError(f'{source["slug"]}: empty current content')
        old_gb = gb_problems(old_raw)
        if old_gb != 0:
            raise RuntimeError(f'{source["slug"]}: current Gutenberg problems={old_gb}')

        target_urls = [x['url'] for x in entry['targets']]
        new_raw, changed = append_section(old_raw, source['slug'], section_title, target_urls)
        if gb_problems(new_raw) != 0:
            raise RuntimeError(f'{source["slug"]}: new Gutenberg problems={gb_problems(new_raw)}')

        if changed and not new_raw.startswith(old_raw.rstrip()):
            raise RuntimeError(f'{source["slug"]}: append-only guard failed')
        if changed:
            added = new_raw[len(old_raw.rstrip()):]
            if '<img ' in added or '<script' in added or '<style' in added or '<a ' in added:
                raise RuntimeError(f'{source["slug"]}: unexpected manual HTML in appended block')
            if added.count('<!-- wp:embed ') != len(target_urls):
                raise RuntimeError(f'{source["slug"]}: embed count mismatch')
            if added.count('<!-- wp:heading ') != 1:
                raise RuntimeError(f'{source["slug"]}: heading count mismatch')
            for url in target_urls:
                if added.count(url) != 2:
                    raise RuntimeError(f'{source["slug"]}: target URL occurrence mismatch for {url}')

        planned.append({
            'source': source,
            'targets': entry['targets'],
            'old_raw': old_raw,
            'new_raw': new_raw,
            'changed': changed,
            'old_sha256': hashlib.sha256(old_raw.encode()).hexdigest(),
        })

    for item in planned:
        if not item['changed']:
            continue
        current = get_post(item['source']['id'])
        current_raw = raw_field(current, 'content')
        if hashlib.sha256(current_raw.encode()).hexdigest() != item['old_sha256']:
            raise RuntimeError(f'{item["source"]["slug"]}: content changed after preflight; aborting before writes')

    written = []
    try:
        for item in planned:
            if not item['changed']:
                continue
            source = item['source']
            updated, _ = req(
                f'{BASE}/posts/{source["id"]}',
                method='POST',
                payload={'content': item['new_raw']},
            )
            if updated.get('status') != 'publish':
                raise RuntimeError(f'{source["slug"]}: update returned status={updated.get("status")}')
            written.append((source, item['old_raw']))

        for item in planned:
            source = item['source']
            check = get_post(source['id'])
            validate_row(check, source, eligible_category_ids, source=True)
            final_raw = raw_field(check, 'content')
            if final_raw != item['new_raw']:
                raise RuntimeError(f'{source["slug"]}: refetched content does not match planned content')
            if gb_problems(final_raw) != 0:
                raise RuntimeError(f'{source["slug"]}: final Gutenberg problems={gb_problems(final_raw)}')
            mark = marker_for(source['slug'])
            if final_raw.count(mark) != 1:
                raise RuntimeError(f'{source["slug"]}: final marker count={final_raw.count(mark)}')
            for target in item['targets']:
                if target['url'] not in final_raw:
                    raise RuntimeError(f'{source["slug"]}: final raw missing {target["url"]}')

        after_counts = public_counts()
        if after_counts != before_counts:
            raise RuntimeError(f'public counts changed: {before_counts} -> {after_counts}')

        for item in planned:
            source = item['source']
            rendered = public_html(source['url'])
            if section_title not in rendered:
                raise RuntimeError(f'{source["slug"]}: public H3 not rendered')
            for target in item['targets']:
                slug_fragment = '/' + target['slug'] + '/'
                if slug_fragment not in rendered:
                    raise RuntimeError(f'{source["slug"]}: public render missing target fragment {slug_fragment}')

    except Exception:
        rollback_errors = rollback(written)
        if rollback_errors:
            print('ROLLBACK_ERRORS=' + json.dumps(rollback_errors, ensure_ascii=False), file=sys.stderr)
        raise

    changed = [x for x in planned if x['changed']]
    unchanged = [x for x in planned if not x['changed']]
    print('# おでかけ関連記事カード 一括設置')
    print('- result: **SUCCESS**')
    print(f'- source_articles: **{len(planned)}**')
    print(f'- changed_articles: **{len(changed)}**')
    print(f'- already_applied: **{len(unchanged)}**')
    print(f'- heading: **{section_title}**')
    print('- method: **公開中の現在本文をGETし、記事末へH3＋内部URLのEmbedカード2〜3枚だけ追記**')
    print(f'- published_before: **{before_counts}**')
    print(f'- published_after: **{public_counts()}**')
    print()
    print('## 設置一覧')
    for item in planned:
        source = item['source']
        target_slugs = ', '.join(x['slug'] for x in item['targets'])
        state = 'added' if item['changed'] else 'already-present'
        print(f'- {source["id"]} `{source["slug"]}` → {target_slugs} ({state})')


if __name__ == '__main__':
    main()
