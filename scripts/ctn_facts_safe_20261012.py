#!/usr/bin/env python3
"""Surgical CTN factual clarity updates. Strict 7-post published SHA guard."""
import os,base64,hashlib,json,urllib.request,urllib.parse,re,sys
from pathlib import Path
TARGETS=[[2222,"ux-resale","54151cb80c6a10510904f6676c8385c09840407b07a3f2e5f451a6b780f6f69d","f157449077971c7d7407519a3d54fba6e2ce402603a7c9d2986b6bcfb38b8c40",[["現在のCTNは最大15社で査定し、やり取りするのは高額査定の上位3社だけ。","CTNは車に合う買取店を絞り、やり取りするのは最大3社だけ。"],["CTNは最大15社で査定し、やり取りするのは<strong>高額査定の上位3社</strong>。","CTNは条件に合う買取店を選び、やり取りは<strong>最大3社</strong>。"]]],[2240,"ux-mitsumori","4d9ea72611aa2e4b7a23ccc1c4f6b037ad8fb39fcca2777e31519a0823f4ed8e","9e004747da93b15ec981521de26203ba19924ff9f0ec5a572ea925a8d42d6a6d",[["CTNは、買取価格の上位3社のみを紹介する仕組みです。","CTNは、条件に合う買取店を最大3社まで紹介する仕組みです。"]]],[2517,"ux-koukai","e7efa7a23616d3d20792ddf213914b67991351606ccd3e48e6fe10f774cbac89","60dfdee41d23b9350d785f2b899397289bf5924cbb9ce0dea1ab7a42386934fe",[["最大15社で査定し、連絡が来るのは<strong>高額査定の上位3社だけ</strong>。","車に合う買取店を選び、やり取りするのは<strong>最大3社だけ</strong>。"]]],[3570,"lexus-ux-emotional-explorer","d54e29cfd2805a22941a2db29a7f7b5fa3cbded42734226d1158975166e5b820","e2fa856b99e1239ac12ac37307dd4a5c7f61ca14a0b85d779be096e11cd27f11",[["最大15社で査定し、やり取りするのは高額査定の上位3社だけ。","車に合う買取店を絞り、やり取りするのは最大3社だけ。"]]],[3601,"lexus-ux250h-used-vs-ux300h","ef35197f7c6f8300bcbd97579803914db91ec5b6a87931c6d7bee85f87afc661","b64f109c73c123ccb79b4bc83a06e13a46a9334c3e2dcc7162f8af2cbc9b9abf",[["最大15社で査定し、高額査定の上位3社とやり取りする仕組みで、","条件に合う買取店を絞り、やり取りは最大3社になる仕組みで、"]]],[3604,"lexus-ux-vs-nx","78bf92eb9cc63d2f57e4e1d1227ab175f14fac6abfd65abc716cfae4b5dd6655","4ae2c1e61aa8a935e439e48c603178703c4d57d958c693a17749121b2eaaa6b6",[["CTNは最大15社の査定から高額査定の上位3社とやり取りする仕組み。","CTNは条件に合う買取店を絞り、やり取りは最大3社に抑えられる仕組み。"]]],[3614,"car-sell-high","237c600e1ff94020298e437a99cc0e0c2eb960b18036a1b3521e07b9ddda4b37","73ffc46ebb16c32ea767c2a47e205a0d3687e7a4aff1534bbdb2c347851777a8",[["現在のCTNは、<strong>最大15社で査定し、高額査定の上位3社だけがユーザーとやり取りする仕組み</strong>です。","CTNは、<strong>車に合う買取店を選び、やり取りするのは最大3社という仕組み</strong>です。"]]]]
BASE='https://tsurikue.com/wp-json/wp/v2/posts'
def digest(t):return hashlib.sha256(t.encode()).hexdigest()
def call(path,auth,payload=None):
 headers={'Authorization':auth,'User-Agent':'tsurikue-ctn-facts/1.0','Accept':'application/json'}
 if payload is not None:headers['Content-Type']='application/json; charset=utf-8'
 data=json.dumps(payload,ensure_ascii=False).encode() if payload is not None else None
 req=urllib.request.Request(BASE+path,data=data,headers=headers,method='POST' if data is not None else 'GET')
 with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)
def get(i,auth):
 q=urllib.parse.urlencode({'context':'edit','_fields':'id,slug,status,title,content,featured_media,categories,author'})
 return call('/'+str(i)+'?'+q,auth)
def transform(s,cfg):
 i,slug,oldsha,newsha,fixes=cfg
 orig=s
 for before,after in fixes:
  if s.count(before)!=1:raise RuntimeError(f'{slug}: expected exact phrase once, found {s.count(before)}')
  s=s.replace(before,after,1)
 if digest(s)!=newsha:raise RuntimeError(f'{slug}: proposed result SHA unexpected')
 for patt in ('<!-- wp:','<!-- /wp:','[blog_parts id=','https://px.a8.net/svt/ejp?a8mat=','<img'):
  if s.count(patt)!=orig.count(patt):raise RuntimeError(f'{slug}: protected structure differs')
 return s
def main(mode):
 user=os.getenv('TSURIKUE_WP_USER');password=os.getenv('TSURIKUE_WP_APP_PASSWORD')
 if not user or not password:raise RuntimeError('WP auth missing')
 auth='Basic '+base64.b64encode((user+':'+password).encode()).decode()
 to_apply=[]
 for cfg in TARGETS:
  row=get(cfg[0],auth)
  if (row['id'],row['slug'],row['status'])!=(cfg[0],cfg[1],'publish'):
   raise RuntimeError(f'{cfg[1]}: identity mismatch')
  s=row['content']['raw']
  if digest(s)!=cfg[2]:raise RuntimeError(f'{cfg[1]}: baseline differs; nothing written')
  new=transform(s,cfg)
  to_apply.append((cfg,row,new))
 print('PREFLIGHT_OK',len(to_apply),flush=True)
 if mode=='check':return
 done=[]
 try:
  for cfg,row,new in to_apply:
   if digest(get(cfg[0],auth)['content']['raw'])!=cfg[2]:raise RuntimeError(f'{cfg[1]}: concurrent edit')
   done.append((cfg,row,new))
   call('/'+str(cfg[0]),auth,{'content':new})
   result=get(cfg[0],auth)
   for field in ('id','slug','status','title','featured_media','categories','author'):
    if result[field]!=row[field]:raise RuntimeError(f'{cfg[1]}: protected WP metadata changed')
   if result['content']['raw']!=new:raise RuntimeError(f'{cfg[1]}: live content mismatch')
   print('UPDATED_VERIFIED',cfg[1],flush=True)
  Path('reports/ctn-facts').mkdir(parents=True,exist_ok=True)
  Path('reports/ctn-facts/result.json').write_text(json.dumps({'status':'SUCCESS','corrected':len(done)},ensure_ascii=False))
 except Exception:
  for cfg,row,new in reversed(done):
   try:
    if digest(get(cfg[0],auth)['content']['raw'])==digest(new):
     call('/'+str(cfg[0]),auth,{'content':row['content']['raw']})
     print('ROLLBACK',cfg[1],flush=True)
   except Exception as e:print('ROLLBACK_FAILED',cfg[1],str(e),flush=True)
  raise
if __name__=='__main__':
 mode=sys.argv[1] if len(sys.argv)>1 else 'check'
 if mode not in ('check','apply'):raise SystemExit(2)
 main(mode)
