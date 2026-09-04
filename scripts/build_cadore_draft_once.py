#!/usr/bin/env python3
from __future__ import annotations
import base64,json,os,urllib.parse,urllib.request

SITE='https://tsurikue.com'; BASE=SITE+'/wp-json/wp/v2'
SLUG='cadore-fukutomi'
TITLE='上ノ原牧場カドーレへ行ってきた｜ジェラート・動物・営業時間まで紹介'
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode()
H={'Authorization':AUTH,'Accept':'application/json','Content-Type':'application/json; charset=utf-8','User-Agent':'tsurikue-cadore/1.0'}
def req(path,method='GET',payload=None):
    d=None if payload is None else json.dumps(payload,ensure_ascii=False).encode()
    r=urllib.request.Request(BASE+path,data=d,headers=H,method=method)
    with urllib.request.urlopen(r,timeout=60) as x:return json.loads(x.read().decode()),dict(x.headers)
def total(k):
    _,h=req(f'/{k}?status=publish&per_page=1&_fields=id'); return int(h.get('X-WP-Total','0'))
def term(tax,slug):
    r,_=req(f'/{tax}?slug={urllib.parse.quote(slug)}&per_page=1&_fields=id'); return int(r[0]['id']) if r else None
def media(mid):
    m,_=req(f'/media/{mid}?context=edit&_fields=id,source_url,slug'); return m
def img(m,alt):
    return f'''<!-- wp:image {{"id":{m["id"]},"sizeSlug":"large","linkDestination":"none"}} -->
<figure class="wp-block-image size-large"><img src="{m["source_url"]}" alt="{alt}" class="wp-image-{m["id"]}"/></figure>
<!-- /wp:image -->'''
def post_by_slug(slug):
    r,_=req('/posts?'+urllib.parse.urlencode({'slug':slug,'status':'publish','context':'edit','per_page':5,'_fields':'id,link'}))
    return r[0]['link'] if r else None
def main():
    before={'posts':total('posts'),'pages':total('pages')}
    ex,_=req('/posts?'+urllib.parse.urlencode({'slug':SLUG,'status':'any','context':'edit','per_page':5,'_fields':'id,status'}))
    if ex: raise RuntimeError('SLUG_EXISTS '+json.dumps(ex,ensure_ascii=False))
    cows=media(1926)   # IMG_0021, existing Cadore section image
    gelato=media(1914) # IMG_6806, existing Cadore gelato section image
    parent=post_by_slug('hiroshima-bokujyou')
    fukutomi=post_by_slug('kohannosato-fukutomi')
    cat=term('categories','sightseeing-leisure')
    tag=term('tags','hiroshima')
    body=f'''<!-- wp:paragraph -->
<p>東広島市福富町にある上ノ原牧場カドーレ。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>ここは「牧場を見に行く場所」というより、<strong>動物と遊んで、ジェラートやチーズ、ピザまで楽しめる小さな牧場レジャースポット</strong>という感じです。</p>
<!-- /wp:paragraph -->
{img(cows,'上ノ原牧場カドーレで見られる牛たち')}
<!-- wp:paragraph -->
<p>僕は広島周辺の遊べる牧場をいろいろ回りましたが、カドーレはその中でもかなり遊びやすい場所でした。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">カドーレは動物との距離が近い</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>牧場エリアでは牛をはじめ、動物たちを近くで見られます。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>公式サイトでは、牛・ロバ・羊・ヤギ・うさぎへの<strong>「もぐもぐ体験」</strong>が案内されていて、エサは常時設置されています。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>訪問時も、ただ遠くから眺めるというより「ちゃんと牧場に来たな」と感じられる距離感でした。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">カドーレのジェラートは濃厚。でもしつこくない</h2>
<!-- /wp:heading -->
{img(gelato,'カドーレで食べた牧場ジェラート')}
<!-- wp:paragraph -->
<p>カドーレへ来たら、やっぱりジェラートは食べたいところ。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>実際に食べた印象は、<strong>濃厚なミルク感がガツンとくるのに、後味はしつこくない。</strong></p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>ダブルでもペロッといける味で、ラムレーズンもかなり美味しかったです。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>公式サイトによると、搾りたての牛乳の一部はその日のうちにジェラートやチーズへ加工され、ジェラートは店内で毎日手作りされています。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">チーズ・ピザ・スイーツまである</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>カドーレはジェラートだけではありません。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>公式サイトでは、焼き立てのピザ、牧場内で作られるチーズ、チーズケーキなども案内されています。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>牧場へ遊びに来て、甘いものだけ食べて帰るのもいいし、ランチ込みで寄るのもあり。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">営業時間・定休日</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>公式サイトでは、営業時間は<strong>10:00〜17:00</strong>、夏期は<strong>10:00〜18:00</strong>。上ノ原チーズケーキは11:00〜17:00です。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>定休日は毎週月曜日。月曜日が祝日の場合は営業し、火曜日が振替休日になります。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>住所は<strong>広島県東広島市福富町上竹仁605</strong>です。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">車なら志和IC・西条ICから行きやすい</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>公式サイトでは、志和ICから約20分、西条ICからは国道375号方面を使って約25〜30分と案内されています。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>福富エリアのドライブ途中に組み込みやすい場所です。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">湖畔の里福富とセットにすると、かなり遊べる</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>カドーレへ行くなら、近くの「道の駅 湖畔の里福富」とセットにするのもおすすめです。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>湖畔の里福富には大型遊具があり、子どもたちは見た瞬間に信じられないくらい走り回ります。</p>
<!-- /wp:paragraph -->
''' + (f'''<!-- wp:paragraph -->
<p><a href="{fukutomi}">道の駅 湖畔の里福富の記事はこちら</a></p>
<!-- /wp:paragraph -->''' if fukutomi else '') + (f'''<!-- wp:paragraph -->
<p>広島周辺の牧場を比べたい人は、<a href="{parent}">広島の遊べる牧場・ジェラート食べ比べ記事</a>もどうぞ。</p>
<!-- /wp:paragraph -->''' if parent else '') + f'''
<!-- wp:heading -->
<h2 class="wp-block-heading">カドーレは牧場＋グルメで楽しめる</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>動物を見て終わりではなく、ジェラートやチーズ、ピザまで楽しめるのがカドーレの強さです。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>福富方面へドライブするなら、湖畔の里福富や十夢ミルクファームと組み合わせても楽しい一日になります。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph {{"fontSize":"small"}} -->
<p class="has-small-font-size">営業時間・定休日・体験内容は2026年9月に上ノ原牧場カドーレ公式サイトで確認しています。最新情報は公式サイトをご確認ください。</p>
<!-- /wp:paragraph -->'''
    payload={'title':TITLE,'slug':SLUG,'status':'draft','content':body,'categories':[cat] if cat else [],'featured_media':int(cows['id'])}
    if tag: payload['tags']=[tag]
    p,_=req('/posts','POST',payload)
    after={'posts':total('posts'),'pages':total('pages')}
    v,_=req(f"/posts/{p['id']}?context=edit&_fields=id,status,slug,content,featured_media,link")
    raw=v['content']['raw']
    checks={'draft':v['status']=='draft','slug':v['slug']==SLUG,'images':f"wp-image-{cows['id']}" in raw and f"wp-image-{gelato['id']}" in raw,'featured':v['featured_media']==int(cows['id']),'public_unchanged':before==after}
    if not all(checks.values()): raise RuntimeError('VERIFY_FAILED '+json.dumps(checks,ensure_ascii=False))
    print(json.dumps({'ok':True,'post_id':p['id'],'link':p['link'],'cows_media':cows,'gelato_media':gelato,'parent':parent,'fukutomi':fukutomi,'checks':checks},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
