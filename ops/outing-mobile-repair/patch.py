from pathlib import Path

p = Path('category-hubs/outing/content.html')
s = p.read_text(encoding='utf-8')
marker_v1 = '/* TQ OUTING MOBILE REPAIR v1 */'
marker_v2 = '/* TQ OUTING MOBILE REPAIR v2 */'

if marker_v1 not in s:
    raise SystemExit('MOBILE_REPAIR_V1_MISSING')
if marker_v2 in s:
    raise SystemExit('MOBILE_REPAIR_V2_ALREADY_PRESENT')

css = r'''
/* TQ OUTING MOBILE REPAIR v2 */
/* Phones: abandon the old 62px + copy two-column card layout entirely. */
@media(max-width:600px){
  .tq-out .tq-out-trip-grid{
    display:grid!important;
    grid-template-columns:1fr!important;
    width:100%!important;
  }
  .tq-out .tq-out-trip-card{
    display:block!important;
    grid-template-columns:none!important;
    width:100%!important;
    min-width:0!important;
    max-width:none!important;
    min-height:0!important;
    padding:20px!important;
  }
  .tq-out .tq-out-trip-card>.wp-block-group__inner-container{
    display:block!important;
    grid-template-columns:none!important;
    width:100%!important;
    max-width:none!important;
  }
  .tq-out .tq-out-trip-badge{
    display:inline-flex!important;
    align-items:center!important;
    justify-content:center!important;
    width:auto!important;
    height:auto!important;
    min-width:0!important;
    margin:0 0 14px!important;
    padding:8px 12px!important;
    border-radius:999px!important;
    white-space:nowrap!important;
    word-break:keep-all!important;
    writing-mode:horizontal-tb!important;
  }
  .tq-out .tq-out-trip-copy{
    display:block!important;
    width:100%!important;
    min-width:0!important;
    max-width:none!important;
    margin:0!important;
    padding:0!important;
  }
  .tq-out .tq-out-trip-copy>.wp-block-group__inner-container{
    display:block!important;
    width:100%!important;
    max-width:none!important;
  }
  .tq-out .tq-out-trip-copy>*,
  .tq-out .tq-out-trip-copy>.wp-block-group__inner-container>*{
    width:100%!important;
    max-width:none!important;
    min-width:0!important;
    margin-left:0!important;
    margin-right:0!important;
    writing-mode:horizontal-tb!important;
    text-orientation:mixed!important;
  }
  .tq-out .tq-out-trip-copy h3,
  .tq-out .tq-out-trip-copy h3 a,
  .tq-out .tq-out-trip-copy p{
    writing-mode:horizontal-tb!important;
    text-orientation:mixed!important;
    white-space:normal!important;
    word-break:normal!important;
    overflow-wrap:anywhere!important;
  }
  .tq-out .tq-out-trip-copy h3{
    font-size:19px!important;
    line-height:1.55!important;
  }
  .tq-out .tq-out-trip-label{
    margin:0 0 7px!important;
  }
  .tq-out .tq-out-trip-text{
    margin:8px 0 0!important;
  }
}
'''.strip()

if s.count('</style>') != 1:
    raise SystemExit(f'EXPECTED_ONE_STYLE_CLOSE found={s.count("</style>")}')
s = s.replace('</style>', css + '\n</style>', 1)

required = [
    marker_v1,
    marker_v2,
    '.tq-out .tq-out-trip-card{',
    'display:block!important;',
    'grid-template-columns:none!important;',
    'writing-mode:horizontal-tb!important;',
    '<!-- tsurikue-category-hub:v2:outing-blocks -->',
    '旅に出る',
]
missing = [x for x in required if x not in s]
if missing:
    raise SystemExit('MOBILE_REPAIR_V2_MISSING=' + repr(missing))

p.write_text(s, encoding='utf-8')
print('OUTING_MOBILE_REPAIR_V2_PATCHED')
