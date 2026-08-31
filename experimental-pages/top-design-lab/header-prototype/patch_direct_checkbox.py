import base64
import hashlib
import json
import os
import pathlib
import urllib.parse
import urllib.request

PAGE_ID = 2983
MARKER = '<!-- tsurikue-experimental-page:v1:top-design-lab -->'
CSS_END = '/* END TQ HEADER DRAWER PROTOTYPE v1 */'
DIRECT_MARKER = '/* TQ DIRECT CHECKBOX HIT TARGET v4 */'

user = os.environ['TSURIKUE_WP_USER']
pw = os.environ['TSURIKUE_WP_APP_PASSWORD']
token = base64.b64encode(f'{user}:{pw}'.encode()).decode()
headers = {
    'Authorization': 'Basic ' + token,
    'Accept': 'application/json',
    'Content-Type': 'application/json; charset=utf-8',
    'User-Agent': 'tsurikue-header-prototype-v4/1.0',
}


def get_page():
    q = urllib.parse.urlencode({'context': 'edit', '_fields': 'id,status,content'})
    req = urllib.request.Request(
        f'https://tsurikue.com/wp-json/wp/v2/pages/{PAGE_ID}?{q}', headers=headers
    )
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode())


def raw_content(page):
    return (page.get('content') or {}).get('raw') or ''


def post_content(content):
    payload = json.dumps({'content': content}, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(
        f'https://tsurikue.com/wp-json/wp/v2/pages/{PAGE_ID}',
        data=payload,
        headers=headers,
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode())


page = get_page()
status = page.get('status')
content = raw_content(page)
if page.get('id') != PAGE_ID or status not in ('draft', 'publish'):
    raise SystemExit('V4_BLOCKED_WRONG_PAGE_STATE')
if MARKER not in content or CSS_END not in content or 'id="tq-menu-toggle"' not in content:
    raise SystemExit('V4_BLOCKED_V3_PROTOTYPE_MISSING')

# Keep reruns idempotent.
if DIRECT_MARKER in content:
    before = content.split(DIRECT_MARKER, 1)[0]
    tail = content.split(DIRECT_MARKER, 1)[1]
    if CSS_END in tail:
        tail = tail.split(CSS_END, 1)[1]
        content = before + CSS_END + tail

# The checkbox itself becomes the real 48px tap target. The visible hamburger is presentation only.
override = r'''
/* TQ DIRECT CHECKBOX HIT TARGET v4 */
.tq-site-menu-toggle{
  position:fixed!important;left:7px!important;top:12px!important;z-index:100001!important;
  width:48px!important;height:48px!important;margin:0!important;padding:0!important;
  opacity:0!important;pointer-events:auto!important;cursor:pointer!important
}
.tq-site-menu-trigger{z-index:100000!important;pointer-events:none!important}
.tq-site-menu__close{display:none!important}
@media(max-width:782px){body.admin-bar .tq-site-menu-toggle{top:58px!important}}
'''
content = content.replace(CSS_END, override + '\n' + CSS_END, 1)
content = content.replace(
    '<input class="tq-site-menu-toggle" type="checkbox" id="tq-menu-toggle" aria-hidden="true">',
    '<input class="tq-site-menu-toggle" type="checkbox" id="tq-menu-toggle" aria-label="メニューを開閉">',
    1,
)

post_content(content)
after = get_page()
after_content = raw_content(after)
if after.get('status') != status:
    raise SystemExit('V4_VERIFY_STATUS_CHANGED')
if DIRECT_MARKER not in after_content or 'id="tq-menu-toggle"' not in after_content:
    raise SystemExit('V4_VERIFY_PATCH_MISSING')

pathlib.Path('experimental-pages/top-design-lab/content.html').write_text(after_content, encoding='utf-8')
cfg_path = pathlib.Path('experimental-pages/top-design-lab/config.json')
cfg = json.loads(cfg_path.read_text(encoding='utf-8'))
cfg['expected_current_content_sha256'] = hashlib.sha256(after_content.encode()).hexdigest()
cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

print('SUCCESS_HEADER_PROTOTYPE_DIRECT_CHECKBOX_V4')
print('status=' + str(after.get('status')))
