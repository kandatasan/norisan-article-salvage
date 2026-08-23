#!/usr/bin/env python3
from __future__ import annotations
import hashlib, html, os, re, time
from pathlib import Path
import apply_ux_koukai_rewrite_once as wp

wp.SLUG='ux300h'
POST_ID=2329
EXPECTED_TITLE='レクサスUX300hを試乗｜UX250hオーナーが比較して感じた3つの違い'
FEATURED_MEDIA=2330
SOURCE_SHA='3635cb069b08ca652fff8417606178b93948ff486f25882df1dbefe3ccca1a12'
PUBLIC_TOTAL=61
REPORT=Path('reports/ux300h-funnel-once')
GULLIVER_BANNER='[blog_parts id="2843"]'
CTN_BUTTON='[blog_parts id="2184"]'
GULLIVER_HREF='https://px.a8.net/svt/ejp?a8mat=4B65SD+8DUSHE+9QU+NVHCY'
GULLIVER_PIXEL='https://www15.a8.net/0.gif?a8mat=4B65SD+8DUSHE+9QU+NVHCY'

SECTION=r'''<!-- wp:heading -->
<h2 class="wp-block-heading">中古車でUX250hとUX300hのどちらを選ぶ？</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>ここまで比べてみると、UX300hは確実に進化しています。<br>でも、UX250hが急に古くてダメな車になったわけではありません。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>私なら、次のように選びます。</p>
<!-- /wp:paragraph -->

<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">新しさや燃費を重視するならUX300h</h3>
<!-- /wp:heading -->

<!-- wp:list -->
<ul><li>少しでも燃費性能の良いUXへ乗りたい</li><li>画面全体を使う液晶メーターが欲しい</li><li>新しいエレクトロシフトマチックが好き</li><li>年式の新しい車を長く乗りたい</li></ul>
<!-- /wp:list -->

<!-- wp:paragraph -->
<p>このような人にはUX300hが向いています。<br>特に液晶メーターは、毎日の運転で「新しくなった」と感じやすい部分でした。</p>
<!-- /wp:paragraph -->

<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">価格や装備の充実を重視するならUX250hもアリ</h3>
<!-- /wp:heading -->

<!-- wp:list -->
<ul><li>同じ予算で装備の充実した車を選びたい</li><li>走りの体感差が大きくないなら価格を抑えたい</li><li>円形メーターのデザインが好き</li><li>従来型シフトレバーの手触りや使いやすさを重視する</li></ul>
<!-- /wp:list -->

<!-- wp:paragraph -->
<p>このような人なら、状態の良いUX250hも十分候補です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><a href="https://tsurikue.com/ux-estimate/">私が購入したUX250hの見積もり総額616万円と、実際に選んだオプションはこちら</a></p>
<!-- /wp:paragraph -->

<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">迷ったら、実際の中古UXを見比べるのが早い</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>中古車は、年式や走行距離だけでなく、車両状態や付いているオプションでも価値が変わります。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>UX250hだから古い、UX300hだから絶対に満足できる。</strong><br>そんなふうに決めるより、同じ予算でどんな車が買えるのかを実車で比べた方が早いです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>ガリバーは全国の共有在庫に加えて、<strong>Web掲載前の非公開在庫</strong>も案内しています。<br>条件に合うUXが入れば、サイトへ出る前に見つかることもあります。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph {"align":"center"} -->
<p class="has-text-align-center"><strong>お宝UX、まだ表に出ていないかも。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:shortcode -->
[blog_parts id="2843"]
<!-- /wp:shortcode -->

<!-- wp:html -->
<div style="text-align:center;margin:1em 0 2em;">
<a href="https://px.a8.net/svt/ejp?a8mat=4B65SD+8DUSHE+9QU+NVHCY" rel="nofollow" style="display:inline-block;padding:14px 24px;border-radius:999px;background:#222;color:#fff;text-decoration:none;font-weight:700;">非公開在庫も含めて中古UXを探してみる</a>
<img border="0" width="1" height="1" src="https://www15.a8.net/0.gif?a8mat=4B65SD+8DUSHE+9QU+NVHCY" alt="">
</div>
<!-- /wp:html -->

<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">価格差で迷うなら、今乗っている車の売却額も確認する</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>欲しいUXが見つかったら、次に見るのは<strong>今の車がいくらで売れるか</strong>です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>私が前のシエンタを手放したときは、ディーラー下取りが50万円、買取店では75万円。<br>その差は25万円でした。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>売却額が25万円上がれば、次の車を25万円安く買えたのとほぼ同じです。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>私のUXを売ったときも、査定額を比較してから427万円で手放しました。<br><a href="https://tsurikue.com/ux-resale/">616万円で購入したUXを427万円で売却した記録はこちら</a></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>CTNは最大15社で査定し、やり取りするのは<strong>高額査定の上位3社だけ</strong>。<br>高く売れる会社は探したい。でも何社からも電話が来るのは避けたい。そんな人に使いやすい仕組みです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph {"align":"center"} -->
<p class="has-text-align-center"><strong>高く売りたい。でも電話ラッシュはいらない。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:shortcode -->
[blog_parts id="2184"]
<!-- /wp:shortcode -->
'''

def retry(fn):
    err=None
    for n in range(3):
        try: return fn()
        except Exception as e:
            err=e
            if n<2: time.sleep(3*(n+1))
    raise err

def article_imgs(s):
    srcs=re.findall(r"<img[^>]+src=['\"]([^'\"]+)['\"]",s,re.I)
    return sorted(set(x for x in srcs if 'a8.net/0.gif' not in x))

def main():
    REPORT.mkdir(parents=True,exist_ok=True)
    u=os.environ.get('TSURIKUE_WP_USER'); p=os.environ.get('TSURIKUE_WP_APP_PASSWORD')
    if not u or not p: raise RuntimeError('missing WordPress secrets')
    auth=wp.auth_header(u,p)
    row=retry(lambda: wp.fetch_post_by_slug(auth)); source=wp.raw_field(row,'content')
    title=html.unescape(wp.raw_field(row,'title'))
    before_public=retry(lambda: wp.public_total(auth))
    if row.get('id')!=POST_ID or row.get('status')!='publish' or title!=EXPECTED_TITLE or row.get('featured_media')!=FEATURED_MEDIA or before_public!=PUBLIC_TOTAL:
        raise RuntimeError('post identity guard failed')
    if hashlib.sha256(source.encode()).hexdigest()!=SOURCE_SHA: raise RuntimeError('source changed after audit')
    for m in ['中古車でUX250hとUX300hのどちらを選ぶ？','まとめ｜新しさは300h、250hにも捨てがたい良さがある','シエンタ','427万円']:
        if m not in source: raise RuntimeError('marker missing: '+m)
    before_imgs=article_imgs(source)
    start=wp.heading_block_start(source,'中古車でUX250hとUX300hのどちらを選ぶ？')
    end=wp.heading_block_start(source,'まとめ｜新しさは300h、250hにも捨てがたい良さがある')
    if end<=start: raise RuntimeError('bad range')
    new=source[:start]+SECTION.strip()+'\n\n'+source[end:]
    if article_imgs(new)!=before_imgs: raise RuntimeError('article image set changed before apply')
    if new.count(GULLIVER_BANNER)!=1 or new.count(CTN_BUTTON)!=1 or new.count(GULLIVER_HREF)!=1 or new.count(GULLIVER_PIXEL)!=1:
        raise RuntimeError('affiliate count guard failed before apply')
    retry(lambda: wp.post_json(f'{wp.SITE_URL}/wp-json/wp/v2/posts/{POST_ID}',auth,{'content':new}))
    after=retry(lambda: wp.fetch_post_by_slug(auth)); saved=wp.raw_field(after,'content')
    after_public=retry(lambda: wp.public_total(auth))
    ok=(after.get('id')==POST_ID and after.get('status')=='publish' and html.unescape(wp.raw_field(after,'title'))==EXPECTED_TITLE and after.get('featured_media')==FEATURED_MEDIA and after_public==PUBLIC_TOTAL and article_imgs(saved)==before_imgs and saved.count(GULLIVER_BANNER)==1 and saved.count(CTN_BUTTON)==1 and saved.count(GULLIVER_HREF)==1 and '迷ったら、実際の中古UXを見比べるのが早い' in saved and '高額査定の上位3社だけ' in saved)
    lines=['# ux300h funnel rewrite','',f"- result: **{'SUCCESS' if ok else 'BLOCKED_AFTER_WRITE'}**",f'- post_id: **{after.get("id")}**',f'- status: **{after.get("status")}**',f'- title: {html.unescape(wp.raw_field(after,"title"))}',f'- featured_media: **{after.get("featured_media",0)}**',f'- public_before: **{before_public}**',f'- public_after: **{after_public}**','- wordpress_write_count: **1**',f'- source_sha256: `{SOURCE_SHA}`',f'- content_sha256: `{hashlib.sha256(saved.encode()).hexdigest()}`',f'- image_count: **{len(article_imgs(saved))}**',f'- gulliver_banner_count: **{saved.count(GULLIVER_BANNER)}**',f'- gulliver_button_link_count: **{saved.count(GULLIVER_HREF)}**',f'- ctn_button_count: **{saved.count(CTN_BUTTON)}**']
    (REPORT/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    if not ok: raise RuntimeError('post-update structural audit failed')
    return 0

if __name__=='__main__': raise SystemExit(main())
