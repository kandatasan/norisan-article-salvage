import base64
import json
import os
from pathlib import Path
import sys
import time
import urllib.request

BASE='https://tsurikue.com/wp-json/wp/v2'
PAGE_ID=3154
BACKUP=Path('/tmp/outing-dark-hero-backup.txt')
USER=os.environ['TSURIKUE_WP_USER']
PW=os.environ['TSURIKUE_WP_APP_PASSWORD']
TOKEN=base64.b64encode(f'{USER}:{PW}'.encode()).decode()


def request(path, method='GET', data=None):
    last=None
    for attempt in range(1,4):
        try:
            payload=None
            headers={'Authorization':'Basic '+TOKEN,'Accept':'application/json','User-Agent':'tsurikue-outing-dark-hero/1.0'}
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
        'mobile_v2':'/* TQ OUTING MOBILE REPAIR v2 */' in s,
        'dark_hero_absent':'/* TQ OUTING DARK HERO v1 */' not in s,
    }
    print('OUTING_DARK_HERO_BACKUP_CHECKS='+json.dumps(checks,ensure_ascii=False))
    if not all(checks.values()): raise SystemExit('DARK_HERO_BACKUP_GUARD_FAILED')
    BACKUP.write_text(s,encoding='utf-8')
    print('OUTING_DARK_HERO_BACKUP_SAVED')


def verify():
    page=get_page(); s=raw(page)
    checks={
        'id':page.get('id')==PAGE_ID,
        'slug':page.get('slug')=='odekake',
        'draft':page.get('status')=='draft',
        'blocks':'<!-- tsurikue-category-hub:v2:outing-blocks -->' in s,
        'mobile_v2':'/* TQ OUTING MOBILE REPAIR v2 */' in s,
        'dark_hero':'/* TQ OUTING DARK HERO v1 */' in s,
        'dark_overlay':'rgba(8,22,28,.74)' in s,
        'white_text':'color:#fff!important;' in s,
        'shadow':'text-shadow:0 3px 18px' in s,
        'travel':'旅に出る' in s,
        'latest':'wp:latest-posts' in s,
    }
    print('OUTING_DARK_HERO_VERIFY='+json.dumps(checks,ensure_ascii=False))
    if not all(checks.values()): raise SystemExit('DARK_HERO_VERIFY_FAILED')
    print('OUTING_DARK_HERO_VERIFIED')


def restore():
    if not BACKUP.exists():
        print('NO_DARK_HERO_BACKUP_TO_RESTORE'); return
    content=BACKUP.read_text(encoding='utf-8')
    page=request(f'/pages/{PAGE_ID}','POST',{'content':content,'status':'draft'})
    ok=page.get('id')==PAGE_ID and page.get('status')=='draft'
    print('OUTING_DARK_HERO_RESTORE='+str(ok))
    if not ok: raise SystemExit('DARK_HERO_RESTORE_FAILED')


if __name__=='__main__':
    mode=sys.argv[1] if len(sys.argv)>1 else ''
    {'backup':backup,'verify':verify,'restore':restore}.get(mode,lambda: (_ for _ in ()).throw(SystemExit('usage: guard.py backup|verify|restore')))()
