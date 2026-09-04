#!/usr/bin/env python3
from __future__ import annotations
import base64,json,os,re,urllib.parse,urllib.request

SITE='https://tsurikue.com'; BASE=SITE+'/wp-json/wp/v2'
POST_ID=3548
STEMS=['img_0021','img_0022','img_0024','img_0028','img_0027','img_0029','img_0025']
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode()
H={'Authorization':AUTH,'Accept':'application/json','Content-Type':'application/json; charset=utf-8','User-Agent':'tsurikue-cadore-media/1.0'}

def req(path,method='GET',payload=None):
    d=None if payload is None else json.dumps(payload,ensure_ascii=False).encode()
    r=urllib.request.Request(BASE+path,data=d,headers=H,method=method)
    with urllib.request.urlopen(r,timeout=60) as x:return json.loads(x.read().decode()),dict(x.headers)

def find_media():
    rows=[]
    for page in range(1,8):
        try:
            r,_=req('/media?'+urllib.parse.urlencode({'context':'edit','per_page':100,'page':page,'orderby':'date','order':'desc','_fields':'id,source_url,mime_type,media_type,slug,title'}))
            rows+=r
        except: break
    out={}
    for stem in STEMS:
        m=[x for x in rows if re.search(rf'/{stem}(?:-\d+)?\.(?:jpe?g|png|webp|mp4|mov)$',x.get('source_url',''),re.I)]
        if not m: raise RuntimeError('MEDIA_NOT_FOUND '+stem)
        out[stem]=sorted(m,key=lambda x:int(x['id']))[-1]
    return out

def img(m,alt):
    return f'''<!-- wp:image {{"id":{m["id"]},"sizeSlug":"large","linkDestination":"none"}} -->
<figure class="wp-block-image size-large"><img src="{m["source_url"]}" alt="{alt}" class="wp-image-{m["id"]}"/></figure>
<!-- /wp:image -->'''

def video(m):
    return f'''<!-- wp:video {{"id":{m["id"]}}} -->
<figure class="wp-block-video"><video controls src="{m["source_url"]}"></video></figure>
<!-- /wp:video -->'''

def main():
    p,_=req(f'/posts/{POST_ID}?context=edit&_fields=id,status,slug,title,content,featured_media')
    if p['status']!='draft': raise RuntimeError('POST_NOT_DRAFT')
    m=find_media()

    body=f'''<!-- wp:paragraph -->
<p>東広島市福富町にある上ノ原牧場カドーレ。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>ここは「牧場を見に行く場所」というより、<strong>動物と遊んで、ジェラートやチーズ、ピザまで楽しめる小さな牧場レジャースポット</strong>という感じです。</p>
<!-- /wp:paragraph -->
{img(m['img_0021'],'上ノ原牧場カドーレの外観')}
<!-- wp:paragraph -->
<p>僕は広島周辺の遊べる牧場をいろいろ回りましたが、カドーレはその中でもかなり遊びやすい場所でした。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">カドーレは動物との距離が近い</h2>
<!-- /wp:heading -->
{img(m['img_0022'],'カドーレのもぐもぐ体験案内')}
<!-- wp:paragraph -->
<p>牧場エリアでは牛をはじめ、動物たちを近くで見られます。</p>
<!-- /wp:paragraph -->
{img(m['img_0024'],'カドーレで牛を間近に見られる牧場エリア')}
<!-- wp:paragraph -->
<p>公式サイトでは、牛・ロバ・羊・ヤギ・うさぎへの<strong>「もぐもぐ体験」</strong>が案内されています。</p>
<!-- /wp:paragraph -->
{video(m['img_0025'])}
<!-- wp:paragraph -->
<p>写真だけだと伝わりにくいですが、動画で見ると「あ、ちゃんと牧場だ」と分かる距離感です。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">カドーレのジェラートは濃厚。でもしつこくない</h2>
<!-- /wp:heading -->
{img(m['img_0029'],'カドーレのジェラート売り場')}
<!-- wp:paragraph -->
<p>カドーレへ来たら、やっぱりジェラートは食べたいところ。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>実際に食べた印象は、<strong>濃厚なミルク感がガツンとくるのに、後味はしつこくない。</strong></p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>ダブルでもペロッといける味で、ラムレーズンもかなり美味しかったです。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">チーズ・ピザ・スイーツまである</h2>
<!-- /wp:heading -->
{img(m['img_0028'],'カドーレのチーズケーキ・スイーツ案内')}
{img(m['img_0027'],'カドーレのスイーツ店舗')}
<!-- wp:paragraph -->
<p>カドーレはジェラートだけではありません。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>公式サイトでは、焼き立てのピザ、牧場内で作られるチーズ、チーズケーキなども案内されています。</p>
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
<h2 class="wp-block-heading">湖畔の里福富とセットにすると、かなり遊べる</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>カドーレへ行くなら、近くの「道の駅 湖畔の里福富」とセットにするのもおすすめです。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p><a href="https://tsurikue.com/kohannosato-fukutomi/">道の駅 湖畔の里福富の記事はこちら</a></p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>広島周辺の牧場を比べたい人は、<a href="https://tsurikue.com/hiroshima-bokujyou/">広島の遊べる牧場・ジェラート食べ比べ記事</a>もどうぞ。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">カドーレは牧場＋グルメで楽しめる</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>動物を見て終わりではなく、ジェラートやチーズ、ピザまで楽しめるのがカドーレの強さです。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>福富方面へドライブするなら、湖畔の里福富や十夢ミルクファームと組み合わせても楽しい一日になります。</p>
<!-- /wp:paragraph -->'''

    payload={'content':body,'featured_media':int(m['img_0021']['id'])}
    u,_=req(f'/posts/{POST_ID}','POST',payload)
    v,_=req(f'/posts/{POST_ID}?context=edit&_fields=id,status,content,featured_media')
    raw=v['content']['raw']
    checks={
        'draft':v['status']=='draft',
        'all_media':all((f"wp-image-{m[s]['id']}" in raw) if s!='img_0025' else (m[s]['source_url'] in raw) for s in STEMS),
        'featured':v['featured_media']==int(m['img_0021']['id'])
    }
    if not all(checks.values()): raise RuntimeError('VERIFY_FAILED '+json.dumps(checks,ensure_ascii=False))
    print(json.dumps({'ok':True,'post_id':POST_ID,'media':{s:{'id':m[s]['id'],'url':m[s]['source_url'],'mime':m[s].get('mime_type')} for s in STEMS},'checks':checks},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
