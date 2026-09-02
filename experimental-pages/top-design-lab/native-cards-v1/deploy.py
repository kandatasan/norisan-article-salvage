#!/usr/bin/env python3
import base64, hashlib, html, json, os, pathlib, re, time, urllib.parse, urllib.request

BASE='https://tsurikue.com/wp-json/wp/v2'
PAGE_ID=2983
EXPECTED_SHA='542616509f56104830dcefdab2cf53d8e9fa08203b88413a9b0bb43e810d6160'
MARKER='<!-- tsurikue-experimental-page:v1:top-design-lab -->'
GRID_START='<!-- wp:group {"className":"tq4-cat-grid"'
NEXT_SECTION='<!-- wp:group {"align":"full","className":"tq4-section tq4-concept"'
CSS_MARK='/* TQ TOP NATIVE IMAGE CARDS v1 */'
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode()
ROOT=pathlib.Path(__file__).resolve().parent
GRID=(ROOT/'card-grid.html').read_text(encoding='utf-8').strip()
OUT=pathlib.Path(os.environ.get('TQ_NATIVE_RESULT_PATH','/tmp/homepage-native-cards-v1-result.json'))
writes=0

LINKS={
    '/category/sightseeing-leisure/':'/odekake/',
    '/category/gourmet/':'/gourmet-guide/',
    '/category/fishing/':'/fishing-guide/',
    '/category/car/':'/car-guide/',
}
TARGETS=list(LINKS.values())

CSS=r'''
/* TQ TOP NATIVE IMAGE CARDS v1 */
.tq4 .tq4-native-grid{align-items:stretch}
.tq4 .tq4-native-card{
  overflow:hidden;
  min-width:0;
  border:1px solid var(--line);
  border-radius:16px;
  background:#fff;
  box-shadow:0 5px 18px rgba(32,33,31,.035);
  transition:transform .18s ease,box-shadow .18s ease;
}
.tq4 .tq4-native-card:hover{transform:translateY(-3px);box-shadow:0 14px 32px rgba(32,33,31,.08)}
.tq4 .tq4-native-image{margin:0!important;overflow:hidden;background:#ecebe6}
.tq4 .tq4-native-image a{display:block;line-height:0;-webkit-tap-highlight-color:transparent;touch-action:manipulation}
.tq4 .tq4-native-image img{
  display:block;width:100%;height:auto;aspect-ratio:4/3;object-fit:cover;
  transition:transform .28s ease,opacity .08s ease
}
.tq4 .tq4-native-image a:hover img{transform:scale(1.025)}
.tq4 .tq4-native-image a:active img{opacity:.78;transform:scale(.99)}
.tq4 .tq4-native-body{padding:20px 18px 21px}
.tq4 .tq4-native-card .tq4-card-label{color:#77786f!important;text-shadow:none!important}
.tq4 .tq4-native-card h3{margin:0;font-size:25px;letter-spacing:-.025em;color:var(--ink)!important}
.tq4 .tq4-native-card h3 a{color:var(--ink)!important;text-shadow:none!important;text-decoration:none!important}
.tq4 .tq4-native-card .tq4-card-desc{color:#555750!important;text-shadow:none!important}
.tq4 .tq4-native-card .tq4-pill-text{
  background:var(--paper)!important;color:#454741!important;border-color:var(--line)!important;
  text-shadow:none!important;backdrop-filter:none!important;-webkit-backdrop-filter:none!important
}
@media(hover:none){
  .tq4 .tq4-native-card:hover{transform:none;box-shadow:0 5px 18px rgba(32,33,31,.035)}
  .tq4 .tq4-native-image a:hover img{transform:none}
}
@media(max-width:560px){
  .tq4 .tq4-native-card{border-radius:13px}
  .tq4 .tq4-native-image img{aspect-ratio:1/1}
  .tq4 .tq4-native-body{padding:15px 12px 16px}
  .tq4 .tq4-native-card h3{font-size:20px}
  .tq4 .tq4-native-card .tq4-card-desc{font-size:10.5px;line-height:1.6}
}
/* END TQ TOP NATIVE IMAGE CARDS v1 */
'''

def req(path,method='GET',data=None,retries=4):
    global writes
    headers={'Authorization':AUTH,'Accept':'application/json','User-Agent':'tsurikue-home-native-cards-v1/1.0'}
    body=None
    if data is not None:
        body=json.dumps(data,ensure_ascii=False).encode('utf-8'); headers['Content-Type']='application/json; charset=utf-8'
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
    row,_=req(f'/pages/{PAGE_ID}?{q}'); return row

def raw(row): return (row.get('content') or {}).get('raw') or ''
def rendered(row): return (row.get('content') or {}).get('rendered') or ''
def sha(s): return hashlib.sha256(s.encode()).hexdigest()
def title(row):
    x=(row.get('title') or {}).get('raw') or (row.get('title') or {}).get('rendered') or ''
    return html.unescape(re.sub(r'<[^>]+>','',x)).strip()
def public_counts():
    _,p=req('/posts?status=publish&per_page=1&_fields=id'); _,g=req('/pages?status=publish&per_page=1&_fields=id')
    return {'posts':int(p or 0),'pages':int(g or 0)}

def checks(text,rendered_text=''):
    return {
      'marker_once':text.count(MARKER)==1,
      'native_grid_once':text.count('tq4-native-grid')>=1,
      'native_cards_four':text.count('class="wp-block-group tq4-native-card ') == 4,
      'native_image_blocks_four':text.count('linkDestination":"custom"')>=4 and text.count('class="wp-block-image size-large tq4-native-image"')==4,
      'image_links':all(f'<a href="{t}"><img' in text for t in TARGETS),
      'title_links':all(f'<a href="{t}">' in text for t in TARGETS),
      'old_cover_cards_gone':not any(x in text for x in ['tq4-cat--outing','tq4-cat--gourmet','tq4-cat--fishing','tq4-cat--car']),
      'old_category_links_gone':not any(x in text for x in LINKS),
      'native_css_once':text.count(CSS_MARK)==1,
      'no_viewport_hacks':not any(x in text for x in ['100vw','100dvw','50vw','50dvw']),
      'hero_copy':'休日、' in text and 'なにして遊ぶ？' in text,
      'rendered_native':(not rendered_text) or ('tq4-native-card' in rendered_text and all(f'href="{t}"' in rendered_text for t in TARGETS)),
    }

before_counts=public_counts(); before=page(); before_raw=raw(before)
state_before={'id':before.get('id'),'slug':before.get('slug'),'status':before.get('status'),'title':title(before),'sha256':sha(before_raw)}
if before.get('id')!=PAGE_ID or before.get('slug')!='top-design' or before.get('status')!='publish': raise RuntimeError('IDENTITY_REFUSED '+json.dumps(state_before,ensure_ascii=False))
if state_before['sha256']!=EXPECTED_SHA: raise RuntimeError('SHA_REFUSED '+json.dumps({'expected':EXPECTED_SHA,'actual':state_before['sha256']},ensure_ascii=False))
if MARKER not in before_raw or GRID_START not in before_raw or NEXT_SECTION not in before_raw: raise RuntimeError('OLD_STRUCTURE_REFUSED')
if CSS_MARK in before_raw or 'tq4-native-card' in before_raw: raise RuntimeError('NATIVE_ALREADY_PRESENT_UNEXPECTED')
for old in LINKS:
    if old not in before_raw: raise RuntimeError('OLD_LINK_MISSING '+old)

start=before_raw.find(GRID_START); end=before_raw.find(NEXT_SECTION,start)
if start<0 or end<0 or end<=start: raise RuntimeError('GRID_BOUNDARY_REFUSED')
patched=before_raw[:start]+GRID+'\n\n'+before_raw[end:]
for old,new in LINKS.items(): patched=patched.replace(old,new)

root_old='  width:100vw;\n  margin-left:calc(50% - 50vw);'
root_new='  width:100%;\n  max-width:100%;\n  margin-left:0;\n  margin-right:0;'
if root_old in patched: patched=patched.replace(root_old,root_new,1)
patched,_=re.subn(r'\n?/\* MOBILE VIEWPORT CENTER FIX v2 \*/.*?(?=/\* MOBILE FULL-WIDTH FIX v3 \*/)','\n',patched,flags=re.S)
patched,_=re.subn(r'\n?/\* MOBILE FULL-WIDTH FIX v3 \*/.*?/\* END MOBILE FULL-WIDTH FIX v3 \*/\n?','\n',patched,flags=re.S)
if '</style>' not in patched: raise RuntimeError('STYLE_CLOSE_MISSING')
patched=patched.replace('</style>',CSS+'\n</style>',1)
pre=checks(patched)
if not all(pre.values()): raise RuntimeError('PREWRITE_CHECK_FAILED '+json.dumps(pre,ensure_ascii=False))

req(f'/pages/{PAGE_ID}',method='POST',data={'content':patched})
after=page(); after_raw=raw(after); after_rendered=rendered(after)
post=checks(after_raw,after_rendered)
identity_ok=(after.get('id')==before.get('id') and after.get('slug')==before.get('slug') and after.get('status')=='publish' and title(after)==title(before))
if not identity_ok or not all(post.values()):
    req(f'/pages/{PAGE_ID}',method='POST',data={'content':before_raw})
    raise RuntimeError('POSTWRITE_FAILED_ROLLED_BACK '+json.dumps({'identity':identity_ok,'checks':post},ensure_ascii=False))
after_counts=public_counts()
if after_counts!=before_counts:
    req(f'/pages/{PAGE_ID}',method='POST',data={'content':before_raw})
    raise RuntimeError('PUBLIC_COUNTS_CHANGED_ROLLED_BACK')
report={'ok':True,'action':'LIVE_HOMEPAGE_NATIVE_IMAGE_CARDS_V1','before':state_before,'after':{'id':after.get('id'),'slug':after.get('slug'),'status':after.get('status'),'title':title(after),'sha256':sha(after_raw)},'checks':post,'public_before':before_counts,'public_after':after_counts,'wordpress_write_count':writes,'publish_transition_count':0,'delete_count':0}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(report,ensure_ascii=False,indent=2))
