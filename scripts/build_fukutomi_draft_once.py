#!/usr/bin/env python3
from __future__ import annotations
import base64,json,os,re,urllib.parse,urllib.request

SITE='https://tsurikue.com'
BASE=SITE+'/wp-json/wp/v2'
SLUG='kohannosato-fukutomi'
TITLE='道の駅 湖畔の里福富は巨大遊具がすごい！公園で遊べる東広島の道の駅'
STEMS=['img_0012','img_0014','img_0018','img_0017','img_0019']
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode()
H={'Authorization':AUTH,'Accept':'application/json','Content-Type':'application/json; charset=utf-8','User-Agent':'tsurikue-fukutomi/1.0'}

def req(path,method='GET',payload=None):
    d=None if payload is None else json.dumps(payload,ensure_ascii=False).encode()
    r=urllib.request.Request(BASE+path,data=d,headers=H,method=method)
    with urllib.request.urlopen(r,timeout=60) as x:return json.loads(x.read().decode()),dict(x.headers)

def total(k):
    _,h=req(f'/{k}?status=publish&per_page=1&_fields=id'); return int(h.get('X-WP-Total','0'))

def term(tax,slug):
    r,_=req(f'/{tax}?slug={urllib.parse.quote(slug)}&per_page=1&_fields=id'); return int(r[0]['id']) if r else None

def media_map():
    rows=[]
    for page in range(1,8):
        try:
            r,_=req('/media?'+urllib.parse.urlencode({'context':'edit','media_type':'image','per_page':100,'page':page,'orderby':'date','order':'desc','_fields':'id,source_url'}))
            rows+=r
        except:break
    out={}
    for stem in STEMS:
        m=[x for x in rows if re.search(rf'/{stem}(?:-\d+)?\.(?:jpe?g|png|webp)$',x.get('source_url',''),re.I)]
        if not m:raise RuntimeError('MEDIA_NOT_FOUND '+stem)
        out[stem]=sorted(m,key=lambda x:int(x['id']))[-1]
    return out

def img(m,alt):
    return f'''<!-- wp:image {{"id":{m["id"]},"sizeSlug":"large","linkDestination":"none"}} -->
<figure class="wp-block-image size-large"><img src="{m["source_url"]}" alt="{alt}" class="wp-image-{m["id"]}"/></figure>
<!-- /wp:image -->'''

def find牧場():
    rows,_=req('/posts?'+urllib.parse.urlencode({'slug':'hiroshima-bokujyou','status':'publish','context':'edit','per_page':5,'_fields':'id,link'}))
    return rows[0]['link'] if rows else None

def main():
    before={'posts':total('posts'),'pages':total('pages')}
    ex,_=req('/posts?'+urllib.parse.urlencode({'slug':SLUG,'status':'any','context':'edit','per_page':5,'_fields':'id,status'}))
    if ex: raise RuntimeError('SLUG_EXISTS '+json.dumps(ex,ensure_ascii=False))
    m=media_map()
    cat=term('categories','sightseeing-leisure')
    tag=term('tags','hiroshima')
    parent=find牧場()
    body=f'''<!-- wp:paragraph -->
<p>東広島市福富町にある「道の駅 湖畔の里福富」。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>ここ、道の駅というより<strong>子どもを思いっきり遊ばせる目的地</strong>として使える場所です。</p>
<!-- /wp:paragraph -->
{img(m['img_0019'],'道の駅 湖畔の里福富の大型遊具と長い滑り台')}
<!-- wp:paragraph -->
<p>子どもたちは、この遊具を見た瞬間に信じられないくらい駆け回ります。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>そして大人はというと……。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p><strong>「いや、これは子ども用だからね」みたいな顔をしながら、実はちょっと楽しい。</strong></p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>感情を抑えるのに必死になりますが、正直、大人もちょっと遊びたくなる道の駅です。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">湖畔の里福富は、大型遊具がとにかくすごい</h2>
<!-- /wp:heading -->
{img(m['img_0018'],'道の駅 湖畔の里福富のふれあい広場にある大型遊具')}
<!-- wp:paragraph -->
<p>公式サイトでは、ふれあい広場に<strong>21種類のアトラクション</strong>があると案内されています。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>しかも大型遊具は無料。<br>「道の駅でちょっと休憩」のつもりで寄ると、たぶん予定が変わります。</p>
<!-- /wp:paragraph -->
{img(m['img_0017'],'湖畔の里福富の大型遊具で遊べるふれあい広場')}
<!-- wp:paragraph -->
<p>滑り台やアスレチックが広い範囲に並んでいて、子どもが走り回りたくなるのも納得です。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">道の駅だから、遊ぶだけで終わらない</h2>
<!-- /wp:heading -->
{img(m['img_0014'],'道の駅 湖畔の里福富の交流館')}
<!-- wp:paragraph -->
<p>湖畔の里福富は、交流館に地元の特産品や農産物、パン、ジェラートなどが並び、食事もできます。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>公式サイトでも「丸1日遊べる道の駅」と案内されていて、遊具だけでなく、デイキャンプ場、宿泊キャンプ場、多目的グラウンド、展望台などもあります。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">ジェラートやバーベキューも楽しめる</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>「福富 道の駅 ジェラート」で検索する人も多いですが、公式サイトでは自家製ジェラートを扱っていることが確認できます。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>また、バーベキューは予約制のデイキャンプ場や、レストランテラスの手ぶらバーベキューが用意されています。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>遊具で遊ぶだけじゃなく、食べる・買う・キャンプするまで一か所で完結しやすいのがいいところです。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">福富は牧場と組み合わせると、さらに楽しい</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>そして湖畔の里福富のいいところは、周辺にも遊べる場所があること。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>近くには<strong>上ノ原牧場カドーレ</strong>や<strong>十夢ミルクファーム</strong>があります。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>僕は広島の「遊べる牧場」を一通り回っていますが、湖畔の里福富とこの2か所を組み合わせると、かなり遊びやすいドライブコースになります。</p>
<!-- /wp:paragraph -->
''' + (f'''<!-- wp:paragraph -->
<p>牧場も合わせて回りたい人は、<a href="{parent}">広島の遊べる牧場まとめ</a>もどうぞ。</p>
<!-- /wp:paragraph -->''' if parent else '') + f'''
<!-- wp:heading -->
<h2 class="wp-block-heading">営業時間とアクセス</h2>
<!-- /wp:heading -->
{img(m['img_0012'],'道の駅 湖畔の里福富の入口')}
<!-- wp:paragraph -->
<p>東広島市公式サイトでは、交流館の開館時間は<strong>平日9:30〜18:00、土日祝9:00〜18:00</strong>。道の駅自体は年中無休です。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>山陽自動車道の西条ICからは国道375号を北へ車で約20分、志和ICからは県道33号経由で約25分と案内されています。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>住所は<strong>広島県東広島市福富町久芳1506</strong>です。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">子どもは全力、大人も実は楽しい道の駅</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>湖畔の里福富は、道の駅として休憩するだけでも便利です。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>でも個人的には、<strong>子どもを遊ばせるために行ってもいい道の駅</strong>だと思っています。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>大型遊具を見た瞬間に走り出す子どもたち。<br>それを見守りながら、実は大人もちょっとワクワクしている。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>福富方面へドライブするなら、カドーレや十夢とセットで寄るのもおすすめです。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph {{"fontSize":"small"}} -->
<p class="has-small-font-size">営業時間・施設情報は2026年9月に東広島市公式サイト、道の駅 湖畔の里福富公式サイトで確認しています。最新情報は公式サイトをご確認ください。</p>
<!-- /wp:paragraph -->'''

    payload={'title':TITLE,'slug':SLUG,'status':'draft','content':body,'categories':[cat],'featured_media':int(m['img_0019']['id'])}
    if tag: payload['tags']=[tag]
    p,_=req('/posts','POST',payload)
    after={'posts':total('posts'),'pages':total('pages')}
    v,_=req(f"/posts/{p['id']}?context=edit&_fields=id,status,slug,title,content,featured_media,link")
    raw=v['content']['raw']
    checks={'draft':v['status']=='draft','slug':v['slug']==SLUG,'images':all(f"wp-image-{m[s]['id']}" in raw for s in STEMS),'featured':v['featured_media']==int(m['img_0019']['id']),'public_unchanged':before==after,'core':'21種類' in raw and 'カドーレ' in raw and '十夢' in raw}
    if not all(checks.values()): raise RuntimeError('VERIFY_FAILED '+json.dumps(checks,ensure_ascii=False))
    print(json.dumps({'ok':True,'action':'FUKUTOMI_DRAFT_CREATED','post_id':p['id'],'link':p['link'],'media_ids':{s:m[s]['id'] for s in STEMS},'parent':parent,'checks':checks,'public_before':before,'public_after':after},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
