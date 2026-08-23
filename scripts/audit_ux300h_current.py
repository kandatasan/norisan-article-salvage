#!/usr/bin/env python3
from __future__ import annotations
import hashlib, html, os, re
from pathlib import Path
import apply_ux_koukai_rewrite_once as wp

wp.SLUG = 'ux300h'
REPORT = Path('reports/ux300h-current-audit')

def main():
    REPORT.mkdir(parents=True, exist_ok=True)
    u=os.environ.get('TSURIKUE_WP_USER'); p=os.environ.get('TSURIKUE_WP_APP_PASSWORD')
    if not u or not p: raise RuntimeError('missing WordPress secrets')
    auth=wp.auth_header(u,p)
    row=wp.fetch_post_by_slug(auth)
    content=wp.raw_field(row,'content')
    title=html.unescape(wp.raw_field(row,'title'))
    imgs=sorted(set(re.findall(r"<img[^>]+src=['\"]([^'\"]+)['\"]", content, re.I)))
    lines=[
        '# ux300h current audit','', '- result: **SUCCESS**',
        f"- post_id: **{row.get('id')}**", f"- status: **{row.get('status')}**", f'- title: {title}',
        f"- featured_media: **{row.get('featured_media',0)}**", f"- public_total: **{wp.public_total(auth)}**",
        '- wordpress_write_count: **0**', f"- content_sha256: `{hashlib.sha256(content.encode()).hexdigest()}`",
        f"- image_count: **{len(imgs)}**", f"- gulliver_banner_2843_count: **{content.count('[blog_parts id=\"2843\"]')}**",
        f"- ctn_banner_2846_count: **{content.count('[blog_parts id=\"2846\"]')}**", f"- ctn_button_2184_count: **{content.count('[blog_parts id=\"2184\"]')}**",
        f"- a8_link_count: **{content.count('px.a8.net')}**", '', '## Markers'
    ]
    for m in ['UX300h、超良くなってるじゃん！','中古車でUX250hとUX300hのどちらを選ぶ？','価格差で迷うなら、今乗っている車の売却額も確認する','シエンタ','427万円']:
        lines.append(f"- {'OK' if m in content else 'MISSING'}: {m}")
    (REPORT/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return 0

if __name__=='__main__': raise SystemExit(main())
