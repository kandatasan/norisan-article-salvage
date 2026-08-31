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
CSS_START = '/* TQ HEADER DRAWER PROTOTYPE v1 */'
CSS_END = '/* END TQ HEADER DRAWER PROTOTYPE v1 */'
HTML_START = '<!-- TQ HEADER NAV PROTOTYPE v1 START -->'
HTML_END = '<!-- TQ HEADER NAV PROTOTYPE v1 END -->'

LINKS = {
    'おでかけ': '/category/sightseeing-leisure/',
    'グルメ': '/category/gourmet/',
    '釣り': '/category/fishing/',
    'クルマ': '/category/car/',
}
PROFILE = '/profile/'
CONTACT = '/contact-form/'
FAMILY = 'https://tsurikue.com/wp-content/uploads/2026/08/e9134f4d-3d71-45fd-a6e7-cf47982bb93d.jpg'
HERO = 'https://tsurikue.com/wp-content/uploads/2026/05/img_4588.jpg'

user = os.environ['TSURIKUE_WP_USER']
pw = os.environ['TSURIKUE_WP_APP_PASSWORD']
token = base64.b64encode(f'{user}:{pw}'.encode()).decode()
headers = {
    'Authorization': 'Basic ' + token,
    'Accept': 'application/json',
    'Content-Type': 'application/json; charset=utf-8',
    'User-Agent': 'tsurikue-header-prototype-v1/1.0',
}


def get_page():
    q = urllib.parse.urlencode({'context': 'edit', '_fields': 'id,slug,status,title,content'})
    req = urllib.request.Request(
        f'https://tsurikue.com/wp-json/wp/v2/pages/{PAGE_ID}?{q}', headers=headers
    )
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode())


def raw_content(page):
    return (page.get('content') or {}).get('raw') or ''


page = get_page()
original = raw_content(page)
original_status = page.get('status')

if page.get('id') != PAGE_ID or original_status not in ('draft', 'publish'):
    raise SystemExit('BLOCKED_WRONG_PAGE_STATE')
if MARKER not in original or '.tq4' not in original or '</style>' not in original:
    raise SystemExit('BLOCKED_EXPECTED_TOP_MISSING')
if HERO not in original or '2992' not in original or FAMILY not in original:
    raise SystemExit('BLOCKED_EXPECTED_MEDIA_MISSING')
for label, href in LINKS.items():
    if label not in original or href not in original:
        raise SystemExit('BLOCKED_CATEGORY_LINK_MISSING_' + label)

# Idempotent cleanup before writing the current prototype.
content = re.sub(
    r'\n?/\* TQ HEADER DRAWER PROTOTYPE v1 \*/.*?/\* END TQ HEADER DRAWER PROTOTYPE v1 \*/\n?',
    '\n',
    original,
    flags=re.S,
)
content = re.sub(
    r'\n?<!-- TQ HEADER NAV PROTOTYPE v1 START -->.*?<!-- TQ HEADER NAV PROTOTYPE v1 END -->\n?',
    '\n',
    content,
    flags=re.S,
)

css = r'''
/* TQ HEADER DRAWER PROTOTYPE v1 */
/* Scope the prototype to the static front page by the presence of .tq4. */
body:has(.tq4) #header{
  position:sticky!important;top:0;z-index:99980;
  background:rgba(255,255,255,.94)!important;
  border-bottom:1px solid #e7e3d9;
  box-shadow:0 4px 18px rgba(32,33,31,.045);
  backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px)
}
body.admin-bar:has(.tq4) #header{top:32px}
body:has(.tq4) #header .l-header__bar{display:none!important}
body:has(.tq4) #header .l-header__inner{
  height:72px;min-height:72px;max-width:1180px!important;
  padding-left:22px!important;padding-right:22px!important
}
body:has(.tq4) #header .c-headLogo__link{
  font-size:24px!important;font-weight:900!important;letter-spacing:.08em;
  color:#20211f!important;line-height:1.1
}
body:has(.tq4) #header .c-headLogo__link:after{
  content:"";display:block;width:31px;height:3px;margin:7px auto 0;border-radius:99px;
  background:linear-gradient(90deg,#f3b92f 0 29%,transparent 29% 35%,#7ab0df 35% 64%,transparent 64% 70%,#8fb56e 70% 100%)
}
body:has(.tq4) #header .l-header__customBtn .c-iconBtn{
  width:48px;height:48px;border:1px solid #e4e0d6;border-radius:50%;background:#fff
}
body:has(.tq4) #header .l-header__menuBtn{opacity:0!important;pointer-events:none!important}
body:has(.tq4) #gnav{display:none!important}

/* Pure HTML/CSS mobile hamburger. */
.tq-site-menu{position:fixed;left:0;top:0;z-index:99996;width:0;height:0;margin:0!important}
.tq-site-menu>summary{
  position:fixed;left:7px;top:12px;z-index:99999;width:48px;height:48px;
  display:flex;align-items:center;justify-content:center;list-style:none;cursor:pointer;
  border-radius:50%;background:transparent
}
.tq-site-menu>summary::-webkit-details-marker{display:none}
.tq-site-menu__bars,.tq-site-menu__bars:before,.tq-site-menu__bars:after{
  display:block;width:25px;height:2px;border-radius:99px;background:#20211f;content:"";
  transition:transform .22s ease,opacity .22s ease
}
.tq-site-menu__bars{position:relative}
.tq-site-menu__bars:before{position:absolute;top:-8px;left:0}
.tq-site-menu__bars:after{position:absolute;top:8px;left:0}
.tq-site-menu[open] .tq-site-menu__bars{background:transparent}
.tq-site-menu[open] .tq-site-menu__bars:before{top:0;transform:rotate(45deg)}
.tq-site-menu[open] .tq-site-menu__bars:after{top:0;transform:rotate(-45deg)}
.tq-site-menu[open]:before{
  content:"";position:fixed;inset:0;z-index:99990;background:rgba(22,24,21,.45);
  backdrop-filter:blur(2px);-webkit-backdrop-filter:blur(2px);pointer-events:none
}
.tq-site-menu__drawer{
  position:fixed;left:0;top:0;z-index:99995;width:min(88vw,360px);height:100dvh;
  overflow:auto;padding:82px 24px 28px;background:#f7f5ef;border-right:1px solid #dedbd1;
  box-shadow:18px 0 50px rgba(18,20,17,.16)
}
.tq-site-menu__eyebrow{margin:0 0 7px;font-size:10px;font-weight:900;letter-spacing:.18em;color:#77786f}
.tq-site-menu__title{margin:0 0 22px;font-size:27px;line-height:1.25;letter-spacing:-.035em;font-weight:900;color:#20211f}
.tq-site-menu__quest{display:grid;gap:8px;margin:0}
.tq-site-menu__quest a{
  position:relative;display:block;padding:15px 44px 15px 16px;border:1px solid #dedbd1;
  border-radius:14px;background:#fff;color:#20211f;text-decoration:none!important
}
.tq-site-menu__quest a:after{content:"→";position:absolute;right:16px;top:50%;transform:translateY(-50%);font-size:18px}
.tq-site-menu__quest small{display:block;margin:0 0 3px;font-size:9px;letter-spacing:.14em;font-weight:900;color:#77786f}
.tq-site-menu__quest strong{display:block;font-size:18px;line-height:1.35}
.tq-site-menu__quest span{display:block;margin-top:3px;font-size:10px;line-height:1.5;color:#77786f}
.tq-site-menu__quest a:nth-child(1){border-left:5px solid #7ab0df}
.tq-site-menu__quest a:nth-child(2){border-left:5px solid #f3b92f}
.tq-site-menu__quest a:nth-child(3){border-left:5px solid #8fb56e}
.tq-site-menu__quest a:nth-child(4){border-left:5px solid #b8a7c7}
.tq-site-menu__utility{display:flex;flex-wrap:wrap;gap:8px 14px;margin:22px 2px 0;padding-top:18px;border-top:1px solid #dedbd1}
.tq-site-menu__utility a{font-size:11px;font-weight:800;color:#555750;text-decoration:none!important}
.tq-site-menu__family{margin:24px 0 0;padding:15px 10px 6px;border-radius:14px;background:#fff;border:1px solid #e4e0d6}
.tq-site-menu__family img{display:block;width:100%;height:auto;max-height:110px;object-fit:contain}
.tq-site-menu__family p{margin:6px 0 0;text-align:center;font-size:9px;font-weight:800;letter-spacing:.08em;color:#85867f}

/* Desktop navigation. */
.tq-site-nav{
  position:fixed;z-index:99992;left:50%;top:0;transform:translateX(-50%);height:72px;
  display:flex;align-items:center;gap:4px;margin:0!important;padding:0
}
.tq-site-nav a{
  position:relative;display:flex;align-items:center;height:44px;padding:0 13px;border-radius:999px;
  color:#3b3d38!important;text-decoration:none!important;font-size:12px;font-weight:800;letter-spacing:.03em;
  transition:background .18s ease,transform .18s ease
}
.tq-site-nav a:hover{background:#f3f0e8;transform:translateY(-1px)}
.tq-site-nav a:after{
  content:"";position:absolute;left:16px;right:16px;bottom:6px;height:2px;border-radius:99px;
  background:#0e4c5a;transform:scaleX(0);transition:transform .18s ease
}
.tq-site-nav a:hover:after{transform:scaleX(1)}

@media(max-width:782px){
  body.admin-bar:has(.tq4) #header{top:46px}
  body.admin-bar .tq-site-menu>summary{top:58px}
  body.admin-bar .tq-site-menu__drawer{padding-top:128px}
}
@media(max-width:959px){
  .tq-site-nav{display:none!important}
  body:has(.tq4) #header .l-header__inner{height:64px;min-height:64px;padding-left:8px!important;padding-right:8px!important}
  body:has(.tq4) #header .c-headLogo__link{font-size:22px!important}
}
@media(min-width:960px){
  .tq-site-menu{display:none!important}
  body:has(.tq4) #header .l-header__logo{min-width:170px}
}
@media(prefers-reduced-motion:reduce){
  .tq-site-menu__bars,.tq-site-menu__bars:before,.tq-site-menu__bars:after,.tq-site-nav a{transition:none!important}
}
/* END TQ HEADER DRAWER PROTOTYPE v1 */
'''
content = content.replace('</style>', css + '\n</style>', 1)

menu_html = f'''
{HTML_START}
<!-- wp:html -->
<details class="tq-site-menu">
  <summary aria-label="メニューを開閉"><span class="tq-site-menu__bars" aria-hidden="true"></span></summary>
  <div class="tq-site-menu__drawer">
    <p class="tq-site-menu__eyebrow">TSURIKUE! / HOLIDAY MENU</p>
    <p class="tq-site-menu__title">今日は、<br>なにして遊ぶ？</p>
    <nav class="tq-site-menu__quest" aria-label="休日メニュー">
      <a href="{LINKS['おでかけ']}"><small>GO OUT</small><strong>おでかけ</strong><span>遊び場・観光・温泉・旅行</span></a>
      <a href="{LINKS['グルメ']}"><small>EAT</small><strong>グルメ</strong><span>街のごはん・旅先グルメ</span></a>
      <a href="{LINKS['釣り']}"><small>FISH</small><strong>釣り</strong><span>気軽な釣り・野食・魚料理</span></a>
      <a href="{LINKS['クルマ']}"><small>CAR</small><strong>クルマ</strong><span>レクサスUX・洗車・カー用品</span></a>
    </nav>
    <div class="tq-site-menu__utility">
      <a href="{PROFILE}">つりくえ！について</a>
      <a href="{CONTACT}">お問い合わせ</a>
    </div>
    <div class="tq-site-menu__family"><img src="{FAMILY}" alt="つりくえ！一家のドット絵"><p>のんびり冒険中。</p></div>
  </div>
</details>
<nav class="tq-site-nav" aria-label="つりくえ！メインナビ">
  <a href="{LINKS['おでかけ']}">おでかけ</a>
  <a href="{LINKS['グルメ']}">グルメ</a>
  <a href="{LINKS['釣り']}">釣り</a>
  <a href="{LINKS['クルマ']}">クルマ</a>
  <a href="{PROFILE}">ABOUT</a>
</nav>
<!-- /wp:html -->
{HTML_END}
'''

first_end = content.find('<!-- /wp:html -->')
if first_end < 0:
    raise SystemExit('BLOCKED_LEADING_HTML_END_MISSING')
first_end += len('<!-- /wp:html -->')
content = content[:first_end] + '\n' + menu_html + content[first_end:]

# Avoid overwriting a manual edit made during this run.
latest = get_page()
latest_content = raw_content(latest)
if latest.get('status') != original_status:
    raise SystemExit('BLOCKED_STATUS_CHANGED_DURING_RUN')
if hashlib.sha256(latest_content.encode()).hexdigest() != hashlib.sha256(original.encode()).hexdigest():
    raise SystemExit('BLOCKED_PAGE_CHANGED_DURING_RUN')

payload = json.dumps({'content': content}, ensure_ascii=False).encode('utf-8')
req = urllib.request.Request(
    f'https://tsurikue.com/wp-json/wp/v2/pages/{PAGE_ID}',
    data=payload,
    headers=headers,
    method='POST',
)
with urllib.request.urlopen(req, timeout=45) as r:
    json.loads(r.read().decode())

after = get_page()
after_content = raw_content(after)
if after.get('status') != original_status:
    raise SystemExit('VERIFY_STATUS_CHANGED')
if after_content.count(CSS_START) != 1 or after_content.count(HTML_START) != 1:
    raise SystemExit('VERIFY_PROTOTYPE_NOT_UNIQUE')
for label, href in LINKS.items():
    if label not in after_content or href not in after_content:
        raise SystemExit('VERIFY_MENU_LINK_MISSING_' + label)

pathlib.Path('experimental-pages/top-design-lab/content.html').write_text(after_content, encoding='utf-8')
cfg_path = pathlib.Path('experimental-pages/top-design-lab/config.json')
cfg = json.loads(cfg_path.read_text(encoding='utf-8'))
cfg['expected_current_content_sha256'] = hashlib.sha256(after_content.encode()).hexdigest()
cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

print('SUCCESS_HEADER_PROTOTYPE')
print('status=' + str(after.get('status')))
