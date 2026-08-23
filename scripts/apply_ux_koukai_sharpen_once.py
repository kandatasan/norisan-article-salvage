#!/usr/bin/env python3
from __future__ import annotations
import hashlib, html, json, os, time
from pathlib import Path
from apply_ux_koukai_rewrite_once import auth_header, fetch_post_by_slug, public_total, raw_field, post_json

SLUG='ux-koukai'
POST_ID=2517
TITLE='レクサスUXはひどい？616万円で買って後悔した欠点と満足している理由'
SOURCE_SHA='8321162a52e27f6c3f669bd29733d74dda515299e01c499848971e58a32c48a3'
REPORT=Path('reports/ux-koukai-sharpen-once')

INTRO='''<!-- wp:paragraph -->
<p><strong>レクサスUX、私はかなり好きでした。</strong><br>でも約616万円で買った車として見ると、<strong>「ここはひどい🤣」と思ったところも普通にあります。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>後席は狭い。<br>荷室は高さがつらい。<br>後席の内装はちょっとショボい。<br>そして納車約5か月・5,000kmで、ディーラー査定350万円。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>高かっただけに、文句もあります🤣</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>この記事では、UX250hを新車で買って、旅行に使って、最後は427万円で売った私が、<strong>「ひどい」「後悔」と検索する前に知っておきたかったこと</strong>を全部ぶちまけます。</p>
<!-- /wp:paragraph -->'''

CONCLUSION='''<!-- wp:heading -->
<h2 class="wp-block-heading">結論｜616万円なら文句あり。でも中古なら話が変わる</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>先にまとめると、私がUXで気になったのはこの6つです。</p>
<!-- /wp:paragraph -->

<!-- wp:table -->
<figure class="wp-block-table"><table><tbody>
<tr><th>気になったところ</th><th>私の本音</th></tr>
<tr><td>後部座席</td><td><strong>正直、狭い</strong></td></tr>
<tr><td>荷室</td><td><strong>広さより高さがつらい</strong></td></tr>
<tr><td>内装</td><td>前席は良い。でも<strong>後席はあっさり</strong></td></tr>
<tr><td>外装</td><td>フェンダーアーチの線がずっと気になる</td></tr>
<tr><td>購入タイミング</td><td>納車半年後にUX300h。<strong>タイミング悪すぎ</strong></td></tr>
<tr><td>査定</td><td>ディーラー350万円。<strong>これは衝撃</strong></td></tr>
</tbody></table></figure>
<!-- /wp:table -->

<!-- wp:paragraph -->
<p>2026年8月時点の新車UXは500万円台ですが、中古なら<strong>200〜300万円台</strong>も狙えます。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>616万円なら「ここ頑張ってよ！」と思った弱点も、250万円や300万円のレクサスだと考えると……。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>いや、めちゃくちゃ良くない？😏</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>しかもガリバーには、Webに出る前の<strong>非公開在庫</strong>があります。<br>希望条件に合う車が入れば、公開前に案内してもらえることもあります。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>お宝UX、まだ表に出てないかも。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:shortcode -->
[blog_parts id="2843"]
<!-- /wp:shortcode -->

<!-- wp:paragraph -->
<p><small>※中古車価格は年式・走行距離・グレード・車両状態などで変わります。価格感は2026年8月に確認した掲載状況をもとにしています。</small></p>
<!-- /wp:paragraph -->'''

CTN='''<!-- wp:paragraph -->
<p>私のUXはディーラー査定350万円に対して、一括査定では最高500万円近い提示が出ました。<br><strong>この差を見たら、1社だけで決めるのは怖いです。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>CTNは最大15社で査定し、連絡が来るのは<strong>高額査定の上位3社だけ</strong>。<br>「高く売りたい。でも電話ラッシュはいらない🤣」という人には、かなり使いやすい仕組みです。</p>
<!-- /wp:paragraph -->

<!-- wp:shortcode -->
[blog_parts id="2846"]
<!-- /wp:shortcode -->'''

POSITIVE_OPEN='''<!-- wp:paragraph -->
<p>ここまで文句を並べましたが、<strong>それでも私はUXが好きでした。</strong><br>理由は単純。UXに乗ってから、車で出かけることそのものが楽しくなったからです。</p>
<!-- /wp:paragraph -->'''

POSITIVE_TAIL='''<!-- wp:paragraph -->
<p>UXを一言でいうなら、<strong>小さな高級車</strong>です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>1〜2人なら後席をほとんど使わない。<br>1〜2泊の旅行荷物は積める。<br>狭い道や小さな駐車場でも扱いやすい。<br>長距離も楽。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>私たち夫婦には、使わない広さより<strong>毎日使う快適さ</strong>の方が大事でした。<br>この尖った立ち位置が、私は好きでした。</p>
<!-- /wp:paragraph -->'''

USED='''<!-- wp:heading -->
<h2 class="wp-block-heading">今からレクサスUXを買うなら、私は中古を選ぶ</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>約616万円で新車を買った私が言います。<br><strong>今もう一度UXを買うなら、中古です。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">200〜300万円台なら、UXの弱点がかなり許せる</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>後席は狭い。荷室も大きくない。後席の内装もあっさり。<br>そこは中古になっても変わりません。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>でも250万円や300万円の「小さな高級車」として見ると、話が変わります。</p>
<!-- /wp:paragraph -->

<!-- wp:list -->
<ul><li>運転しやすいサイズ</li><li>静かで乗り心地が良い</li><li>前席の質感はしっかりレクサス</li><li>長距離でも疲れにくい</li><li>見た目はいま見ても好き</li></ul>
<!-- /wp:list -->

<!-- wp:paragraph -->
<p><strong>この値段なら、かなり強い。</strong><br>私はそう思います。</p>
<!-- /wp:paragraph -->

<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">UX250hも、急に古くてダメな車になったわけじゃない</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>UX300hは確かに進化していました。<br>でも250h、全然ダメになってない。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>新しさや燃費ならUX300h。<br>価格と装備のバランスならUX250h。<br><strong>私は中古250hも普通に候補です。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><a href="https://tsurikue.com/ux300h/">UX250hオーナーだった私がUX300hへ試乗して比べた記事はこちら</a></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>中古UXを探すなら、ネットに出ている車だけで決めるのはちょっともったいないです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>ガリバーには<strong>一般公開前の非公開在庫</strong>があり、希望条件に合う車が入れば公開前に案内してもらえることがあります。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph {"align":"center"} -->
<p class="has-text-align-center"><strong>200〜300万円台のお宝UX、探してみる？😏</strong></p>
<!-- /wp:paragraph -->

<!-- wp:html -->
<div style="text-align:center;margin:1em 0 2em;">
<a href="https://px.a8.net/svt/ejp?a8mat=4B65SD+8DUSHE+9QU+NVHCY" rel="nofollow" style="display:inline-block;padding:14px 24px;border-radius:999px;background:#222;color:#fff;text-decoration:none;font-weight:700;">非公開在庫も含めて中古UXを探してみる</a>
<img border="0" width="1" height="1" src="https://www15.a8.net/0.gif?a8mat=4B65SD+8DUSHE+9QU+NVHCY" alt="">
</div>
<!-- /wp:html -->

<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">今の車が高く売れれば、中古UXはさらに狙いやすい</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>私のUXは、ディーラー査定350万円。<br>一括査定では最高500万円近い提示。<br>最終的には427万円で売却しました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>前の車を高く売れれば、そのぶん次のUXを安く買えたのと同じ。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>CTNなら最大15社で査定して、やり取りするのは<strong>高値を付けた上位3社だけ</strong>。<br>高く売りたい。でも何社からも電話が来るのはイヤ。そんな人向けです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph {"align":"center"} -->
<p class="has-text-align-center"><strong>高く売りたい。でも電話ラッシュはいらない。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:shortcode -->
[blog_parts id="2184"]
<!-- /wp:shortcode -->

<!-- wp:paragraph -->
<p><small>※査定額は車種、年式、走行距離、車両状態、査定時期などによって異なります。</small></p>
<!-- /wp:paragraph -->'''

SUMMARY='''<!-- wp:heading -->
<h2 class="wp-block-heading">まとめ｜616万円なら文句あり。中古UXならかなりアリ</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>レクサスUXの弱点はハッキリしています。</p>
<!-- /wp:paragraph -->

<!-- wp:list -->
<ul><li><strong>後席は狭い</strong></li><li><strong>荷室は高さがつらい</strong></li><li>後席側の内装は前席よりあっさり</li><li>フェンダーアーチの線が私は気になった</li><li>私の場合は納車半年後にUX300hが登場</li><li>ディーラー査定350万円にはへこんだ</li></ul>
<!-- /wp:list -->

<!-- wp:paragraph -->
<p><strong>約616万円で買った私は、ここに普通に文句があります🤣</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>でも、大きすぎない。運転しやすい。静か。長距離も楽。<br>そして見るたびにちょっと嬉しい。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>UXに乗ってから、山陰、角島、淡路島と、クルマで出かけることそのものが楽しくなりました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>新車500万円台なら、欠点まで分かったうえで選びたい。</strong><br><strong>でも200〜300万円台の中古UXなら、私はかなりアリだと思います。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>広さが必要ならNXや別のSUV。<br>1〜2人で乗ることが多くて「小さな高級車」が欲しいならUX。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>だが！<strong>私はUXの方が好きなのでしょうがない🤣</strong></p>
<!-- /wp:paragraph -->'''

def bstart(s,t):
    i=s.find(t)
    if i<0: raise RuntimeError('anchor missing: '+t)
    j=s.rfind('<!-- wp:',0,i)
    if j<0: raise RuntimeError('block missing: '+t)
    return j

def hstart(s,t):
    i=s.find(t)
    if i<0: raise RuntimeError('heading missing: '+t)
    j=s.rfind('<!-- wp:heading',0,i)
    if j<0: raise RuntimeError('heading block missing: '+t)
    return j

def repl(s,a,b,x,headings=False):
    p=hstart if headings else bstart
    i,j=p(s,a),p(s,b)
    if j<=i: raise RuntimeError('bad range')
    return s[:i]+x.strip()+'\n\n'+s[j:]

def drop_para(s,t):
    if t not in s: return s
    i=bstart(s,t); j=s.find('<!-- /wp:paragraph -->',i)
    if j<0: raise RuntimeError('paragraph close missing')
    return s[:i]+s[j+len('<!-- /wp:paragraph -->'):]

def build(s):
    if hashlib.sha256(s.encode()).hexdigest()!=SOURCE_SHA: raise RuntimeError('source changed after audit')
    for m in ['結論｜レクサスUXはひどくない。でも616万円で見ると気になる','今からレクサスUXを買うなら、私は中古を選ぶ','まとめ｜UXは高くて狭い。でも中古なら話が変わる']:
        if m not in s: raise RuntimeError('missing source marker: '+m)
    s=repl(s,'「レクサスUXはひどい」と検索している人は、購入前に不安になっている人だと思います。','この記事で紹介する車両',INTRO)
    s=repl(s,'結論｜レクサスUXはひどくない。でも616万円で見ると気になる','レクサスUXを買って「ひどい」と感じた6つの欠点',CONCLUSION,True)
    s=drop_para(s,'ふざけているようですが、実際に使うとこういう場面があります。')
    s=s.replace('ここは無理にかばえません。','ここは、かばえません🤣').replace('これは車そのものの欠点ではありません.\nでも、購入タイミングとしては悔しかったです。','車の欠点ではありません。\n<strong>私のタイミングが悪かった🤣</strong>').replace('UX250hを選んだこと自体は後悔していません。\nでも、購入時期については少し悔しさが残っています。','<strong>250hは好き。でも、これは悔しい。</strong>')
    s=repl(s,'そしてもうひとつ。','それでもレクサスUXを買って後悔していない理由',CTN)
    s=repl(s,'ここまで欠点を並べると、不満の多い車に見えるかもしれません。','納車後は、広島県内だけでなく、山陰、角島、淡路島へも出かけました。',POSITIVE_OPEN)
    s=repl(s,'UXの魅力は、小さい高級車として見たときに分かりやすいです。','今からレクサスUXを買うなら、私は中古を選ぶ',POSITIVE_TAIL)
    s=repl(s,'今からレクサスUXを買うなら、私は中古を選ぶ','レクサスUXに関するよくある質問',USED,True)
    i=hstart(s,'まとめ｜UXは高くて狭い。でも中古なら話が変わる'); s=s[:i]+SUMMARY.strip()+'\n'
    checks={'[blog_parts id="2843"]':1,'[blog_parts id="2846"]':1,'[blog_parts id="2184"]':1,'https://px.a8.net/svt/ejp?a8mat=4B65SD+8DUSHE+9QU+NVHCY':1}
    for k,v in checks.items():
        if s.count(k)!=v: raise RuntimeError('affiliate count mismatch: '+k)
    for m in ['荷室でテトリス','こぶし1個半','350万円','500万円近い','427万円','山陰','角島','淡路島']:
        if m not in s: raise RuntimeError('fact lost: '+m)
    return s

def retry(fn):
    e=None
    for n in range(3):
        try:return fn()
        except Exception as x:
            e=x
            if n<2: time.sleep(3*(n+1))
    raise e

def report(d):
    REPORT.mkdir(parents=True,exist_ok=True)
    (REPORT/'result.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# ux-koukai sharpen','',f"- result: **{d.get('result')}**",f"- post_id: **{d.get('post_id','unknown')}**",f"- status: **{d.get('status','unknown')}**",f"- title: {d.get('title','')}",f"- featured_media: **{d.get('featured_media',0)}**",f"- public_before: **{d.get('public_before','unknown')}**",f"- public_after: **{d.get('public_after','unknown')}**",f"- wordpress_write_count: **{d.get('wordpress_write_count',0)}**",f"- source_sha256: `{d.get('source_sha','')}`",f"- content_sha256: `{d.get('content_sha','')}`",f"- gulliver_banner_count: **{d.get('gulliver_banner_count',0)}**",f"- gulliver_button_count: **{d.get('gulliver_button_count',0)}**",f"- ctn_banner_count: **{d.get('ctn_banner_count',0)}**",f"- ctn_button_count: **{d.get('ctn_button_count',0)}**"]
    if d.get('error'): lines.append(f"- error: `{d['error']}`")
    (REPORT/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

def main():
    d={'result':'BLOCKED','wordpress_write_count':0}
    try:
        u,p=os.environ.get('TSURIKUE_WP_USER'),os.environ.get('TSURIKUE_WP_APP_PASSWORD')
        if not u or not p: raise RuntimeError('missing WordPress secrets')
        a=auth_header(u,p); total=retry(lambda:public_total(a)); before=retry(lambda:fetch_post_by_slug(a)); cur=raw_field(before,'content')
        pid=int(before.get('id') or 0); title=html.unescape(raw_field(before,'title')); status=before.get('status'); media=int(before.get('featured_media') or 0)
        d.update(post_id=pid,status=status,title=title,featured_media=media,public_before=total,source_sha=hashlib.sha256(cur.encode()).hexdigest())
        if pid!=POST_ID or status!='publish' or title!=TITLE: raise RuntimeError('post identity/state mismatch')
        want=build(cur); resp=post_json(f'https://tsurikue.com/wp-json/wp/v2/posts/{pid}',a,{'content':want,'status':'publish'}); d['wordpress_write_count']=1
        if int(resp.get('id') or 0)!=pid or resp.get('status')!='publish': raise RuntimeError('update response mismatch')
        after=retry(lambda:fetch_post_by_slug(a)); atotal=retry(lambda:public_total(a)); ac=raw_field(after,'content'); atitle=html.unescape(raw_field(after,'title'))
        if atotal!=total or after.get('status')!='publish' or atitle!=TITLE or int(after.get('featured_media') or 0)!=media: raise RuntimeError('post-update state mismatch')
        for m in ['高かっただけに、文句もあります🤣','非公開在庫','高額査定の上位3社だけ','荷室でテトリス','まとめ｜616万円なら文句あり。中古UXならかなりアリ']:
            if m not in ac: raise RuntimeError('post-update marker missing: '+m)
        counts=(ac.count('[blog_parts id="2843"]'),ac.count('https://px.a8.net/svt/ejp?a8mat=4B65SD+8DUSHE+9QU+NVHCY'),ac.count('[blog_parts id="2846"]'),ac.count('[blog_parts id="2184"]'))
        if counts!=(1,1,1,1): raise RuntimeError('post-update affiliate count mismatch')
        d.update(result='SUCCESS',public_after=atotal,content_sha=hashlib.sha256(ac.encode()).hexdigest(),gulliver_banner_count=counts[0],gulliver_button_count=counts[1],ctn_banner_count=counts[2],ctn_button_count=counts[3])
        report(d); return 0
    except Exception as e:
        d['error']=str(e); report(d); return 1

if __name__=='__main__': raise SystemExit(main())
