#!/usr/bin/env python3
import base64
import hashlib
import html
import json
import os
import pathlib
import re
import time
import urllib.parse
import urllib.request

BASE='https://tsurikue.com/wp-json/wp/v2'
PAGE_ID=2983
EXPECTED_SHA='542616509f56104830dcefdab2cf53d8e9fa08203b88413a9b0bb43e810d6160'
MARKER='<!-- tsurikue-experimental-page:v1:top-design-lab -->'
PATCH_START='/* TQ TOP CARD RESPONSE + HUB LINKS v2 */'
PATCH_END='/* END TQ TOP CARD RESPONSE + HUB LINKS v2 */'
STYLE_CLOSE='</style>'
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode()
OUT=pathlib.Path(os.environ.get('TQ_HOME_RESULT_PATH','/tmp/homepage-complete-v2-result.json'))
writes=0

LINKS={
    '/category/sightseeing-leisure/':'/odekake/',
    '/category/gourmet/':'/gourmet-guide/',
    '/category/fishing/':'/fishing-guide/',
    '/category/car/':'/car-guide/',
}

CSS=r'''
/* TQ TOP CARD RESPONSE + HUB LINKS v2 */
.tq4 .tq4-cat{
  position:relative!important;
  overflow:hidden!important;
  isolation:isolate;
  cursor:pointer;
  touch-action:manipulation;
  -webkit-tap-highlight-color:transparent;
}
.tq4 .tq4-cat h3 a{
  position:static!important;
  -webkit-tap-highlight-color:transparent;
}
.tq4 .tq4-cat h3 a::after{
  content:"";
  position:absolute;
  inset:-999px;
  z-index:6;
  background:transparent;
  transition:background-color .12s ease;
}
.tq4 .tq4-cat h3 a:active::after{background:rgba(255,255,255,.13)}
@supports selector(.tq4-cat:has(h3 a:active)){
  .tq4 .tq4-cat:has(h3 a:active){
    transform:translateY(1px) scale(.985)!important;
    box-shadow:0 5px 14px rgba(32,33,31,.10)!important;
    transition-duration:.08s!important;
  }
}
@media(hover:none){
  .tq4 .tq4-cat:hover{transform:none;box-shadow:none}
  .tq4 .tq4-cat:hover img{transform:none!important}
}
.editor-styles-wrapper .tq4 .tq4-cat h3 a::after,
.block-editor-block-list__layout .tq4 .tq4-cat h3 a::after{display:none!important}
/* END TQ TOP CARD RESPONSE + HUB LINKS v2 */
'''


def req(path,method='GET',data=None,retries=4):
    global writes
    headers={'Authorization':AUTH,'Accept':'application/json','User-Agent':'tsurikue-home-live-patch-v2/1.3'}
    body=None
    if data is not None:
        body=json.dumps(data,ensure_ascii=False).encode('utf-8')
        headers['Content-Type']='application/json; charset=utf-8'
    last=None
    for i in range(retries):
        try:
            request=urllib.request.Request(BASE+path,data=body,headers=headers,method=method)
            with urllib.request.urlopen(request,timeout=60) as response:
                raw=response.read(); total=response.headers.get('X-WP-Total')
                if method not in ('GET','HEAD'): writes+=1
                return json.loads(raw.decode('utf-8')),total
        except Exception as exc:
            last=exc
            if i+1==retries: raise
            time.sleep(2*(i+1))
    raise last


def get_page():
    q=urllib.parse.urlencode({'context':'edit','_fields':'id,slug,status,title,content,link'})
    row,_=req(f'/pages/{PAGE_ID}?{q}')
    return row


def raw(page): return (page.get('content') or {}).get('raw') or ''
def rendered(page): return (page.get('content') or {}).get('rendered') or ''
def sha(text): return hashlib.sha256(text.encode()).hexdigest()
def title(page):
    value=(page.get('title') or {}).get('raw') or (page.get('title') or {}).get('rendered') or ''
    return html.unescape(re.sub(r'<[^>]+>','',value)).strip()


def count_public():
    _,posts=req('/posts?status=publish&per_page=1&_fields=id')
    _,pages=req('/pages?status=publish&per_page=1&_fields=id')
    return {'posts':int(posts or 0),'pages':int(pages or 0)}


def structural_checks(text):
    return {
        'marker_once':text.count(MARKER)==1,
        'four_cards':all(c in text for c in ['tq4-cat--outing','tq4-cat--gourmet','tq4-cat--fishing','tq4-cat--car']),
        'hero_copy':'休日、' in text and 'なにして遊ぶ？' in text,
        'choose_copy':'今日はどれ？' in text,
        'style_block':text.count('<style>')>=1 and text.count(STYLE_CLOSE)>=1,
    }


def final_checks(text,rendered_text):
    c=structural_checks(text)
    c.update({
        'patch_once':text.count(PATCH_START)==1 and text.count(PATCH_END)==1,
        'old_category_links_gone':not any(k in text for k in LINKS),
        'hub_links':all(f'href="{v}"' in text for v in LINKS.values()),
        'full_card_css':'h3 a::after' in text and 'position:absolute' in text and 'inset:-999px' in text and 'overflow:hidden!important' in text,
        'touch_response':'touch-action:manipulation' in text and 'a:active::after' in text,
        'no_viewport_hacks':not any(x in text for x in ['100vw','100dvw','50vw','50dvw']),
        'rendered_patch':PATCH_START in rendered_text,
    })
    return c

before_counts=count_public()
before=get_page(); before_raw=raw(before)
before_state={'id':before.get('id'),'slug':before.get('slug'),'status':before.get('status'),'title':title(before),'sha256':sha(before_raw)}
if before.get('id')!=PAGE_ID or before.get('status')!='publish' or before.get('slug')!='top-design':
    raise RuntimeError('HOME_IDENTITY_REFUSED '+json.dumps(before_state,ensure_ascii=False))
if before_state['sha256']!=EXPECTED_SHA:
    raise RuntimeError('HOME_SHA_REFUSED '+json.dumps({'expected':EXPECTED_SHA,'actual':before_state['sha256']},ensure_ascii=False))
pre=structural_checks(before_raw)
if not all(pre.values()):
    raise RuntimeError('HOME_OLD_STRUCTURE_REFUSED '+json.dumps(pre,ensure_ascii=False))
if PATCH_START in before_raw:
    raise RuntimeError('HOME_PATCH_ALREADY_PRESENT_UNEXPECTED')
for old in LINKS:
    if old not in before_raw:
        raise RuntimeError('HOME_EXPECTED_OLD_LINK_MISSING '+old)

patched=before_raw
for old,new in LINKS.items():
    patched=patched.replace(old,new)

# Replace only the known root viewport hack; preserve all other CSS/content.
root_old='  width:100vw;\n  margin-left:calc(50% - 50vw);'
root_new='  width:100%;\n  max-width:100%;\n  margin-left:0;\n  margin-right:0;'
if root_old not in patched:
    raise RuntimeError('HOME_ROOT_VIEWPORT_HACK_NOT_FOUND')
patched=patched.replace(root_old,root_new,1)

# Remove the two known historical viewport workaround blocks only.
patched,n1=re.subn(r'\n?/\* MOBILE VIEWPORT CENTER FIX v2 \*/.*?(?=/\* MOBILE FULL-WIDTH FIX v3 \*/)','\n',patched,flags=re.S)
patched,n2=re.subn(r'\n?/\* MOBILE FULL-WIDTH FIX v3 \*/.*?/\* END MOBILE FULL-WIDTH FIX v3 \*/\n?','\n',patched,flags=re.S)
if n1!=1 or n2!=1:
    raise RuntimeError('HOME_VIEWPORT_BLOCK_COUNT_REFUSED '+json.dumps({'v2':n1,'v3':n2}))

# The old custom-header prototype was intentionally removed. Insert the card
# interaction CSS into the existing homepage style block instead.
if STYLE_CLOSE not in patched:
    raise RuntimeError('HOME_STYLE_CLOSE_MISSING')
patched=patched.replace(STYLE_CLOSE,CSS+'\n'+STYLE_CLOSE,1)

pre_final=final_checks(patched,patched)
if not all(pre_final.values()):
    raise RuntimeError('HOME_PATCHED_STRUCTURE_REFUSED '+json.dumps(pre_final,ensure_ascii=False))

req(f'/pages/{PAGE_ID}',method='POST',data={'content':patched})
after=get_page(); after_raw=raw(after); after_rendered=rendered(after)
after_state={'id':after.get('id'),'slug':after.get('slug'),'status':after.get('status'),'title':title(after),'sha256':sha(after_raw)}
checks=final_checks(after_raw,after_rendered)
identity_ok=(after.get('id')==PAGE_ID and after.get('slug')==before.get('slug') and after.get('status')=='publish' and title(after)==title(before))
if not identity_ok or not all(checks.values()):
    req(f'/pages/{PAGE_ID}',method='POST',data={'content':before_raw})
    raise RuntimeError('HOME_POSTWRITE_VERIFY_FAILED_ROLLED_BACK '+json.dumps({'identity_ok':identity_ok,'checks':checks,'state':after_state},ensure_ascii=False))

after_counts=count_public()
if after_counts!=before_counts:
    req(f'/pages/{PAGE_ID}',method='POST',data={'content':before_raw})
    raise RuntimeError('HOME_PUBLIC_COUNTS_CHANGED_ROLLED_BACK '+json.dumps({'before':before_counts,'after':after_counts},ensure_ascii=False))

report={
    'ok':True,
    'action':'PATCHED_LIVE_HOMEPAGE_COMPLETE_V2',
    'before':before_state,
    'after':after_state,
    'checks':checks,
    'public_before':before_counts,
    'public_after':after_counts,
    'wordpress_write_count':writes,
    'live_write_count':1,
    'publish_transition_count':0,
    'delete_count':0,
    'changed_scope':['four hub href families','full-card hit CSS','legacy viewport-width fixes'],
}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
