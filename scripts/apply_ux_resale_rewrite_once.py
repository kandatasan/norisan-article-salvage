#!/usr/bin/env python3
from __future__ import annotations
import hashlib, html, json, os, re, time
from pathlib import Path
import apply_ux_koukai_rewrite_once as wp

wp.SLUG = 'ux-resale'
POST_ID = 2222
OLD_TITLE = 'レクサスUXはいくらで売れた？616万円で購入し427万円で売却した記録'
NEW_TITLE = 'レクサスUXのリセールは？616万円で購入し427万円で売却した記録'
SOURCE_SHA = 'c7ad0e93cf206b419730d3954f1c12245854ce6c2c46b868386d49d5f0f8c008'
REPORT = Path('reports/ux-resale-rewrite-once')
CTN_BANNER = '[blog_parts id="2846"]'
CTN_BUTTON = '[blog_parts id="2184"]'


def retry(fn):
    err = None
    for n in range(3):
        try:
            return fn()
        except Exception as e:
            err = e
            if n < 2: time.sleep(3 * (n + 1))
    raise err


def extract_image_blocks(source: str) -> list[str]:
    blocks = re.findall(r'<!-- wp:image\b.*?<!-- /wp:image -->', source, re.S)
    if len(blocks) != 3:
        raise RuntimeError(f'expected 3 image blocks, got {len(blocks)}')
    return blocks


def build(source: str) -> str:
    if hashlib.sha256(source.encode()).hexdigest() != SOURCE_SHA:
        raise RuntimeError('source changed after audit')
    for marker in ['350万円','500万円前後','430万円','435万円','427万円','カーセブン','ネクステージ','生活に余裕がなくなり']:
        if marker not in source:
            raise RuntimeError('source marker missing: ' + marker)
    images = extract_image_blocks(source)

    article = f'''<!-- wp:paragraph -->
<p>レクサスUXを<strong>616万円で購入して、427万円で売却しました。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>ただ、私が一番驚いたのは最終的な売却額ではありません。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>納車約5か月・5,000kmの同じ頃に受けた査定が、<strong>レクサスディーラー350万円</strong>と<strong>別の実車査定500万円前後</strong>。<br>同じUXなのに、約150万円差がありました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>車の査定、1社だけ見て決めるのは怖い。</strong><br>この記事は、まだ売るつもりがなかった頃の査定から、2025年2月にカーセブンへ427万円で実際に売却するまでの記録です。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">結論｜UXのリセールは悪いとは思わなかった。ただし査定先で150万円差が出た</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>まず、私のUXに実際についた金額を時系列で並べます。</p>
<!-- /wp:paragraph -->

<!-- wp:table -->
<figure class="wp-block-table"><table><tbody>
<tr><th>時期・車両条件</th><th>査定先・方法</th><th>金額</th><th>結果</th></tr>
<tr><td>2023年11月<br>納車約5か月・5,000km</td><td>レクサスディーラー<br>実車査定</td><td><strong>350万円</strong></td><td>売却せず</td></tr>
<tr><td>2023年11月<br>納車約5か月・5,000km</td><td>当時利用した別の査定サービス<br>実車査定</td><td><strong>500万円前後</strong></td><td>売却せず</td></tr>
<tr><td>納車から約1年<br>1万2,000km</td><td>査定会社<br>電話による概算</td><td>430万円</td><td>売却せず</td></tr>
<tr><td>納車から約1年<br>1万2,000km</td><td>ネクステージ<br>実車査定</td><td><strong>435万円</strong></td><td>売却せず</td></tr>
<tr><td>2025年2月<br>前回の実車査定から半年近く経過</td><td>CTN経由のカーセブン<br>実車査定・買取</td><td><strong>427万円</strong></td><td>実際に売却</td></tr>
</tbody></table></figure>
<!-- /wp:table -->

<!-- wp:paragraph -->
<p>350万円、500万円前後、430万円、435万円は査定時の提示額。<br><strong>実際に売却した金額は427万円</strong>です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>なお、購入額616万円にはオプションや諸費用も含まれます。616万円と427万円の差を、そのまま車両本体の値下がりとして見ることはできません。</p>
<!-- /wp:paragraph -->

{images[0]}

<!-- wp:paragraph -->
<p><strong>ここまで査定額が動くなら、自分の車も1社だけでは判断しにくい。</strong><br>CTNは最大15社で査定し、高額査定の上位3社とやり取りする仕組みです。</p>
<!-- /wp:paragraph -->

<!-- wp:shortcode -->
{CTN_BANNER}
<!-- /wp:shortcode -->

<!-- wp:heading -->
<h2 class="wp-block-heading">納車5か月のディーラー査定は350万円だった</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>納車から約5か月、走行距離5,000kmの頃。<br>いつものレクサスディーラーで査定してもらうと、提示額は<strong>350万円</strong>でした。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>616万円で購入してまだ5か月。オプションや諸費用込みの購入額と単純比較できないのは分かっています。<br><strong>それでも350万円は、かなりへこみました。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>担当者に聞いたところ、私が利用した店舗では公平性を保つため、第三者機関の査定をもとに金額を出しているとの説明でした。担当者との付き合いだけで査定額を上げるような仕組みではないようです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>一方でディーラーには、買い替え時に次の車が納車されるまで査定額を保証できることがあり、その間もUXに乗り続けられるという気楽さがあります。<br>金額だけでは測れないメリットはありました。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">同じ時期、別の実車査定では500万円前後だった</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>ディーラー査定と同じ頃、別の査定サービスでもUXを見てもらいました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>そこで提示されたのが<strong>500万円前後</strong>。<br>ディーラーの350万円とは、約150万円の差です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>同じ車、ほぼ同じ時期。それでも約150万円違いました。</strong><br>このとき初めて、査定先を変えるだけで見える金額がここまで変わることを実感しました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>ただし、500万円前後はあくまで提示額。この時点ではUXを売っていません。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>当時の担当者からは、UXはレクサス車の中では比較的リセールが高い車種だと説明されました。市場全体を私が調査した結論ではありませんが、「UXは不人気なのでは」と気にしていた私には嬉しい話でした。</p>
<!-- /wp:paragraph -->

{images[1]}

<!-- wp:paragraph -->
<p><strong>350万円だけ見ていたら、私はUXの価値をかなり低く考えていたはずです。</strong><br>高く売れる会社を探したい。でも何社からも電話が来るのは避けたい。CTNは高額査定の上位3社だけとやり取りする仕組みなので、そこが分かりやすいです。</p>
<!-- /wp:paragraph -->

<!-- wp:shortcode -->
{CTN_BANNER}
<!-- /wp:shortcode -->

<!-- wp:heading -->
<h2 class="wp-block-heading">納車約1年・1万2,000kmで435万円だった</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>納車から約1年、走行距離が1万2,000kmになった頃にも査定を受けました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>電話で車の状態やオプションを伝えた概算が430万円。<br>その後ネクステージに実車を見てもらい、提示されたのが<strong>435万円</strong>です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>電話概算との差は5万円。<br>この時点でも私は売却せず、そのままUXに乗り続けました。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">それでも売らなかった。でも生活のために手放すことになった</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>435万円が出たときも、本当はUXを手放すつもりはありませんでした。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>ところが、その後は生活に余裕がなくなりました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>UXに飽きたわけでも、後席や荷室の狭さが嫌になったわけでもありません。<br>見た目も、運転のしやすさも、乗り心地も気に入っていました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>それでも、生活のために手放すしかありませんでした。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><a href="https://tsurikue.com/ux-koukai/">レクサスUXを買って後悔した点</a>もあります。<br>でも、その欠点が売却理由ではありません。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">売ると決めてCTNを使った｜連絡が来たのは2社だった</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>実際に売却すると決めたあと、CTN車一括査定へ申し込みました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>CTNは最大15社で査定し、やり取りするのは<strong>高額査定の上位3社</strong>。<br>私が利用したときに連絡が来たのは、カーセブンとネクステージの2社でした。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>2社とも電話だけで金額を決めたわけではありません。実際にUXを見てもらい、結果的にカーセブンとネクステージの一騎打ちになりました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>最終的にUXを買い取ったのは、カーセブンです。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">カーセブンへ427万円で実際に売却した</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>2025年2月、カーセブンへUXを<strong>427万円</strong>で売却しました。<br>これは査定で言われただけの数字ではなく、実際の売却価格です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>半年近く前にネクステージから提示された実車査定は435万円。査定会社は異なりますが、そこから半年近くたった実売却額との差は8万円でした。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>もっと価格が落ちていると思っていたので、427万円で買い取ってもらえたことには本当に助けられました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>高く売れたから喜んで手放したわけではありません。<br>気に入っていたUXを売る悲しさと、想像していたより高く売れた安堵。その両方がありました。</p>
<!-- /wp:paragraph -->

{images[2]}

<!-- wp:paragraph -->
<p><strong>私の場合、CTN経由で2社に実車査定してもらい、最終的に427万円で売却しました。</strong><br>高く売れる会社は探したい。でも電話ラッシュは避けたい。そんな人には、上位3社だけとやり取りする仕組みは使いやすいと思います。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph {"align":"center"} -->
<p class="has-text-align-center"><strong>高く売りたい。でも何社からも電話はいらない。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:shortcode -->
{CTN_BANNER}
<!-- /wp:shortcode -->

<!-- wp:shortcode -->
{CTN_BUTTON}
<!-- /wp:shortcode -->

<!-- wp:paragraph -->
<p><small>※査定額は車種、年式、走行距離、車両状態、装備、査定時期などによって異なります。</small></p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">レクサスUXのリセールで私が学んだこと</h2>
<!-- /wp:heading -->

<!-- wp:list -->
<ul>
<li><strong>1社の査定だけでUXの価値を決めない</strong></li>
<li><strong>査定の提示額と実際の売却額は分けて考える</strong></li>
<li><strong>売る予定がなくても、相場を知っておくと判断材料になる</strong></li>
</ul>
<!-- /wp:list -->

<!-- wp:paragraph -->
<p>私のUXでは、同じ時期でも350万円と500万円前後まで差が出ました。<br>だから「UXのリセールが悪い・良い」と決めつける前に、<strong>どこで査定した金額なのか</strong>を見ることが大切だと感じています。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">まとめ｜616万円で買ったUXは427万円で売れた</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>私のUXの記録をまとめると、<strong>ディーラー350万円 → 別の実車査定500万円前後 → 約1年後435万円 → 最終427万円で売却</strong>でした。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>これは私が所有していた1台の記録なので、すべてのUXが同じ金額で売れるわけではありません。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>それでも、最初の350万円だけを見ていたら「UXのリセールはかなり厳しい」と思っていたはずです。<br><strong>UXの価値そのものより、査定先によって見えてくる金額が大きく違った。</strong>これが、何度も査定を受けて実際に売却した私の結論です。</p>
<!-- /wp:paragraph -->
'''

    source_imgs = set(re.findall(r"<img[^>]+src=['\"]([^'\"]+)['\"]", source, re.I))
    out_imgs = set(re.findall(r"<img[^>]+src=['\"]([^'\"]+)['\"]", article, re.I))
    if source_imgs != out_imgs:
        raise RuntimeError('image set changed')
    if article.count(CTN_BANNER) != 3 or article.count(CTN_BUTTON) != 1:
        raise RuntimeError('CTN placement count mismatch')
    for marker in ['616万円','350万円','500万円前後','430万円','435万円','427万円','カーセブン','ネクステージ','生活に余裕がなくなりました','レクサスUXを買って後悔した点']:
        if marker not in article: raise RuntimeError('fact lost: ' + marker)
    if '🤣' in article or '😏' in article or '普通に' in article:
        raise RuntimeError('style cleanup failed')
    return article


def report(d: dict):
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT/'result.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines = ['# ux-resale rewrite','',f"- result: **{d.get('result')}**",f"- post_id: **{d.get('post_id','unknown')}**",f"- status: **{d.get('status','unknown')}**",f"- title: {d.get('title','')}",f"- featured_media: **{d.get('featured_media',0)}**",f"- public_before: **{d.get('public_before','unknown')}**",f"- public_after: **{d.get('public_after','unknown')}**",f"- wordpress_write_count: **{d.get('wordpress_write_count',0)}**",f"- source_sha256: `{d.get('source_sha','')}`",f"- content_sha256: `{d.get('content_sha','')}`",f"- image_count: **{d.get('image_count',0)}**",f"- ctn_banner_count: **{d.get('ctn_banner_count',0)}**",f"- ctn_button_count: **{d.get('ctn_button_count',0)}**"]
    if d.get('error'): lines.append(f"- error: `{d['error']}`")
    (REPORT/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def main():
    d={'result':'BLOCKED','wordpress_write_count':0}
    try:
        u=os.environ.get('TSURIKUE_WP_USER'); p=os.environ.get('TSURIKUE_WP_APP_PASSWORD')
        if not u or not p: raise RuntimeError('missing WordPress secrets')
        auth=wp.auth_header(u,p)
        total=retry(lambda: wp.public_total(auth)); before=retry(lambda: wp.fetch_post_by_slug(auth)); cur=wp.raw_field(before,'content')
        pid=int(before.get('id') or 0); title=html.unescape(wp.raw_field(before,'title')); status=before.get('status'); media=int(before.get('featured_media') or 0)
        d.update(post_id=pid,status=status,title=title,featured_media=media,public_before=total,source_sha=hashlib.sha256(cur.encode()).hexdigest())
        if pid!=POST_ID or status!='publish' or title!=OLD_TITLE or media!=2223: raise RuntimeError('post identity/state mismatch')
        want=build(cur)
        resp=wp.post_json(f'https://tsurikue.com/wp-json/wp/v2/posts/{pid}',auth,{'title':NEW_TITLE,'content':want,'status':'publish'}); d['wordpress_write_count']=1
        if int(resp.get('id') or 0)!=pid or resp.get('status')!='publish': raise RuntimeError('update response mismatch')
        after=retry(lambda: wp.fetch_post_by_slug(auth)); atotal=retry(lambda: wp.public_total(auth)); ac=wp.raw_field(after,'content'); atitle=html.unescape(wp.raw_field(after,'title'))
        if atotal!=total or after.get('status')!='publish' or atitle!=NEW_TITLE or int(after.get('featured_media') or 0)!=media: raise RuntimeError('post-update state mismatch')
        if ac.count(CTN_BANNER)!=3 or ac.count(CTN_BUTTON)!=1: raise RuntimeError('post-update CTN count mismatch')
        source_imgs=set(re.findall(r"<img[^>]+src=['\"]([^'\"]+)['\"]",cur,re.I)); after_imgs=set(re.findall(r"<img[^>]+src=['\"]([^'\"]+)['\"]",ac,re.I))
        if source_imgs!=after_imgs: raise RuntimeError('post-update image set changed')
        for marker in ['査定先で150万円差','生活のために手放すしかありませんでした','高額査定の上位3社','まとめ｜616万円で買ったUXは427万円で売れた']:
            if marker not in ac: raise RuntimeError('post-update marker missing: '+marker)
        d.update(result='SUCCESS',status=after.get('status'),title=atitle,public_after=atotal,content_sha=hashlib.sha256(ac.encode()).hexdigest(),image_count=len(after_imgs),ctn_banner_count=ac.count(CTN_BANNER),ctn_button_count=ac.count(CTN_BUTTON))
        report(d); return 0
    except Exception as e:
        d['error']=str(e); report(d); return 1

if __name__=='__main__': raise SystemExit(main())
