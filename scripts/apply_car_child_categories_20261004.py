#!/usr/bin/env python3
import base64, json, os, urllib.parse, urllib.request
from pathlib import Path
SITE='https://tsurikue.com'; UA='tsurikue-car-category-20261004/1.1'
def auth():
 u=os.environ['TSURIKUE_WP_USER']; p=os.environ['TSURIKUE_WP_APP_PASSWORD']; return 'Basic '+base64.b64encode(f'{u}:{p}'.encode()).decode()
def req(path,a,method='GET',payload=None):
 data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode(); r=urllib.request.Request(SITE+path,data=data,method=method,headers={'Authorization':a,'Accept':'application/json','Content-Type':'application/json; charset=utf-8','User-Agent':UA})
 with urllib.request.urlopen(r,timeout=60) as x:return json.loads(x.read().decode()),dict(x.headers)
def cat(slug,a,required=True):
 q=urllib.parse.urlencode({'context':'edit','slug':slug,'per_page':100,'_fields':'id,slug,name,parent,count'}); rows,_=req('/wp-json/wp/v2/categories?'+q,a)
 if len(rows)==1:return rows[0]
 if not rows and not required:return None
 raise RuntimeError(f'category lookup failed {slug}: {len(rows)}')
def post(pid,a):
 q=urllib.parse.urlencode({'context':'edit','_fields':'id,slug,status,title,content,excerpt,featured_media,categories'}); return req(f'/wp-json/wp/v2/posts/{pid}?'+q,a)[0]
def snap(r):return {k:r.get(k) for k in ['id','slug','status','title','content','excerpt','featured_media']}
def pub(a):
 n=0
 for ep in ['posts','pages']:
  q=urllib.parse.urlencode({'context':'edit','status':'publish','per_page':1,'_fields':'id'}); _,h=req('/wp-json/wp/v2/'+ep+'?'+q,a); n+=int(h.get('X-WP-Total','0'))
 return n
def title(r):
 v=r.get('title') or {}; return (v.get('raw') or v.get('rendered') or '') if isinstance(v,dict) else str(v)
def main():
 a=auth(); before=pub(a); car=cat('car',a)
 if car['name']!='クルマ' or int(car['parent'])!=0:raise RuntimeError('car guard')
 lex=cat('lexus-ux',a)
 if lex['name'] not in ['レクサスUX','レクサス'] or int(lex['parent'])!=int(car['id']):raise RuntimeError('lexus guard')
 if lex['name']=='レクサスUX':req(f"/wp-json/wp/v2/categories/{lex['id']}",a,'POST',{'name':'レクサス','parent':int(car['id'])})
 fj=cat('landcruiser-fj',a)
 if fj['name']!='ランドクルーザーFJ':raise RuntimeError('FJ guard')
 if int(fj['parent'])!=int(car['id']):req(f"/wp-json/wp/v2/categories/{fj['id']}",a,'POST',{'parent':int(car['id'])})
 tanto=cat('tanto',a,False)
 if tanto is None:tanto,_=req('/wp-json/wp/v2/categories',a,'POST',{'name':'タント','slug':'tanto','parent':int(car['id'])})
 elif tanto['name']!='タント':raise RuntimeError('tanto name guard')
 elif int(tanto['parent'])!=int(car['id']):req(f"/wp-json/wp/v2/categories/{tanto['id']}",a,'POST',{'parent':int(car['id'])})
 tanto=cat('tanto',a); changes=[]
 for pid in [3964,3965,3973]:
  r=post(pid,a)
  if r['status']!='draft' or 'タント' not in title(r):raise RuntimeError(f'Tanto draft guard mismatch {pid}: status={r.get("status")} title={title(r)!r}')
  s=snap(r); desired=sorted([int(car['id']),int(tanto['id'])]); current=sorted(int(x) for x in r.get('categories',[]))
  if current!=desired:req(f'/wp-json/wp/v2/posts/{pid}',a,'POST',{'categories':desired})
  z=post(pid,a)
  if snap(z)!=s or sorted(int(x) for x in z.get('categories',[]))!=desired:raise RuntimeError(f'post verify failed {pid}')
  changes.append({'post_id':pid,'slug':r['slug'],'before':current,'after':desired})
 lex=cat('lexus-ux',a); fj=cat('landcruiser-fj',a); tanto=cat('tanto',a)
 if lex['name']!='レクサス' or int(lex['parent'])!=int(car['id']):raise RuntimeError('lexus final')
 if int(fj['parent'])!=int(car['id']):raise RuntimeError('FJ final')
 if tanto['name']!='タント' or int(tanto['parent'])!=int(car['id']):raise RuntimeError('tanto final')
 after=pub(a)
 if before!=after:raise RuntimeError('public count changed')
 report={'public_before':before,'public_after':after,'car':car,'lexus':lex,'tanto':tanto,'landcruiser_fj':fj,'post_changes':changes}; out=Path('reports/car-child-categories'); out.mkdir(parents=True,exist_ok=True); (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); (out/'summary.md').write_text(f"# Car child categories\n\n- レクサス: **{lex['name']}** / slug `{lex['slug']}` / parent **{lex['parent']}**\n- タント: **{tanto['name']}** / slug `{tanto['slug']}` / parent **{tanto['parent']}**\n- ランドクルーザーFJ: **{fj['name']}** / slug `{fj['slug']}` / parent **{fj['parent']}**\n- タント下書き分類: **3件**\n- public_before: **{before}**\n- public_after: **{after}**\n",encoding='utf-8'); print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
