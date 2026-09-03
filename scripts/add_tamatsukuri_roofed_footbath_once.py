#!/usr/bin/env python3
from __future__ import annotations
import base64,json,os,re,urllib.parse,urllib.request
SITE='https://tsurikue.com';BASE=SITE+'/wp-json/wp/v2';POST_ID=3483;SLUG='tamatsukuri-onsen-footbath';STEM='img_7014';MARK='<!-- tamatsukuri-roofed-footbath:v1 -->'
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode();H={'Authorization':AUTH,'Accept':'application/json','Content-Type':'application/json; charset=utf-8','User-Agent':'tsurikue-tamatsukuri-roofed-footbath/1.0'}
def req(path,method='GET',payload=None):
 d=None if payload is None else json.dumps(payload,ensure_ascii=False).encode();r=urllib.request.Request(BASE+path,data=d,headers=H,method=method)
 with urllib.request.urlopen(r,timeout=60) as x:return json.loads(x.read().decode()),dict(x.headers)
def total(k):
 _,h=req(f'/{k}?status=publish&per_page=1&_fields=id');return int(h.get('X-WP-Total','0'))
def find_media():
 rows=[]
 for page in range(1,6):
  try:
   r,_=req('/media?'+urllib.parse.urlencode({'context':'edit','media_type':'image','per_page':100,'page':page,'orderby':'date','order':'desc','_fields':'id,source_url'}));rows+=r
  except Exception:break
 m=[x for x in rows if re.search(rf'/{STEM}(?:-\d+)?\.(?:jpe?g|png|webp)$',str(x.get('source_url','')),re.I)]
 if not m:raise RuntimeError('MEDIA_NOT_FOUND '+STEM)
 return sorted(m,key=lambda x:int(x['id']))[-1]
def main():
 p,_=req(f'/posts/{POST_ID}?context=edit&_fields=id,slug,status,title,content,featured_media,link');raw=p['content']['raw'];before={'posts':total('posts'),'pages':total('pages')}
 if p['slug']!=SLUG or p['status']!='draft':raise RuntimeError('TARGET_MISMATCH '+json.dumps({'slug':p['slug'],'status':p['status']},ensure_ascii=False))
 if MARK in raw:
  print(json.dumps({'ok':True,'action':'ALREADY_APPLIED','post_id':POST_ID,'url':p['link']},ensure_ascii=False));return
 m=find_media();mid=int(m['id']);src=m['source_url']
 if f'wp-image-{mid}' in raw:raise RuntimeError('IMAGE_ALREADY_PRESENT_WITHOUT_MARK')
 anchor='<!-- wp:paragraph -->\n<p>川沿いをぶらぶら歩いて、そのまま足湯へ寄れるのが玉造温泉のいいところ。<br>雨や日差しが気になる日は、屋根付きの姫神広場も使いやすそうです。</p>\n<!-- /wp:paragraph -->'
 if raw.count(anchor)!=1:raise RuntimeError('ANCHOR_MISSING')
 block=f'''{MARK}\n<!-- wp:image {{"id":{mid},"sizeSlug":"large","linkDestination":"none"}} -->\n<figure class="wp-block-image size-large"><img src="{src}" alt="玉造温泉の姫神広場にある屋根付き足湯" class="wp-image-{mid}"/></figure>\n<!-- /wp:image -->'''
 new=raw.replace(anchor,anchor+'\n\n'+block,1)
 req(f'/posts/{POST_ID}','POST',{'content':new})
 v,_=req(f'/posts/{POST_ID}?context=edit&_fields=id,slug,status,content,featured_media,link');after={'posts':total('posts'),'pages':total('pages')};vr=v['content']['raw']
 checks={'slug':v['slug']==SLUG,'draft':v['status']=='draft','image':f'wp-image-{mid}' in vr,'marker':MARK in vr,'featured_unchanged':v['featured_media']==p['featured_media'],'public_unchanged':before==after}
 if not all(checks.values()):raise RuntimeError('VERIFY_FAILED '+json.dumps(checks,ensure_ascii=False))
 print(json.dumps({'ok':True,'action':'TAMATSUKURI_ROOFED_FOOTBATH_ADDED','post_id':POST_ID,'media_id':mid,'media_url':src,'checks':checks,'public_before':before,'public_after':after},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
# trigger: 2026-09-04
