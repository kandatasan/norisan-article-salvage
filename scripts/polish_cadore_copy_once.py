#!/usr/bin/env python3
from __future__ import annotations
import base64,json,os,re,urllib.request

SITE='https://tsurikue.com'; BASE=SITE+'/wp-json/wp/v2'; POST_ID=3548
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode()
H={'Authorization':AUTH,'Accept':'application/json','Content-Type':'application/json; charset=utf-8','User-Agent':'tsurikue-cadore-copy/1.0'}

def req(path,method='GET',payload=None):
    data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode()
    r=urllib.request.Request(BASE+path,data=data,headers=H,method=method)
    with urllib.request.urlopen(r,timeout=60) as x:return json.loads(x.read().decode())

def main():
    p=req(f'/posts/{POST_ID}?context=edit&_fields=id,status,title,content,featured_media')
    if p['status']!='draft': raise RuntimeError('POST_NOT_DRAFT')
    raw=p['content']['raw']
    media_before=sorted(re.findall(r'wp-(?:image|video)[^>]*?|"id":(\d+)',raw))
    image_ids_before=sorted(re.findall(r'wp-image-(\d+)',raw))
    video_urls_before=sorted(re.findall(r'<video[^>]+src="([^"]+)"',raw))

    replacements={
'''<!-- wp:paragraph -->
<p>東広島市福富町にある上ノ原牧場カドーレ。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>ここは「牧場を見に行く場所」というより、<strong>動物と遊んで、ジェラートやチーズ、ピザまで楽しめる小さな牧場レジャースポット</strong>という感じです。</p>
<!-- /wp:paragraph -->''':
'''<!-- wp:paragraph -->
<p>東広島市福富町にある<strong>上ノ原牧場カドーレ</strong>。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>「牧場だから、牛を見て終わりかな？」と思ったら、いい意味で違いました。<br>動物との距離が近く、ジェラートやチーズ、ピザまで楽しめます。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>子どもは動物、大人はグルメ。</strong><br>家族で行っても、それぞれちゃんと楽しめる牧場です。</p>
<!-- /wp:paragraph -->''',

'''<!-- wp:paragraph -->
<p>僕は広島周辺の遊べる牧場をいろいろ回りましたが、カドーレはその中でもかなり遊びやすい場所でした。</p>
<!-- /wp:paragraph -->''':
'''<!-- wp:paragraph -->
<p>僕は広島の「遊べる牧場」を一通り回りましたが、カドーレはその中でも<strong>牧場とグルメのバランスがかなり良い</strong>と感じました。</p>
<!-- /wp:paragraph -->''',

'''<!-- wp:paragraph -->
<p>牧場エリアでは牛をはじめ、動物たちを近くで見られます。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>公式サイトでは、牛・ロバ・羊・ヤギ・うさぎへの<strong>「もぐもぐ体験」</strong>が案内されていて、エサは常時設置されています。</p>
<!-- /wp:paragraph -->''':
'''<!-- wp:paragraph -->
<p>カドーレでまず楽しいのが、動物との距離の近さ。<br>牛をはじめ、牧場らしい動物たちをかなり近くで見られます。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>公式サイトでは、牛・ロバ・羊・ヤギ・うさぎへの<strong>「もぐもぐ体験」</strong>も案内されています。</p>
<!-- /wp:paragraph -->''',

'''<!-- wp:paragraph -->
<p>訪問時も、ただ遠くから眺めるというより「ちゃんと牧場に来たな」と感じられる距離感でした。</p>
<!-- /wp:paragraph -->''':
'''<!-- wp:paragraph -->
<p>遠くから眺めるだけじゃないので、子どもはかなり喜ぶはず。<br>大人でも目の前に牛が来ると、普通にテンション上がります😁</p>
<!-- /wp:paragraph -->''',

'''<!-- wp:heading -->
<h2 class="wp-block-heading">カドーレのジェラートは濃厚。でもしつこくない</h2>
<!-- /wp:heading -->''':
'''<!-- wp:heading -->
<h2 class="wp-block-heading">カドーレへ来たらジェラートは食べたい</h2>
<!-- /wp:heading -->''',

'''<!-- wp:paragraph -->
<p>カドーレへ来たら、やっぱりジェラートは食べたいところ。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>実際に食べた印象は、<strong>濃厚なミルク感がガツンとくるのに、後味はしつこくない。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>ダブルでもペロッといける味で、ラムレーズンもかなり美味しかったです。</p>
<!-- /wp:paragraph -->''':
'''<!-- wp:paragraph -->
<p>そしてカドーレといえば、やっぱりジェラート。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>実際に食べてみると、<strong>ミルク感はしっかり濃いのに、後味は重すぎない。</strong><br>牧場ジェラートらしい満足感があります。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>ダブルでもペロッといけました。<br>僕が食べた中では、ラムレーズンもかなり美味しかったです。</p>
<!-- /wp:paragraph -->''',

'''<!-- wp:paragraph -->
<p>カドーレはジェラートだけではありません。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>公式サイトでは、焼き立てのピザ、牧場内で作られるチーズ、チーズケーキなども案内されています。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>牧場へ遊びに来て、甘いものだけ食べて帰るのもいいし、ランチ込みで寄るのもあり。</p>
<!-- /wp:paragraph -->''':
'''<!-- wp:paragraph -->
<p>ジェラートだけで帰るのもったいないのが、カドーレの悩ましいところ。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>公式サイトでは、焼き立てのピザ、牧場内で作られるチーズ、チーズケーキなども案内されています。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>おやつ目的でも、ランチ目的でも寄れる。</strong><br>「牧場に遊びに行く」というより、福富ドライブの立ち寄り先として使いやすいです。</p>
<!-- /wp:paragraph -->''',

'''<!-- wp:heading -->
<h2 class="wp-block-heading">車なら志和IC・西条ICから行きやすい</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>公式サイトでは、志和ICから約20分、西条ICからは国道375号方面を使って約25〜30分と案内されています。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>福富エリアのドライブ途中に組み込みやすい場所です。</p>
<!-- /wp:paragraph -->''':
'''<!-- wp:heading -->
<h2 class="wp-block-heading">福富ドライブに組み込みやすい場所</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>公式サイトでは、志和ICから約20分、西条ICからは国道375号方面を使って約25〜30分と案内されています。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>カドーレ単体でも楽しめますが、福富には一緒に回りたい場所があるので、車でのドライブと相性がいいです。</p>
<!-- /wp:paragraph -->''',

'''<!-- wp:paragraph -->
<p>カドーレへ行くなら、近くの「道の駅 湖畔の里福富」とセットにするのもおすすめです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>湖畔の里福富には大型遊具があり、子どもたちは見た瞬間に信じられないくらい走り回ります。</p>
<!-- /wp:paragraph -->''':
'''<!-- wp:paragraph -->
<p>カドーレへ行くなら、近くの<strong>道の駅 湖畔の里福富</strong>とセットにするのがかなりおすすめ。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>湖畔の里福富には大型遊具があり、子どもたちは見た瞬間に信じられないくらい走り回ります。<br>カドーレで動物と遊んで、道の駅でさらに全力。親の体力だけが心配です🤣</p>
<!-- /wp:paragraph -->''',

'''<!-- wp:heading -->
<h2 class="wp-block-heading">カドーレは牧場＋グルメで楽しめる</h2>
<!-- /wp:heading -->''':
'''<!-- wp:heading -->
<h2 class="wp-block-heading">カドーレは「牧場＋グルメ」で大人も子どもも楽しい</h2>
<!-- /wp:heading -->''',

'''<!-- wp:paragraph -->
<p>動物を見て終わりではなく、ジェラートやチーズ、ピザまで楽しめるのがカドーレの強さです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>福富方面へドライブするなら、湖畔の里福富や十夢ミルクファームと組み合わせても楽しい一日になります。</p>
<!-- /wp:paragraph -->''':
'''<!-- wp:paragraph -->
<p>動物だけでも、ジェラートだけでも終わらない。<br><strong>牧場とグルメを一緒に楽しめるのが、カドーレの強さ</strong>だと思います。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>福富方面へドライブするなら、湖畔の里福富や十夢ミルクファームと組み合わせるのもおすすめ。<br>カドーレを目的地のひとつにすると、かなり遊びやすい一日になります。</p>
<!-- /wp:paragraph -->'''
    }

    count=0
    for old,new in replacements.items():
        if old in raw:
            raw=raw.replace(old,new,1); count+=1
        else:
            raise RuntimeError('EXPECTED_TEXT_NOT_FOUND: '+old[:120])

    req(f'/posts/{POST_ID}','POST',{'content':raw})
    v=req(f'/posts/{POST_ID}?context=edit&_fields=id,status,content,featured_media,modified')
    vr=v['content']['raw']
    image_ids_after=sorted(re.findall(r'wp-image-(\d+)',vr))
    video_urls_after=sorted(re.findall(r'<video[^>]+src="([^"]+)"',vr))
    checks={
        'draft':v['status']=='draft',
        'images_preserved':image_ids_before==image_ids_after,
        'videos_preserved':video_urls_before==video_urls_after,
        'fukutomi_image_preserved':'wp-image-3539' in vr,
        'manual_images_preserved':all(x in vr for x in ['wp-image-3551','wp-image-3554','wp-image-3550']),
        'copy_updated':'親の体力だけが心配です🤣' in vr and '牧場とグルメのバランスがかなり良い' in vr
    }
    if not all(checks.values()): raise RuntimeError('VERIFY_FAILED '+json.dumps(checks,ensure_ascii=False))
    print(json.dumps({'ok':True,'post_id':POST_ID,'replacements':count,'modified':v['modified'],'image_ids':image_ids_after,'video_urls':video_urls_after,'checks':checks},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
