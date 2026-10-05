#!/usr/bin/env python3
"""User-authorized rewrite of existing published post 3981 only."""
import base64
import hashlib
import html
import json
import os
from pathlib import Path
import re
import urllib.request

BASE = 'https://tsurikue.com/wp-json/wp/v2'
POST_ID = 3981
SLUG = 'tanto-four-adults-rear-seat'
OLD_TITLE = 'タントは4人乗ると狭い？大人4人で乗った感想｜後部座席はかなり広い'
NEW_TITLE = 'タントは大人4人でも狭くない？後部座席の広さと荷物の本音'
ROOT = Path('editorial/tanto-rear-seat-polish-20261005')
REPORT = Path('reports/tanto-rear-seat-polish-20261005')

def text(value):
    value = re.sub(r'<!--.*?-->', '', value, flags=re.S)
    value = re.sub(r'<[^>]*>', '', value)
    return re.sub(r'\s+', '', html.unescape(value))

def req(path, payload=None):
    # Only this exact post may be written; credentials never appear in reports.
    if payload is not None and path != f'/posts/{POST_ID}':
        raise RuntimeError('WRITE_TARGET_MISMATCH')
    token = base64.b64encode((os.environ['TSURIKUE_WP_USER'] + ':' + os.environ['TSURIKUE_WP_APP_PASSWORD']).encode()).decode()
    headers = {'Authorization': 'Basic ' + token, 'Accept': 'application/json', 'User-Agent': 'tsurikue-rear-seat-polish/20261005'}
    data = None
    if payload is not None:
        if set(payload) != {'title', 'content'}:
            raise RuntimeError('UNEXPECTED_WRITE_FIELDS')
        data = json.dumps(payload, ensure_ascii=False).encode()
        headers['Content-Type'] = 'application/json; charset=utf-8'
    request = urllib.request.Request(BASE + path, headers=headers, data=data, method='POST' if payload is not None else 'GET')
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode()), dict(response.headers)

def get_post():
    row, _ = req(f'/posts/{POST_ID}?context=edit')
    if row['id'] != POST_ID or row['slug'] != SLUG or row['status'] != 'publish':
        raise RuntimeError('EXACT_PUBLISHED_TARGET_MISMATCH')
    return row

def counts():
    result = {}
    for kind in ('posts', 'pages'):
        _, headers = req(f'/{kind}?status=publish&per_page=1&_fields=id')
        result[kind] = int(headers['X-WP-Total'])
    return result

def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

def ids(value):
    return sorted(set(int(x) for x in re.findall(r'wp-image-(\d+)', value)))

def main():
    post = get_post()
    source = post['content']['raw']
    if post['title']['raw'] == NEW_TITLE and '<!-- tsurikue-editorial:tanto-rear-seat-polish:20261005 -->' in source:
        print('Already applied; no WordPress write.')
        return
    if post['title']['raw'] != OLD_TITLE:
        raise RuntimeError('TITLE_CHANGED_SINCE_REVIEW')
    # Exact complete textual baseline captured from the current live article.
    if text(source) != text((ROOT / 'expected-current.txt').read_text()):
        raise RuntimeError('BODY_CHANGED_SINCE_REVIEW')
    if ids(source) != [3961, 3962]:
        raise RuntimeError('UNEXPECTED_BODY_IMAGES')
    images = re.findall(r'<!-- wp:image\b[^>]*-->.*?<!-- /wp:image -->', source, flags=re.S)
    if len(images) != 2:
        raise RuntimeError('EXPECTED_TWO_IMAGE_BLOCKS')
    content = (ROOT / 'content.html').read_text()
    for media_id in (3961, 3962):
        matches = [block for block in images if f'wp-image-{media_id}' in block]
        if len(matches) != 1:
            raise RuntimeError('IMAGE_MAPPING_MISMATCH')
        content = content.replace(f'<!-- KEEP_IMAGE_{media_id} -->', matches[0])
        req(f'/media/{media_id}?context=edit')
    if post['featured_media']:
        req(f'/media/{post["featured_media"]}?context=edit')
    if '<h1' in content or 'KEEP_IMAGE_' in content or content.count('<h2 ') != 4:
        raise RuntimeError('OUTPUT_STRUCTURE_MISMATCH')
    if ids(content) != ids(source) or 'https://tsurikue.com/tanto-6year-review/' not in content:
        raise RuntimeError('OUTPUT_ASSET_MISMATCH')
    before = counts()
    REPORT.mkdir(parents=True, exist_ok=True)
    # Durable workflow artifact contains the current raw source and proposed output.
    (REPORT / 'before.json').write_text(json.dumps(post, ensure_ascii=False, indent=2))
    (REPORT / 'proposed-content.html').write_text(content)
    latest = get_post()
    if latest['content']['raw'] != source or latest['title']['raw'] != OLD_TITLE or latest['modified_gmt'] != post['modified_gmt'] or latest['featured_media'] != post['featured_media']:
        raise RuntimeError('CONCURRENT_EDIT_DETECTED')
    req(f'/posts/{POST_ID}', {'title': NEW_TITLE, 'content': content})
    after = get_post()
    if after['title']['raw'] != NEW_TITLE or after['content']['raw'] != content:
        raise RuntimeError('WRITTEN_CONTENT_VERIFICATION_FAILED')
    for field in ('slug', 'status', 'featured_media', 'categories', 'tags', 'author', 'date', 'date_gmt'):
        if after[field] != post[field]:
            raise RuntimeError(f'PRESERVED_FIELD_CHANGED:{field}')
    if counts() != before:
        raise RuntimeError('PUBLIC_COUNTS_CHANGED')
    result = {'post_id': POST_ID, 'slug': SLUG, 'status': after['status'], 'title': NEW_TITLE, 'body_media': ids(content), 'featured_media': after['featured_media'], 'public_before': before, 'public_after': before, 'wordpress_write_count': 1, 'new_publish_count': 0, 'media_upload_count': 0, 'before_sha256': digest(source), 'after_sha256': digest(content)}
    (REPORT / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
