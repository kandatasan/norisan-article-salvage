#!/usr/bin/env python3
from __future__ import annotations
import hashlib, html, os, re, time
from pathlib import Path
import apply_ux_koukai_rewrite_once as wp

wp.SLUG='ux300h'
REPORT=Path('reports/ux300h-affiliate-current')
G='[blog_parts id="2843"]'; CB='[blog_parts id="2846"]'; CT='[blog_parts id="2184"]'

def retry(fn):
    err=None
    for n in range(3):
        try:return fn()
        except Exception as e:
            err=e
            if n<2:time.sleep(3*(n+1))
    raise err

def snippet(raw, marker, before=500, after=1000):
    i=raw.find(marker)
    if i<0:return ''
    return raw[max(0,i-before):min(len(raw),i+len(marker)+after)]

def main():
    REPORT.mkdir(parents=True,exist_ok=True)
    u=os.environ.get('TSURIKUE_WP_USER');p=os.environ.get('TSURIKUE_WP_APP_PASSWORD')
    if not u or not p:raise RuntimeError('missing WordPress secrets')
    auth=wp.auth_header(u,p); row=retry(lambda:wp.fetch_post_by_slug(auth)); raw=wp.raw_field(row,'content')
    lines=['# ux300h affiliate context','', '- result: **SUCCESS**',f'- content_sha256: `{hashlib.sha256(raw.encode()).hexdigest()}`',f'- gulliver_2843_count: **{raw.count(G)}**',f'- ctn_banner_2846_count: **{raw.count(CB)}**',f'- ctn_button_2184_count: **{raw.count(CT)}**','', '## Gulliver insertion context','```html',snippet(raw,'実車の装備と価格を比べた方がよいと思います。'), '```','', '## CTN replacement context','```html',snippet(raw,'45秒で愛車の相場',700,1400),'```']
    (REPORT/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return 0

if __name__=='__main__':raise SystemExit(main())
