#!/usr/bin/env python3
from __future__ import annotations
import hashlib, html, os, re, time
from pathlib import Path
import apply_ux_koukai_rewrite_once as wp

wp.SLUG='ux300h'
POST_ID=2329
REPORT=Path('reports/ux300h-affiliate-current')
G='[blog_parts id="2843"]'
CB='[blog_parts id="2846"]'
CT='[blog_parts id="2184"]'
GH='https://px.a8.net/svt/ejp?a8mat=4B65SD+8DUSHE+9QU+NVHCY'

def retry(fn):
    err=None
    for n in range(3):
        try:return fn()
        except Exception as e:
            err=e
            if n<2:time.sleep(3*(n+1))
    raise err

def imgs(s):
    xs=re.findall(r"<img[^>]+src=['\"]([^'\"]+)['\"]",s,re.I)
    return sorted(set(x for x in xs if 'a8.net/0.gif' not in x))

def main():
    REPORT.mkdir(parents=True,exist_ok=True)
    u=os.environ.get('TSURIKUE_WP_USER');p=os.environ.get('TSURIKUE_WP_APP_PASSWORD')
    if not u or not p: raise RuntimeError('missing WordPress secrets')
    auth=wp.auth_header(u,p)
    row=retry(lambda:wp.fetch_post_by_slug(auth)); raw=wp.raw_field(row,'content')
    title=html.unescape(wp.raw_field(row,'title'))
    pub=retry(lambda:wp.public_total(auth))
    lines=['# ux300h fresh affiliate audit','', '- result: **SUCCESS**',f'- post_id: **{row.get("id")}**',f'- status: **{row.get("status")}**',f'- title: {title}',f'- featured_media: **{row.get("featured_media",0)}**',f'- public_total: **{pub}**','- wordpress_write_count: **0**',f'- content_sha256: `{hashlib.sha256(raw.encode()).hexdigest()}`',f'- article_image_count: **{len(imgs(raw))}**',f'- gulliver_2843_count: **{raw.count(G)}**',f'- ctn_banner_2846_count: **{raw.count(CB)}**',f'- ctn_button_2184_count: **{raw.count(CT)}**',f'- custom_gulliver_href_count: **{raw.count(GH)}**',f"- marker_gulliver: **{'YES' if 'お宝UX、まだ表に出ていないかも。' in raw else 'NO'}**",f"- marker_ctn: **{'YES' if '高く売りたい。でも電話ラッシュはいらない。' in raw else 'NO'}**"]
    (REPORT/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return 0

if __name__=='__main__': raise SystemExit(main())
