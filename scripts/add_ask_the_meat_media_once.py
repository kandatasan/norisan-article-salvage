#!/usr/bin/env python3
from __future__ import annotations
import base64,json,os,urllib.parse,urllib.request
SITE='https://tsurikue.com'; BASE=SITE+'/wp-json/wp/v2'; SLUG='ask-the-meat'
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode()
H={'Authorization':AUTH,'Accept':'application/json','Content-Type':'application/json; charset=utf-8','User-Agent':'tsurikue-ask-meat-media/1.1'}
def req(path,method='GET',payload=None):
 d=None if payload is None else json.dumps(payload,ensure_ascii=False).encode(); r=urllib.request.Request(BASE+path,data=d,headers=H,method=method)
 with urllib.request.urlopen(r,timeout=60) as x:return json.loads(x.read().decode()),dict(x.headers)
def total(k):
 _,h=req(f'/{k}?status=publish&per_page=1&_fields=id');return int(h.get('X-WP-Total','0'))
def post():
 r,_=req('/posts?'+urllib.parse.urlencode({'slug':SLUG,'context':'edit','status':'publish','per_page':10,'_fields':'id,slug,status,content,featured_media,link'}))
 if len(r)!=1:raise RuntimeError('POST_NOT_UNIQUE')
 return r[0]
def recent():
 rows=[]
 for page in range(1,4):
  try:
   r,_=req('/media?'+urllib.parse.urlencode({'context':'edit','media_type':'image','per_page':100,'page':page,'orderby':'date','order':'desc','after':'2026-09-03T13:00:00','_fields':'id,date,source_url'}));rows+=r
  except Exception:break
 return rows
def block(m,n):
 mid=int(m['id']);src=m['source_url']; alt=f'アスクザミートで食べた熟成肉コースの写真{n}'
 return f'''<!-- wp:image {{"id":{mid},"sizeSlug":"large","linkDestination":"none"}} -->\n<figure class="wp-block-image size-large"><img src="{src}" alt="{alt}" class="wp-image-{mid}"/><figcaption class="wp-element-caption">アスクザミートで食べた熟成肉コース。部位名は分かりませんが、とにかく旨かったです。</figcaption></figure>\n<!-- /wp:image -->'''
def main():
 p=post();raw=p['content']['raw'];before={'posts':total('posts'),'pages':total('pages')};marker='<!-- ask-the-meat-media:v2-neutral -->'
 if marker in raw:
  print(json.dumps({'ok':True,'action':'ALREADY_APPLIED','url':p['link']},ensure_ascii=False));return
 rows=recent();c=sorted([m for m in rows if int(m['id'])>3291 and str(m.get('source_url','')).lower().endswith(('.jpg','.jpeg','.png','.webp'))],key=lambda x:int(x['id']))[-10:]
 if len(c)<8:raise RuntimeError('RECENT_MEDIA_NOT_FOUND '+json.dumps([(x['id'],x['source_url']) for x in c],ensure_ascii=False))
 ids=[int(x['id']) for x in c]
 if any(f'wp-image-{i}' in raw for i in ids):raise RuntimeError('PARTIAL_INSERTION')
 bs=[block(m,i+1) for i,m in enumerate(c)]
 h='<h2 class="wp-block-heading">アスクザミートの熟成肉コースを6人で食べてきた</h2>'
 if raw.count(h)!=1:raise RuntimeError('HEADING_ANCHOR')
 raw=raw.replace(h,marker+'\n\n'+bs[0]+'\n\n'+h,1)
 anchors=[
 '<p>親戚6人で集まって食べたのですが、とにかく肉が次々に出てきます。<br>霜降りの肉、赤身っぽい肉、厚みのある肉。</p>',
 '<p><strong>肉の味が濃い。</strong></p>',
 '<p>もちろん柔らかい肉もありました。<br>でも、それだけじゃない。</p>',
 '<p><strong>とにかく旨い。</strong></p>',
 '<p>焼肉で約5,000円と聞くと安い金額ではありません。<br>ただ、私にとっては<strong>「今まで食べた焼肉の中でも最強クラスかもしれない」</strong>と思うくらい、満足度の高い肉でした。</p>',
 '<p>家族や親戚で、ちょっといい焼肉を食べたい日に候補にしやすいと思います。</p>',
 '<p>この記事を書くにあたって写真を見返しても、やっぱり肉の部位は分かりません。</p>',
 '<p>グルメ記事としては困った話です。</p>',
 '<p>でも、味の記憶はしっかり残っています。<br><strong>アスクザミートは、私が今まで食べた焼肉の中でも最強クラス。</strong></p>']
 for a,b in zip(anchors,bs[1:]):
  if raw.count(a)!=1:raise RuntimeError('ANCHOR_MISSING '+a[:35])
  raw=raw.replace(a,a+'\n\n'+b,1)
 req(f"/posts/{p['id']}",'POST',{'content':raw})
 v,_=req(f"/posts/{p['id']}?context=edit&_fields=id,status,content,featured_media,link");vr=v['content']['raw'];after={'posts':total('posts'),'pages':total('pages')}
 checks={'all_images':all(f'wp-image-{i}' in vr for i in ids),'no_salad_caption':'サラダ' not in vr,'neutral_caption':vr.count('部位名は分かりませんが、とにかく旨かったです。')==len(ids),'published':v['status']=='publish','counts_unchanged':before==after,'featured_unchanged':v['featured_media']==p['featured_media']}
 if not all(checks.values()):raise RuntimeError('VERIFY_FAILED '+json.dumps(checks,ensure_ascii=False))
 print(json.dumps({'ok':True,'action':'ASK_THE_MEAT_NEUTRAL_MEDIA_ADDED','post_id':v['id'],'url':v['link'],'media_ids':ids,'image_count':len(ids),'checks':checks},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
