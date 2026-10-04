#!/usr/bin/env python3
import base64, json, os, urllib.parse, urllib.request
from pathlib import Path

SITE='https://tsurikue.com'
UA='tsurikue-car-category-20261004/1.0'

def auth():
    u=os.environ['TSURIKUE_WP_USER']; p=os.environ['TSURIKUE_WP_APP_PASSWORD']
    return 'Basic '+base64.b64encode(f'{u}:{p}'.encode()).decode()

def req(path,a,method='GET',payload=None):
    data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode()
    r=urllib.request.Request(SITE+path,data=data,method=method,headers={'Authorization':a,'Accept':'application/json','Content-Type':'application/json; charset=utf-8','User-Agent':UA})
    with urllib.request.urlopen(r,timeout=60) as x:
        return json.loads(x.read().decode()),dict(x.headers)

def cat_by_slug(slug,a,required=True):
    q=urllib.parse.urlencode({'context':'edit','slug':slug,'per_page':100,'_fields':'id,slug,name,parent,count'})
    rows,_=req('/wp-json/wp/v2/categories?'+q,a)
    if len(rows)==1:return rows[0]
    if not rows and not required:return None
    raise RuntimeError(f'category lookup failed slug={slug} count={len(rows)}')

def post(post_id,a):
    q=urllib.parse.urlencode({'context':'edit','_fields':'id,slug,status,title,content,excerpt,featured_media,categories'})
    row,_=req(f'/wp-json/wp/v2/posts/{post_id}?'+q,a); return row

def snap(r):
    return {k:r.get(k) for k in ['id','slug','status','title','content','excerpt','featured_media']}

def count_public(a):
    total=0
    for ep in ['posts','pages']:
        q=urllib.parse.urlencode({'context':'edit','status':'publish','per_page':1,'_fields':'id'})
        _,h=req('/wp-json/wp/v2/'+ep+'?'+q,a); total+=int(h.get('X-WP-Total','0'))
    return total

def main():
    a=auth(); before=count_public(a)
    car=cat_by_slug('car',a)
    if car['name']!='クルマ' or int(car['parent'])!=0: raise RuntimeError('car parent guard mismatch')

    lex=cat_by_slug('lexus-ux',a)
    if lex['name'] not in ['レクサスUX','レクサス']: raise RuntimeError('lexus name guard mismatch')
    if int(lex['parent'])!=int(car['id']): raise RuntimeError('lexus parent guard mismatch')
    if lex['name']=='レクサスUX':
        lex,_=req(f"/wp-json/wp/v2/categories/{lex['id']}",a,'POST',{'name':'レクサス','parent':int(car['id'])})

    fj=cat_by_slug('landcruiser-fj',a)
    if fj['name']!='ランドクルーザーFJ': raise RuntimeError('FJ name guard mismatch')
    if int(fj['parent'])!=int(car['id']):
        fj,_=req(f"/wp-json/wp/v2/categories/{fj['id']}",a,'POST',{'parent':int(car['id'])})

    tanto=cat_by_slug('tanto',a,False)
    if tanto is None:
        tanto,_=req('/wp-json/wp/v2/categories',a,'POST',{'name':'タント','slug':'tanto','parent':int(car['id'])})
    else:
        if tanto['name']!='タント': raise RuntimeError('existing tanto category has unexpected name')
        if int(tanto['parent'])!=int(car['id']):
            tanto,_=req(f"/wp-json/wp/v2/categories/{tanto['id']}",a,'POST',{'parent':int(car['id'])})

    targets=[
      (3964,'tanto-6year-review'),
      (3965,'tanto-6years-review'),
      (3973,'tanto-used-best-year'),
    ]
    changes=[]
    for pid,slug in targets:
        r=post(pid,a)
        if r['slug']!=slug or r['status']!='draft': raise RuntimeError(f'post guard mismatch {pid}')
        s=snap(r); desired=sorted([int(car['id']),int(tanto['id'])]); current=sorted(int(x) for x in r.get('categories',[]))
        if current!=desired:
            req(f'/wp-json/wp/v2/posts/{pid}',a,'POST',{'categories':desired})
        after=post(pid,a)
        if snap(after)!=s: raise RuntimeError(f'non-category fields changed {pid}')
        if sorted(int(x) for x in after.get('categories',[]))!=desired: raise RuntimeError(f'category verify failed {pid}')
        changes.append({'post_id':pid,'slug':slug,'before':current,'after':desired})

    lex2=cat_by_slug('lexus-ux',a); fj2=cat_by_slug('landcruiser-fj',a); tanto2=cat_by_slug('tanto',a)
    if lex2['name']!='レクサス' or int(lex2['parent'])!=int(car['id']): raise RuntimeError('lexus final verify failed')
    if int(fj2['parent'])!=int(car['id']): raise RuntimeError('FJ final verify failed')
    if tanto2['name']!='タント' or int(tanto2['parent'])!=int(car['id']): raise RuntimeError('tanto final verify failed')
    after=count_public(a)
    if before!=after: raise RuntimeError('public post/page count changed')
    report={'public_before':before,'public_after':after,'car':car,'lexus':lex2,'tanto':tanto2,'landcruiser_fj':fj2,'post_changes':changes}
    out=Path('reports/car-child-categories'); out.mkdir(parents=True,exist_ok=True)
    (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'summary.md').write_text(f"# Car child categories\n\n- クルマ ID: **{car['id']}**\n- レクサス: **{lex2['name']}** / slug `{lex2['slug']}` / parent **{lex2['parent']}**\n- タント: **{tanto2['name']}** / slug `{tanto2['slug']}` / parent **{tanto2['parent']}**\n- ランドクルーザーFJ: **{fj2['name']}** / slug `{fj2['slug']}` / parent **{fj2['parent']}**\n- タント下書き分類: **{len(changes)}件**\n- public_before: **{before}**\n- public_after: **{after}**\n",encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
