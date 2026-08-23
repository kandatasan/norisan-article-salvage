#!/usr/bin/env python3
from __future__ import annotations
import hashlib, html, os, re, time, urllib.request
from pathlib import Path
import apply_ux_koukai_rewrite_once as wp

wp.SLUG='ux300h'
POST_ID=2329
FEATURED_MEDIA=2330
EXPECTED_TITLE='レクサスUX300hを試乗｜UX250hオーナーが比較して感じた3つの違い'
SOURCE_SHA='94e49922e8b9b330daa199a4a3aebad4652068003723760293b00fc980055142'
PUBLIC_TOTAL=61
SUMMARY='まとめ｜新しさは300h、250hにも捨てがたい良さがある'
REPORT=Path('reports/ux300h-affiliates-current-once')
G='[blog_parts id="2843"]'; CB='[blog_parts id="2846"]'; CT='[blog_parts id="2184"]'

BRIDGE='''<!-- wp:paragraph -->
<p>中古でUX250hとUX300hを選ぶなら、同じ予算でどんな車両が出ているかを見比べるのが早いです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph {"align":"center"} -->
<p class="has-text-align-center"><strong>中古UXを実車ベースで見比べてみる。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:shortcode -->
[blog_parts id="2843"]
<!-- /wp:shortcode -->

<!-- wp:paragraph -->
<p>乗り換えなら、今の車がいくらで売れるかも確認しておくと予算を組みやすくなります。</p>
<!-- /wp:paragraph -->

<!-- wp:shortcode -->
[blog_parts id="2846"]
<!-- /wp:shortcode -->

<!-- wp:paragraph {"align":"center"} -->
<p class="has-text-align-center"><strong>高く売りたい。でも電話ラッシュはいらない。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:shortcode -->
[blog_parts id="2184"]
<!-- /wp:shortcode -->'''

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
    return sorted(set(x for x in xs if 'a8.net/0.gif' not in x and '/svt/bgt?' not in x))

def public_has_markers():
    url='https://tsurikue.com/ux300h/?affiliate_refresh='+str(int(time.time()))
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Cache-Control':'no-cache','Pragma':'no-cache'})
    try:
        with urllib.request.urlopen(req,timeout=30) as r: body=r.read().decode('utf-8','replace')
        return ('中古UXを実車ベースで見比べてみる。' in body and '高く売りたい。でも電話ラッシュはいらない。' in body)
    except Exception:
        return False

def main():
    REPORT.mkdir(parents=True,exist_ok=True)
    u=os.environ.get('TSURIKUE_WP_USER');p=os.environ.get('TSURIKUE_WP_APP_PASSWORD')
    if not u or not p:raise RuntimeError('missing WordPress secrets')
    auth=wp.auth_header(u,p); row=retry(lambda:wp.fetch_post_by_slug(auth)); source=wp.raw_field(row,'content')
    title=html.unescape(wp.raw_field(row,'title')); before_public=retry(lambda:wp.public_total(auth)); before_imgs=imgs(source)
    if row.get('id')!=POST_ID or row.get('status')!='publish' or title!=EXPECTED_TITLE or row.get('featured_media')!=FEATURED_MEDIA or before_public!=PUBLIC_TOTAL:raise RuntimeError('identity guard failed')
    current_sha=hashlib.sha256(source.encode()).hexdigest()
    if current_sha!=SOURCE_SHA:raise RuntimeError('source changed after fresh audit: '+current_sha)
    if source.count(G) or source.count(CB) or source.count(CT):raise RuntimeError('target shortcode already exists')
    if SUMMARY not in source:raise RuntimeError('summary heading missing')
    pos=wp.heading_block_start(source,SUMMARY)
    new=source[:pos]+BRIDGE.strip()+'\n\n'+source[pos:]
    if imgs(new)!=before_imgs:raise RuntimeError('article image set changed before write')
    if new.count(G)!=1 or new.count(CB)!=1 or new.count(CT)!=1:raise RuntimeError('shortcode counts invalid before write')
    retry(lambda:wp.post_json(f'{wp.SITE_URL}/wp-json/wp/v2/posts/{POST_ID}',auth,{'content':new}))
    after=retry(lambda:wp.fetch_post_by_slug(auth)); saved=wp.raw_field(after,'content'); after_public=retry(lambda:wp.public_total(auth))
    view_url=f'{wp.SITE_URL}/wp-json/wp/v2/posts/{POST_ID}?context=view&_fields=id,status,title,content,featured_media'
    view,_=retry(lambda:wp.get_json(view_url,auth)); rendered=(view.get('content') or {}).get('rendered','')
    r2843='data-partsID="2843"' in rendered; r2846='data-partsID="2846"' in rendered; r2184='data-partsID="2184"' in rendered
    ok=(after.get('status')=='publish' and after.get('featured_media')==FEATURED_MEDIA and after_public==PUBLIC_TOTAL and html.unescape(wp.raw_field(after,'title'))==EXPECTED_TITLE and imgs(saved)==before_imgs and saved.count(G)==1 and saved.count(CB)==1 and saved.count(CT)==1 and r2843 and r2846 and r2184)
    front=public_has_markers()
    lines=['# UX300h current affiliate patch','',f"- result: **{'SUCCESS' if ok else 'BLOCKED_AFTER_WRITE'}**",f'- post_id: **{after.get("id")}**',f'- status: **{after.get("status")}**',f'- title: {html.unescape(wp.raw_field(after,"title"))}',f'- featured_media: **{after.get("featured_media",0)}**',f'- public_before: **{before_public}**',f'- public_after: **{after_public}**','- wordpress_write_count: **1**',f'- source_sha256: `{SOURCE_SHA}`',f'- content_sha256: `{hashlib.sha256(saved.encode()).hexdigest()}`',f'- article_image_count: **{len(imgs(saved))}**',f'- gulliver_2843_count: **{saved.count(G)}**',f'- ctn_banner_2846_count: **{saved.count(CB)}**',f'- ctn_button_2184_count: **{saved.count(CT)}**',f"- rendered_2843: **{'YES' if r2843 else 'NO'}**",f"- rendered_2846: **{'YES' if r2846 else 'NO'}**",f"- rendered_2184: **{'YES' if r2184 else 'NO'}**",f"- public_front_markers_visible: **{'YES' if front else 'NO'}**"]
    (REPORT/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    if not ok:raise RuntimeError('post-write audit failed')
    return 0

if __name__=='__main__':
    try:
        raise SystemExit(main())
    except Exception as e:
        REPORT.mkdir(parents=True,exist_ok=True)
        (REPORT/'summary.md').write_text('# UX300h current affiliate patch\n\n- result: **BLOCKED_BEFORE_WRITE**\n- wordpress_write_count: **0**\n- error_type: **'+type(e).__name__+'**\n- error: `'+str(e).replace('`','')+'`\n',encoding='utf-8')
        raise
