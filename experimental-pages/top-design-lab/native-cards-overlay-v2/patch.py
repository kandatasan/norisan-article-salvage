#!/usr/bin/env python3
import base64, hashlib, html, json, os, pathlib, re, time, urllib.parse, urllib.request

BASE='https://tsurikue.com/wp-json/wp/v2'
PAGE_ID=2983
EXPECTED_SHA='31bef153107d2d2531492ec397b82e6c220d88d1dd06ff35c764fa889b8bc368'
OLD_MARK='/* TQ TOP NATIVE IMAGE CARDS v1 */'
OLD_END='/* END TQ TOP NATIVE IMAGE CARDS v1 */'
NEW_MARK='/* TQ TOP NATIVE IMAGE CARDS OVERLAY v2 */'
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode()
OUT=pathlib.Path(os.environ.get('TQ_OVERLAY_RESULT_PATH','/tmp/homepage-native-overlay-v2-result.json'))
writes=0
TARGETS=['/odekake/','/gourmet-guide/','/fishing-guide/','/car-guide/']

CSS=r'''/* TQ TOP NATIVE IMAGE CARDS OVERLAY v2 */
.tq4 .tq4-native-grid{align-items:stretch}
.tq4 .tq4-native-card{
  position:relative;
  overflow:hidden;
  min-width:0;
  border:1px solid var(--line);
  border-radius:16px;
  background:#1f211f;
  box-shadow:0 5px 18px rgba(32,33,31,.05);
  transition:transform .18s ease,box-shadow .18s ease;
}
.tq4 .tq4-native-card:hover{transform:translateY(-3px);box-shadow:0 14px 32px rgba(32,33,31,.12)}
.tq4 .tq4-native-card:after{
  content:"";
  position:absolute;
  z-index:1;
  inset:28% 0 0;
  pointer-events:none;
  background:linear-gradient(180deg,rgba(16,18,16,0),rgba(16,18,16,.20) 22%,rgba(16,18,16,.84) 100%);
}
.tq4 .tq4-native-image{margin:0!important;overflow:hidden;background:#ecebe6}
.tq4 .tq4-native-image a{
  display:block;
  line-height:0;
  -webkit-tap-highlight-color:transparent;
  touch-action:manipulation;
}
.tq4 .tq4-native-image img{
  display:block;
  width:100%;
  height:auto;
  aspect-ratio:4/5;
  object-fit:cover;
  transition:transform .28s ease,opacity .08s ease;
}
.tq4 .tq4-native-image a:hover img{transform:scale(1.025)}
.tq4 .tq4-native-image a:active img{opacity:.82;transform:scale(.99)}
.tq4 .tq4-native-body{
  position:absolute;
  z-index:2;
  left:0;
  right:0;
  bottom:0;
  padding:24px 19px 20px;
  pointer-events:none;
  background:none!important;
}
.tq4 .tq4-native-card .tq4-card-label{
  margin:0 0 7px;
  color:rgba(255,255,255,.80)!important;
  text-shadow:0 1px 10px rgba(0,0,0,.35)!important;
}
.tq4 .tq4-native-card h3{
  margin:0;
  font-size:27px;
  letter-spacing:-.025em;
  color:#fff!important;
  text-shadow:0 2px 14px rgba(0,0,0,.42)!important;
}
.tq4 .tq4-native-card h3 a{
  color:#fff!important;
  text-decoration:none!important;
  text-shadow:inherit!important;
}
.tq4 .tq4-native-card .tq4-card-desc{
  margin:11px 0 0;
  color:rgba(255,255,255,.88)!important;
  text-shadow:0 1px 9px rgba(0,0,0,.42)!important;
}
.tq4 .tq4-native-card .tq4-pill-text{
  display:inline-block;
  margin:13px 0 0;
  padding:6px 9px;
  border-radius:999px;
  background:rgba(247,245,239,.90)!important;
  color:#30322e!important;
  border:1px solid rgba(255,255,255,.20)!important;
  text-shadow:none!important;
  backdrop-filter:none!important;
  -webkit-backdrop-filter:none!important;
}
@media(hover:none){
  .tq4 .tq4-native-card:hover{transform:none;box-shadow:0 5px 18px rgba(32,33,31,.05)}
  .tq4 .tq4-native-image a:hover img{transform:none}
}
@media(max-width:560px){
  .tq4 .tq4-native-card{border-radius:13px}
  .tq4 .tq4-native-image img{aspect-ratio:4/5}
  .tq4 .tq4-native-body{padding:20px 12px 14px}
  .tq4 .tq4-native-card h3{font-size:21px}
  .tq4 .tq4-native-card .tq4-card-desc{font-size:10.5px;line-height:1.55;margin-top:8px}
  .tq4 .tq4-native-card .tq4-pill-text{font-size:9px;padding:5px 7px;margin-top:10px}
  .tq4 .tq4-native-card:after{inset:20% 0 0}
}
/* END TQ TOP NATIVE IMAGE CARDS OVERLAY v2 */'''

def req(path,method='GET',data=None,retries=4):
    global writes
    headers={'Authorization':AUTH,'Accept':'application/json','User-Agent':'tsurikue-home-native-overlay-v2/1.0'}
    body=None
    if data is not None:
        body=json.dumps(data,ensure_ascii=False).encode('utf-8')
        headers['Content-Type']='application/json; charset=utf-8'
    last=None
    for i in range(retries):
        try:
            q=urllib.request.Request(BASE+path,data=body,headers=headers,method=method)
            with urllib.request.urlopen(q,timeout=60) as r:
                raw=r.read(); total=r.headers.get('X-WP-Total')
                if method not in ('GET','HEAD'): writes+=1
                return json.loads(raw.decode()),total
        except Exception as e:
            last=e
            if i+1==retries: raise
            time.sleep(2*(i+1))
    raise last

def page():
    q=urllib.parse.urlencode({'context':'edit','_fields':'id,slug,status,title,content,link'})
    row,_=req(f'/pages/{PAGE_ID}?{q}')
    return row

def raw(row): return (row.get('content') or {}).get('raw') or ''
def rendered(row): return (row.get('content') or {}).get('rendered') or ''
def sha(s): return hashlib.sha256(s.encode()).hexdigest()
def title(row):
    x=(row.get('title') or {}).get('raw') or (row.get('title') or {}).get('rendered') or ''
    return html.unescape(re.sub(r'<[^>]+>','',x)).strip()
def counts():
    _,p=req('/posts?status=publish&per_page=1&_fields=id')
    _,g=req('/pages?status=publish&per_page=1&_fields=id')
    return {'posts':int(p or 0),'pages':int(g or 0)}

def checks(text,rendered_text=''):
    return {
      'native_cards_four':text.count('class="wp-block-group tq4-native-card ')==4,
      'image_links':all(f'<a href="{t}"><img' in text for t in TARGETS),
      'title_links':all(f'<a href="{t}">' in text for t in TARGETS),
      'overlay_css_once':text.count(NEW_MARK)==1,
      'old_native_css_gone':OLD_MARK not in text,
      'overlay_body_css':'pointer-events:none' in text and '.tq4 .tq4-native-body{' in text,
      'gradient_css':'.tq4 .tq4-native-card:after{' in text,
      'no_old_category_links':not any(x in text for x in ['/category/sightseeing-leisure/','/category/gourmet/','/category/fishing/','/category/car/']),
      'no_viewport_hacks':not any(x in text for x in ['100vw','100dvw','50vw','50dvw']),
      'rendered_overlay':(not rendered_text) or ('tq4-native-card' in rendered_text and all(f'href="{t}"' in rendered_text for t in TARGETS)),
    }

before_counts=counts(); before=page(); before_raw=raw(before)
state={'id':before.get('id'),'slug':before.get('slug'),'status':before.get('status'),'title':title(before),'sha256':sha(before_raw)}
if before.get('id')!=PAGE_ID or before.get('slug')!='top-design' or before.get('status')!='publish':
    raise RuntimeError('IDENTITY_REFUSED '+json.dumps(state,ensure_ascii=False))
if state['sha256']!=EXPECTED_SHA:
    raise RuntimeError('SHA_REFUSED '+json.dumps({'expected':EXPECTED_SHA,'actual':state['sha256']},ensure_ascii=False))
if before_raw.count(OLD_MARK)!=1 or before_raw.count(OLD_END)!=1:
    raise RuntimeError('OLD_CSS_BOUNDARY_REFUSED')
if NEW_MARK in before_raw:
    raise RuntimeError('OVERLAY_ALREADY_PRESENT')

start=before_raw.find(OLD_MARK)
end=before_raw.find(OLD_END,start)+len(OLD_END)
patched=before_raw[:start]+CSS+before_raw[end:]
pre=checks(patched)
if not all(pre.values()):
    raise RuntimeError('PREWRITE_CHECK_FAILED '+json.dumps(pre,ensure_ascii=False))

req(f'/pages/{PAGE_ID}',method='POST',data={'content':patched})
after=page(); after_raw=raw(after); after_rendered=rendered(after)
post=checks(after_raw,after_rendered)
identity_ok=(after.get('id')==before.get('id') and after.get('slug')==before.get('slug') and after.get('status')=='publish' and title(after)==title(before))
if not identity_ok or not all(post.values()):
    req(f'/pages/{PAGE_ID}',method='POST',data={'content':before_raw})
    raise RuntimeError('POSTWRITE_FAILED_ROLLED_BACK '+json.dumps({'identity':identity_ok,'checks':post},ensure_ascii=False))
after_counts=counts()
if after_counts!=before_counts:
    req(f'/pages/{PAGE_ID}',method='POST',data={'content':before_raw})
    raise RuntimeError('PUBLIC_COUNTS_CHANGED_ROLLED_BACK')

report={'ok':True,'action':'LIVE_HOMEPAGE_NATIVE_IMAGE_OVERLAY_V2','before':state,'after':{'id':after.get('id'),'slug':after.get('slug'),'status':after.get('status'),'title':title(after),'sha256':sha(after_raw)},'checks':post,'public_before':before_counts,'public_after':after_counts,'wordpress_write_count':writes,'publish_transition_count':0,'delete_count':0}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
