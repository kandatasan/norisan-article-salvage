#!/usr/bin/env python3
from __future__ import annotations
import base64,json,os,re,urllib.parse,urllib.request
SITE='https://tsurikue.com';BASE=SITE+'/wp-json/wp/v2';SLUG='ask-the-meat';MARK='<!-- ask-the-meat-trim:v2 -->'
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode();H={'Authorization':AUTH,'Accept':'application/json','Content-Type':'application/json; charset=utf-8','User-Agent':'tsurikue-ask-meat-trim/1.2'}
def req(path,method='GET',payload=None):
 d=None if payload is None else json.dumps(payload,ensure_ascii=False).encode();r=urllib.request.Request(BASE+path,data=d,headers=H,method=method)
 with urllib.request.urlopen(r,timeout=60) as x:return json.loads(x.read().decode()),dict(x.headers)
def total(k):
 _,h=req(f'/{k}?status=publish&per_page=1&_fields=id');return int(h.get('X-WP-Total','0'))
def post():
 r,_=req('/posts?'+urllib.parse.urlencode({'slug':SLUG,'context':'edit','status':'publish','per_page':10,'_fields':'id,status,content,featured_media,link'}))
 if len(r)!=1:raise RuntimeError('POST_NOT_UNIQUE')
 return r[0]
def para(s):return '<!-- wp:paragraph -->\n<p>'+s+'</p>\n<!-- /wp:paragraph -->'
def heading(s):return '<!-- wp:heading -->\n<h2 class="wp-block-heading">'+s+'</h2>\n<!-- /wp:heading -->'
def main():
 p=post();old=p['content']['raw'];before={'posts':total('posts'),'pages':total('pages')}
 if MARK in old:
  print(json.dumps({'ok':True,'action':'ALREADY_TRIMMED','url':p['link']},ensure_ascii=False));return
 imgs=re.findall(r'<!-- wp:image .*?<!-- /wp:image -->',old,flags=re.S)
 if not imgs:raise RuntimeError('NO_USER_SELECTED_IMAGES')
 table='''<!-- wp:table -->\n<figure class="wp-block-table"><table><tbody><tr><th>店名</th><td>アスク ザ ミート（ask the meat）</td></tr><tr><th>住所</th><td>広島県広島市安佐南区緑井2-8-15</td></tr><tr><th>アクセス</th><td>JR可部線 緑井駅から徒歩約5分</td></tr><tr><th>営業時間</th><td>17:00〜24:00（L.O.23:30）</td></tr><tr><th>定休日</th><td>火曜日</td></tr><tr><th>駐車場</th><td>普通車2台＋軽1台</td></tr><tr><th>今回食べたコース</th><td>熟成肉料理のみコース 4,980円〜（税込）</td></tr><tr><th>予約</th><td>予約可</td></tr></tbody></table></figure>\n<!-- /wp:table -->'''
 note='''<!-- wp:paragraph {"fontSize":"small"} -->\n<p class="has-small-font-size">※店舗情報・コース料金は2026年9月に確認した掲載情報です。営業日・価格・コース内容は変わることがあるため、予約時にお店へ確認してください。</p>\n<!-- /wp:paragraph -->'''
 chunks=[MARK,
 para('広島市安佐南区緑井の「アスク ザ ミート（ask the meat）」へ、親戚6人で行ってきました。<br>今回食べたのは、<strong>熟成肉料理のみコース 4,980円〜</strong>です。'),
 para('先に感想を言うと、<strong>めちゃくちゃ旨い。</strong><br>これまで食べてきた焼肉の中でも、最強クラスかもしれません。'),imgs[0],
 heading('肉の名前は分からん。でも、とにかく旨い'),
 para('肉の部位はほとんど覚えていません。<br>でも、写真を見返すと「これ旨かったなあ」と味の記憶はしっかり残っています。'),
 para('柔らかいだけではなく、なんというか<strong>肉そのものの味が濃い</strong>。<br>噛んだときに「あ、いい肉食べてるわ」と分かる感じでした。')]
 rest=imgs[1:];cut=(len(rest)+1)//2
 chunks+=rest[:cut]
 if rest:chunks.append(para('食レポはこれ以上うまく言えません。<br><strong>とにかく旨かった。</strong>たぶん、この一言がいちばん正確です。'))
 chunks+=rest[cut:]
 chunks += [heading('熟成肉コースは4,980円〜'),
 para('今回利用したコースは<strong>4,980円（税込）〜</strong>。<br>仕入れによって内容が毎回変わるため、予約時に内容や料金を確認するのがおすすめです。'),
 heading('行くなら事前予約がおすすめ'),
 para('かなり人気のあるお店なので、行く日が決まっているなら<strong>事前予約がおすすめ</strong>です。<br>駐車場は店舗前。現在の掲載情報では普通車2台＋軽1台となっています。'),
 heading('アスクザミートの店舗情報'),table,note,
 para('<a href="https://tabelog.com/hiroshima/A3401/A340107/34019810/" target="_blank" rel="nofollow noopener">アスク ザ ミートの掲載情報を確認する</a>'),
 heading('過去最強クラスかもしれない'),
 para('部位名まで詳しく説明できる記事ではありません。<br>それでも、<strong>「また食べたい」と思えるくらい旨かった</strong>ことは間違いありません。'),
 para('安佐南区でちょっといい肉を食べたいときは、候補に入れてみてください。<br>ほかの実食記事は、<a href="https://tsurikue.com/gourmet/">つりくえ！グルメトップ</a>からどうぞ。')]
 new='\n\n'.join(chunks)
 req(f"/posts/{p['id']}",'POST',{'content':new})
 v,_=req(f"/posts/{p['id']}?context=edit&_fields=id,status,content,featured_media,link");raw=v['content']['raw'];after={'posts':total('posts'),'pages':total('pages')}
 checks={'marker':MARK in raw,'images_preserved':len(re.findall(r'<!-- wp:image ',raw))==len(imgs),'published':v['status']=='publish','counts':before==after,'featured':v['featured_media']==p['featured_media'],'core':'肉そのものの味が濃い' in raw and '最強クラス' in raw}
 if not all(checks.values()):raise RuntimeError('VERIFY_FAILED '+json.dumps(checks,ensure_ascii=False))
 print(json.dumps({'ok':True,'action':'ASK_THE_MEAT_TRIMMED','url':v['link'],'kept_images':len(imgs),'before_chars':len(old),'after_chars':len(new),'reduction_pct':round((1-len(new)/len(old))*100,1),'checks':checks},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
