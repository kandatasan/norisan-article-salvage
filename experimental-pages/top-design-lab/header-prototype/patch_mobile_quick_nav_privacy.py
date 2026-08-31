import base64
import hashlib
import json
import os
import pathlib
import re
import urllib.parse
import urllib.request

PAGE_ID = 2983
MARKER = '<!-- tsurikue-experimental-page:v1:top-design-lab -->'
CSS_END = '/* END TQ HEADER DRAWER PROTOTYPE v1 */'
HTML_START = '<!-- TQ HEADER NAV PROTOTYPE v1 START -->'
HTML_END = '<!-- TQ HEADER NAV PROTOTYPE v1 END -->'
PATCH_START = '/* TQ MOBILE QUICK NAV PRIVACY v1 */'
PATCH_END = '/* END TQ MOBILE QUICK NAV PRIVACY v1 */'
PRIVACY_LINK = '<a href="/privacy-policy/">プライバシーポリシー</a>'

user = os.environ['TSURIKUE_WP_USER']
pw = os.environ['TSURIKUE_WP_APP_PASSWORD']
token = base64.b64encode(f'{user}:{pw}'.encode()).decode()
headers = {
    'Authorization': 'Basic ' + token,
    'Accept': 'application/json',
    'Content-Type': 'application/json; charset=utf-8',
    'User-Agent': 'tsurikue-mobile-quick-nav-v1/1.0',
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
    raise SystemExit('MOBILE_NAV_BLOCKED_WRONG_PAGE_STATE')
if MARKER not in content or CSS_END not in content or HTML_START not in content or HTML_END not in content:
    raise SystemExit('MOBILE_NAV_BLOCKED_HEADER_PROTOTYPE_MISSING')
if 'class="tq-site-nav"' not in content or 'class="tq-site-menu__utility"' not in content:
    raise SystemExit('MOBILE_NAV_BLOCKED_EXPECTED_NAV_MISSING')

# Idempotently remove this patch before rebuilding it.
content = re.sub(
    r'\n?/\* TQ MOBILE QUICK NAV PRIVACY v1 \*/.*?/\* END TQ MOBILE QUICK NAV PRIVACY v1 \*/\n?',
    '\n',
    content,
    flags=re.S,
)

# Add the privacy link only inside the custom drawer utility area.
start = content.index(HTML_START)
end = content.index(HTML_END, start) + len(HTML_END)
section = content[start:end]
section = re.sub(
    r'\s*<a href="/privacy-policy/">プライバシーポリシー</a>',
    '',
    section,
)
needle = '<a href="/contact-form/">お問い合わせ</a>'
if needle not in section:
    raise SystemExit('MOBILE_NAV_BLOCKED_CONTACT_LINK_MISSING')
section = section.replace(needle, needle + '\n      ' + PRIVACY_LINK, 1)
content = content[:start] + section + content[end:]

css = r'''
/* TQ MOBILE QUICK NAV PRIVACY v1 */
@media(max-width:959px){
  .tq-site-nav{
    position:sticky!important;
    top:64px!important;
    left:auto!important;
    right:auto!important;
    transform:none!important;
    z-index:99970!important;
    display:flex!important;
    align-items:center!important;
    justify-content:flex-start!important;
    width:100%!important;
    max-width:none!important;
    height:44px!important;
    margin:0!important;
    padding:0 8px!important;
    gap:2px!important;
    overflow-x:auto!important;
    overflow-y:hidden!important;
    white-space:nowrap!important;
    background:rgba(255,255,255,.97)!important;
    border-top:1px solid #f3f0e8!important;
    border-bottom:1px solid #e7e3d9!important;
    box-shadow:0 3px 12px rgba(32,33,31,.035)!important;
    scrollbar-width:none;
    -webkit-overflow-scrolling:touch;
  }
  .tq-site-nav::-webkit-scrollbar{display:none}
  .tq-site-nav a{
    flex:1 0 auto!important;
    min-width:72px!important;
    height:44px!important;
    padding:0 10px!important;
    justify-content:center!important;
    border-radius:0!important;
    font-size:11px!important;
    font-weight:850!important;
    letter-spacing:.02em!important;
  }
  .tq-site-nav a:after{
    left:16px!important;
    right:16px!important;
    bottom:4px!important;
  }
  .tq-site-nav a:last-child{display:none!important}
  body.admin-bar .tq-site-nav{top:110px!important}
}
/* END TQ MOBILE QUICK NAV PRIVACY v1 */
'''
content = content.replace(CSS_END, css + '\n' + CSS_END, 1)

post_content(content)
after = get_page()
after_content = raw_content(after)
if after.get('status') != status:
    raise SystemExit('MOBILE_NAV_VERIFY_STATUS_CHANGED')
if PATCH_START not in after_content or PATCH_END not in after_content:
    raise SystemExit('MOBILE_NAV_VERIFY_CSS_PATCH_MISSING')
if PRIVACY_LINK not in after_content:
    raise SystemExit('MOBILE_NAV_VERIFY_PRIVACY_LINK_MISSING')
if after_content.count(PRIVACY_LINK) != 1:
    raise SystemExit('MOBILE_NAV_VERIFY_PRIVACY_LINK_DUPLICATED')

pathlib.Path('experimental-pages/top-design-lab/content.html').write_text(after_content, encoding='utf-8')
cfg_path = pathlib.Path('experimental-pages/top-design-lab/config.json')
cfg = json.loads(cfg_path.read_text(encoding='utf-8'))
cfg['expected_current_content_sha256'] = hashlib.sha256(after_content.encode()).hexdigest()
cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

print('SUCCESS_MOBILE_QUICK_NAV_PRIVACY_V1')
print('status=' + str(after.get('status')))
