#!/usr/bin/env python3
from __future__ import annotations
import hashlib, html, os, re, time
from pathlib import Path
import apply_ux_koukai_rewrite_once as wp

wp.SLUG='ux300h'
POST_ID=2329
EXPECTED_TITLE='レクサスUX300hを試乗｜UX250hオーナーが比較して感じた3つの違い'
FEATURED_MEDIA=2330
SOURCE_SHA='8c3280319e1b0c83c7df03fb75b791e3970fa6d21fb7f22a232a21351e923986'
PUBLIC_TOTAL=61
MARKER='<!-- tsurikue-ux300h-cache-refresh-20260823 -->'
REPORT=Path('reports/ux300h-cache-refresh')
GULLIVER='[blog_parts id="2843"]'
CTN='[blog_parts id="2184"]'
GULLIVER_HREF='https://px.a8.net/svt/ejp?a8mat=4B65SD+8DUSHE+9QU+NVHCY'

def retry(fn):
    err=None
    for n in range(3):
        try:return fn()
        except Exception as e:
            err=e
            if n<2:time.sleep(3*(n+1))
    raise err

def article_imgs(s):
    srcs=re.findall(r"<img[^>]+src=['\"]([^'\"]+)['\"]",s,re.I)
    return sorted(set(x for x in srcs if 'a8.net/0.gif' not in x))

def main():
    REPORT.mkdir(parents=True,exist_ok=True)
    u=os.environ.get('TSURIKUE_WP_USER');p=os.environ.get('TSURIKUE_WP_APP_PASSWORD')
    if not u or not p:raise RuntimeError('missing WordPress secrets')
    auth=wp.auth_header(u,p)
    row=retry(lambda:wp.fetch_post_by_slug(auth));source=wp.raw_field(row,'content')
    title=html.unescape(wp.raw_field(row,'title'));before_public=retry(lambda:wp.public_total(auth))
    if row.get('id')!=POST_ID or row.get('status')!='publish' or title!=EXPECTED_TITLE or row.get('featured_media')!=FEATURED_MEDIA or before_public!=PUBLIC_TOTAL:
        raise RuntimeError('identity guard failed')
    if MARKER in source:
        lines=['# ux300h cache refresh','', '- result: **ALREADY_REFRESHED**','- wordpress_write_count: **0**',f'- content_sha256: `{hashlib.sha256(source.encode()).hexdigest()}`']
        (REPORT/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');return 0
    if hashlib.sha256(source.encode()).hexdigest()!=SOURCE_SHA:raise RuntimeError('source changed')
    if source.count(GULLIVER)!=1 or source.count(CTN)!=1 or source.count(GULLIVER_HREF)!=1:raise RuntimeError('affiliate guard failed')
    before_imgs=article_imgs(source)
    new=source.rstrip()+'\n\n'+MARKER+'\n'
    retry(lambda:wp.post_json(f'{wp.SITE_URL}/wp-json/wp/v2/posts/{POST_ID}',auth,{'content':new}))
    after=retry(lambda:wp.fetch_post_by_slug(auth));saved=wp.raw_field(after,'content');after_public=retry(lambda:wp.public_total(auth))
    view_url=f'{wp.SITE_URL}/wp-json/wp/v2/posts/{POST_ID}?context=view&_fields=id,status,title,content,featured_media'
    view,_=retry(lambda:wp.get_json(view_url,auth));rendered=(view.get('content') or {}).get('rendered','')
    ok=(after.get('status')=='publish' and after.get('featured_media')==FEATURED_MEDIA and after_public==PUBLIC_TOTAL and article_imgs(saved)==before_imgs and saved.count(GULLIVER)==1 and saved.count(CTN)==1 and saved.count(GULLIVER_HREF)==1 and 'お宝UX、まだ表に出ていないかも。' in rendered and '高く売りたい。でも電話ラッシュはいらない。' in rendered and rendered.count('px.a8.net')>=3)
    lines=['# ux300h cache refresh','',f"- result: **{'SUCCESS' if ok else 'BLOCKED_AFTER_WRITE'}**",f'- post_id: **{after.get("id")}**',f'- status: **{after.get("status")}**',f'- featured_media: **{after.get("featured_media",0)}**',f'- public_before: **{before_public}**',f'- public_after: **{after_public}**','- wordpress_write_count: **1**',f'- article_image_count: **{len(article_imgs(saved))}**',f'- gulliver_shortcode_count: **{saved.count(GULLIVER)}**',f'- gulliver_custom_link_count: **{saved.count(GULLIVER_HREF)}**',f'- ctn_button_count: **{saved.count(CTN)}**',f'- rendered_px_a8_count: **{rendered.count("px.a8.net")}**',f'- content_sha256: `{hashlib.sha256(saved.encode()).hexdigest()}`']
    (REPORT/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    if not ok:raise RuntimeError('post-refresh audit failed')
    return 0

if __name__=='__main__':raise SystemExit(main())

# retrigger cache refresh
