import base64
import json
import os
from pathlib import Path
import sys
import time
import urllib.request

BASE='https://tsurikue.com/wp-json/wp/v2'
PAGE_ID=3154
BACKUP=Path('/tmp/outing-mobile-repair-backup.txt')
USER=os.environ['TSURIKUE_WP_USER']
PW=os.environ['TSURIKUE_WP_APP_PASSWORD']
TOKEN=base64.b64encode(f'{USER}:{PW}'.encode()).decode()


def request(path, method='GET', data=None):
    last=None
    for attempt in range(1,4):
        try:
            payload=None
            headers={'Authorization':'Basic '+TOKEN,'Accept':'application/json','User-Agent':'tsurikue-outing-mobile-repair/1.0'}
            if data is not None:
                payload=json.dumps(data,ensure_ascii=False).encode('utf-8')
                headers['Content-Type']='application/json; charset=utf-8'
            req=urllib.request.Request(BASE+path,data=payload,method=method,headers=headers)
            with urllib.request.urlopen(req,timeout=35) as r:
                return json.loads(r.read().decode('utf-8'))
        except Exception as e:
            last=e
            if attempt<3: time.sleep(6)
    raise RuntimeError(f'REQUEST_FAILED {method} {path}: {last}')


def get_page():
    return request(f'/pages/{PAGE_ID}?context=edit&_fields=id,slug,status,content')


def raw(page):
    c=page.get('content') or {}
    return c.get('raw') or c.get('rendered') or ''


def backup():
    page=get_page(); s=raw(page)
    checks={
        'id':page.get('id')==PAGE_ID,
        'slug':page.get('slug')=='odekake',
        'draft':page.get('status')=='draft',
        'blocks':'<!-- tsurikue-category-hub:v2:outing-blocks -->' in s,
        'repair_absent':'/* TQ OUTING MOBILE REPAIR v1 */' not in s,
    }
    print('OUTING_MOBILE_BACKUP_CHECKS='+json.dumps(checks,ensure_ascii=False))
    if not all(checks.values()): raise SystemExit('BACKUP_GUARD_FAILED')
    BACKUP.write_text(s,encoding='utf-8')
    print('OUTING_MOBILE_BACKUP_SAVED')


def verify():
    page=get_page(); s=raw(page)
    checks={
        'id':page.get('id')==PAGE_ID,
        'slug':page.get('slug')=='odekake',
        'draft':page.get('status')=='draft',
        'blocks':'<!-- tsurikue-category-hub:v2:outing-blocks -->' in s,
        'repair':'/* TQ OUTING MOBILE REPAIR v1 */' in s,
        'dark_hero':'.tq-out .tq-out-hero{color:#20211f!important}' in s,
        'trip_one_col':'.tq-out .tq-out-trip-grid{grid-template-columns:1fr!important}' in s,
        'local_one_col':'.tq-out .tq-out-local-grid{grid-template-columns:1fr!important}' in s,
        'travel':'旅に出る' in s,
        'latest':'wp:latest-posts' in s,
    }
    print('OUTING_MOBILE_VERIFY='+json.dumps(checks,ensure_ascii=False))
    if not all(checks.values()): raise SystemExit('VERIFY_FAILED')
    print('OUTING_MOBILE_REPAIR_VERIFIED')


def restore():
    if not BACKUP.exists():
        print('NO_BACKUP_TO_RESTORE'); return
    content=BACKUP.read_text(encoding='utf-8')
    page=request(f'/pages/{PAGE_ID}','POST',{'content':content,'status':'draft'})
    ok=page.get('id')==PAGE_ID and page.get('status')=='draft'
    print('OUTING_MOBILE_RESTORE='+str(ok))
    if not ok: raise SystemExit('RESTORE_FAILED')


if __name__=='__main__':
    mode=sys.argv[1] if len(sys.argv)>1 else ''
    {'backup':backup,'verify':verify,'restore':restore}.get(mode,lambda: (_ for _ in ()).throw(SystemExit('usage: guard.py backup|verify|restore')))()
