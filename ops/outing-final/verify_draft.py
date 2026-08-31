import base64, json, os, urllib.parse, urllib.request

BASE='https://tsurikue.com/wp-json/wp/v2'
SLUG='odekake'
STATUS='draft'
MARKER='/* TQ OUTING FINAL POLISH v1 */'
PAGE_MARKER='<!-- tsurikue-category-hub:v1:outing -->'
ONE_COLUMN='/* TQ OUTING ONE COLUMN v1 */'

user=os.environ['TSURIKUE_WP_USER']
pw=os.environ['TSURIKUE_WP_APP_PASSWORD']
token=base64.b64encode(f'{user}:{pw}'.encode()).decode()
headers={'Authorization':'Basic '+token,'Accept':'application/json','User-Agent':'tsurikue-outing-final-verify/1.0'}
q=urllib.parse.urlencode({'slug':SLUG,'status':STATUS,'context':'edit','per_page':10,'_fields':'id,slug,status,title,content'})
req=urllib.request.Request(BASE+'/pages?'+q,headers=headers)
with urllib.request.urlopen(req,timeout=40) as r:
    items=json.loads(r.read().decode('utf-8'))
if len(items)!=1:
    raise SystemExit(f'OUTING_DRAFT_COUNT={len(items)}')
page=items[0]
content=(page.get('content') or {}).get('raw') or (page.get('content') or {}).get('rendered') or ''
checks={
    'id':page.get('id')==3154,
    'slug':page.get('slug')==SLUG,
    'draft':page.get('status')==STATUS,
    'page_marker':PAGE_MARKER in content,
    'one_column':ONE_COLUMN in content,
    'final_polish':MARKER in content,
    'sidebar_hidden':'body:has(.tq-out) .l-sidebar{display:none!important}' in content,
    'desktop_width':'width:min(1160px,90vw)!important' in content,
    'h2_reset':'body:has(.tq-out) .tq-out h2' in content,
    'h3_reset':'body:has(.tq-out) .tq-out h3' in content,
    'latest':'wp:latest-posts' in content,
    'temp_nav_absent':'tq-global-site-nav-ref:v1' not in content,
}
print('OUTING_FINAL_DRAFT='+json.dumps({'page_id':page.get('id'),'checks':checks},ensure_ascii=False))
if not all(checks.values()):
    raise SystemExit('OUTING_FINAL_DRAFT_VERIFY_FAILED')
print('OUTING_FINAL_DRAFT_VERIFIED')
