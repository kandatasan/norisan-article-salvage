#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, os, pathlib, re, time, urllib.parse, urllib.request

BASE='https://tsurikue.com/wp-json/wp/v2'
PAGE_ID=3154
SLUG='odekake'
TITLE='おでかけ'
EXPECTED_SHA='bcec617347135488c791509814174aedfb58052cc6eb63851323c96315c41619'
DOLPHIN='https://tsurikue.com/wp-content/uploads/2026/09/img_2419.jpg'
H1='<h1 class="wp-block-heading">今日は、<br>どこ行く？</h1>'
ROOT_BLOCK='<!-- wp:group {"className":"tq-outing-v3","layout":{"type":"constrained"}} -->'
ROOT_DIV='<div class="wp-block-group tq-outing-v3">'
V7_MARK='/* tq-outing-spacing:v7:hero-up */'
V8_MARK='/* tq-outing-structure:v8:standalone-hero */'
AUTO_MARK='/* tq-outing-auto-index:v3 */'
HERO_RE=re.compile(r'<!-- wp:cover .*?"className":"tq-hero".*?<!-- /wp:cover -->',re.S)
HTML_RE=re.compile(r'<!-- wp:html -->.*?<!-- /wp:html -->',re.S)
HERO_SELECTOR_RE=re.compile(r'\.tq-outing-v3 \.tq-hero(?=[\s,{])')
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode()
OUT=pathlib.Path('/tmp/outing-v8-result.json')
writes=0

def req(path,method='GET',data=None,retries=4):
    global writes
    headers={'Authorization':AUTH,'Accept':'application/json','User-Agent':'tsurikue-outing-v8/1.0'}
    body=None
    if data is not None:
        body=json.dumps(data,ensure_ascii=False).encode('utf-8')
        headers['Content-Type']='application/json; charset=utf-8'
    last=None
    for i in range(retries):
        try:
            r=urllib.request.Request(BASE+path,data=body,headers=headers,method=method)
            with urllib.request.urlopen(r,timeout=60) as resp:
                if method not in ('GET','HEAD'): writes+=1
                return json.loads(resp.read().decode()),resp.headers.get('X-WP-Total')
        except Exception as e:
            last=e
            if i+1==retries: raise
            time.sleep(2*(i+1))
    raise last

def page():
    q=urllib.parse.urlencode({'context':'edit','_fields':'id,slug,status,title,content'})
    return req(f'/pages/{PAGE_ID}?{q}')[0]
def raw(row): return (row.get('content') or {}).get('raw') or ''
def sha(text): return hashlib.sha256(text.encode()).hexdigest()
def clean_title(row):
    x=(row.get('title') or {}).get('raw') or (row.get('title') or {}).get('rendered') or ''
    return html.unescape(re.sub(r'<[^>]+>','',x)).strip()
def counts():
    _,p=req('/posts?status=publish&per_page=1&_fields=id')
    _,g=req('/pages?status=publish&per_page=1&_fields=id')
    return {'posts':int(p or 0),'pages':int(g or 0)}

def structural_checks(text):
    hero_new_block='"className":"tq-outing-v3 tq-hero"'
    hero_new_div='class="wp-block-cover tq-outing-v3 tq-hero"'
    hero_i=text.find('<!-- wp:cover ')
    html_i=text.find('<!-- wp:html -->')
    root_i=text.find(ROOT_BLOCK)
    first_wp=re.search(r'<!-- wp:[a-z-]+',text)
    return {
        'v8_marker_once':text.count(V8_MARK)==1,
        'v7_marker_once':text.count(V7_MARK)==1,
        'dolphin_twice':text.count(DOLPHIN)==2,
        'heading_once':text.count(H1)==1,
        'hero_block_class_once':text.count(hero_new_block)==1,
        'hero_div_class_once':text.count(hero_new_div)==1,
        'old_hero_block_class_gone':'"className":"tq-hero"' not in text,
        'root_block_once':text.count(ROOT_BLOCK)==1,
        'root_div_once':text.count(ROOT_DIV)==1,
        'hero_first_gutenberg_block':bool(first_wp and first_wp.group(0)=='<!-- wp:cover'),
        'order_hero_html_root':hero_i>=0 and html_i>hero_i and root_i>html_i,
        'hero_outside_root':hero_i>=0 and root_i>hero_i,
        'standalone_selector':'.tq-outing-v3.tq-hero{' in text and '.tq-outing-v3.tq-hero .wp-block-cover__inner-container' in text,
        'auto_index_preserved':text.count(AUTO_MARK)==1,
        'five_details':text.count('class="wp-block-details tq-accordion ')==5,
        'far_preserved':'ちょっと遠くへ' in text,
        'no_viewport_hacks':not any(x in text for x in ['100vw','100dvw','50vw','50dvw']),
    }

before_counts=counts(); before=page(); s=raw(before)
identity={'id':before.get('id'),'slug':before.get('slug'),'status':before.get('status'),'title':clean_title(before),'sha256':sha(s)}
expected={'id':PAGE_ID,'slug':SLUG,'status':'publish','title':TITLE,'sha256':EXPECTED_SHA}
if identity!=expected:
    raise RuntimeError('OUTING_V8_STALE_OR_IDENTITY_REFUSED '+json.dumps(identity,ensure_ascii=False))
if V8_MARK in s or s.count(V7_MARK)!=1 or s.count(DOLPHIN)!=2 or s.count(H1)!=1:
    raise RuntimeError('OUTING_V8_SOURCE_MARKER_REFUSED')
if s.count(ROOT_BLOCK)!=1 or s.count(ROOT_DIV)!=1 or s.count(AUTO_MARK)!=1:
    raise RuntimeError('OUTING_V8_ROOT_OR_AUTO_SOURCE_REFUSED')
hero_matches=list(HERO_RE.finditer(s)); html_matches=list(HTML_RE.finditer(s))
if len(hero_matches)!=1 or len(html_matches)!=1:
    raise RuntimeError(f'OUTING_V8_BLOCK_MATCH_REFUSED hero={len(hero_matches)} html={len(html_matches)}')
hero=hero_matches[0].group(0); custom=html_matches[0].group(0)
if s.find(hero)<s.find(ROOT_BLOCK) or s.find(custom)>s.find(ROOT_BLOCK):
    raise RuntimeError('OUTING_V8_UNEXPECTED_SOURCE_ORDER')

# Standalone hero keeps the same visual scope class, while it is no longer a child of the content group.
hero2=hero.replace('"className":"tq-hero"','"className":"tq-outing-v3 tq-hero"',1)
hero2=hero2.replace('class="wp-block-cover tq-hero"','class="wp-block-cover tq-outing-v3 tq-hero"',1)
if hero2==hero:
    raise RuntimeError('OUTING_V8_HERO_CLASS_REPLACE_FAILED')

# Hero-specific selectors previously depended on the outer tq-outing-v3 group. Make them work on the standalone cover itself.
custom2,nsel=HERO_SELECTOR_RE.subn('.tq-outing-v3.tq-hero',custom)
if nsel<2:
    raise RuntimeError(f'OUTING_V8_HERO_SELECTOR_REPLACE_FAILED {nsel}')
custom2=custom2.replace('<style>','<style>\n'+V8_MARK,1)

# Remove the old nested hero and the custom HTML block, then rebuild the top-level Gutenberg order:
# standalone hero -> custom HTML (CSS/auto index) -> content group.
rest=s.replace(hero,'',1).replace(custom,'',1)
first_wp=re.search(r'<!-- wp:',rest)
if not first_wp or rest[first_wp.start():].startswith('<!-- wp:group') is False:
    raise RuntimeError('OUTING_V8_REMAINDER_NOT_ROOT_GROUP')
leading=rest[:first_wp.start()].rstrip()
body=rest[first_wp.start():].lstrip()
patched=leading+'\n'+hero2+'\n\n'+custom2+'\n\n'+body

pre=structural_checks(patched)
if not all(pre.values()):
    raise RuntimeError('OUTING_V8_PREWRITE_CHECK_FAILED '+json.dumps(pre,ensure_ascii=False))

req(f'/pages/{PAGE_ID}',method='POST',data={'content':patched})
after=page(); ar=raw(after); after_counts=counts(); post=structural_checks(ar)
after_identity=after.get('id')==PAGE_ID and after.get('slug')==SLUG and after.get('status')=='publish' and clean_title(after)==TITLE
if not after_identity or not all(post.values()) or after_counts!=before_counts:
    req(f'/pages/{PAGE_ID}',method='POST',data={'content':s})
    raise RuntimeError('OUTING_V8_POSTWRITE_FAILED_ROLLED_BACK '+json.dumps({'identity':after_identity,'checks':post,'counts':after_counts},ensure_ascii=False))
rep={'ok':True,'action':'OUTING_V8_STANDALONE_HERO','before':identity,'after_sha':sha(ar),'checks':post,'public_before':before_counts,'public_after':after_counts,'wordpress_write_count':writes,'publish_transition_count':0,'delete_count':0}
OUT.write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(rep,ensure_ascii=False,indent=2))
