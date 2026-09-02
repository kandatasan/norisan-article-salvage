#!/usr/bin/env python3
import base64, hashlib, json, os, pathlib, re, time, urllib.error, urllib.request
BASE='https://tsurikue.com/wp-json/wp/v2'
PAGE_ID=3316
SLUG='fishing-guide'
TITLE='釣り｜初心者向けの釣り方・実釣レビュー・釣行記'
STATUS='draft'
OLD_SHA='82a5788bb541fe61a8aee5e0fa06476a8d807c7582751b5dc572424a5b4d67ca'
MARKER='tsurikue-category-hub:v3.1:fishing-simple'
HERO_URL='https://tsurikue.com/wp-content/uploads/2026/06/IMG_9050-768x1024.jpeg'
ROOT=pathlib.Path(__file__).resolve().parent
USER=os.environ['TSURIKUE_WP_USER']
APP=os.environ['TSURIKUE_WP_APP_PASSWORD']
AUTH='Basic '+base64.b64encode(f'{USER}:{APP}'.encode()).decode()
writes=0

def req(path, method='GET', data=None, timeout=45, retries=4):
    global writes
    hdr={'Authorization':AUTH,'User-Agent':'tsurikue-fishing-hub-v3/1.0'}
    body=None
    if isinstance(data,(dict,list)):
        body=json.dumps(data,ensure_ascii=False).encode()
        hdr['Content-Type']='application/json; charset=utf-8'
    elif data is not None:
        body=data
    last=None
    for i in range(retries):
        try:
            r=urllib.request.Request(BASE+path,data=body,headers=hdr,method=method)
            with urllib.request.urlopen(r,timeout=timeout) as res:
                raw=res.read()
                total=res.headers.get('X-WP-Total')
                ctype=res.headers.get('Content-Type','')
                parsed=json.loads(raw.decode()) if 'json' in ctype else raw
                if method not in ('GET','HEAD'): writes += 1
                return parsed,total
        except (urllib.error.URLError, TimeoutError) as e:
            last=e
            if i+1==retries: raise
            time.sleep(2*(i+1))
    raise last

def count_public():
    _,p=req('/posts?status=publish&per_page=1&_fields=id')
    _,q=req('/pages?status=publish&per_page=1&_fields=id')
    return {'posts':int(p or 0),'pages':int(q or 0)}

def get_page():
    p,_=req(f'/pages/{PAGE_ID}?context=edit&_fields=id,slug,status,title,content,link,modified')
    return p

def raw_content(page):
    c=page.get('content',{})
    return c.get('raw','') if isinstance(c,dict) else ''

def checks(content):
    return {
        'marker_once': content.count(MARKER)==1,
        'single_custom_html': content.count('<!-- wp:html -->')==1,
        'hero_url': HERO_URL in content,
        'hero_alt': '手元の小さなルアーと、ランディングネットに入った魚' in content,
        'pick_links': all(x in content for x in ['/sabiki-beginner/','/kantan-aoriika/','/kanritsuriba/']),
        'lab_links': all(x in content for x in ['/gulpalivepowder/','/gekiyasu-metal-vibration/','/inkonohane-tsuretayo/']),
        'swell_post_list': '<!-- wp:loos/post-list' in content,
        'swell_fishing_category': '"catID":"1"' in content,
        'swell_six_posts': '"listCount":6' in content,
        'no_core_latest_posts': '<!-- wp:latest-posts' not in content,
        'archive_link': 'https://tsurikue.com/category/fishing/' in content,
        'mobile_css': 'grid-template-columns:1fr!important' in content,
        'no_emoji': not bool(re.search('[\U0001F300-\U0001FAFF]',content)),
    }

before=count_public()
page=get_page()
if page['id']!=PAGE_ID or page['slug']!=SLUG or page['status']!=STATUS or page['title']['raw']!=TITLE:
    raise RuntimeError('PAGE_IDENTITY_MISMATCH '+json.dumps({'id':page.get('id'),'slug':page.get('slug'),'status':page.get('status'),'title':page.get('title',{}).get('raw')},ensure_ascii=False))
current=raw_content(page)
current_sha=hashlib.sha256(current.encode()).hexdigest()

if MARKER in current:
    final_checks=checks(current)
    if not all(final_checks.values()):
        raise RuntimeError('V3_VERIFY_FAILED '+json.dumps(final_checks,ensure_ascii=False))
    after=count_public()
    if before!=after: raise RuntimeError('PUBLIC_COUNTS_CHANGED')
    print(json.dumps({'action':'VERIFIED_EXISTING_FISHING_V3','page_id':PAGE_ID,'slug':SLUG,'status':STATUS,'wordpress_write_count':writes,'public_before':before,'public_after':after,'hero_url':HERO_URL,'checks':final_checks,'content_sha256':current_sha},ensure_ascii=False))
    raise SystemExit

if current_sha!=OLD_SHA:
    raise RuntimeError('STALE_DRAFT_REFUSED '+json.dumps({'expected':OLD_SHA,'actual':current_sha},ensure_ascii=False))

desired=(ROOT/'content.template.html').read_text(encoding='utf-8')
pre_checks=checks(desired)
if not all(pre_checks.values()):
    raise RuntimeError('DESIRED_STRUCTURE_FAILED '+json.dumps(pre_checks,ensure_ascii=False))

req(f'/pages/{PAGE_ID}',method='POST',data={'content':desired,'status':'draft'})
final=get_page()
if final['status']!='draft' or final['slug']!=SLUG:
    raise RuntimeError('FINAL_IDENTITY_FAILED')
saved=raw_content(final)
final_checks=checks(saved)
if not all(final_checks.values()):
    raise RuntimeError('FINAL_STRUCTURE_FAILED '+json.dumps(final_checks,ensure_ascii=False))
after=count_public()
if before!=after:
    raise RuntimeError('PUBLIC_COUNTS_CHANGED '+json.dumps({'before':before,'after':after}))

print(json.dumps({
    'action':'UPDATED_FISHING_CATEGORY_HUB_V3',
    'page_id':PAGE_ID,'slug':SLUG,'status':final['status'],
    'preview_link':final['link']+'?preview=true',
    'wordpress_write_count':writes,'publish_count':0,'delete_count':0,
    'public_before':before,'public_after':after,
    'hero_url':HERO_URL,'checks':final_checks,
    'old_content_sha256':current_sha,
    'final_content_sha256':hashlib.sha256(saved.encode()).hexdigest(),
    'block_counts':{
        'html':saved.count('<!-- wp:html -->'),
        'group':saved.count('<!-- wp:group '),
        'heading':saved.count('<!-- wp:heading'),
        'paragraph':saved.count('<!-- wp:paragraph'),
        'swell_post_list':saved.count('<!-- wp:loos/post-list')
    }
},ensure_ascii=False))
