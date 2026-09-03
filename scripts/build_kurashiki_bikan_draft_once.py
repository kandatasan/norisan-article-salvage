#!/usr/bin/env python3
from __future__ import annotations
import base64,json,os,re,urllib.parse,urllib.request
SITE='https://tsurikue.com';BASE=SITE+'/wp-json/wp/v2';SLUG='kurashiki-bikan-chiku';TITLE='倉敷美観地区を散策｜くらしき桃子のパフェ・デニム・川沿いを楽しんできた'
STEMS=['img_7645','img_7646','img_7650','img_7652','img_7654','img_7655']
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode();H={'Authorization':AUTH,'Accept':'application/json','Content-Type':'application/json; charset=utf-8','User-Agent':'tsurikue-kurashiki-bikan/1.0'}
def req(path,method='GET',payload=None):
 d=None if payload is None else json.dumps(payload,ensure_ascii=False).encode();r=urllib.request.Request(BASE+path,data=d,headers=H,method=method)
 with urllib.request.urlopen(r,timeout=60) as x:return json.loads(x.read().decode()),dict(x.headers)
def total(k):
 _,h=req(f'/{k}?status=publish&per_page=1&_fields=id');return int(h.get('X-WP-Total','0'))
def medias():
 rows=[]
 for page in range(1,7):
  try:r,_=req('/media?'+urllib.parse.urlencode({'context':'edit','media_type':'image','per_page':100,'page':page,'orderby':'date','order':'desc','_fields':'id,source_url'}));rows+=r
  except:break
 out={}
 for stem in STEMS:
  m=[x for x in rows if re.search(rf'/{stem}(?:-\d+)?\.(?:jpe?g|png|webp)$',x.get('source_url',''),re.I)]
  if not m:raise RuntimeError('MEDIA_NOT_FOUND '+stem)
  out[stem]=sorted(m,key=lambda x:int(x['id']))[-1]
 return out
def img(m,alt):return f'''<!-- wp:image {{"id":{m['id']},"sizeSlug":"large","linkDestination":"none"}} -->\n<figure class="wp-block-image size-large"><img src="{m['source_url']}" alt="{alt}" class="wp-image-{m['id']}"/></figure>\n<!-- /wp:image -->'''
def term_id(tax,slug):
 r,_=req(f'/{tax}?slug={urllib.parse.quote(slug)}&per_page=1&_fields=id,slug');return int(r[0]['id']) if r else None
def main():
 before={'posts':total('posts'),'pages':total('pages')};existing,_=req('/posts?'+urllib.parse.urlencode({'slug':SLUG,'status':'any','context':'edit','per_page':5,'_fields':'id,status,slug'}))
 if existing:raise RuntimeError('SLUG_EXISTS '+json.dumps(existing,ensure_ascii=False))
 m=medias();cat=term_id('categories','sightseeing-leisure');tag=term_id('tags','far-trip')
 if not cat:raise RuntimeError('CATEGORY_NOT_FOUND')
 body=f'''<!-- wp:paragraph -->\n<p>妻「いつも北か西しか行かないよね」</p>\n<!-- /wp:paragraph -->\n<!-- wp:paragraph -->\n<p>言われてみれば、たしかにそう。<br>山陰か山口。だいたいそっち方面ばかりです。</p>\n<!-- /wp:paragraph -->\n<!-- wp:paragraph -->\n<p>じゃあ、たまには東へ行ってみようか。<br>そういえば2人で倉敷美観地区へ行ったこともない。</p>\n<!-- /wp:paragraph -->\n<!-- wp:paragraph -->\n<p><strong>ということで、今回は岡山へ！</strong></p>\n<!-- /wp:paragraph -->\n<!-- wp:heading -->\n<h2 class="wp-block-heading">美観地区へ行く前に、まずはくらしき桃子へ</h2>\n<!-- /wp:heading -->\n<!-- wp:paragraph -->\n<p>美観地区へ突入する前に向かったのが、くらしき桃子。<br>岡山まで来たなら、やっぱりフルーツは食べておきたい。</p>\n<!-- /wp:paragraph -->\n{img(m['img_7645'],'くらしき桃子で食べた桃とシャインマスカットのパフェ')}\n<!-- wp:paragraph -->\n<p>妻が選んだのは、桃とシャインマスカットのパフェ。<br>記憶では4,000円近かったような……。</p>\n<!-- /wp:paragraph -->\n<!-- wp:paragraph -->\n<p>なかなか良いお値段だったので、私は日和って比較的安かった柑橘系のパフェにしました。笑</p>\n<!-- /wp:paragraph -->\n{img(m['img_7646'],'くらしき桃子で食べた柑橘系のフルーツパフェ')}\n<!-- wp:paragraph -->\n<p>でも、これが<strong>美味い！</strong><br>柑橘の甘酸っぱさの中にほんのり苦みがあって、爽やかで良かったです。</p>\n<!-- /wp:paragraph -->\n<!-- wp:paragraph -->\n<p>気がつけば、スプーンで器のヘリの方までこそいでいました。</p>\n<!-- /wp:paragraph -->\n<!-- wp:heading -->\n<h2 class="wp-block-heading">パフェを食べたら倉敷美観地区へ</h2>\n<!-- /wp:heading -->\n{img(m['img_7652'],'倉敷美観地区の倉敷川と白壁の町並み')}\n<!-- wp:paragraph -->\n<p>パフェを食べたところで、美観地区へ。<br>倉敷川沿いに白壁の建物や柳が並んでいて、ぶらぶら歩くだけでも良い雰囲気です。</p>\n<!-- /wp:paragraph -->\n{img(m['img_7650'],'倉敷美観地区の橋と白壁の町並み')}\n<!-- wp:heading -->\n<h2 class="wp-block-heading">風情ある倉敷川で、私が見つけたもの</h2>\n<!-- /wp:heading -->\n<!-- wp:paragraph -->\n<p>川沿いを歩きながら水面を見ていると、魚を発見。</p>\n<!-- /wp:paragraph -->\n<!-- wp:paragraph -->\n<p><strong>「ライギョ！ ライギョ泳いどる！！ ライギョ！！！」</strong></p>\n<!-- /wp:paragraph -->\n<!-- wp:paragraph -->\n<p>一人で大興奮して、ふと妻の方を見ると……。</p>\n<!-- /wp:paragraph -->\n<!-- wp:paragraph -->\n<p><strong>はるか彼方にいました。</strong><br>俺、完全にヤバい人みたいになってる。</p>\n<!-- /wp:paragraph -->\n{img(m['img_7655'],'倉敷美観地区の倉敷川を泳ぐ白鳥')}\n<!-- wp:paragraph -->\n<p>白鳥まで泳いでいて、川を眺めているだけでも結構楽しい。<br>まあ、私は白鳥よりライギョに夢中でしたが。</p>\n<!-- /wp:paragraph -->\n<!-- wp:heading -->\n<h2 class="wp-block-heading">デニム屋さん、かわいい。でも真夏だった</h2>\n<!-- /wp:heading -->\n{img(m['img_7654'],'倉敷美観地区の白壁の町並みと店舗')}\n<!-- wp:paragraph -->\n<p>そのまま歩いてデニム屋さんを覗いてみると、これがまじでかわいい。<br>気になる商品がいろいろありました。</p>\n<!-- /wp:paragraph -->\n<!-- wp:paragraph -->\n<p>ただし、この日は<strong>真夏の灼熱猛暑日。</strong><br>デニムを見ながらも、頭の中には暑さがちらつく。</p>\n<!-- /wp:paragraph -->\n<!-- wp:paragraph -->\n<p>これが秋ごろだったら、たぶん何か衝動買いしていたと思います。</p>\n<!-- /wp:paragraph -->\n<!-- wp:heading -->\n<h2 class="wp-block-heading">倉敷美観地区は、目的を決めすぎず歩くのも楽しい</h2>\n<!-- /wp:heading -->\n<!-- wp:paragraph -->\n<p>「たまには東へ行ってみよう」から始まった岡山ドライブ。<br>最初にパフェを食べて、美観地区をぶらぶらして、魚を見つけて大騒ぎして、デニム屋さんを覗く。</p>\n<!-- /wp:paragraph -->\n<!-- wp:paragraph -->\n<p>有名スポットを全部回ったわけではありませんが、こういう<strong>目的を決めすぎない散策</strong>も美観地区にはよく似合う気がします。</p>\n<!-- /wp:paragraph -->\n<!-- wp:paragraph -->\n<p>次はもう少し涼しい季節に行きたい。<br>そのときは、デニム屋さんが危ないかもしれません。</p>\n<!-- /wp:paragraph -->'''
 payload={'title':TITLE,'slug':SLUG,'status':'draft','content':body,'categories':[cat],'featured_media':int(m['img_7652']['id'])}
 if tag:payload['tags']=[tag]
 p,_=req('/posts','POST',payload);after={'posts':total('posts'),'pages':total('pages')}
 v,_=req(f"/posts/{p['id']}?context=edit&_fields=id,status,slug,title,content,featured_media,categories,tags,link");raw=v['content']['raw']
 checks={'draft':v['status']=='draft','slug':v['slug']==SLUG,'title':v['title']['raw']==TITLE,'images':all(f"wp-image-{m[s]['id']}" in raw for s in STEMS),'featured':v['featured_media']==int(m['img_7652']['id']),'public_unchanged':before==after}
 if not all(checks.values()):raise RuntimeError('VERIFY_FAILED '+json.dumps(checks,ensure_ascii=False))
 print(json.dumps({'ok':True,'action':'KURASHIKI_BIKAN_DRAFT_CREATED','post_id':p['id'],'preview':p['link'],'media':{s:m[s]['id'] for s in STEMS},'category':cat,'tag':tag,'checks':checks,'public_before':before,'public_after':after},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
# retry-after-img-7654-upload
