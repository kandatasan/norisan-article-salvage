from pathlib import Path

SOURCE = Path('category-hubs/outing/content.html')
PAGE_MARKER = '<!-- tsurikue-category-hub:v1:outing -->'
ONE_COLUMN = '/* TQ OUTING ONE COLUMN v1 */'
MARKER = '/* TQ OUTING FINAL POLISH v1 */'

CSS = r'''
/* TQ OUTING FINAL POLISH v1 */
body:has(.tq-out){overflow-x:clip}
body:has(.tq-out) .l-content,
body:has(.tq-out) .l-mainContent,
body:has(.tq-out) .l-mainContent__inner,
body:has(.tq-out) .post_content{padding-top:0!important;padding-bottom:0!important}
body:has(.tq-out) .post_content> :first-child{margin-top:0!important}
body:has(.tq-out) .post_content> :last-child{margin-bottom:0!important}
body:has(.tq-out) .tq-out h3{background:transparent!important;color:inherit!important;padding:0!important;border:0!important;box-shadow:none!important}
body:has(.tq-out) .tq-out h3:before,body:has(.tq-out) .tq-out h3:after{content:none!important;display:none!important}
.tq-out #hiroshima,.tq-out #trip,.tq-out #route{scroll-margin-top:120px}
.tq-out-choice,.tq-out-card,.tq-out-trip-card,.tq-out-route-card{-webkit-tap-highlight-color:transparent}
.tq-out-final a{transition:transform .2s ease,background .2s ease}
.tq-out-final a:hover{transform:translateY(-2px);background:rgba(255,255,255,.45)}
@media(min-width:960px){
  .tq-out-wrap,.tq-out-hero-inner,.tq-out-final-inner,.tq-out-latest>.wp-block-group__inner-container{width:min(1160px,90vw)!important;max-width:none!important}
  .tq-out-hero{min-height:550px}
  .tq-out-section{padding:88px 0}
  .tq-out-choose-grid,.tq-out-local-grid,.tq-out-trip-grid{gap:14px}
  .tq-out-route-list{gap:12px}
  .tq-out-choice{min-height:158px;padding:24px}
  .tq-out-trip-card{min-height:176px;padding:25px}
}
@media(max-width:959px){
  .tq-out,.tq-out-latest,.tq-out-final{max-width:100vw!important}
}
@media(max-width:560px){
  .tq-out-wrap,.tq-out-hero-inner,.tq-out-final-inner,.tq-out-latest>.wp-block-group__inner-container{width:calc(100% - 32px)!important;max-width:none!important}
  .tq-out-head p{max-width:none}
  .tq-out-choice span{font-size:11px;line-height:1.6}
  .tq-out-final a{width:100%;justify-self:stretch!important}
}
@media(max-width:359px){.tq-out-choose-grid{grid-template-columns:1fr}}
'''.strip()

s = SOURCE.read_text(encoding='utf-8')
if PAGE_MARKER not in s:
    raise SystemExit('OUTING_PAGE_MARKER_MISSING')
if ONE_COLUMN not in s:
    raise SystemExit('OUTING_ONE_COLUMN_MARKER_MISSING')

if MARKER in s:
    print('OUTING_FINAL_POLISH_ALREADY_PRESENT')
else:
    if s.count('</style>') != 1:
        raise SystemExit(f'STYLE_END_COUNT_INVALID={s.count("</style>")}')
    s = s.replace('</style>', CSS + '\n</style>', 1)
    SOURCE.write_text(s, encoding='utf-8')
    print('OUTING_FINAL_POLISH_INSERTED')

check = SOURCE.read_text(encoding='utf-8')
required = [
    MARKER,
    'width:min(1160px,90vw)!important',
    'body:has(.tq-out) .tq-out h3',
    'scroll-margin-top:120px',
    '@media(max-width:359px){.tq-out-choose-grid{grid-template-columns:1fr}}',
]
missing = [x for x in required if x not in check]
if missing:
    raise SystemExit('OUTING_FINAL_VERIFY_MISSING=' + repr(missing))
if check.count(MARKER) != 1:
    raise SystemExit(f'OUTING_FINAL_MARKER_COUNT={check.count(MARKER)}')
print('OUTING_FINAL_POLISH_SOURCE_VERIFIED')
