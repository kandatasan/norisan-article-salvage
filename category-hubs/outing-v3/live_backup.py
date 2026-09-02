#!/usr/bin/env python3
import base64
import hashlib
import json
import os
import pathlib
import sys
import urllib.request

BASE = 'https://tsurikue.com/wp-json/wp/v2'
PAGE_ID = 3154
SLUG = 'odekake'
TITLE = 'おでかけ'
AUTH = 'Basic ' + base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode()
BACKUP = pathlib.Path(os.environ.get('TQ_OUTING_BACKUP_PATH', '/tmp/outing-v3-live-backup.json'))


def req(path, method='GET', data=None):
    headers = {'Authorization': AUTH, 'Accept': 'application/json', 'User-Agent': 'tsurikue-outing-v3-backup/1.0'}
    body = None
    if data is not None:
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        headers['Content-Type'] = 'application/json; charset=utf-8'
    request = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode('utf-8'))


def raw(page):
    return (page.get('content') or {}).get('raw') or ''


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def get_page():
    return req(f'/pages/{PAGE_ID}?context=edit&_fields=id,slug,status,title,content')


def title(page):
    return (page.get('title') or {}).get('raw') or ''


mode = sys.argv[1] if len(sys.argv) > 1 else ''
if mode == 'backup':
    page = get_page()
    if page.get('id') != PAGE_ID or page.get('slug') != SLUG or page.get('status') != 'publish' or title(page) != TITLE:
        raise RuntimeError('BACKUP_IDENTITY_FAILED')
    payload = {'page_id': PAGE_ID, 'slug': SLUG, 'status': 'publish', 'title': TITLE, 'content': raw(page), 'sha256': digest(raw(page))}
    BACKUP.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'backup': str(BACKUP), 'sha256': payload['sha256']}, ensure_ascii=False))
elif mode == 'rollback':
    payload = json.loads(BACKUP.read_text(encoding='utf-8'))
    if payload.get('page_id') != PAGE_ID or payload.get('slug') != SLUG or payload.get('status') != 'publish' or payload.get('title') != TITLE:
        raise RuntimeError('ROLLBACK_BACKUP_IDENTITY_FAILED')
    req(f'/pages/{PAGE_ID}', method='POST', data={'content': payload['content']})
    page = get_page()
    if page.get('slug') != SLUG or page.get('status') != 'publish' or title(page) != TITLE or digest(raw(page)) != payload['sha256']:
        raise RuntimeError('ROLLBACK_VERIFY_FAILED')
    print(json.dumps({'rolled_back': True, 'sha256': payload['sha256']}, ensure_ascii=False))
else:
    raise SystemExit('usage: live_backup.py backup|rollback')
