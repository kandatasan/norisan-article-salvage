#!/usr/bin/env python3
import hashlib
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent
CONTENT = ROOT / 'content.html'
CONFIG = ROOT / 'config.json'
MARKER = '<!-- tsurikue-experimental-page:v1:top-design-lab -->'
INSERT_BEFORE = '/* TQ HEADER DRAWER PROTOTYPE v1 */'
PATCH_START = '/* TQ TOP CARD RESPONSE + HUB LINKS v2 */'
PATCH_END = '/* END TQ TOP CARD RESPONSE + HUB LINKS v2 */'

content = CONTENT.read_text(encoding='utf-8')
if MARKER not in content:
    raise SystemExit('HOMEPAGE_MARKER_MISSING')

# All four homepage navigation surfaces should enter the designed hub pages,
# not the plain WordPress category archives.
links = {
    '/category/sightseeing-leisure/': '/odekake/',
    '/category/gourmet/': '/gourmet-guide/',
    '/category/fishing/': '/fishing-guide/',
    '/category/car/': '/car-guide/',
}
for old, new in links.items():
    if old in content:
        content = content.replace(old, new)
    elif new not in content:
        raise SystemExit(f'HOMEPAGE_LINK_TARGET_MISSING old={old} new={new}')

# Remove old viewport-unit full-width workarounds. The later v4/v5 rules already
# make the homepage full width using parent sizing and percentages, so these are
# redundant and are the source of the editor/mobile width recalculation wobble.
content = content.replace(
    '  width:100vw;\n  margin-left:calc(50% - 50vw);',
    '  width:100%;\n  max-width:100%;\n  margin-left:0;\n  margin-right:0;',
    1,
)
for start, end in [
    ('MOBILE VIEWPORT CENTER FIX v2', 'MOBILE FULL-WIDTH FIX v3'),
]:
    pass
content = re.sub(
    r'\n?/\* MOBILE VIEWPORT CENTER FIX v2 \*/.*?(?=/\* MOBILE FULL-WIDTH FIX v3 \*/)',
    '\n',
    content,
    flags=re.S,
)
content = re.sub(
    r'\n?/\* MOBILE FULL-WIDTH FIX v3 \*/.*?/\* END MOBILE FULL-WIDTH FIX v3 \*/\n?',
    '\n',
    content,
    flags=re.S,
)

# Replace previous response patch idempotently.
content = re.sub(
    r'\n?/\* TQ TOP CARD RESPONSE \+ HUB LINKS v2 \*/.*?/\* END TQ TOP CARD RESPONSE \+ HUB LINKS v2 \*/\n?',
    '\n',
    content,
    flags=re.S,
)
if INSERT_BEFORE not in content:
    raise SystemExit('HOMEPAGE_INSERT_MARKER_MISSING')

css = r'''
/* TQ TOP CARD RESPONSE + HUB LINKS v2 */
/* The existing H3 anchor becomes the real hit target for the entire photo card. */
.tq4 .tq4-cat{
  position:relative!important;
  isolation:isolate;
  cursor:pointer;
  touch-action:manipulation;
  -webkit-tap-highlight-color:transparent;
}
.tq4 .tq4-cat h3 a{
  position:static!important;
  -webkit-tap-highlight-color:transparent;
}
.tq4 .tq4-cat h3 a::after{
  content:"";
  position:absolute;
  inset:0;
  z-index:6;
  border-radius:inherit;
  background:transparent;
  transition:background-color .12s ease;
}
.tq4 .tq4-cat h3 a:active::after{background:rgba(255,255,255,.13)}
@supports selector(.tq4-cat:has(h3 a:active)){
  .tq4 .tq4-cat:has(h3 a:active){
    transform:translateY(1px) scale(.985)!important;
    box-shadow:0 5px 14px rgba(32,33,31,.10)!important;
    transition-duration:.08s!important;
  }
}
@media(hover:none){
  .tq4 .tq4-cat:hover{transform:none;box-shadow:none}
  .tq4 .tq4-cat:hover img{transform:none!important}
}
/* Keep the block editor editable; the stretched hit area is frontend-only. */
.editor-styles-wrapper .tq4 .tq4-cat h3 a::after,
.block-editor-block-list__layout .tq4 .tq4-cat h3 a::after{display:none!important}
/* END TQ TOP CARD RESPONSE + HUB LINKS v2 */
'''
content = content.replace(INSERT_BEFORE, css + '\n' + INSERT_BEFORE, 1)

required = [
    PATCH_START, PATCH_END,
    'href="/odekake/"', 'href="/gourmet-guide/"',
    'href="/fishing-guide/"', 'href="/car-guide/"',
    'tq4-cat--outing', 'tq4-cat--gourmet', 'tq4-cat--fishing', 'tq4-cat--car',
]
missing = [x for x in required if x not in content]
if missing:
    raise SystemExit('HOMEPAGE_PREPARE_REQUIRED_MISSING=' + repr(missing))
if any(old in content for old in links):
    raise SystemExit('HOMEPAGE_OLD_CATEGORY_LINK_REMAINS')
if '100vw' in content or '100dvw' in content or '50vw' in content or '50dvw' in content:
    raise SystemExit('HOMEPAGE_VIEWPORT_WIDTH_HACK_REMAINS')
if content.count(PATCH_START) != 1:
    raise SystemExit('HOMEPAGE_RESPONSE_PATCH_DUPLICATED')

CONTENT.write_text(content, encoding='utf-8')
cfg = json.loads(CONFIG.read_text(encoding='utf-8'))
cfg['expected_current_content_sha256'] = hashlib.sha256(content.encode()).hexdigest()
cfg['homepage_revision'] = 'complete-v2-card-response-hub-links'
CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

print(json.dumps({
    'ok': True,
    'content_sha256': cfg['expected_current_content_sha256'],
    'category_archive_links_remaining': sum(content.count(x) for x in links),
    'response_patch_count': content.count(PATCH_START),
    'viewport_hacks': {k: content.count(k) for k in ['100vw','100dvw','50vw','50dvw']},
}, ensure_ascii=False))
