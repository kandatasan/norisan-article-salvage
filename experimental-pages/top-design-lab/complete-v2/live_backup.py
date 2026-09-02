#!/usr/bin/env python3
import base64
import hashlib
import json
import os
import pathlib
import sys
import urllib.parse
import urllib.request

BASE='https://tsurikue.com/wp-json/wp/v2'
PAGE_ID=2983
MARKER='<!-- tsurikue-experimental-page:v1:top-design-lab -->'
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode()
BACKUP=pathlib.Path(os.environ.get('TQ_HOME_BACKUP_PATH','/tmp/homepage-complete-v2-backup.json'))


def req(path, method='GET', data=None):
    headers={'Authorization':AUTH,'Accept':'application/json','User-Agent':'tsurikue-home-complete-v2-backup/1.0'}
    body=None
    if data is not None:
        body=json.dumps(data,ensure_ascii=False).encode('utf-8')
        headers['Content-Type']='application/json; charset=utf-8'
    request=urllib.request.Request(BASE+path,data=body,headers=headers,method=method)
    with urllib.request.urlopen(request,timeout=60) as response:
        return json.loads(response.read().decode('utf-8'))


def get_page():
    q=urllib.parse.urlencode({'context':'edit','_fields':'id,slug,status,title,content'})
    return req(f'/pages/{PAGE_ID}?{q}')


def raw(page): return (page.get('content') or {}).get('raw') or ''
def sha(text): return hashlib.sha256(text.encode()).hexdigest()
def title(page): return (page.get('title') or {}).get('raw') or ''

mode=sys.argv[1] if len(sys.argv)>1 else ''
if mode=='backup':
    page=get_page(); content=raw(page)
    if page.get('id')!=PAGE_ID or page.get('status')!='publish' or MARKER not in content:
        raise RuntimeError('HOME_BACKUP_IDENTITY_FAILED')
    payload={'page_id':PAGE_ID,'slug':page.get('slug'),'status':'publish','title':title(page),'content':content,'sha256':sha(content)}
    BACKUP.write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'backup':str(BACKUP),'slug':payload['slug'],'sha256':payload['sha256']},ensure_ascii=False))
elif mode=='rollback':
    payload=json.loads(BACKUP.read_text(encoding='utf-8'))
    if payload.get('page_id')!=PAGE_ID or payload.get('status')!='publish' or MARKER not in payload.get('content',''):
        raise RuntimeError('HOME_ROLLBACK_BACKUP_IDENTITY_FAILED')
    req(f'/pages/{PAGE_ID}',method='POST',data={'content':payload['content']})
    page=get_page(); content=raw(page)
    if page.get('status')!='publish' or page.get('slug')!=payload.get('slug') or title(page)!=payload.get('title') or sha(content)!=payload.get('sha256'):
        raise RuntimeError('HOME_ROLLBACK_VERIFY_FAILED')
    print(json.dumps({'rolled_back':True,'sha256':payload['sha256']},ensure_ascii=False))
else:
    raise SystemExit('usage: live_backup.py backup|rollback')
