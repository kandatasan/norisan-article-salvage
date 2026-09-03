#!/usr/bin/env python3
from __future__ import annotations
import base64, html, json, os, re, urllib.parse, urllib.request

SITE='https://tsurikue.com'; BASE=SITE+'/wp-json/wp/v2'; UA='tsurikue-gourmet-tag-organizer/1.0'
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode()
# Keep the first pass intentionally broad. Multi-tagging is allowed when a post clearly spans two food intents.
GENRES={
 'ramen':('ラーメン','ramen',('ラーメン','らーめん','中華そば','つけ麺','担々麺','担担麺')),
 'seafood':('海鮮・魚','seafood',('海鮮','刺身','寿司','鮨','魚','かに','カニ','蟹','牡蠣','かき','マグロ','まぐろ','鯛','うなぎ','鰻','漁港','市場')),
 'meat':('肉・がっつり','meat-hearty',('焼肉','ステーキ','肉','ハンバーグ','とんかつ','トンカツ','唐揚げ','からあげ','チキン','牛','豚','鶏')),
 'local':('ご当地グルメ','local-gourmet',('ご当地','名物','名産','郷土','ソウルフード','B級グルメ','b級グルメ')),
 'cafe':('カフェ・甘いもの','cafe-sweets',('カフェ','喫茶','コーヒー','珈琲','スイーツ','ケーキ','パフェ','プリン','アイス','ジェラート','ソフトクリーム','パンケーキ','クレープ','和菓子','甘味')),
}

def req(path,method='GET',payload=None):
 h={'Authorization':AUTH,'Accept':'application/json','User-Agent':UA}; data=None
 if payload is not None: data=json.dumps(payload,ensure_ascii=False).encode(); h['Content-Type']='application/json; charset=utf-8'
 r=urllib.request.Request(BASE+path,data=data,headers=h,method=method)
 with urllib.request.urlopen(r,timeout=60) as x:return json.loads(x.read().decode()),dict(x.headers)
def clean(v):
 if isinstance(v,dict):v=v.get('raw') or v.get('rendered') or ''
 return html.unescape(re.sub(r'<[^>]+>',' ',v or '')).strip()
def allrows(ep,params=None):
 out=[]; p=1; params=dict(params or {})
 while True:
  q=dict(params,per_page=100,page=p); rows,h=req('/'+ep+'?'+urllib.parse.urlencode(q)); out+=rows
  if p>=int(h.get('X-WP-TotalPages','1')):return out
  p+=1
def totals():
 o={}
 for ep in ('posts','pages'):
  _,h=req(f'/{ep}?status=publish&per_page=1&_fields=id');o[ep]=int(h.get('X-WP-Total','0'))
 return o
def exact_cat(cats):
 # Prefer the known gourmet slug; fall back to exact Japanese category name.
 m=[x for x in cats if x.get('slug') in ('gourmet','food') or clean(x.get('name'))=='グルメ']
 if len(m)!=1: raise RuntimeError('GOURMET_CATEGORY_NOT_UNIQUE '+json.dumps([(x.get('id'),x.get('name'),x.get('slug')) for x in m],ensure_ascii=False))
 return m[0]
def descendants(cats,root):
 ids={int(root)}; changed=True
 while changed:
  changed=False
  for c in cats:
   if int(c.get('parent') or 0) in ids and int(c['id']) not in ids:ids.add(int(c['id']));changed=True
 return ids
def get_or_create_tag(tags,name,slug):
 exact=[t for t in tags if clean(t.get('name'))==name]
 if exact:return exact[0],False
 slughit=[t for t in tags if t.get('slug')==slug]
 if slughit:raise RuntimeError('TAG_SLUG_COLLISION '+slug)
 t,_=req('/tags',method='POST',payload={'name':name,'slug':slug});tags.append(t);return t,True
def classify(post):
 text=' '.join([clean(post.get('title')),clean(post.get('excerpt')),clean(post.get('content'))])
 hits=[]
 for key,(_,_,words) in GENRES.items():
  if any(w.lower() in text.lower() for w in words):hits.append(key)
 return hits

def main():
 before=totals(); cats=allrows('categories',{'context':'edit','hide_empty':'false','_fields':'id,name,slug,parent,count'}); tags=allrows('tags',{'context':'edit','hide_empty':'false','_fields':'id,name,slug,count'}); root=exact_cat(cats); catids=descendants(cats,root['id'])
 posts=allrows('posts',{'context':'edit','status':'publish','categories':','.join(map(str,sorted(catids))),'_fields':'id,slug,link,title,excerpt,content,tags,categories'})
 if not posts:raise RuntimeError('NO_GOURMET_POSTS')
 created=[]; genre_tags={}
 for key,(name,slug,_) in GENRES.items():
  t,new=get_or_create_tag(tags,name,slug);genre_tags[key]=t
  if new:created.append({'id':t['id'],'name':name,'slug':t['slug']})
 updates=[]; unclassified=[]; assignments={k:[] for k in GENRES}
 for p in posts:
  hits=classify(p)
  if not hits:unclassified.append({'id':p['id'],'slug':p['slug'],'title':clean(p['title']),'link':p['link']});continue
  old=list(map(int,p.get('tags') or [])); add=[int(genre_tags[k]['id']) for k in hits]; new=old+[x for x in add if x not in old]
  for k in hits:assignments[k].append(p['slug'])
  if new!=old:
   req(f"/posts/{p['id']}",method='POST',payload={'tags':new});updates.append({'id':p['id'],'slug':p['slug'],'added':[genre_tags[k]['name'] for k in hits if int(genre_tags[k]['id']) not in old]})
 after=totals()
 if after!=before:raise RuntimeError(f'PUBLIC_TOTALS_CHANGED {before}->{after}')
 # Verify every write persisted and no existing tag was removed.
 verify={p['id']:p for p in allrows('posts',{'context':'edit','status':'publish','categories':','.join(map(str,sorted(catids))),'_fields':'id,slug,tags'})}
 for u in updates:
  v=verify[u['id']]; expected=[genre_tags[k]['id'] for k in classify(next(p for p in posts if p['id']==u['id']))]
  if not all(int(x) in list(map(int,v.get('tags') or [])) for x in expected):raise RuntimeError('VERIFY_FAILED '+u['slug'])
 report={'ok':True,'action':'GOURMET_TAGS_ORGANIZED','gourmet_category':{'id':root['id'],'name':clean(root['name']),'slug':root['slug'],'category_ids':sorted(catids)},'published_gourmet_posts':len(posts),'existing_tags_before':len(tags)-len(created),'created_tags':created,'genre_tags':{k:{'id':v['id'],'name':clean(v['name']),'slug':v['slug']} for k,v in genre_tags.items()},'assignments':assignments,'updated_posts':updates,'unclassified':unclassified,'public_before':before,'public_after':after}
 print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
