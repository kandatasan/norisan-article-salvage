#!/usr/bin/env python3
import base64, hashlib, html, json, os, pathlib, re, time, urllib.parse, urllib.request
BASE='https://tsurikue.com/wp-json/wp/v2'; PAGE_ID=3154; EXPECTED_SHA='9d4f54a8d3f36a837898a38b888c98e2f7fdb1caff140a853f1836820bd58f6e'; MARK='/* tq-outing-spacing:v7:hero-up */'; DOLPHIN='https://tsurikue.com/wp-content/uploads/2026/09/img_2419.jpg'; H1='<h1 class="wp-block-heading">今日は、<br>どこ行く？</h1>'
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode(); OUT=pathlib.Path('/tmp/outing-v7-result.json')
CSS='''\n/* tq-outing-spacing:v7:hero-up */
.page-id-3154 .c-pageTitle{display:none!important}
.page-id-3154 #content{padding-top:24px!important}
@media(max-width:760px){.page-id-3154 #content{padding-top:8px!important}}
'''
def req(path,method='GET',data=None):
 h={'Authorization':AUTH,'Accept':'application/json','User-Agent':'tsurikue-outing-v7/1.0'}; b=None
 if data is not None: b=json.dumps(data,ensure_ascii=False).encode(); h['Content-Type']='application/json; charset=utf-8'
 for i in range(4):
  try:
   r=urllib.request.Request(BASE+path,data=b,headers=h,method=method)
   with urllib.request.urlopen(r,timeout=60) as x:return json.loads(x.read().decode()),x.headers.get('X-WP-Total')
  except Exception:
   if i==3: raise
   time.sleep(2*(i+1))
def page():
 q=urllib.parse.urlencode({'context':'edit','_fields':'id,slug,status,title,content'}); return req(f'/pages/{PAGE_ID}?{q}')[0]
def raw(p): return p['content']['raw']
def sha(s): return hashlib.sha256(s.encode()).hexdigest()
def counts(): return {'posts':int(req('/posts?status=publish&per_page=1&_fields=id')[1]),'pages':int(req('/pages?status=publish&per_page=1&_fields=id')[1])}
bc=counts(); p=page(); s=raw(p)
if sha(s)!=EXPECTED_SHA or p['slug']!='odekake' or p['status']!='publish': raise SystemExit('STALE_OR_IDENTITY')
if MARK in s or s.count(DOLPHIN)!=2 or s.count(H1)!=1: raise SystemExit('SOURCE_REFUSED')
patched=s.replace('</style>',CSS+'\n</style>',1)
req(f'/pages/{PAGE_ID}',method='POST',data={'content':patched})
a=page(); ar=raw(a); ac=counts()
checks={'mark':ar.count(MARK)==1,'dolphin':ar.count(DOLPHIN)==2,'h1':ar.count(H1)==1,'hide_title':'.page-id-3154 .c-pageTitle{display:none!important}' in ar,'desktop_pad':'.page-id-3154 #content{padding-top:24px!important}' in ar,'mobile_pad':'@media(max-width:760px){.page-id-3154 #content{padding-top:8px!important}}' in ar,'counts':ac==bc,'status':a['status']=='publish'}
if not all(checks.values()):
 req(f'/pages/{PAGE_ID}',method='POST',data={'content':s}); raise SystemExit('POSTWRITE_FAILED_ROLLED_BACK '+json.dumps(checks))
rep={'ok':True,'before_sha':EXPECTED_SHA,'after_sha':sha(ar),'checks':checks,'counts':ac}; OUT.write_text(json.dumps(rep,ensure_ascii=False,indent=2)); print(json.dumps(rep,ensure_ascii=False,indent=2))
