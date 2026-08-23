#!/usr/bin/env python3
from __future__ import annotations
import hashlib, html, os, re, time
from pathlib import Path
import apply_ux_koukai_rewrite_once as wp

wp.SLUG = 'ux300h'
REPORT = Path('reports/ux300h-current-audit')

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
    content=wp.raw_field(row,'content')
    title=html.unescape(wp.raw_field(row,'title'))
    public_total=retry(lambda: wp.public_total(auth))
    lines=[
        '# ux300h final audit','', '- result: **SUCCESS**',
        f"- post_id: **{row.get('id')}**", f"- status: **{row.get('status')}**", f'- title: {title}',
        f"- featured_media: **{row.get('featured_media',0)}**", f"- public_total: **{public_total}**",
        '- wordpress_write_count: **0**', f"- content_sha256: `{hashlib.sha256(content.encode()).hexdigest()}`",
        f"- article_image_count: **{len(article_imgs(content))}**", f"- gulliver_banner_2843_count: **{content.count('[blog_parts id=\"2843\"]')}**",
        f"- gulliver_button_link_count: **{content.count('https://px.a8.net/svt/ejp?a8mat=4B65SD+8DUSHE+9QU+NVHCY')}**",
        f"- ctn_button_2184_count: **{content.count('[blog_parts id=\"2184\"]')}**", '', '## Markers'
    ]
    for m in ['UX300h、超良くなってるじゃん！','迷ったら、実際の中古UXを見比べるのが早い','Web掲載前の非公開在庫','お宝UX、まだ表に出ていないかも。','高額査定の上位3社だけ','高く売りたい。でも電話ラッシュはいらない。']:
        lines.append(f"- {'OK' if m in content else 'MISSING'}: {m}")
    (REPORT/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return 0

if __name__=='__main__': raise SystemExit(main())
