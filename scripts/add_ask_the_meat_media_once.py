#!/usr/bin/env python3
from __future__ import annotations
import base64,json,os,re,urllib.parse,urllib.request
SITE='https://tsurikue.com'; BASE=SITE+'/wp-json/wp/v2'; SLUG='ask-the-meat'
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode()
H={'Authorization':AUTH,'Accept':'application/json','Content-Type':'application/json; charset=utf-8','User-Agent':'tsurikue-ask-meat-media/1.0'}
def req(path,method='GET',payload=None):
 d=None if payload is None else json.dumps(payload,ensure_ascii=False).encode(); r=urllib.request.Request(BASE+path,data=d,headers=H,method=method)
 with urllib.request.urlopen(r,timeout=60) as x:return json.loads(x.read().decode()),dict(x.headers)
def total(kind):
 _,h=req(f'/{kind}?status=publish&per_page=1&_fields=id');return int(h.get('X-WP-Total','0'))
def post():
 rows,_=req('/posts?'+urllib.parse.urlencode({'slug':SLUG,'context':'edit','status':'publish','per_page':10,'_fields':'id,slug,status,title,content,featured_media,link'}))
 if len(rows)!=1: raise RuntimeError('POST_NOT_UNIQUE')
 return rows[0]
def media_recent():
 # User uploaded the meal photos immediately before this run. Pull recent Sept media and identify the batch by image dimensions/filenames around existing featured image.
 rows=[]
 for page in range(1,4):
  q=urllib.parse.urlencode({'context':'edit','media_type':'image','per_page':100,'page':page,'orderby':'date','order':'desc','after':'2026-09-03T13:00:00','_fields':'id,date,slug,source_url,alt_text,caption,media_details'})
  try:r,_=req('/media?'+q);rows+=r
  except Exception:break
 return rows
def block(m,alt,caption):
 src=m['source_url']; mid=int(m['id'])
 return f'''<!-- wp:image {{"id":{mid},"sizeSlug":"large","linkDestination":"none"}} -->\n<figure class="wp-block-image size-large"><img src="{src}" alt="{alt}" class="wp-image-{mid}"/><figcaption class="wp-element-caption">{caption}</figcaption></figure>\n<!-- /wp:image -->'''
def main():
 p=post(); raw=p['content']['raw']; before={'posts':total('posts'),'pages':total('pages')}
 if '<!-- ask-the-meat-media:v1 -->' in raw:
  print(json.dumps({'ok':True,'action':'ALREADY_APPLIED','post_id':p['id'],'url':p['link']},ensure_ascii=False));return
 rows=media_recent()
 # Select images uploaded after the existing featured image (3291), newest batch first; require at least 8 so unrelated media cannot silently pass.
 candidates=[m for m in rows if int(m['id'])>3291 and str(m.get('source_url','')).lower().endswith(('.jpg','.jpeg','.png','.webp'))]
 candidates=sorted(candidates,key=lambda x:int(x['id']))
 if len(candidates)<8: raise RuntimeError('RECENT_MEAT_MEDIA_NOT_FOUND '+json.dumps([(m['id'],m['source_url']) for m in candidates],ensure_ascii=False))
 # Limit to the contiguous latest upload batch, max 10 images supplied for this article.
 candidates=candidates[-10:]
 ids=[int(m['id']) for m in candidates]
 if any(f'wp-image-{i}' in raw for i in ids): raise RuntimeError('PARTIAL_INSERTION')
 pics=[
 ('アスクザミートの熟成肉コースで提供された霜降り肉','最初から肉の迫力がすごい。今回のコースは仕入れによって内容が変わります。'),
 ('アスクザミートで提供された熟成肉','部位名は覚えていませんが、見た目だけでも期待が高まります。'),
 ('アスクザミートの肉を焼いている様子','親戚6人で焼きながらいただきました。'),
 ('焼いた肉を箸で持ち上げたところ','柔らかさだけではなく、肉そのものの味の濃さが印象的でした。'),
 ('アスクザミートで提供された霜降り肉の盛り合わせ','写真を見返しても、やっぱり旨そうです。'),
 ('焼いた熟成肉をタレにつけているところ','タレで食べても、肉の存在感がしっかりあります。'),
 ('アスクザミートで提供された赤身の肉','霜降り系だけでなく、いろいろな肉を楽しめました。'),
 ('アスクザミートの長皿に盛られた肉','6人で食べても満足感のあるコースでした。'),
 ('アスクザミートで提供された赤身肉','部位を説明できなくても、旨かった記憶はしっかり残っています。'),
 ('アスクザミートのサラダ','肉だけでなくサラダもいただきました。')]
 # Map in upload order; photos were uploaded by the user as the article batch.
 bs=[block(m,*pics[i]) for i,m in enumerate(candidates)]
 marker='<!-- ask-the-meat-media:v1 -->'
 raw=raw.replace('<!-- wp:heading -->\n<h2 class="wp-block-heading">アスクザミートの熟成肉コースを6人で食べてきた</h2>',marker+'\n\n'+bs[0]+'\n\n<!-- wp:heading -->\n<h2 class="wp-block-heading">アスクザミートの熟成肉コースを6人で食べてきた</h2>',1)
 anchors=[
 '<p>親戚6人で集まって食べたのですが、とにかく肉が次々に出てきます。<br>霜降りの肉、赤身っぽい肉、厚みのある肉。</p>\n<!-- /wp:paragraph -->',
 '<p><strong>肉の味が濃い。</strong></p>\n<!-- /wp:paragraph -->',
 '<p>もちろん柔らかい肉もありました。<br>でも、それだけじゃない。</p>\n<!-- /wp:paragraph -->',
 '<p><strong>とにかく旨い。</strong></p>\n<!-- /wp:paragraph -->',
 '<p>焼肉で約5,000円と聞くと安い金額ではありません。<br>ただ、私にとっては<strong>「今まで食べた焼肉の中でも最強クラスかもしれない」</strong>と思うくらい、満足度の高い肉でした。</p>\n<!-- /wp:paragraph -->',
 '<p>家族や親戚で、ちょっといい焼肉を食べたい日に候補にしやすいと思います。</p>\n<!-- /wp:paragraph -->',
 '<p>この記事を書くにあたって写真を見返しても、やっぱり肉の部位は分かりません。</p>\n<!-- /wp:paragraph -->',
 '<p>グルメ記事としては困った話です。</p>\n<!-- /wp:paragraph -->',
 '<p>でも、味の記憶はしっかり残っています。<br><strong>アスクザミートは、私が今まで食べた焼肉の中でも最強クラス。</strong></p>\n<!-- /wp:paragraph -->']
 for a,b in zip(anchors,bs[1:]):
  if raw.count(a)!=1: raise RuntimeError('ANCHOR_MISSING '+a[:50])
  raw=raw.replace(a,a+'\n\n'+b,1)
 req(f"/posts/{p['id']}",'POST',{'content':raw})
 v,_=req(f"/posts/{p['id']}?context=edit&_fields=id,slug,status,content,featured_media,link")
 vr=v['content']['raw']; after={'posts':total('posts'),'pages':total('pages')}
 checks={'marker':marker in vr,'images':all(f'wp-image-{i}' in vr for i in ids),'status':v['status']=='publish','counts':before==after,'featured_unchanged':v['featured_media']==p['featured_media']}
 if not all(checks.values()): raise RuntimeError('VERIFY_FAILED '+json.dumps(checks))
 print(json.dumps({'ok':True,'action':'ASK_THE_MEAT_MEDIA_ADDED','post_id':v['id'],'url':v['link'],'media_ids':ids,'image_count':len(ids),'checks':checks,'public_before':before,'public_after':after},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
