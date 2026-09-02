#!/usr/bin/env python3
import base64, hashlib, json, os, urllib.error, urllib.parse, urllib.request
from pathlib import Path

BASE='https://tsurikue.com/wp-json/wp/v2'
CAR_ID=10
UX_ID=11
LIVE_PAGE_ID=3294
PREVIEW_SLUG='car-guide-v2-preview'
MARKER='tsurikue-category-hub:v2:car-model-first-preview'
TOKENS=('{{UX_CATEGORY_ID}}','{{FJ_CATEGORY_ID}}')
UX_POST_IDS=[2975,2962,2956,2948,2907,2902,2897,2886,2881,2874,2870,2222,2517,2186,2329,2240,2530]
GENERIC_CAR_POST_ID=2575
ALL_STATUSES='publish,draft,pending,private,future'

user=os.environ.get('TSURIKUE_WP_USER'); password=os.environ.get('TSURIKUE_WP_APP_PASSWORD')
if not user or not password: raise SystemExit('Missing WordPress credentials')
token=base64.b64encode(f'{user}:{password}'.encode()).decode()
HEADERS={'Authorization':'Basic '+token,'Accept':'application/json','Content-Type':'application/json; charset=utf-8','User-Agent':'tsurikue-car-v2/1.1'}

def request(method,path,data=None):
    body=None if data is None else json.dumps(data,ensure_ascii=False).encode()
    req=urllib.request.Request(BASE+path,data=body,headers=HEADERS,method=method)
    try:
        with urllib.request.urlopen(req,timeout=50) as r:
            raw=r.read().decode(); return (json.loads(raw) if raw else None),dict(r.headers)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'{method} {path} HTTP {e.code}: '+e.read().decode(errors='replace')[:1200]) from e

def get(path): return request('GET',path)[0]
def post(path,data): return request('POST',path,data)[0]
def query(path,**params): return get(path+'?'+urllib.parse.urlencode(params))
def raw(item): return ((item.get('content') or {}).get('raw') or '')
def digest(text): return hashlib.sha256(text.encode()).hexdigest()

def public_count(kind):
    _,h=request('GET',f'/{kind}?status=publish&per_page=1&_fields=id')
    return int(h.get('X-WP-Total','0'))

def category_by_slug(slug):
    items=query('/categories',slug=slug,context='edit',per_page=20,_fields='id,name,slug,parent,count,link')
    return items[0] if items else None

def ensure_taxonomy():
    car=category_by_slug('car')
    if not car or car['id']!=CAR_ID or car['parent']!=0: raise SystemExit('CAR_PARENT_MISMATCH '+repr(car))
    ux=category_by_slug('lexus-ux')
    if not ux:
        legacy=get(f'/categories/{UX_ID}?context=edit&_fields=id,name,slug,parent,count,link')
        if legacy['parent']!=CAR_ID or legacy['slug']!='car-goods-wash': raise SystemExit('LEGACY_CATEGORY_UNEXPECTED '+repr(legacy))
        ux=post(f'/categories/{UX_ID}',{'name':'レクサスUX','slug':'lexus-ux','parent':CAR_ID,'description':'レクサスUXの購入・使い勝手・本音・売却など、実体験を中心にまとめています。'})
    if ux['id']!=UX_ID or ux['parent']!=CAR_ID: raise SystemExit('LEXUS_UX_CATEGORY_MISMATCH '+repr(ux))
    fj=category_by_slug('landcruiser-fj')
    if not fj:
        fj=post('/categories',{'name':'ランドクルーザーFJ','slug':'landcruiser-fj','parent':CAR_ID,'description':'ランドクルーザーFJの納車後レビュー・使い勝手・遊び方などをまとめるカテゴリです。'})
    if fj['parent']!=CAR_ID: raise SystemExit('FJ_PARENT_MISMATCH '+repr(fj))
    return car,ux,fj

def get_post(pid):
    return get(f'/posts/{pid}?context=edit&_fields=id,slug,status,title,categories,link')

def assign(pid,add=(),remove=()):
    item=get_post(pid); before=sorted(item.get('categories') or [])
    cats=set(before); cats.update(add); cats.difference_update(remove); after=sorted(cats)
    changed=before!=after
    if changed: post(f'/posts/{pid}',{'categories':after})
    check=get_post(pid)
    if sorted(check.get('categories') or [])!=after: raise SystemExit(f'CATEGORY_VERIFY_FAILED {pid}')
    return {'id':pid,'slug':check['slug'],'status':check['status'],'categories':check['categories'],'changed':changed}

def category_posts(cat_id):
    out=[]; page=1
    while True:
        items=query('/posts',categories=cat_id,context='edit',status=ALL_STATUSES,per_page=100,page=page,_fields='id,slug,status,categories')
        out.extend(items)
        if len(items)<100: return out
        page+=1

def make_content(ux_id,fj_id):
    text=Path(__file__).with_name('content.template.html').read_text(encoding='utf-8')
    text=text.replace(TOKENS[0],str(ux_id)).replace(TOKENS[1],str(fj_id))
    leftovers=[t for t in TOKENS if t in text]
    if leftovers: raise SystemExit('UNRESOLVED_TEMPLATE_PLACEHOLDERS '+repr(leftovers))
    return text

def preview_page():
    items=query('/pages',slug=PREVIEW_SLUG,context='edit',status='publish,draft,pending,private,future,trash',per_page=20,_fields='id,slug,status,title,content,link')
    if len(items)>1: raise SystemExit('PREVIEW_NOT_UNIQUE '+repr([(p['id'],p['status']) for p in items]))
    return items[0] if items else None

def write_preview(content):
    title='クルマ｜レクサスUX・ランドクルーザーFJ'
    p=preview_page()
    if p:
        if p['status']!='draft': raise SystemExit('PREVIEW_NOT_DRAFT '+repr((p['id'],p['status'])))
        same=MARKER in raw(p) and raw(p)==content and p['title']['raw']==title
        if same: return p,False
        return post(f"/pages/{p['id']}",{'title':title,'content':content,'status':'draft'}),True
    return post('/pages',{'title':title,'slug':PREVIEW_SLUG,'content':content,'status':'draft'}),True

def verify_preview(pid,ux_id,fj_id):
    p=get(f'/pages/{pid}?context=edit&_fields=id,slug,status,title,content,link')
    text=raw(p)
    checks={
        'draft':p['status']=='draft','slug':p['slug']==PREVIEW_SLUG,'marker':MARKER in text,
        'one_html':text.count('<!-- wp:html -->')==1,'two_details':text.count('<!-- wp:details')==2,
        'two_model_lists':text.count('<!-- wp:latest-posts')==2,
        'swell_latest':'<!-- wp:loos/post-list' in text and '"catID":"10"' in text,
        'ux_filter':f'"categories":[{ux_id}]' in text,'fj_filter':f'"categories":[{fj_id}]' in text,
        'placeholders_gone':all(t not in text for t in TOKENS),'hero':'IMG_2012.jpeg' in text,
        'copy':'どのクルマを見る？' in text and 'レクサスUX' in text and 'ランドクルーザーFJ' in text,
    }
    if not all(checks.values()): raise SystemExit('PREVIEW_VERIFY_FAILED '+json.dumps(checks,ensure_ascii=False))
    return p,checks

def main():
    counts_before={'posts':public_count('posts'),'pages':public_count('pages')}
    live_before=get(f'/pages/{LIVE_PAGE_ID}?context=edit&_fields=id,slug,status,title,content,link')
    if live_before['slug']!='car-guide' or live_before['status']!='publish': raise SystemExit('LIVE_CAR_PAGE_UNEXPECTED')
    live_sha=digest(raw(live_before))

    car,ux,fj=ensure_taxonomy()
    migrations=[assign(pid,add=(CAR_ID,ux['id'])) for pid in UX_POST_IDS]
    migrations.append(assign(GENERIC_CAR_POST_ID,add=(CAR_ID,),remove=(ux['id'],)))

    actual={p['id'] for p in category_posts(ux['id'])}; expected=set(UX_POST_IDS)
    if actual!=expected: raise SystemExit('UX_MEMBERSHIP_MISMATCH '+repr({'unexpected':sorted(actual-expected),'missing':sorted(expected-actual)}))
    if category_by_slug('car-goods-wash') is not None: raise SystemExit('LEGACY_WASH_SLUG_REMAINS')

    content=make_content(ux['id'],fj['id'])
    p,written=write_preview(content)
    preview,checks=verify_preview(p['id'],ux['id'],fj['id'])

    live_after=get(f'/pages/{LIVE_PAGE_ID}?context=edit&_fields=id,slug,status,title,content,link')
    if live_after['status']!='publish' or digest(raw(live_after))!=live_sha: raise SystemExit('LIVE_CAR_PAGE_CHANGED')
    counts_after={'posts':public_count('posts'),'pages':public_count('pages')}
    if counts_before!=counts_after: raise SystemExit('PUBLIC_COUNTS_CHANGED '+repr((counts_before,counts_after)))

    ux_after=get(f"/categories/{ux['id']}?context=edit&_fields=id,name,slug,parent,count,link")
    fj_after=get(f"/categories/{fj['id']}?context=edit&_fields=id,name,slug,parent,count,link")
    result={'ok':True,'public_counts_before':counts_before,'public_counts_after':counts_after,
      'live_car_page':{'id':LIVE_PAGE_ID,'status':'publish','sha_unchanged':True},
      'taxonomy':{'car':{'id':car['id'],'slug':car['slug']},'lexus_ux':ux_after,'landcruiser_fj':fj_after,'legacy_wash_slug_exists':False},
      'migration_writes':sum(1 for m in migrations if m['changed']),'migration_results':migrations,
      'preview':{'id':preview['id'],'slug':preview['slug'],'status':preview['status'],'written':written,'checks':checks}}
    print('CAR_MODEL_FIRST_V2_AUDIT '+json.dumps(result,ensure_ascii=False))

if __name__=='__main__': main()
