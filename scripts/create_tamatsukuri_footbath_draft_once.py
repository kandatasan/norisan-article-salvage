#!/usr/bin/env python3
from __future__ import annotations
import base64,json,os,re,urllib.parse,urllib.request
SITE='https://tsurikue.com';BASE=SITE+'/wp-json/wp/v2';SLUG='tamatsukuri-onsen-footbath'
TITLE='玉造温泉の足湯は無料！アッッッツイけど気持ちいい｜美肌温泉も持ち帰ってみた'
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode()
H={'Authorization':AUTH,'Accept':'application/json','Content-Type':'application/json; charset=utf-8','User-Agent':'tsurikue-tamatsukuri-footbath/1.0'}
def req(path,method='GET',payload=None):
 d=None if payload is None else json.dumps(payload,ensure_ascii=False).encode();r=urllib.request.Request(BASE+path,data=d,headers=H,method=method)
 with urllib.request.urlopen(r,timeout=60) as x:return json.loads(x.read().decode()),dict(x.headers)
def total(k):
 _,h=req(f'/{k}?status=publish&per_page=1&_fields=id');return int(h.get('X-WP-Total','0'))
def term(kind,slug):
 r,_=req(f'/{kind}?'+urllib.parse.urlencode({'slug':slug,'per_page':10,'_fields':'id,slug,name'}))
 if len(r)!=1:raise RuntimeError(f'TERM_NOT_UNIQUE {kind} {slug} {r}')
 return int(r[0]['id'])
def all_media():
 rows=[]
 for page in range(1,6):
  try:
   r,_=req('/media?'+urllib.parse.urlencode({'context':'edit','media_type':'image','per_page':100,'page':page,'orderby':'date','order':'desc','_fields':'id,date,source_url'}));rows+=r
  except Exception:break
 return rows
def pick(rows,stem):
 m=[x for x in rows if re.search(rf'/{re.escape(stem)}(?:-\d+)?\.(?:jpe?g|png|webp)$',str(x.get('source_url','')),re.I)]
 if not m:raise RuntimeError('MEDIA_NOT_FOUND '+stem)
 return sorted(m,key=lambda x:int(x['id']))[-1]
def img(m,alt):
 mid=int(m['id']);src=m['source_url']
 return f'''<!-- wp:image {{"id":{mid},"sizeSlug":"large","linkDestination":"none"}} -->\n<figure class="wp-block-image size-large"><img src="{src}" alt="{alt}" class="wp-image-{mid}"/></figure>\n<!-- /wp:image -->'''
def p(s):return f'<!-- wp:paragraph -->\n<p>{s}</p>\n<!-- /wp:paragraph -->'
def h2(s):return f'<!-- wp:heading -->\n<h2 class="wp-block-heading">{s}</h2>\n<!-- /wp:heading -->'
def main():
 existing,_=req('/posts?'+urllib.parse.urlencode({'slug':SLUG,'context':'edit','status':'any','per_page':10,'_fields':'id,slug,status,link'}))
 if existing:
  print(json.dumps({'ok':True,'action':'ALREADY_EXISTS','post':existing},ensure_ascii=False,indent=2));return
 before={'posts':total('posts'),'pages':total('pages')};rows=all_media()
 stems=['img_7023','img_7019','img_7013','img_7015','img_7017','img_7018','img_7014']
 ms={s:pick(rows,s) for s in stems}
 category=term('categories','sightseeing-leisure');sanin=term('tags','sanin')
 content='\n\n'.join([
 '<!-- tamatsukuri-footbath:v1 -->',
 p('妻が「<strong>化粧水になる温泉（？）があって、そこでボトルに詰められるらしい</strong>」という情報を聞きつけ、ドライブがてら玉造温泉へ行ってきました。'),
 p('ここ、何度来てものどかで良い感じなんですよね。<br>景色と時間が「のんびりして行ってね！」って言ってくれてるようなね。'),
 img(ms['img_7023'],'玉造温泉の玉湯川沿いの風景'),
 h2('玉造温泉の足湯は無料。現在は3か所'),
 p('玉造温泉の公式サイトでは、現在<strong>無料で楽しめる足湯が3か所</strong>案内されています。<br>玉湯川沿いに2か所、もう1か所は屋根付きの姫神広場です。'),
 p('川沿いをぶらぶら歩いて、そのまま足湯へ寄れるのが玉造温泉のいいところ。<br>雨や日差しが気になる日は、屋根付きの姫神広場も使いやすそうです。'),
 img(ms['img_7014'],'玉造温泉の姫神広場にある屋根付き足湯'),
 h2('まずは「美肌温泉ボトル」をゲット'),
 p('今回の目的のひとつが、妻が聞きつけた温泉水。<br>湯薬師広場では、<strong>玉造温泉の源泉をボトルに入れて持ち帰れます。</strong>'),
 img(ms['img_7019'],'玉造温泉の湯薬師広場で手に入れた美肌温泉ボトル'),
 p('公式では「美肌温泉ボトル」と案内されていて、ボトルを持っていなくても現地で購入できます。<br>持ち帰った温泉水は、5日間を目安に使う案内になっています。'),
 h2('むかーし食べた、あの干し柿を探したのですが…'),
 p('化粧水ボトルを見事ゲットしたところで、ふと思い出したものがありました。<br>むかーし玉造温泉のお土産屋さんで食べた<strong>干し柿</strong>です。'),
 p('これが信じられないほど美味しかったんですよ。<br>干し柿なのに、なんというかチョコレートみたいで、本当に美味しかったんだよー😭'),
 p('せっかくなので「あれ、もう一回食べたい！」とお店へ向かったのですが……残念ながら、そのお店はもうなくなっていました。'),
 h2('抹茶ラテを買って、川沿いの足湯へ'),
 p('そのまま温泉街をぶらっと歩き、お店で抹茶ラテを購入。<br>玉湯川の景色を見ながら飲むだけで、だいぶ旅行気分です。'),
 img(ms['img_7013'],'玉造温泉の温泉街で立ち寄ったお店'),
 img(ms['img_7015'],'玉造温泉の川沿いで飲んだ抹茶ラテ'),
 img(ms['img_7017'],'玉造温泉の足湯と抹茶ラテ'),
 h2('足を入れた瞬間、アッッッツイ！！！'),
 p('さて、抹茶ラテを片手に足湯へ。<br>のんびり浸かろうと足を入れた、その瞬間。'),
 p('<strong>アッッッツイ！！！</strong>'),
 img(ms['img_7018'],'玉造温泉の川沿いの足湯に実際に入っているところ'),
 p('よく見ると、こちら側に近いほど熱い……みたいなことが書いてあります。'),
 p('はっはーん。<br><strong>ここいらはベテラン用なんだな。</strong>'),
 p('そう理解して、少し離れた方へ移動。<br>これでゆっくり入れるはず。'),
 p('<strong>アッッッツイ！！！</strong>'),
 p('<strong>全部熱いじゃないか！ よくも騙した！</strong>'),
 p('まあ、これはこれで気持ちいいんですけどね。<br>公式案内にも、足湯は源泉をそのまま使っているため<strong>熱い日がある</strong>とされています。なるほど。そういうことか。'),
 h2('玉造温泉は、何度来ても「のんびり」が似合う'),
 p('足湯は熱かった。<br>あの干し柿には再会できなかった。<br>でも、温泉街をぶらぶら歩いて、抹茶ラテを飲んで、温泉水まで持って帰った。'),
 p('やっぱり玉造温泉は、何度来てもいいところです。<br><strong>景色と時間が「のんびりして行ってね！」って言ってくれてるような場所。</strong>'),
 p('足湯だけなら無料なので、玉造温泉を散策するときはタオルを1枚持って歩いてみてください。<br>姫神広場では「あしゆのたおる」も販売されています。'),
 p('<small>※足湯の場所や利用条件、美肌温泉ボトルの案内は2026年9月に玉造温泉公式サイトで確認しています。現地状況は変更される場合があります。</small>'),
 p('<a href="https://tamayado.com/about" target="_blank" rel="nofollow noopener">玉造温泉公式サイトで足湯・美肌温泉スポットを確認する</a>'),
 p('ほかのおでかけ記事は、<a href="https://tsurikue.com/odekake/">つりくえ！おでかけトップ</a>からどうぞ。')])
 payload={'title':TITLE,'slug':SLUG,'status':'draft','content':content,'categories':[category],'tags':[sanin],'featured_media':int(ms['img_7018']['id'])}
 created,_=req('/posts','POST',payload);pid=int(created['id'])
 v,_=req(f'/posts/{pid}?context=edit&_fields=id,slug,status,title,content,categories,tags,featured_media,link')
 after={'posts':total('posts'),'pages':total('pages')}
 checks={'slug':v['slug']==SLUG,'draft':v['status']=='draft','title':v['title']['raw']==TITLE,'category':category in v['categories'],'sanin':sanin in v['tags'],'featured':v['featured_media']==int(ms['img_7018']['id']),'marker':'tamatsukuri-footbath:v1' in v['content']['raw'],'images':all(f'wp-image-{int(ms[s]["id"])}' in v['content']['raw'] for s in stems),'public_unchanged':before==after}
 if not all(checks.values()):raise RuntimeError('VERIFY_FAILED '+json.dumps(checks,ensure_ascii=False))
 print(json.dumps({'ok':True,'action':'TAMATSUKURI_FOOTBATH_DRAFT_CREATED','post_id':pid,'slug':SLUG,'status':v['status'],'title':TITLE,'featured_media':v['featured_media'],'media':{s:int(ms[s]['id']) for s in stems},'checks':checks,'public_before':before,'public_after':after},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
