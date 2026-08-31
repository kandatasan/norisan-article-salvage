from pathlib import Path

p = Path('category-hubs/outing/content.html')
s = p.read_text(encoding='utf-8')
marker = '/* TQ OUTING DARK HERO v1 */'
if marker in s:
    raise SystemExit('DARK_HERO_ALREADY_PRESENT')

required_before = [
    '<!-- tsurikue-category-hub:v2:outing-blocks -->',
    '/* TQ OUTING MOBILE REPAIR v2 */',
    'class="wp-block-cover alignfull tq-out-hero"',
]
missing = [x for x in required_before if x not in s]
if missing:
    raise SystemExit('DARK_HERO_PREREQ_MISSING=' + repr(missing))

css = r'''
/* TQ OUTING DARK HERO v1 */
/* Darken the photo while keeping the image visible; make all hero copy crisp white. */
.tq-out .tq-out-hero .wp-block-cover__background{
  background:linear-gradient(90deg,rgba(8,22,28,.74) 0%,rgba(11,28,31,.60) 58%,rgba(14,29,31,.50) 100%)!important;
  opacity:1!important;
}
.tq-out .tq-out-hero,
.tq-out .tq-out-hero .tq-out-brand,
.tq-out .tq-out-hero h1,
.tq-out .tq-out-hero .tq-out-hero-lead{
  color:#fff!important;
}
.tq-out .tq-out-hero .tq-out-hero-note{
  color:rgba(255,255,255,.88)!important;
}
.tq-out .tq-out-hero h1{
  text-shadow:0 3px 18px rgba(0,0,0,.48),0 1px 2px rgba(0,0,0,.72)!important;
}
.tq-out .tq-out-hero .tq-out-brand,
.tq-out .tq-out-hero .tq-out-hero-lead,
.tq-out .tq-out-hero .tq-out-hero-note{
  text-shadow:0 2px 10px rgba(0,0,0,.48),0 1px 1px rgba(0,0,0,.58)!important;
}
'''.strip()

if s.count('</style>') != 1:
    raise SystemExit(f'EXPECTED_ONE_STYLE_CLOSE found={s.count("</style>")}')
s = s.replace('</style>', css + '\n</style>', 1)

required_after = [
    marker,
    'rgba(8,22,28,.74)',
    'color:#fff!important;',
    'text-shadow:0 3px 18px',
    '/* TQ OUTING MOBILE REPAIR v2 */',
]
missing = [x for x in required_after if x not in s]
if missing:
    raise SystemExit('DARK_HERO_PATCH_MISSING=' + repr(missing))

p.write_text(s, encoding='utf-8')
print('OUTING_DARK_HERO_PATCHED')
