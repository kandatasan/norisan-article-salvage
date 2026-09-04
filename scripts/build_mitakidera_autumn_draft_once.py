#!/usr/bin/env python3
from __future__ import annotations
import base64,json,os,re,urllib.parse,urllib.request
SITE='https://tsurikue.com'; BASE=SITE+'/wp-json/wp/v2'
SLUG='mitakidera-autumn'; TITLE='広島・三滝寺（三瀧寺）の紅葉｜2025年11月の色づきと秋の境内を散策'
STEMS=['img_5563','img_5564','img_5566','img_5567','img_5568','img_5569','img_5570','img_5571','img_5572']
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode()
H={'Authorization':AUTH,'Accept':'application/json','Content-Type':'application/json; charset=utf-8','User-Agent':'tsurikue-mitakidera/1.0'}
def req(path,method='GET',payload=None):
 d=None if payload is None else json.dumps(payload,ensure_ascii=False).encode()
 r=urllib.request.Request(BASE+path,data=d,headers=H,method=method)
 with urllib.request.urlopen(r,timeout=60) as x:return json.loads(x.read().decode()),dict(x.headers)
def total(k):
 _,h=req(f'/{k}?status=publish&per_page=1&_fields=id'); return int(h.get('X-WP-Total','0'))
def medias():
 rows=[]
 for page in range(1,8):
  try:r,_=req('/media?'+urllib.parse.urlencode({'context':'edit','media_type':'image','per_page':100,'page':page,'orderby':'date','order':'desc','_fields':'id,source_url'})); rows+=r
  except:break
 out={}
 for stem in STEMS:
  m=[x for x in rows if re.search(rf'/{stem}(?:-\d+)?\.(?:jpe?g|png|webp)$',x.get('source_url',''),re.I)]
  if not m:raise RuntimeError('MEDIA_NOT_FOUND '+stem)
  out[stem]=sorted(m,key=lambda x:int(x['id']))[-1]
 return out
def img(m,alt,caption=None):
 cap=f'<figcaption class="wp-element-caption">{caption}</figcaption>' if caption else ''
 return f'''<!-- wp:image {{"id":{m['id']},"sizeSlug":"large","linkDestination":"none"}} -->
<figure class="wp-block-image size-large"><img src="{m['source_url']}" alt="{alt}" class="wp-image-{m['id']}"/>{cap}</figure>
<!-- /wp:image -->'''
def term(tax,slug):
 r,_=req(f'/{tax}?slug={urllib.parse.quote(slug)}&per_page=1&_fields=id'); return int(r[0]['id']) if r else None
def main():
 before={'posts':total('posts'),'pages':total('pages')}
 ex,_=req('/posts?'+urllib.parse.urlencode({'slug':SLUG,'status':'any','context':'edit','per_page':5,'_fields':'id,status,slug'}))
 if ex:raise RuntimeError('SLUG_EXISTS '+json.dumps(ex,ensure_ascii=False))
 m=medias(); cat=term('categories','sightseeing-leisure'); tag=term('tags','hiroshima')
 if not cat:raise RuntimeError('CATEGORY_NOT_FOUND')
 hero=m['img_5570']
 body=f'''{img(hero,'紅葉に囲まれた広島の三滝寺（三瀧寺）の多宝塔','2025年11月撮影')}
<!-- wp:paragraph -->
<p>広島で紅葉を見たい。<br>でも、丸一日かけて歩き回るほどではなく、気軽に秋を楽しみたい。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>そんな日に、三滝寺はちょうどいい場所です。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>広島市内から近いし、何より<strong>歩く距離がちょうどいい。</strong><br>今回は妻と母も一緒だったので、なおさらそう感じました。</p>
<!-- /wp:paragraph -->
<!-- wp:heading -->
<h2 class="wp-block-heading">広島市内から近くて、歩く距離もちょうどいい</h2>
<!-- /wp:heading -->
{img(m['img_5563'],'秋の三滝寺の石段と紅葉')}
<!-- wp:paragraph -->
<p>広島の紅葉スポットといえば、三段峡や帝釈峡も本当にきれいです。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>ただし……。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p><strong>とにかく歩く！</strong></p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>もちろん、それも含めて楽しい場所なんですけどね。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>その点、三滝寺は境内をのんびり歩きながら紅葉を楽しめます。<br>妻と母と3人で歩く今回のおでかけには、この距離感がちょうどよかったです。</p>
<!-- /wp:paragraph -->
{img(m['img_5564'],'三滝寺の境内に続く石段と色づいた木々')}
<!-- wp:heading -->
<h2 class="wp-block-heading">コンパクトだから見どころが少ない？いやいや、大間違い</h2>
<!-- /wp:heading -->
{img(m['img_5566'],'紅葉に囲まれた三滝寺の境内')}
<!-- wp:paragraph -->
<p>歩く距離がほどよいからといって、「見るところも少ないんじゃない？」と思ったら大間違い。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>紅葉が美しいだけでなく、三滝寺には名前の由来にもなった<strong>3つの瀧</strong>があります。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>木々に囲まれた石段を歩いて、お寺を見て、紅葉を眺めて、さらに瀧まである。<br><strong>短い距離の中に見どころがギュッと詰まっている感じです。</strong></p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>……と言いつつ、瀧の写真をなぜか1枚も撮ってませんでした🤣<br>紅葉ばっかり撮ってたんでしょうね。</p>
<!-- /wp:paragraph -->
{img(m['img_5567'],'三滝寺の秋の境内と紅葉')}
<!-- wp:heading -->
<h2 class="wp-block-heading">紅葉の中に現れる朱色の多宝塔</h2>
<!-- /wp:heading -->
{img(m['img_5568'],'三滝寺の多宝塔と秋の紅葉')}
<!-- wp:paragraph -->
<p>境内を歩いていると、紅葉の中に朱色の多宝塔が現れます。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>ここはさすがに足が止まります。<br>赤や黄色に色づいた木々と朱色の塔が並ぶと、秋らしさが一気に濃くなる。</p>
<!-- /wp:paragraph -->
{img(m['img_5569'],'色づいた木々の間から見える三滝寺の多宝塔')}
{img(m['img_5571'],'三滝寺の多宝塔を囲む黄色と赤の紅葉')}
<!-- wp:heading -->
<h2 class="wp-block-heading">派手な遠出じゃなくても、ちゃんと秋を楽しめる</h2>
<!-- /wp:heading -->
{img(m['img_5572'],'秋の三滝寺の境内と色づいた木々')}
<!-- wp:paragraph -->
<p>三段峡や帝釈峡まで紅葉を見に行くのも楽しい。<br>でも、「今日はそこまで歩きたくないな」という日もあります。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>そんなときに、広島市内から行きやすく、妻や母とゆっくり歩けた三滝寺はちょうどよかったです。</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph -->
<p>コンパクトだけど、紅葉もお寺も瀧もある。<br><strong>近場で秋らしい景色をのんびり楽しみたい日に、かなり良い場所でした。</strong></p>
<!-- /wp:paragraph -->'''
 payload={'title':TITLE,'slug':SLUG,'status':'draft','content':body,'categories':[cat],'featured_media':int(hero['id'])}
 if tag:payload['tags']=[tag]
 p,_=req('/posts','POST',payload); after={'posts':total('posts'),'pages':total('pages')}
 v,_=req(f"/posts/{p['id']}?context=edit&_fields=id,status,slug,title,content,featured_media,categories,tags,link"); raw=v['content']['raw']
 checks={'draft':v['status']=='draft','slug':v['slug']==SLUG,'images':all(f"wp-image-{m[s]['id']}" in raw for s in STEMS),'caption':'2025年11月撮影' in raw,'featured':v['featured_media']==int(hero['id']),'public_unchanged':before==after}
 if not all(checks.values()):raise RuntimeError('VERIFY_FAILED '+json.dumps(checks,ensure_ascii=False))
 print(json.dumps({'ok':True,'post_id':p['id'],'link':p['link'],'media':{s:m[s]['id'] for s in STEMS},'category':cat,'tag':tag,'checks':checks,'public_before':before,'public_after':after},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
