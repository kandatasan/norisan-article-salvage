#!/usr/bin/env python3
from __future__ import annotations
import base64,json,os,re,urllib.parse,urllib.request

SITE='https://tsurikue.com'
BASE=SITE+'/wp-json/wp/v2'
SLUG='beppu-benten-ike'
TITLE='別府弁天池は本当に青い？水中まで透明だった｜駐車場・秋芳洞からのアクセスも紹介'
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode()
H={'Authorization':AUTH,'Accept':'application/json','Content-Type':'application/json; charset=utf-8','User-Agent':'tsurikue-benten/1.0'}

def req(path,method='GET',payload=None):
    data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode()
    r=urllib.request.Request(BASE+path,data=data,headers=H,method=method)
    with urllib.request.urlopen(r,timeout=60) as x:
        return json.loads(x.read().decode()),dict(x.headers)

def total(k):
    _,h=req(f'/{k}?status=publish&per_page=1&_fields=id')
    return int(h.get('X-WP-Total','0'))

def term(tax,slug):
    r,_=req(f'/{tax}?slug={urllib.parse.quote(slug)}&per_page=1&_fields=id')
    return int(r[0]['id']) if r else None

def recent_images():
    rows=[]
    for page in range(1,5):
        try:
            r,_=req('/media?'+urllib.parse.urlencode({
                'context':'edit','media_type':'image','per_page':100,'page':page,
                'orderby':'date','order':'desc','after':'2026-09-04T00:38:00',
                '_fields':'id,date,source_url'
            }))
            rows+=r
        except Exception:
            break
    c=sorted(rows,key=lambda x:int(x['id']))[-6:]
    if len(c)!=6:
        raise RuntimeError('BENTEN_MEDIA_BATCH_NOT_FOUND '+json.dumps([(m['id'],m['source_url']) for m in rows[-20:]],ensure_ascii=False))
    return c

def img(m,alt):
    return f'''<!-- wp:image {{"id":{m["id"]},"sizeSlug":"large","linkDestination":"none"}} -->
<figure class="wp-block-image size-large"><img src="{m["source_url"]}" alt="{alt}" class="wp-image-{m["id"]}"/></figure>
<!-- /wp:image -->'''

def find_parent():
    rows,_=req('/posts?'+urllib.parse.urlencode({'search':'山口','status':'publish','context':'edit','per_page':100,'_fields':'id,title,link'}))
    for p in rows:
        t=p['title']['raw']
        if '山口県は魅力満載' in t or ('山口' in t and 'ドライブ' in t and '観光' in t):
            return p['link']
    return None

def main():
    before={'posts':total('posts'),'pages':total('pages')}
    ex,_=req('/posts?'+urllib.parse.urlencode({'slug':SLUG,'status':'any','context':'edit','per_page':10,'_fields':'id,status,slug'}))
    if ex:
        raise RuntimeError('SLUG_EXISTS '+json.dumps(ex,ensure_ascii=False))

    media=recent_images()
    cat=term('categories','sightseeing-leisure')
    tag=term('tags','yamaguchi')
    if not cat:
        raise RuntimeError('CATEGORY_NOT_FOUND')
    parent=find_parent()
    pics=[img(m,f'山口県美祢市の別府弁天池と周辺の様子{i+1}') for i,m in enumerate(media)]
    parent_html=f'''<!-- wp:paragraph -->
<p>山口をまとめて回るなら、<a href="{parent}">山口ドライブ・観光の記事</a>もどうぞ。</p>
<!-- /wp:paragraph -->''' if parent else ''

    body=f'''<!-- wp:paragraph -->
<p>山口県美祢市にある別府弁天池。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>規模だけ見れば大きな観光地ではありません。<br>でも実際に見てみると、<strong>淡水系の絶景としては最高峰クラスかもしれない</strong>と思うほど水がきれいでした。</p>
<!-- /wp:paragraph -->
{pics[0]}
<!-- wp:paragraph -->
<p>色だけなら、高知で見た仁淀川を思い出します。<br>ただ、山道を走って向かった仁淀川と比べると、別府弁天池はかなり立ち寄りやすい。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>しかも周辺には秋吉台や秋芳洞などの名所があります。<br><strong>「○○へ行くついで」に選びやすいのも、別府弁天池の良さでした。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">別府弁天池は小さい。でも水の美しさは別格</h2>
<!-- /wp:heading -->
{pics[1]}
<!-- wp:paragraph -->
<p>最初に感じたのは、「思ったよりコンパクトだな」でした。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>ところが水を見ると、そんなことはどうでもよくなります。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p><strong>透明なのに、青い。</strong><br>光の入り方によってはエメラルドグリーンにも見えて、池の底まで見えるほど透き通っています。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>別府弁天池湧水は環境省の「名水百選」に選ばれている湧水です。<br>大きさよりも、この水の色と透明度を見に行く場所だと思いました。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">周辺の水路まで、とんでもなく透明</h2>
<!-- /wp:heading -->
{pics[2]}
<!-- wp:paragraph -->
<p>別府弁天池そのものも十分きれいですが、個人的に驚いたのが周辺の水路。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>水中カメラを入れてみると、底が見えるどころか、<strong>水中なのにずっと先まで見える。</strong></p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>水があるのに、水がないみたい。<br>ここまで透明だと、ちょっと感覚がおかしくなります。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">水中写真にはサワガニも隠れていた</h2>
<!-- /wp:heading -->
{pics[3]}
<!-- wp:paragraph -->
<p>水中を撮っていると、サワガニも発見。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>さて、どこにいるでしょう。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>濁った水なら気づかなかったはず。<br>池の青さだけでなく、周辺の水まで透き通っているのが面白かったです。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">別府弁天池本体にカメラを沈めたかった。でも無理だった</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>ここまで透明なら当然、気になります。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p><strong>「別府弁天池の中にカメラを沈めたら、どう見えるんだろう？」</strong></p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>好奇心にはかられました。<br>ただ、僕にはその勇気が圧倒的に足りていませんでした。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>さすがにこの神秘的な池にカメラを突っ込む気にはなれず、水中撮影は周辺の水路だけ。<br>池の中は自分の目で楽しむことにしました。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">水汲み場には「財宝が授かる」という案内も</h2>
<!-- /wp:heading -->
{pics[4]}
<!-- wp:paragraph -->
<p>周辺を歩いていると、水汲み場の案内もありました。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>山口県の公式観光サイトでは、専用の給水所があり、この水には<strong>飲むと長寿が保たれ、財宝が授かるという言い伝え</strong>があると紹介されています。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>金運アップと言われると、ちょっと気になります。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">別府弁天池の駐車場は無料・約40台</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>山口県公式観光サイトによると、駐車場は<strong>無料で約40台</strong>。大型バスにも対応しています。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>中国自動車道の美祢IC、小郡萩道路の十文字ICからは、どちらも車で約20分です。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">営業時間は？公式では年中無休・料金無料</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>別府弁天池について、山口県公式観光サイトでは<strong>年中無休・料金無料</strong>と案内されています。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>特定の営業時間は掲載されていません。<br>周辺の売店や飲食店、釣り堀などはそれぞれ営業時間があるため、利用する場合は個別に確認してください。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">秋芳洞から別府弁天池は車で約15分</h2>
<!-- /wp:heading -->
{pics[5]}
<!-- wp:paragraph -->
<p>別府弁天池をおすすめしやすい理由が、周辺観光との組み合わせやすさです。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>山口県公式観光サイトでは、<strong>秋芳洞や秋吉台から車で約15分ほど</strong>と紹介されています。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>僕も、別府弁天池だけを目的に一日使うというより、山口ドライブの途中に組み込むのがいいと思いました。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">バスだけで行くなら少し計画が必要</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>公共交通の場合、山口県公式観光サイトでは、JR新山口駅からバスで約40分の「秋芳洞」まで行き、そこからタクシーで約20分というアクセスが案内されています。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>車なら周辺スポットまでまとめて回りやすいので、別府弁天池はドライブとの相性がいい場所です。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">別府弁天池は「ついで」に入れやすい淡水絶景</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>別府弁天池は、巨大な湖でも長い渓谷でもありません。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>でも、<strong>規模の小ささだけでスルーするには、あまりにも水がきれい。</strong></p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>高知の仁淀川を思い出すような色。<br>水中なのにずっと先まで見える周辺水路。<br>そして秋吉台や秋芳洞と組み合わせやすい立地。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>山口をドライブするなら、かなり入れやすい寄り道スポットです。</p>
<!-- /wp:paragraph -->
{parent_html}
<!-- wp:paragraph {{"fontSize":"small"}} -->
<p class="has-small-font-size">駐車場・アクセス・休業日・料金は、2026年9月に山口県公式観光サイトで確認した情報です。最新情報は公式サイトでご確認ください。</p>
<!-- /wp:paragraph -->'''

    payload={'title':TITLE,'slug':SLUG,'status':'draft','content':body,'categories':[cat],'featured_media':int(media[0]['id'])}
    if tag:
        payload['tags']=[tag]
    p,_=req('/posts','POST',payload)
    after={'posts':total('posts'),'pages':total('pages')}
    v,_=req(f"/posts/{p['id']}?context=edit&_fields=id,status,slug,title,content,featured_media,categories,tags,link")
    raw=v['content']['raw']
    ids=[int(m['id']) for m in media]
    checks={
        'draft':v['status']=='draft',
        'slug':v['slug']==SLUG,
        'images':all(f'wp-image-{i}' in raw for i in ids),
        'featured':v['featured_media']==ids[0],
        'public_unchanged':before==after,
        'seo_info':all(x in raw for x in ['約40台','年中無休','約15分','新山口駅'])
    }
    if not all(checks.values()):
        raise RuntimeError('VERIFY_FAILED '+json.dumps(checks,ensure_ascii=False))
    print(json.dumps({
        'ok':True,'action':'BEPPU_BENTEN_DRAFT_CREATED','post_id':p['id'],'link':p['link'],
        'media_ids':ids,'category':cat,'tag':tag,'parent_link':parent,
        'checks':checks,'public_before':before,'public_after':after
    },ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
