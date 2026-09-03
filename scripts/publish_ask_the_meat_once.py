#!/usr/bin/env python3
from __future__ import annotations
import base64, json, os, urllib.parse, urllib.request

SITE='https://tsurikue.com'; BASE=SITE+'/wp-json/wp/v2'; SLUG='ask-the-meat'; CATEGORY_ID=9; FEATURED_MEDIA=3291
TITLE='アスクザミートの熟成肉コースを6人で食べてきた｜肉の味が濃い。過去最強クラスかも'
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode()
HEADERS={'Authorization':AUTH,'Accept':'application/json','Content-Type':'application/json; charset=utf-8','User-Agent':'tsurikue-ask-the-meat/1.0'}

def req(path,method='GET',payload=None):
    data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode()
    r=urllib.request.Request(BASE+path,data=data,headers=HEADERS,method=method)
    with urllib.request.urlopen(r,timeout=60) as x:return json.loads(x.read().decode()),dict(x.headers)

def total(kind):
    _,h=req(f'/{kind}?status=publish&per_page=1&_fields=id');return int(h.get('X-WP-Total','0'))

def tag(slug):
    rows,_=req('/tags?'+urllib.parse.urlencode({'slug':slug,'context':'edit','per_page':10,'_fields':'id,name,slug'}))
    if len(rows)!=1:raise RuntimeError('TAG_NOT_UNIQUE '+slug)
    return rows[0]

def existing():
    rows,_=req('/posts?'+urllib.parse.urlencode({'slug':SLUG,'context':'edit','status':'any','per_page':10,'_fields':'id,slug,status,link'}))
    return rows

def image_block():
    return '''<!-- wp:image {"id":3291,"sizeSlug":"large","linkDestination":"none"} -->
<figure class="wp-block-image size-large"><img src="https://tsurikue.com/wp-content/uploads/2026/09/img_7358.jpg" alt="アスクザミートの熟成肉コースで出てきた霜降りの肉" class="wp-image-3291"/><figcaption class="wp-element-caption">部位の名前は分かりません。でも、見た瞬間に「これは旨いやつ」と分かる肉でした。</figcaption></figure>
<!-- /wp:image -->'''

def content():
    return f'''<!-- wp:paragraph -->
<p>広島市安佐南区緑井にある焼肉店「アスク ザ ミート（ask the meat）」へ、親戚6人で行ってきました。<br>今回食べたのは、<strong>熟成肉料理のみコース 4,980円〜</strong>です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>先に感想を言います。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>めちゃくちゃ旨い。</strong><br>これまで食べてきた焼肉の中でも、最強クラスかもしれません。</p>
<!-- /wp:paragraph -->

{image_block()}

<!-- wp:paragraph -->
<p>肉の部位は、正直よく分かりません。<br>食レポも得意ではありません。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>それでも「あの肉は旨かった」と言いたくなる店でした。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">アスクザミートの熟成肉コースを6人で食べてきた</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>今回利用したのは、食べログにも掲載されている<strong>「熟成肉料理のみコース 4,980円〜」</strong>。<br>仕入れによって内容が毎回変わるコースなので、何が出てくるかはその日次第です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>親戚6人で集まって食べたのですが、とにかく肉が次々に出てきます。<br>霜降りの肉、赤身っぽい肉、厚みのある肉。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>そして困ったことに、私は部位の名前をほとんど覚えていません。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>「これは○○で、こちらは○○です」みたいな解説はできません。</strong><br>でも、食べた感想は覚えています。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">柔らかいだけじゃない。肉そのものの味が濃い</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>高い肉の感想というと「柔らかい」「脂が甘い」みたいな表現になりがちですが、アスクザミートで一番印象に残ったのは少し違いました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>肉の味が濃い。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>うまく説明できません。<br>ただ、噛んだときに「あ、いい肉食べてるわ」と分かる感じです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>もちろん柔らかい肉もありました。<br>でも、それだけじゃない。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>タレの味で食べるというより、肉そのものが旨い。<br>私の語彙力では、結局ここへ戻ってきます。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>とにかく旨い。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">4,980円〜でこの肉なら満足度は高かった</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>今回の熟成肉コースは4,980円（税込）から。<br>現在の掲載情報でも、仕入れによって内容が変わるため「4,980円〜」となっています。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>焼肉で約5,000円と聞くと安い金額ではありません。<br>ただ、私にとっては<strong>「今まで食べた焼肉の中でも最強クラスかもしれない」</strong>と思うくらい、満足度の高い肉でした。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>家族や親戚で、ちょっといい焼肉を食べたい日に候補にしやすいと思います。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">アスクザミートは事前予約がおすすめ</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>ここはかなり人気があります。<br>行くなら<strong>事前予約がおすすめ</strong>です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>席数も大きな焼肉店ほど多くありません。<br>特に週末など、行く日が決まっているなら先に席を押さえておく方が安心です。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">駐車場は店舗前に普通車2台＋軽1台</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>駐車場は店舗前にあります。<br>現在の掲載情報では<strong>普通車2台＋軽自動車1台</strong>です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>私の記憶も「店舗前に数台」という感じでした。<br>6人など複数人で行く場合は、車をまとめられるならまとめた方が動きやすいと思います。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">アスクザミートの店舗情報</h2>
<!-- /wp:heading -->

<!-- wp:table -->
<figure class="wp-block-table"><table><tbody><tr><th>店名</th><td>アスク ザ ミート（ask the meat）</td></tr><tr><th>住所</th><td>広島県広島市安佐南区緑井2-8-15</td></tr><tr><th>アクセス</th><td>JR可部線 緑井駅から徒歩約5分</td></tr><tr><th>営業時間</th><td>17:00〜24:00（L.O.23:30）</td></tr><tr><th>定休日</th><td>火曜日</td></tr><tr><th>駐車場</th><td>普通車2台＋軽1台</td></tr><tr><th>今回食べたコース</th><td>熟成肉料理のみコース 4,980円〜（税込）</td></tr><tr><th>予約</th><td>予約可</td></tr></tbody></table></figure>
<!-- /wp:table -->

<!-- wp:paragraph {"fontSize":"small"} -->
<p class="has-small-font-size">※店舗情報・コース料金は2026年9月に確認した掲載情報です。営業日・価格・コース内容は変わることがあるため、予約時にお店へ確認してください。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><a href="https://tabelog.com/hiroshima/A3401/A340107/34019810/" target="_blank" rel="nofollow noopener">アスク ザ ミートの掲載情報を確認する</a></p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">肉の名前は分からん。でも、とにかく旨かった</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>この記事を書くにあたって写真を見返しても、やっぱり肉の部位は分かりません。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>グルメ記事としては困った話です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>でも、味の記憶はしっかり残っています。<br><strong>アスクザミートは、私が今まで食べた焼肉の中でも最強クラス。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>「安佐南区でちょっといい焼肉を食べたい」なら、候補に入れてみてください。<br>行くなら、予約してからがおすすめです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>ほかの実食記事は、<a href="https://tsurikue.com/gourmet/">つりくえ！グルメトップ</a>からどうぞ。</p>
<!-- /wp:paragraph -->'''

def main():
    if existing():raise RuntimeError('POST_ALREADY_EXISTS '+SLUG)
    before={'posts':total('posts'),'pages':total('pages')}
    t_hiro=tag('hiroshima');t_meat=tag('meat-hearty')
    media,_=req(f'/media/{FEATURED_MEDIA}?context=edit&_fields=id,source_url,mime_type')
    if media.get('id')!=FEATURED_MEDIA or not str(media.get('mime_type','')).startswith('image/'):
        raise RuntimeError('FEATURED_MEDIA_INVALID')
    payload={'title':TITLE,'slug':SLUG,'status':'publish','content':content(),'excerpt':'広島市安佐南区緑井のアスクザミートで「熟成肉料理のみコース 4,980円〜」を親戚6人で実食。部位名は分からなくても、肉そのものの味の濃さに驚いた。駐車場・予約・営業時間も紹介します。','categories':[CATEGORY_ID],'tags':[int(t_hiro['id']),int(t_meat['id'])],'featured_media':FEATURED_MEDIA}
    post,_=req('/posts',method='POST',payload=payload)
    after={'posts':total('posts'),'pages':total('pages')}
    if after['posts']!=before['posts']+1 or after['pages']!=before['pages']:
        raise RuntimeError('PUBLIC_COUNTS_UNEXPECTED '+json.dumps({'before':before,'after':after},ensure_ascii=False))
    verify,_=req(f"/posts/{post['id']}?context=edit&_fields=id,slug,status,link,categories,tags,featured_media,title,content")
    checks={'slug':verify.get('slug')==SLUG,'status':verify.get('status')=='publish','category':CATEGORY_ID in verify.get('categories',[]),'hiroshima':int(t_hiro['id']) in verify.get('tags',[]),'meat':int(t_meat['id']) in verify.get('tags',[]),'featured':verify.get('featured_media')==FEATURED_MEDIA,'content':'肉の味が濃い' in (verify.get('content',{}).get('raw') or '')}
    if not all(checks.values()):raise RuntimeError('VERIFY_FAILED '+json.dumps(checks,ensure_ascii=False))
    print(json.dumps({'ok':True,'action':'ASK_THE_MEAT_PUBLISHED','post_id':verify['id'],'url':verify['link'],'title':TITLE,'tags':{'hiroshima':t_hiro,'meat':t_meat},'featured_media':FEATURED_MEDIA,'checks':checks,'public_before':before,'public_after':after},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
