import base64
import json
import os
import re
import urllib.parse
import urllib.request

PAGE_ID = 2983
MARKER = '<!-- tsurikue-experimental-page:v1:top-design-lab -->'
CSS_START = '/* TQ HEADER DRAWER PROTOTYPE v1 */'
CSS_END = '/* END TQ HEADER DRAWER PROTOTYPE v1 */'
HTML_START = '<!-- TQ HEADER NAV PROTOTYPE v1 START -->'
HTML_END = '<!-- TQ HEADER NAV PROTOTYPE v1 END -->'

user = os.environ['TSURIKUE_WP_USER']
pw = os.environ['TSURIKUE_WP_APP_PASSWORD']
token = base64.b64encode(f'{user}:{pw}'.encode()).decode()
headers = {
    'Authorization': 'Basic ' + token,
    'Accept': 'application/json',
    'Content-Type': 'application/json; charset=utf-8',
    'User-Agent': 'tsurikue-header-prototype-rollback/1.0',
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
    raise SystemExit('ROLLBACK_BLOCKED_WRONG_PAGE_STATE')
if MARKER not in content or '.tq4' not in content:
    raise SystemExit('ROLLBACK_BLOCKED_EXPECTED_PAGE_MISSING')

clean = re.sub(
    r'\n?/\* TQ HEADER DRAWER PROTOTYPE v1 \*/.*?/\* END TQ HEADER DRAWER PROTOTYPE v1 \*/\n?',
    '\n',
    content,
    flags=re.S,
)
clean = re.sub(
    r'\n?<!-- TQ HEADER NAV PROTOTYPE v1 START -->.*?<!-- TQ HEADER NAV PROTOTYPE v1 END -->\n?',
    '\n',
    clean,
    flags=re.S,
)

if clean == content:
    print('ROLLBACK_NOT_NEEDED')
    raise SystemExit(0)

post_content(clean)
after = get_page()
after_content = raw_content(after)
if after.get('status') != status:
    raise SystemExit('ROLLBACK_STATUS_CHANGED')
if CSS_START in after_content or HTML_START in after_content or 'tq-menu-toggle' in after_content:
    raise SystemExit('ROLLBACK_PROTOTYPE_STILL_PRESENT')
if MARKER not in after_content or '.tq4' not in after_content:
    raise SystemExit('ROLLBACK_BASE_PAGE_DAMAGED')

print('ROLLBACK_HEADER_PROTOTYPE_SUCCESS')
