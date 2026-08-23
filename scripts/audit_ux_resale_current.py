#!/usr/bin/env python3
from __future__ import annotations
import hashlib, html, os, re
from pathlib import Path
import apply_ux_koukai_rewrite_once as wp

wp.SLUG = 'ux-resale'
REPORT = Path('reports/ux-resale-current-audit')

def main():
    REPORT.mkdir(parents=True, exist_ok=True)
    u = os.environ.get('TSURIKUE_WP_USER'); p = os.environ.get('TSURIKUE_WP_APP_PASSWORD')
    if not u or not p: raise RuntimeError('missing WordPress secrets')
    auth = wp.auth_header(u,p)
    row = wp.fetch_post_by_slug(auth)
    content = wp.raw_field(row,'content')
    title = html.unescape(wp.raw_field(row,'title'))
    imgs = sorted(set(re.findall(r"<img[^>]+src=['\"]([^'\"]+)['\"]", content, re.I)))
    markers = [
        'レクサスUXの実際の売却価格は427万円だった','最初はUXを売る予定などなかった',
        '納車5か月のディーラー査定は350万円だった','別の実車査定では500万円前後が提示された',
        '納車から約1年後の実車査定は435万円だった','生活に余裕がなくなり、UXの売却を決めた',
        'CTNでカーセブンとネクステージの一騎打ちになった','カーセブンへ427万円で実際に売却した',
        'レクサスUXのリセールが悪いとは思わなかった','まとめ｜427万円で買い取ってもらえたことには助けられた'
    ]
    lines = ['# ux-resale current audit','', '- result: **SUCCESS**', f"- post_id: **{row.get('id')}**", f"- status: **{row.get('status')}**", f'- title: {title}', f"- featured_media: **{row.get('featured_media',0)}**", f"- public_total: **{wp.public_total(auth)}**", '- wordpress_write_count: **0**', f"- content_sha256: `{hashlib.sha256(content.encode()).hexdigest()}`", f"- image_count: **{len(imgs)}**", f"- ctn_banner_2846_count: **{content.count('[blog_parts id=\"2846\"]')}**", f"- ctn_button_2184_count: **{content.count('[blog_parts id=\"2184\"]')}**", f"- px_a8_ctn_links: **{content.count('px.a8.net')}**", '', '## Markers']
    for m in markers: lines.append(f"- {'OK' if m in content else 'MISSING'}: {m}")
    (REPORT/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (REPORT/'source.sha256').write_text(hashlib.sha256(content.encode()).hexdigest()+'\n',encoding='utf-8')
    return 0

if __name__ == '__main__': raise SystemExit(main())
