#!/usr/bin/env python3
from __future__ import annotations
import hashlib, html, os, re, time
from pathlib import Path
import apply_ux_koukai_rewrite_once as wp

wp.SLUG = 'ux300h'
POST_ID = 2329
REPORT = Path('reports/ux300h-current-audit')
GULLIVER_HREF = 'https://px.a8.net/svt/ejp?a8mat=4B65SD+8DUSHE+9QU+NVHCY'

def retry(fn):
    err=None
    for n in range(3):
        try: return fn()
        except Exception as e:
            err=e
            if n<2: time.sleep(3*(n+1))
    raise err

def article_imgs(content):
    srcs=re.findall(r"<img[^>]+src=['\"]([^'\"]+)['\"]", content, re.I)
    return sorted(set(x for x in srcs if 'a8.net/0.gif' not in x))

def main():
    REPORT.mkdir(parents=True, exist_ok=True)
    u=os.environ.get('TSURIKUE_WP_USER'); p=os.environ.get('TSURIKUE_WP_APP_PASSWORD')
    if not u or not p: raise RuntimeError('missing WordPress secrets')
    auth=wp.auth_header(u,p)
    row=retry(lambda: wp.fetch_post_by_slug(auth))
    raw=wp.raw_field(row,'content')
    title=html.unescape(wp.raw_field(row,'title'))
    public_total=retry(lambda: wp.public_total(auth))
    view_url=f'{wp.SITE_URL}/wp-json/wp/v2/posts/{POST_ID}?context=view&_fields=id,status,title,content,featured_media'
    view_row,_=retry(lambda: wp.get_json(view_url,auth))
    rendered=(view_row.get('content') or {}).get('rendered','')
    lines=[
        '# ux300h rendered affiliate audit','', '- result: **SUCCESS**',
        f"- post_id: **{row.get('id')}**", f"- status: **{row.get('status')}**", f'- title: {title}',
        f"- featured_media: **{row.get('featured_media',0)}**", f"- public_total: **{public_total}**",
        '- wordpress_write_count: **0**', f"- raw_sha256: `{hashlib.sha256(raw.encode()).hexdigest()}`",
        f"- raw_article_image_count: **{len(article_imgs(raw))}**",
        f"- raw_gulliver_shortcode_count: **{raw.count('[blog_parts id=\"2843\"]')}**",
        f"- raw_gulliver_custom_link_count: **{raw.count(GULLIVER_HREF)}**",
        f"- raw_ctn_button_count: **{raw.count('[blog_parts id=\"2184\"]')}**",
        f"- rendered_length: **{len(rendered)}**",
        f"- rendered_gulliver_href_count: **{rendered.count(GULLIVER_HREF)}**",
        f"- rendered_px_a8_count: **{rendered.count('px.a8.net')}**",
        f"- rendered_literal_gulliver_shortcode_count: **{rendered.count('[blog_parts id=\"2843\"]')}**",
        f"- rendered_literal_ctn_shortcode_count: **{rendered.count('[blog_parts id=\"2184\"]')}**",
        f"- rendered_gulliver_text_count: **{rendered.count('非公開在庫も含めて中古UXを探してみる')}**",
        f"- rendered_ctn_text_count: **{rendered.count('高く売りたい。でも電話ラッシュはいらない。')}**",
        f"- rendered_ctn_brand_count: **{rendered.count('CTN')}**",
        '', '## Rendered markers'
    ]
    for m in ['迷ったら、実際の中古UXを見比べるのが早い','Web掲載前の非公開在庫','お宝UX、まだ表に出ていないかも。','高額査定の上位3社だけ','高く売りたい。でも電話ラッシュはいらない。']:
        lines.append(f"- {'OK' if m in rendered else 'MISSING'}: {m}")
    (REPORT/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return 0

if __name__=='__main__': raise SystemExit(main())
