from pathlib import Path

p = Path('category-hubs/outing/content.html')
s = p.read_text(encoding='utf-8')

MARKER = '/* TQ OUTING ONE COLUMN v1 */'
ANCHOR = "body:has(.tq-out) .l-content{padding-top:0!important}\nbody:has(.tq-out) #content{z-index:auto!important}"

PATCH = r'''body:has(.tq-out) .l-content{padding-top:0!important}
body:has(.tq-out) #content{z-index:auto!important}
/* TQ OUTING ONE COLUMN v1 */
body:has(.tq-out) #content.l-content.l-container{width:100%!important;max-width:none!important;padding-left:0!important;padding-right:0!important}
body:has(.tq-out) .l-mainContent{width:100%!important;max-width:none!important;flex:1 1 100%!important;margin:0!important}
body:has(.tq-out) .l-mainContent__inner,body:has(.tq-out) .post_content{width:100%!important;max-width:none!important;margin-left:0!important;margin-right:0!important}
body:has(.tq-out) .l-sidebar{display:none!important}
body:has(.tq-out) .tq-out h2,body:has(.tq-out) .tq-out-final h2,body:has(.tq-out) .tq-out-latest h2{background:transparent!important;color:inherit!important;padding:0!important;border:0!important;box-shadow:none!important}
body:has(.tq-out) .tq-out h2:before,body:has(.tq-out) .tq-out h2:after,body:has(.tq-out) .tq-out-final h2:before,body:has(.tq-out) .tq-out-final h2:after,body:has(.tq-out) .tq-out-latest h2:before,body:has(.tq-out) .tq-out-latest h2:after{content:none!important;display:none!important}'''

if '<!-- tsurikue-category-hub:v1:outing -->' not in s:
    raise SystemExit('OUTING_MARKER_MISSING')

if MARKER in s:
    print('OUTING_ONE_COLUMN_ALREADY_PRESENT')
else:
    if s.count(ANCHOR) != 1:
        raise SystemExit(f'ANCHOR_COUNT_INVALID={s.count(ANCHOR)}')
    s = s.replace(ANCHOR, PATCH, 1)
    p.write_text(s, encoding='utf-8')
    print('OUTING_ONE_COLUMN_SOURCE_PATCHED')

check = p.read_text(encoding='utf-8')
required = [
    MARKER,
    'body:has(.tq-out) .l-sidebar{display:none!important}',
    'body:has(.tq-out) .l-mainContent{width:100%!important',
    'body:has(.tq-out) .tq-out h2',
]
missing = [x for x in required if x not in check]
if missing:
    raise SystemExit('PATCH_VERIFY_MISSING=' + repr(missing))
print('OUTING_ONE_COLUMN_SOURCE_VERIFIED')
