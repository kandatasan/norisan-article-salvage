from __future__ import annotations

import html
import json
import re
from pathlib import Path

SOURCE = Path('category-hubs/outing/content.html')
OLD_MARKER = '<!-- tsurikue-category-hub:v1:outing -->'
BLOCK_MARKER = '<!-- tsurikue-category-hub:v2:outing-blocks -->'
PLACEHOLDER = '{{OUTING_CATEGORY_IDS}}'


def attrs_json(attrs: dict | None) -> str:
    if not attrs:
        return ''
    return ' ' + json.dumps(attrs, ensure_ascii=False, separators=(',', ':'))


def group(class_name: str, inner: str, *, align: str | None = None,
          anchor: str | None = None, layout: dict | None = None) -> str:
    attrs: dict = {'className': class_name, 'layout': layout or {'type': 'constrained'}}
    if align:
        attrs['align'] = align
    if anchor:
        attrs['anchor'] = anchor
    classes = ['wp-block-group']
    if align:
        classes.append(f'align{align}')
    if class_name:
        classes.extend(class_name.split())
    id_attr = f' id="{html.escape(anchor, quote=True)}"' if anchor else ''
    return (
        f'<!-- wp:group{attrs_json(attrs)} -->\n'
        f'<div{id_attr} class="{" ".join(classes)}">{inner}</div>\n'
        '<!-- /wp:group -->'
    )


def paragraph(text: str, class_name: str | None = None) -> str:
    attrs = {'className': class_name} if class_name else None
    cls = f' class="{class_name}"' if class_name else ''
    return (
        f'<!-- wp:paragraph{attrs_json(attrs)} -->\n'
        f'<p{cls}>{text}</p>\n'
        '<!-- /wp:paragraph -->'
    )


def heading(level: int, text: str, class_name: str | None = None) -> str:
    attrs: dict = {}
    if level != 2:
        attrs['level'] = level
    if class_name:
        attrs['className'] = class_name
    cls = 'wp-block-heading' + (f' {class_name}' if class_name else '')
    return (
        f'<!-- wp:heading{attrs_json(attrs or None)} -->\n'
        f'<h{level} class="{cls}">{text}</h{level}>\n'
        '<!-- /wp:heading -->'
    )


def cover(url: str, inner: str, class_name: str) -> str:
    attrs = {
        'url': url,
        'dimRatio': 80,
        'overlayColor': 'white',
        'isUserOverlayColor': True,
        'align': 'full',
        'className': class_name,
    }
    return (
        f'<!-- wp:cover{attrs_json(attrs)} -->\n'
        f'<div class="wp-block-cover alignfull {class_name}">'
        f'<img class="wp-block-cover__image-background" alt="" src="{html.escape(url, quote=True)}" data-object-fit="cover"/>'
        '<span aria-hidden="true" class="wp-block-cover__background has-white-background-color has-background-dim-80 has-background-dim"></span>'
        f'<div class="wp-block-cover__inner-container">{inner}</div></div>\n'
        '<!-- /wp:cover -->'
    )


def buttons(label: str, href: str) -> str:
    return (
        '<!-- wp:buttons {"className":"tq-out-final-actions"} -->\n'
        '<div class="wp-block-buttons tq-out-final-actions">'
        '<!-- wp:button {"className":"tq-out-final-button"} -->\n'
        f'<div class="wp-block-button tq-out-final-button"><a class="wp-block-button__link wp-element-button" href="{html.escape(href, quote=True)}">{label}</a></div>\n'
        '<!-- /wp:button --></div>\n'
        '<!-- /wp:buttons -->'
    )


def linked_title(level: int, title: str, href: str) -> str:
    return heading(level, f'<a href="{html.escape(href, quote=True)}">{title}</a>')


def cta(text: str, href: str, class_name: str) -> str:
    return paragraph(f'<a href="{html.escape(href, quote=True)}">{text}</a>', class_name)


def section_head(kicker: str, title: str, note: str) -> str:
    left = group(
        'tq-out-head-left',
        paragraph(kicker, 'tq-out-kicker') + '\n' + heading(2, title),
    )
    return group('tq-out-head', left + '\n' + paragraph(note, 'tq-out-head-note'))


def choice_card(label: str, title: str, text: str, href: str, arrow: str) -> str:
    inner = '\n'.join([
        paragraph(label, 'tq-out-choice-label'),
        linked_title(3, title, href),
        paragraph(text, 'tq-out-choice-text'),
        cta(arrow, href, 'tq-out-arrow'),
    ])
    return group('tq-out-choice', inner)


def local_card(css_class: str, label: str, title: str, text: str,
               href: str, more: str) -> str:
    inner = '\n'.join([
        paragraph(label, 'tq-out-card-label'),
        linked_title(3, title, href),
        paragraph(text, 'tq-out-card-text'),
        cta(more, href, 'tq-out-more'),
    ])
    return group(f'tq-out-card {css_class}'.strip(), inner)


def trip_card(badge: str, label: str, title: str, text: str, href: str) -> str:
    copy = group('tq-out-trip-copy', '\n'.join([
        paragraph(label, 'tq-out-trip-label'),
        linked_title(3, title, href),
        paragraph(text, 'tq-out-trip-text'),
    ]))
    return group('tq-out-trip-card', paragraph(badge, 'tq-out-trip-badge') + '\n' + copy)


def route_card(label: str, title: str, text: str, href: str) -> str:
    copy = group('tq-out-route-copy', linked_title(3, title, href) + '\n' + paragraph(text, 'tq-out-route-text'))
    return group('tq-out-route-card', '\n'.join([
        paragraph(label, 'tq-out-route-label'),
        copy,
        cta('→', href, 'tq-out-route-arrow'),
    ]))


def validate_block_stack(content: str) -> None:
    pattern = re.compile(r'<!--\s*(/?)wp:([a-z0-9-]+)(?:\s+\{.*?\})?\s*(/?)-->', re.S | re.I)
    stack: list[str] = []
    for m in pattern.finditer(content):
        closing, name, self_close = m.group(1), m.group(2), m.group(3)
        if self_close:
            continue
        if closing:
            if not stack or stack[-1] != name:
                raise SystemExit(f'BLOCK_STACK_MISMATCH closing={name} stack={stack[-5:]}')
            stack.pop()
        else:
            stack.append(name)
    if stack:
        raise SystemExit(f'UNCLOSED_BLOCKS={stack[-10:]}')


BLOCK_CSS = r'''
/* TQ OUTING BLOCKS v1 */
.tq-out.wp-block-group{width:100%!important;max-width:none!important;margin:0!important;padding:0!important}
.tq-out .wp-block-group__inner-container{width:100%!important;max-width:none!important}
.tq-out>.wp-block-cover,.tq-out>.wp-block-group{margin-block-start:0!important;margin-block-end:0!important}
.tq-out .tq-out-section,.tq-out .tq-out-latest,.tq-out .tq-out-final{width:100%!important;max-width:none!important;margin-left:0!important;margin-right:0!important}
.tq-out .tq-out-head>.wp-block-group__inner-container{display:flex!important;justify-content:space-between;align-items:flex-end;gap:28px}
.tq-out .tq-out-choose-grid>.wp-block-group__inner-container{display:grid!important;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}
.tq-out .tq-out-local-grid>.wp-block-group__inner-container{display:grid!important;grid-template-columns:1.2fr .8fr .8fr;gap:12px}
.tq-out .tq-out-trip-grid>.wp-block-group__inner-container{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.tq-out .tq-out-route-list>.wp-block-group__inner-container{display:grid!important;gap:10px}
.tq-out .tq-out-card>.wp-block-group__inner-container{display:flex!important;flex-direction:column;justify-content:flex-end;height:100%}
.tq-out .tq-out-trip-card>.wp-block-group__inner-container{display:grid!important;grid-template-columns:82px 1fr;gap:18px;align-items:center}
.tq-out .tq-out-route-card>.wp-block-group__inner-container{display:grid!important;grid-template-columns:145px 1fr auto;gap:24px;align-items:center}
.tq-out .tq-out-final-inner>.wp-block-group__inner-container{display:grid!important;grid-template-columns:1fr auto;gap:30px;align-items:center}
.tq-out .tq-out-kicker{margin:0 0 10px!important}
.tq-out .tq-out-head-note{margin:0!important;max-width:430px;color:var(--sub);font-size:13px;line-height:1.9}
.tq-out-choice .tq-out-choice-label{margin:0 0 18px!important;color:#73756f;font-size:9px;font-weight:900;letter-spacing:.15em}
.tq-out-choice h3{margin:0!important;font-size:20px!important;line-height:1.35!important}
.tq-out-choice .tq-out-choice-text{margin:8px 0 0!important;color:#5f615b;font-size:11px;line-height:1.65}
.tq-out-choice .tq-out-arrow{margin:14px 0 0!important;font-size:13px;font-weight:900}
.tq-out-card .tq-out-card-label{margin:0 0 9px!important;color:#74766f;font-size:9px;font-weight:900;letter-spacing:.14em}
.tq-out-card .tq-out-card-text{margin:11px 0 0!important;color:#5b5d57;font-size:12px;line-height:1.8}
.tq-out-card .tq-out-more{margin:18px 0 0!important;font-size:11px;font-weight:900}
.tq-out-trip-badge{margin:0!important}
.tq-out-trip-card .tq-out-trip-label{margin:0 0 6px!important;color:#7b7c76;font-size:9px;font-weight:850}
.tq-out-trip-card .tq-out-trip-text{margin:7px 0 0!important;color:#666861;font-size:11px;line-height:1.7}
.tq-out-route-card .tq-out-route-label{margin:0!important;font-size:9px;font-weight:900;letter-spacing:.12em;color:#73756f}
.tq-out-route-card .tq-out-route-text{margin:5px 0 0!important;color:#62645e;font-size:11px;line-height:1.65}
.tq-out-route-card .tq-out-route-arrow{margin:0!important;font-size:22px;font-weight:900}
.tq-out h3 a,.tq-out .tq-out-more a,.tq-out .tq-out-arrow a,.tq-out .tq-out-route-arrow a{color:inherit!important;text-decoration:none!important}
.tq-out .tq-out-latest{margin:0!important}
.tq-out .tq-out-latest>.wp-block-group__inner-container{width:100%!important;max-width:none!important}
.tq-out .tq-out-latest-head{margin-bottom:28px}
.tq-out .tq-out-final{margin:0!important}
.tq-out .tq-out-final-actions,.tq-out .tq-out-final-button{margin:0!important}
.tq-out .tq-out-final-button .wp-block-button__link{display:inline-flex;align-items:center;justify-content:center;min-height:48px;padding:0 20px;border:1px solid rgba(32,33,31,.5);border-radius:999px;color:#20211f!important;text-decoration:none!important;font-size:12px;font-weight:900;background:rgba(255,255,255,.25)}
@media(min-width:960px){
  .tq-out .tq-out-choose-grid>.wp-block-group__inner-container,.tq-out .tq-out-local-grid>.wp-block-group__inner-container,.tq-out .tq-out-trip-grid>.wp-block-group__inner-container{gap:14px}
  .tq-out .tq-out-route-list>.wp-block-group__inner-container{gap:12px}
}
@media(max-width:860px){
  .tq-out .tq-out-choose-grid>.wp-block-group__inner-container{grid-template-columns:repeat(2,minmax(0,1fr))}
  .tq-out .tq-out-local-grid>.wp-block-group__inner-container{grid-template-columns:1fr 1fr}
  .tq-out .tq-out-trip-grid>.wp-block-group__inner-container{grid-template-columns:1fr}
  .tq-out .tq-out-route-card>.wp-block-group__inner-container{grid-template-columns:110px 1fr}
  .tq-out .tq-out-route-arrow{display:none}
  .tq-out .tq-out-final-inner>.wp-block-group__inner-container{grid-template-columns:1fr}
}
@media(max-width:560px){
  .tq-out .tq-out-head>.wp-block-group__inner-container{display:block!important}
  .tq-out .tq-out-head-note{margin-top:10px!important;max-width:none}
  .tq-out .tq-out-local-grid>.wp-block-group__inner-container{grid-template-columns:1fr}
  .tq-out .tq-out-trip-card>.wp-block-group__inner-container{grid-template-columns:62px 1fr;gap:14px}
  .tq-out .tq-out-route-card>.wp-block-group__inner-container{grid-template-columns:1fr;gap:8px}
  .tq-out .tq-out-final-actions,.tq-out .tq-out-final-button,.tq-out .tq-out-final-button .wp-block-button__link{width:100%}
}
@media(max-width:359px){.tq-out .tq-out-choose-grid>.wp-block-group__inner-container{grid-template-columns:1fr}}
'''.strip()


def build_blocks() -> str:
    hero_inner = group('tq-out-hero-inner', '\n'.join([
        paragraph('GO OUT / TSURIKUE!', 'tq-out-brand'),
        heading(1, '次の休日、<br>どこ行く？'),
        paragraph('広島からふらっと日帰り。たまには1泊2日で遠くまで。実際に走ったコースと、寄ってみて面白かった場所を集めました。', 'tq-out-hero-lead'),
        paragraph('観光地を並べるだけではなく、「この順番で回った」「ここで予定が狂った」まで含めた、つりくえ！のおでかけ記録です。', 'tq-out-hero-note'),
    ]))
    hero = cover('https://tsurikue.com/wp-content/uploads/2026/05/img_4588.jpg', hero_inner, 'tq-out-hero')

    choices = [
        ('NEARBY', '広島で遊ぶ', '江田島・世羅・湯来など、日帰りで遊びやすい場所。', '#hiroshima', '↓'),
        ('ROAD TRIP', '旅に出る', '山口・鳥取・大分・淡路島。実際に出かけた旅をまとめました。', '#trip', '↓'),
        ('MODEL COURSE', 'ルートを真似する', '実際に走った順番で、1泊2日や日帰りコースを紹介。', '#route', '↓'),
        ('ALL ARTICLES', '全部のおでかけ', 'スポット記事も旅行記も、新着順でまとめて見る。', '/category/sightseeing-leisure/', '→'),
    ]
    choose_grid = group('tq-out-choose-grid', '\n'.join(choice_card(*c) for c in choices), layout={'type': 'grid', 'columnCount': 4})
    choose = group(
        'tq-out-section tq-out-choose',
        group('tq-out-wrap', section_head('CHOOSE YOUR QUEST', '今日は、どう遊ぶ？', '近場でゆるく遊ぶ日も、朝から車を走らせる日も。気分に近い入口からどうぞ。') + '\n' + choose_grid),
        align='full',
    )

    locals_data = [
        ('tq-out-card--main', 'START HERE', '広島観光・レジャーまとめ', '今日どこ行く？を決めたい日に。実際に遊びに行った場所をまとめて探せます。', '/hiroshima-sightseeing/', '広島のおでかけを探す →'),
        ('tq-out-card--etajima', 'ISLAND', '江田島', '海沿いを走って、気になる場所へ寄り道。島ドライブの日。', '/etajima-sightseeing/', '江田島へ →'),
        ('tq-out-card--sera', 'FLOWERS & FARM', '世羅', '花畑、牧場、ジェラート、夢吊橋。のんびり走る日帰り旅。', '/sera-sightseeing/', '世羅へ →'),
        ('tq-out-card--yuki', 'RIVER & NATURE', '湯来町', '牧場、川遊び、釣り堀。自然の中で遊びたい休日に。', '/yuki-town-drive/', '湯来へ →'),
        ('', 'WALK', '西条酒蔵通り', '白壁と赤レンガ煙突の町を歩いて、酒蔵めぐり。', '/saijo-sakagura-dori/', '西条を歩く →'),
    ]
    local_grid = group('tq-out-local-grid', '\n'.join(local_card(*c) for c in locals_data), layout={'type': 'grid', 'columnCount': 3})
    local = group(
        'tq-out-section tq-out-local',
        group('tq-out-wrap', section_head('HIROSHIMA', 'まずは広島で遊ぶ', '海も山も街もあるので、「何しよう？」からでも決めやすい。つりくえ！で一番記事が育っているエリアです。') + '\n' + local_grid),
        align='full', anchor='hiroshima',
    )

    trips_data = [
        ('YAMAGUCHI', '1 NIGHT / 2 DAYS', '山口｜ムーバレー・萩・元乃隅・角島へ', '山口西部をぐるっと走った、欲張りな1泊2日。', '/yamaguchi-drive/'),
        ('TOTTORI', 'DRIVE', '鳥取｜境港・大山・コナン・砂の美術館', '最後は雨。予定通りにいかないところまで旅行です。', '/tottori-drive/'),
        ('OITA', '1 NIGHT / 2 DAYS', '大分｜別府・湯布院・日田へ', '下関に寄って別府泊。翌日は湯布院と日田まで。', '/hiroshima-oita-1night-2days-drive/'),
        ('AWAJI', 'QUEST', '淡路島｜ドラゴンクエスト アイランド', '大人4人で本気の冒険。つりくえ！の名前と相性が良すぎる場所。', '/dqisland/'),
    ]
    trip_grid = group('tq-out-trip-grid', '\n'.join(trip_card(*c) for c in trips_data), layout={'type': 'grid', 'columnCount': 2})
    trip = group(
        'tq-out-section tq-out-trip',
        group('tq-out-wrap', section_head('ROAD TRIP', '旅に出る', 'せっかくの休みなら、いつもより少し遠くへ。山口・鳥取・大分・淡路島など、実際に出かけた旅を集めました。') + '\n' + trip_grid),
        align='full', anchor='trip',
    )

    routes_data = [
        ('YAMAGUCHI / 1泊2日', 'ムーバレー → 萩 → 元乃隅 → 角島', '広島発。山口の西側を1泊2日で走る。', '/yamaguchi-drive/'),
        ('OITA / 1泊2日', '下関に寄り道 → 別府泊 → 湯布院 → 日田', '九州まで行くなら、別府だけでは帰らない。', '/hiroshima-oita-1night-2days-drive/'),
        ('SANIN / 1泊2日', '広島から山陰へ。海と温泉をつなぐ旅', '長距離ドライブも、寄り道を入れるとクエストになる。', '/hiroshima-sanin-1night-2days/'),
    ]
    route_list = group('tq-out-route-list', '\n'.join(route_card(*c) for c in routes_data))
    route = group(
        'tq-out-section tq-out-route',
        group('tq-out-wrap', section_head('REAL ROUTES', '実際に走った順番で', 'モデルコースは机の上で組まず、実際に動いたルートを優先。丸ごと真似しても、気になる場所だけ拾ってもOKです。') + '\n' + route_list),
        align='full', anchor='route',
    )

    latest_head = group('tq-out-latest-head', '\n'.join([
        paragraph('LATEST QUESTS', 'tq-out-kicker'),
        heading(2, '新着のおでかけ'),
        paragraph('ここは自動更新。新しく遊びに行った記事が増えると、順番に入れ替わります。', 'tq-out-latest-note'),
    ]))
    latest_posts = (
        f'<!-- wp:latest-posts {{"categories":[{PLACEHOLDER}],"postsToShow":6,"displayPostDate":true,'
        '"displayFeaturedImage":true,"featuredImageSizeSlug":"medium","addLinkToFeaturedImage":true,'
        '"className":"tq-out-latest-list"} /-->'
    )
    latest = group('tq-out-latest', group('tq-out-wrap', latest_head + '\n' + latest_posts), align='full')

    final_copy = group('tq-out-final-copy', heading(2, 'まだ決められない？') + '\n' + paragraph('それなら、とりあえず全部眺めてみるのもアリです。'))
    final = group('tq-out-final', group('tq-out-final-inner', final_copy + '\n' + buttons('おでかけ記事を全部見る →', '/category/sightseeing-leisure/')), align='full')

    return group('tq-out', '\n\n'.join([hero, choose, local, trip, route, latest, final]), align='full')


def main() -> None:
    source = SOURCE.read_text(encoding='utf-8')
    if OLD_MARKER not in source:
        raise SystemExit('OLD_MARKER_MISSING')
    if BLOCK_MARKER in source:
        validate_block_stack(source)
        print('OUTING_ALREADY_BLOCKIZED')
        return
    if source.count('<!-- wp:html -->') < 2:
        raise SystemExit('EXPECTED_LEGACY_HTML_BLOCKS_MISSING')
    if '<main class="tq-out">' not in source:
        raise SystemExit('LEGACY_MAIN_MISSING')
    if '旅に出る' not in source or 'ちょっと遠くへ' in source:
        raise SystemExit('TRAVEL_WORDING_NOT_CURRENT')
    style_match = re.search(r'<style>.*?</style>', source, re.S)
    if not style_match:
        raise SystemExit('STYLE_BLOCK_MISSING')
    style = style_match.group(0)
    if '/* TQ OUTING BLOCKS v1 */' not in style:
        style = style.replace('</style>', '\n' + BLOCK_CSS + '\n</style>')

    blocks = build_blocks()
    output = '\n'.join([
        OLD_MARKER,
        BLOCK_MARKER,
        '<!-- wp:html -->',
        style,
        '<!-- /wp:html -->',
        '',
        blocks,
        '',
    ])

    validate_block_stack(output)
    checks = {
        'single_custom_html': output.count('<!-- wp:html -->') == 1,
        'groups': output.count('<!-- wp:group ') >= 35,
        'headings': output.count('<!-- wp:heading') >= 18,
        'paragraphs': output.count('<!-- wp:paragraph') >= 35,
        'cover': '<!-- wp:cover ' in output,
        'latest': '<!-- wp:latest-posts ' in output,
        'placeholder': PLACEHOLDER in output,
        'legacy_main_absent': '<main class="tq-out">' not in output,
        'legacy_card_links_absent': '<a class="tq-out-card' not in output and '<a class="tq-out-trip-card' not in output,
        'travel_wording': output.count('旅に出る') >= 2 and 'ちょっと遠くへ' not in output,
    }
    if not all(checks.values()):
        raise SystemExit('BLOCK_SOURCE_CHECK_FAILED=' + json.dumps(checks, ensure_ascii=False))

    SOURCE.write_text(output, encoding='utf-8')
    print('OUTING_GUTENBERG_BLOCKS_CREATED=' + json.dumps(checks, ensure_ascii=False))
    print('BYTES=', len(output.encode('utf-8')))


if __name__ == '__main__':
    main()
