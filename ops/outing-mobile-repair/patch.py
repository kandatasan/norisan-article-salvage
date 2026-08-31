from pathlib import Path

p = Path('category-hubs/outing/content.html')
s = p.read_text(encoding='utf-8')
marker = '/* TQ OUTING MOBILE REPAIR v1 */'
if marker in s:
    raise SystemExit('MOBILE_REPAIR_ALREADY_PRESENT')

css = r'''
/* TQ OUTING MOBILE REPAIR v1 */
/* Gutenberg Cover defaults to white text; this hero uses a pale overlay, so keep copy dark. */
.tq-out .tq-out-hero{color:#20211f!important}
.tq-out .tq-out-hero .tq-out-brand,
.tq-out .tq-out-hero h1,
.tq-out .tq-out-hero .tq-out-hero-lead{color:#20211f!important}
.tq-out .tq-out-hero .tq-out-hero-note{color:#5f615b!important}

/* Gutenberg grid blocks render the grid on the block itself (not an inner-container). */
.tq-out .tq-out-choose-grid{display:grid!important;grid-template-columns:repeat(4,minmax(0,1fr))!important}
.tq-out .tq-out-local-grid{display:grid!important;grid-template-columns:1.2fr .8fr .8fr!important}
.tq-out .tq-out-trip-grid{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important}
.tq-out .tq-out-trip-card,.tq-out .tq-out-trip-copy{min-width:0!important}
.tq-out .tq-out-trip-copy{width:100%!important;max-width:none!important}
.tq-out .tq-out-trip-copy>h3,
.tq-out .tq-out-trip-copy>.tq-out-trip-label,
.tq-out .tq-out-trip-copy>.tq-out-trip-text{width:100%!important;max-width:none!important}

@media(max-width:860px){
  .tq-out .tq-out-choose-grid{grid-template-columns:repeat(2,minmax(0,1fr))!important}
  .tq-out .tq-out-local-grid{grid-template-columns:repeat(2,minmax(0,1fr))!important}
  .tq-out .tq-out-trip-grid{grid-template-columns:1fr!important}
}
@media(max-width:560px){
  .tq-out .tq-out-local-grid{grid-template-columns:1fr!important}
  .tq-out .tq-out-trip-card{grid-template-columns:62px minmax(0,1fr)!important;gap:14px!important}
  .tq-out .tq-out-trip-badge{white-space:nowrap!important;word-break:keep-all!important}
  .tq-out .tq-out-trip-copy h3{font-size:16px!important;line-height:1.5!important;word-break:normal!important;overflow-wrap:anywhere}
}
'''.strip()

if s.count('</style>') != 1:
    raise SystemExit(f'EXPECTED_ONE_STYLE_CLOSE found={s.count("</style>")}')
s = s.replace('</style>', css + '\n</style>', 1)

required = [
    marker,
    '.tq-out .tq-out-hero{color:#20211f!important}',
    '.tq-out .tq-out-trip-grid{grid-template-columns:1fr!important}',
    '.tq-out .tq-out-local-grid{grid-template-columns:1fr!important}',
    '<!-- tsurikue-category-hub:v2:outing-blocks -->',
    '旅に出る',
]
missing = [x for x in required if x not in s]
if missing:
    raise SystemExit('MOBILE_REPAIR_MISSING=' + repr(missing))

p.write_text(s, encoding='utf-8')
print('OUTING_MOBILE_REPAIR_PATCHED')
