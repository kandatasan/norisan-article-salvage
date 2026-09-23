#!/usr/bin/env python3
"""Remove only nine authorized archive-hosted image blocks from three live posts."""
import argparse
import base64
import hashlib
import html
import json
import os
from pathlib import Path
import re
import urllib.request

SITE = 'https://tsurikue.com'
OUT = Path('reports/remove-wayback-images-20260924')
TARGETS = {
    1883: ('aoriika-nikki', [
        '20230606062936im_/https://i0.wp.com/tsurikue.com/wp-content/uploads/2022/10/image-7.jpg?fit=768%2C991&ssl=1',
        '20230606062936im_/https://i0.wp.com/tsurikue.com/wp-content/uploads/2022/10/image-1-3.jpg?resize=409%2C785&ssl=1',
        '20230606062936im_/https://i0.wp.com/tsurikue.com/wp-content/uploads/2022/10/image-7.jpg?resize=768%2C991&ssl=1',
    ]),
    1887: ('etajima-sightseeing', [
        '20230605060332im_/https://i0.wp.com/tsurikue.com/wp-content/uploads/2023/06/img_0307-scaled.jpg?fit=2560%2C1920&ssl=1',
        '20230605060332im_/https://i0.wp.com/tsurikue.com/wp-content/uploads/2023/06/img_0460.jpg?resize=1024%2C1024&ssl=1',
        '20230605060332im_/https://i0.wp.com/tsurikue.com/wp-content/uploads/2023/06/img_0461.jpg?resize=1024%2C1024&ssl=1',
        '20230605060332im_/https://i0.wp.com/tsurikue.com/wp-content/uploads/2023/06/img_0462.jpg?resize=1024%2C1024&ssl=1',
        '20230605060332im_/https://i0.wp.com/tsurikue.com/wp-content/uploads/2023/06/img_0463.jpg?resize=1024%2C1024&ssl=1',
    ]),
    1892: ('higashihiroshima-ramen', [
        '20230916040417im_/https://i0.wp.com/tsurikue.com/wp-content/uploads/2023/08/img_1339.jpg?resize=1024%2C768&ssl=1',
    ]),
}
PATTERN = re.compile(r'(?:<!-- wp:image\b[^>]*-->\s*)?<figure\b[^>]*>(?:(?!</figure>).)*</figure>(?:\s*<!-- /wp:image -->)?', re.S)

def require(ok, message):
    if not ok:
        raise RuntimeError(message)

def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

def transform(content, post_id):
    expected = ['https://web.archive.org/web/' + s for s in TARGETS[post_id][1]]
    removed = []
    def replace(match):
        block = match.group()
        if 'web.archive.org' not in block:
            return block
        sources = [html.unescape(s) for s in re.findall(r'<img\b[^>]*\bsrc="([^"]+)"', block)]
        require(len(sources) == 1 and sources[0] in expected, 'Unexpected archive figure')
        # Only a single image and its empty wrappers may be removed; no captions or prose.
        residue = re.sub(r'<!--.*?-->|<[^>]*>', '', block, flags=re.S).strip()
        require(not residue, 'Figure contains text; manual review needed')
        removed.append(sources[0])
        return ''
    fixed = PATTERN.sub(replace, content)
    require(sorted(removed) == sorted(expected), f'{post_id}: archive URLs/count changed')
    require('web.archive.org' not in fixed, 'Archive reference remains')
    require(len(re.findall(r'<img\b', content)) - len(re.findall(r'<img\b', fixed)) == len(expected), 'Image count mismatch')
    def prose(s):
        return re.sub(r'\s+', '', html.unescape(re.sub(r'<!--.*?-->|<[^>]*>', '', s, flags=re.S)))
    require(prose(content) == prose(fixed), 'Non-image text changed')
    return fixed, removed

def request(path, method='GET', payload=None):
    token = base64.b64encode((os.environ['TSURIKUE_WP_USER'] + ':' + os.environ['TSURIKUE_WP_APP_PASSWORD']).encode()).decode()
    headers = {'Authorization': 'Basic ' + token, 'Accept': 'application/json', 'User-Agent': 'tsurikue-scoped-image-cleanup/1.0'}
    data = None
    if payload is not None:
        require(method == 'POST' and set(payload) == {'content'}, 'Content-only writes required')
        require(path in [f'/posts/{i}' for i in TARGETS], 'Write target not authorized')
        data = json.dumps(payload, ensure_ascii=False).encode()
        headers['Content-Type'] = 'application/json; charset=utf-8'
    with urllib.request.urlopen(urllib.request.Request(SITE + '/wp-json/wp/v2' + path, data=data, headers=headers, method=method), timeout=45) as resp:
        return json.load(resp), resp.headers

def get_post(post_id):
    row = request(f'/posts/{post_id}?context=edit')[0]
    require(row['id'] == post_id and row['slug'] == TARGETS[post_id][0] and row['status'] == 'publish', 'Target identity/status mismatch')
    require(isinstance(row.get('content', {}).get('raw'), str), 'Raw current content required')
    return row

def invariant(row):
    return {k: row.get(k) for k in ['id', 'slug', 'status', 'title', 'featured_media', 'author', 'categories', 'tags', 'date', 'date_gmt', 'excerpt', 'meta']}

def counts():
    return {kind: int(request(f'/{kind}?status=publish&per_page=1&_fields=id')[1]['X-WP-Total']) for kind in ['posts', 'pages']}

def save(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['preflight', 'apply'], required=True)
    mode = parser.parse_args().mode
    OUT.mkdir(parents=True, exist_ok=True)
    summary = ['# Remove nine Wayback image blocks', f'- mode: {mode}', '- scope: posts 1883, 1887, 1892; content only; no media deletion']
    try:
        public_before = counts()
        plans = []
        # Validate all three before any write; retain the latest source and exact removed blocks.
        for post_id in TARGETS:
            before = get_post(post_id)
            content = before['content']['raw']
            fixed, removed = transform(content, post_id)
            save(f'{post_id}-before.json', before)
            save(f'{post_id}-plan.json', {'post_id': post_id, 'slug': before['slug'], 'before_sha256': digest(content), 'after_sha256': digest(fixed), 'removed_urls': removed, 'content_after': fixed})
            plans.append((post_id, before, fixed, removed))
            summary.append(f'- preflight {post_id} / {before["slug"]}: {len(removed)} images; text unchanged; before_sha256={digest(content)}')
        if mode == 'apply':
            for post_id, before, fixed, removed in plans:
                fresh = get_post(post_id)
                require(fresh['content']['raw'] == before['content']['raw'] and invariant(fresh) == invariant(before) and fresh['modified_gmt'] == before['modified_gmt'], 'Concurrent edit detected; stopping')
                request(f'/posts/{post_id}', 'POST', {'content': fixed})
                after = get_post(post_id)
                save(f'{post_id}-after.json', after)
                require(after['content']['raw'] == fixed, 'Written content differs')
                require(invariant(after) == invariant(before), 'Non-content fields changed')
                summary.append(f'- APPLIED {post_id}: removed {len(removed)}; status=publish retained; featured_media={after["featured_media"]} unchanged')
        public_after = counts()
        require(public_before == public_after, 'Public counts changed')
        summary.append(f'- public_before={public_before}; public_after={public_after}')
        summary.append('- result: SUCCESS' if mode == 'apply' else '- result: PREFLIGHT_OK (no writes)')
    except Exception:
        summary.append('- result: STOPPED; review logs and per-post backups; do not assume all targets updated')
        raise
    finally:
        report = '\n'.join(summary) + '\n'
        (OUT / 'summary.md').write_text(report, encoding='utf-8')
        print(report)

if __name__ == '__main__':
    main()
