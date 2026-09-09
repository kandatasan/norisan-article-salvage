#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, os, re, urllib.parse, urllib.request

SITE = 'https://tsurikue.com'
POST_ID = 3633
SLUG = 'karato-market'
UA = 'tsurikue-karato-final-three-fixes-20260909/1.0'

TOKEN = re.compile(r'<!--\s+/?wp:[\s\S]*?-->')
OPEN = re.compile(r'<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->')
CLOSE = re.compile(r'<!--\s+/wp:([\w\-/]+)\s+-->')


def auth_header() -> str:
    user = os.environ.get('TSURIKUE_WP_USER')
    pw = os.environ.get('TSURIKUE_WP_APP_PASSWORD')
    if not user or not pw:
        raise SystemExit('BLOCKED_MISSING_SECRETS')
    return 'Basic ' + base64.b64encode(f'{user}:{pw}'.encode()).decode()


def req(url: str, method: str = 'GET', payload=None, timeout: int = 60):
    headers = {'Authorization': auth_header(), 'Accept': 'application/json', 'User-Agent': UA}
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode()
        headers['Content-Type'] = 'application/json; charset=utf-8'
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        body = json.loads(resp.read().decode())
        return body, dict(resp.headers)


def raw(row, key: str) -> str:
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get('raw') or value.get('rendered') or ''
    return str(value)


def count_published(endpoint: str) -> int:
    q = urllib.parse.urlencode({'status': 'publish', 'per_page': 1, '_fields': 'id'})
    _, headers = req(f'{SITE}/wp-json/wp/v2/{endpoint}?{q}', timeout=45)
    return int(headers.get('X-WP-Total', '0'))


def public_counts():
    posts = count_published('posts')
    pages = count_published('pages')
    return {'posts': posts, 'pages': pages, 'total': posts + pages}


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


def remove_exact_once(text: str, block: str, label: str) -> str:
    n = text.count(block)
    if n != 1:
        raise RuntimeError(f'{label}: expected exactly 1 match, got {n}')
    return text.replace(block, '', 1)


def apply_three_fixes(content: str) -> str:
    # 1) Intro: keep the answer and the sense of discovery; move taste/detail to the H3 body.
    intro_blocks = [
        '''<!-- wp:paragraph -->\n<p>アナゴは丸ごと一本。食べ応えも味も最高。<br>マグロの脳天は脂たっぷりでトロトロなのに、赤身みたいにマグロの風味がしっかりあります。</p>\n<!-- /wp:paragraph -->\n\n''',
        '''<!-- wp:paragraph -->\n<p>「脳天」という名前で一瞬ひるむかもしれませんが、脳みそではありません。頭の肉です。<br>名前に抵抗がなければ、ぜひ食べてほしい。</p>\n<!-- /wp:paragraph -->\n\n''',
        '''<!-- wp:paragraph -->\n<p>しかも、唐戸市場は寿司だけじゃありません。<br>ふぐ、サザエ、アワビ、海鮮丼。売り場を歩くたびに次の海鮮が出てきて、つい立ち止まる。さらに<strong>高級魚のクエまで</strong>並んでいました。</p>\n<!-- /wp:paragraph -->\n\n''',
    ]
    for i, block in enumerate(intro_blocks, 1):
        content = remove_exact_once(content, block, f'intro detail {i}')

    # 2) Treasure-hunt section: delete the one paragraph that repeats the already-shown kue / market expansion.
    repeated = '''<!-- wp:paragraph -->\n<p>寿司でクエまで食べたと思ったら、売り場には活魚、刺身、海鮮丼。<br><strong>見るたびに候補が増える。</strong>これ、うれしいけど困るやつです。</p>\n<!-- /wp:paragraph -->\n\n'''
    content = remove_exact_once(content, repeated, 'repeated kue market paragraph')

    # 3) Move the entire basic-info section from after the summary to immediately before the summary.
    marker = '<!-- tsurikue:facility-info:karato-market:v1 -->'
    summary_heading = '''<!-- wp:heading -->\n<h2 class="wp-block-heading">まとめ｜唐戸市場で迷ったら、アナゴとマグロの脳天を食べてほしい</h2>\n<!-- /wp:heading -->'''
    if content.count(marker) != 1:
        raise RuntimeError(f'facility marker: expected 1, got {content.count(marker)}')
    if content.count(summary_heading) != 1:
        raise RuntimeError(f'summary heading: expected 1, got {content.count(summary_heading)}')

    facility_pos = content.index(marker)
    summary_pos = content.index(summary_heading)
    if facility_pos < summary_pos:
        raise RuntimeError('facility info is already before summary; refusing to make any write')

    facility = content[facility_pos:].strip()
    before_facility = content[:facility_pos].rstrip()
    summary_pos2 = before_facility.index(summary_heading)
    pre_summary = before_facility[:summary_pos2].rstrip()
    summary = before_facility[summary_pos2:].strip()
    content = pre_summary + '\n\n' + facility + '\n\n' + summary + '\n'

    return content


def main():
    q = urllib.parse.urlencode({'context': 'edit', '_fields': 'id,slug,status,title,content,modified'})
    row, _ = req(f'{SITE}/wp-json/wp/v2/posts/{POST_ID}?{q}')
    if row.get('id') != POST_ID or row.get('slug') != SLUG:
        raise RuntimeError(f'wrong target: id={row.get("id")} slug={row.get("slug")}')
    if row.get('status') != 'publish':
        raise RuntimeError(f'expected publish, got {row.get("status")}')

    old = raw(row, 'content')
    if gb_problems(old) != 0:
        raise RuntimeError(f'current Gutenberg problems={gb_problems(old)}')

    before = public_counts()
    new = apply_three_fixes(old)
    if new == old:
        raise RuntimeError('no change generated')
    if gb_problems(new) != 0:
        raise RuntimeError(f'new Gutenberg problems={gb_problems(new)}')

    # Guardrails: only text/order changes; media and links counts must stay identical.
    for token, label in [('<img ', 'images'), ('<a ', 'links'), ('<!-- wp:heading', 'headings'), ('<!-- wp:table', 'tables')]:
        if old.count(token) != new.count(token):
            raise RuntimeError(f'{label} count changed: {old.count(token)} -> {new.count(token)}')

    # The requested removals must be gone and the basic-info section must precede summary.
    if 'アナゴは丸ごと一本。食べ応えも味も最高。' in new.split('<h2 class="wp-block-heading">唐戸市場で絶対食べてほしい', 1)[0]:
        raise RuntimeError('intro detail still present before first H2')
    if '寿司でクエまで食べたと思ったら、売り場には活魚、刺身、海鮮丼。' in new:
        raise RuntimeError('repeat paragraph still present')
    if new.index('<!-- tsurikue:facility-info:karato-market:v1 -->') > new.index(summary_heading):
        raise RuntimeError('facility section did not move before summary')

    updated, _ = req(f'{SITE}/wp-json/wp/v2/posts/{POST_ID}', method='POST', payload={'content': new})
    if updated.get('status') != 'publish':
        raise RuntimeError(f'update returned non-publish status={updated.get("status")}')

    check, _ = req(f'{SITE}/wp-json/wp/v2/posts/{POST_ID}?{q}')
    final = raw(check, 'content')
    after = public_counts()
    if final != new:
        raise RuntimeError('refetched content does not match submitted content')
    if check.get('status') != 'publish':
        raise RuntimeError(f'refetch status={check.get("status")}')
    if before != after:
        raise RuntimeError(f'public counts changed: {before} -> {after}')
    if gb_problems(final) != 0:
        raise RuntimeError(f'final Gutenberg problems={gb_problems(final)}')

    print('# 唐戸市場 最終3点修正')
    print('- result: **SUCCESS**')
    print(f'- post_id: **{POST_ID}**')
    print(f'- slug: **{SLUG}**')
    print(f'- status: **{check.get("status")}**')
    print('- changed: **導入の先回り説明を削減 / 魚の宝探しの重複1段落を削除 / 基本情報をまとめ前へ移動**')
    print(f'- chars_before: **{len(old)}**')
    print(f'- chars_after: **{len(final)}**')
    print(f'- gutenberg_problems: **{gb_problems(final)}**')
    print(f'- published_before: **{before}**')
    print(f'- published_after: **{after}**')
    print(f'- content_sha256: **{hashlib.sha256(final.encode()).hexdigest()}**')


if __name__ == '__main__':
    main()
