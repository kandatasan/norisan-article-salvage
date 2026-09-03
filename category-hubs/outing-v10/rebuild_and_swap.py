#!/usr/bin/env python3
from __future__ import annotations
import base64, html, json, os, pathlib, re, time, urllib.parse, urllib.request
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

BASE='https://tsurikue.com/wp-json/wp/v2'
SITE='https://tsurikue.com'
OLD_ID=3154
OLD_SLUG='odekake'
OLD_TITLE='おでかけ'
TEMP_SLUG='odekake-clean-v10-preview'
LEGACY_SLUG='odekake-legacy-3154-20260903'
MARK='tsurikue-category-hub:v10:outing-clean-rebuild'
DOLPHIN='https://tsurikue.com/wp-content/uploads/2026/09/img_2419.jpg'
ROOT=pathlib.Path(__file__).resolve().parents[1]
TPL=ROOT/'outing-v3'/'content.template.html'
OUT=pathlib.Path('/tmp/outing-v10-result.json')
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode()
writes=0
new_id=None
old_backup=None


def req(path,method='GET',data=None,retries=4):
    global writes
    headers={'Authorization':AUTH,'Accept':'application/json','User-Agent':'tsurikue-outing-v10/1.0'}
    body=None
    if data is not None:
        body=json.dumps(data,ensure_ascii=False).encode(); headers['Content-Type']='application/json; charset=utf-8'
    last=None
    for i in range(retries):
        try:
            r=urllib.request.Request(BASE+path,data=body,headers=headers,method=method)
            with urllib.request.urlopen(r,timeout=60) as resp:
                if method not in ('GET','HEAD'): writes+=1
                return json.loads(resp.read().decode()), resp.headers.get('X-WP-Total')
        except Exception as e:
            last=e
            if i+1==retries: raise
            time.sleep(2*(i+1))
    raise last


def clean(v):
    if isinstance(v,dict): v=v.get('raw') or v.get('rendered') or ''
    return html.unescape(re.sub(r'<[^>]+>','',v or '')).strip()

def get_page(pid):
    return req(f'/pages/{pid}?context=edit&_fields=id,slug,status,title,content,link')[0]

def counts():
    _,p=req('/posts?status=publish&per_page=1&_fields=id')
    _,g=req('/pages?status=publish&per_page=1&_fields=id')
    return {'posts':int(p or 0),'pages':int(g or 0)}

def terms(kind):
    return req(f'/{kind}?context=edit&per_page=100&hide_empty=false&_fields=id,name,slug,parent,count')[0]

def exact_slug(rows,slug):
    x=[r for r in rows if r.get('slug')==slug]
    if len(x)!=1: raise RuntimeError(f'TERM_SLUG {slug} {x}')
    return x[0]

def exact_name(rows,name):
    x=[r for r in rows if clean(r.get('name'))==name]
    if len(x)!=1: raise RuntimeError(f'TERM_NAME {name} {x}')
    return x[0]

def post_query(category_ids,tag_id):
    q={'categories':','.join(map(str,category_ids)),'tags':tag_id,'status':'publish','per_page':100,'orderby':'date','order':'desc','_fields':'id,slug,link,title,date,categories,tags'}
    return req('/posts?'+urllib.parse.urlencode(q))[0]

def items(posts):
    return '\n'.join(f'<li><a href="{html.escape(p["link"],quote=True)}">{html.escape(clean(p["title"]))}</a></li>' for p in posts)


def build():
    cats=terms('categories'); tags=terms('tags')
    outing=exact_slug(cats,'sightseeing-leisure'); drive=exact_slug(cats,'drive')
    if int(drive.get('parent') or 0)!=int(outing['id']): raise RuntimeError('DRIVE_NOT_CHILD')
    cat_ids=[int(outing['id']),int(drive['id'])]
    specs={'hiroshima':'hiroshima','etajima':'etajima','yamaguchi':'yamaguchi','sanin':'sanin'}
    groups={}
    for key,slug in specs.items():
        term=exact_slug(tags,slug); ps=post_query(cat_ids,int(term['id']))
        if not ps: raise RuntimeError('EMPTY '+key)
        groups[key]=(term,ps)
    far=exact_name(tags,'ちょっと遠くへ'); farps=post_query(cat_ids,int(far['id']))
    groups['far']=(far,farps)
    far_slugs={p['slug'] for p in farps}
    required_far={'kochi-1night-2days-drive','hiroshima-oita-1night-2days-drive','dqisland'}
    if not required_far.issubset(far_slugs): raise RuntimeError('FAR_MISSING '+json.dumps(sorted(required_far-far_slugs),ensure_ascii=False))

    s=TPL.read_text(encoding='utf-8')
    # Generate only from the pristine V3 template, never from the old live page.
    s=s.replace('tsurikue-category-hub:v3:outing-region-accordion-final',MARK,1)
    s=s.replace('.tq-outing-v3','.tq-outing-clean').replace('tq-outing-v3','tq-outing-clean')
    s=s.replace('.tq-outing-clean .tq-hero','.tq-outing-clean.tq-hero')
    s=s.replace('https://tsurikue.com/wp-content/uploads/2026/05/img_4588.jpg',DOLPHIN)
    s=s.replace('今日は、どこ行く？','今日は、<br>どこ行く？')
    s=s.replace('"focalPoint":{"x":0.5,"y":0.55}','"focalPoint":{"x":0.58,"y":0.45}')
    s=s.replace('object-position:50% 55%','object-position:58% 45%').replace('data-object-position="50% 55%"','data-object-position="58% 45%"')
    # No alignfull or inherited full-width group tricks.
    s=s.replace('<!-- wp:group {"align":"full","className":"tq-outing-clean","layout":{"type":"constrained"}} -->','<!-- wp:group {"className":"tq-outing-clean","layout":{"type":"constrained"}} -->',1)
    s=s.replace('<div class="wp-block-group alignfull tq-outing-clean">','<div class="wp-block-group tq-outing-clean">',1)
    # Page-local SWELL chrome reset: no duplicated page title/breadcrumb space above the hero.
    s=s.replace('<style>','<style>\n.c-pageTitle,.p-breadcrumb{display:none!important}\n#content.l-content{padding-top:0!important}\n',1)
    # Move the Cover out of the content group and make it the first Gutenberg block.
    hero_re=re.compile(r'<!-- wp:cover .*?"className":"tq-hero".*?<!-- /wp:cover -->',re.S)
    hm=hero_re.search(s)
    if not hm: raise RuntimeError('HERO_NOT_FOUND')
    hero=hm.group(0).replace('"className":"tq-hero"','"className":"tq-outing-clean tq-hero"',1).replace('class="wp-block-cover tq-hero"','class="wp-block-cover tq-outing-clean tq-hero"',1)
    s=s[:hm.start()]+s[hm.end():]
    html_re=re.compile(r'<!-- wp:html -->.*?<!-- /wp:html -->',re.S)
    xm=html_re.search(s)
    if not xm: raise RuntimeError('CUSTOM_HTML_NOT_FOUND')
    custom=xm.group(0); s=s[:xm.start()]+s[xm.end():]
    first_wp=s.find('<!-- wp:')
    if first_wp<0: raise RuntimeError('NO_ROOT')
    lead=s[:first_wp].rstrip(); body=s[first_wp:].lstrip()
    s=lead+'\n'+hero+'\n\n'+custom+'\n\n'+body

    repl={
      '{{OUTING_CATEGORY_ID}}':','.join(map(str,cat_ids)),
      '{{HIROSHIMA_TAG_ID}}':str(groups['hiroshima'][0]['id']), '{{ETAJIMA_TAG_ID}}':str(groups['etajima'][0]['id']),
      '{{YAMAGUCHI_TAG_ID}}':str(groups['yamaguchi'][0]['id']), '{{SANIN_TAG_ID}}':str(groups['sanin'][0]['id']), '{{FAR_TAG_ID}}':str(far['id']),
    }
    for key in groups:
        up=key.upper(); repl[f'{{{{{up}_COUNT}}}}']=str(len(groups[key][1])); repl[f'{{{{{up}_ITEMS}}}}']=items(groups[key][1])
    for a,b in repl.items(): s=s.replace(a,b)
    if re.search(r'\{\{[A-Z_]+\}\}',s): raise RuntimeError('UNRESOLVED_PLACEHOLDER')
    checks={
      'marker':s.count(MARK)==1,'hero_first':s.find('<!-- wp:cover')<s.find('<!-- wp:html')<s.find('<!-- wp:group'),
      'dolphin':s.count(DOLPHIN)==2,'heading':'今日は、<br>どこ行く？' in s,'details':s.count('<!-- wp:details ')==5,
      'no_alignfull':'alignfull' not in s,'no_viewport':all(x not in s for x in ['100vw','100dvw','50vw','50dvw']),
      'far_three':all(x in s for x in required_far),'cat_pair':f'categories={cat_ids[0]}%2C{cat_ids[1]}' not in s, # script uses literal after replacement
    }
    # REST script should query both parent and child categories.
    if f'categories={cat_ids[0]},{cat_ids[1]}&tags=' not in s: checks['script_parent_child']=False
    else: checks['script_parent_child']=True
    if not all(checks.values()): raise RuntimeError('BUILD_CHECK '+json.dumps(checks,ensure_ascii=False))
    return s, {'categories':cat_ids,'groups':{k:{'tag':int(v[0]['id']),'count':len(v[1]),'slugs':[p['slug'] for p in v[1]]} for k,v in groups.items()}}


def browser(url,width,height):
    o=Options(); o.add_argument('--headless=new'); o.add_argument('--no-sandbox'); o.add_argument('--disable-dev-shm-usage'); o.add_argument(f'--window-size={width},{height}')
    d=webdriver.Chrome(options=o)
    try:
        d.get(url+'?tq_v10='+str(int(time.time()))); time.sleep(4)
        return d.execute_script(r'''
const q=s=>document.querySelector(s), r=e=>e?e.getBoundingClientRect():null;
const hero=q('.tq-outing-clean.tq-hero'), header=q('#header'), post=q('.post_content'), root=q('div.wp-block-group.tq-outing-clean:not(.tq-hero)');
const far=q('.tq-accordion-far');
return {url:location.href, hero:r(hero),header:r(header),post:r(post),root:r(root),scrollW:document.documentElement.scrollWidth,clientW:document.documentElement.clientWidth,
 h1:hero&&hero.querySelector('h1')?hero.querySelector('h1').innerText.trim():null,img:hero&&hero.querySelector('img')?(hero.querySelector('img').currentSrc||hero.querySelector('img').src):null,
 heroParent:hero&&hero.parentElement?hero.parentElement.className:null,heroInRoot:root?root.querySelectorAll('.tq-hero').length:null,details:document.querySelectorAll('details.tq-accordion').length,
 farText:far?far.innerText:'',title:q('.c-pageTitle')?getComputedStyle(q('.c-pageTitle')).display:null,breadcrumb:q('.p-breadcrumb')?getComputedStyle(q('.p-breadcrumb')).display:null,auto:document.documentElement.dataset.tqOutingAuto||null};
''')
    finally: d.quit()

def render_ok(m,mobile=False):
    gap=m['hero']['top']-m['header']['bottom'] if m['hero'] and m['header'] else 999
    return {
      'hero':bool(m['hero']),'dolphin':m['img']==DOLPHIN,'heading':m['h1']=='今日は、\nどこ行く？','direct_post':m['heroParent']=='post_content',
      'outside_group':m['heroInRoot']==0,'details':m['details']==5,'far_kochi':'高知' in m['farText'],'far_oita':'大分' in m['farText'],'far_dq':'ドラゴンクエスト' in m['farText'],
      'no_overflow':m['scrollW']<=m['clientW']+2,'top_gap_small':gap<=12,'title_hidden':m['title'] in (None,'none'),'breadcrumb_hidden':m['breadcrumb'] in (None,'none'),'auto':m['auto'] in ('ready','fallback')
    },gap


def rollback():
    global new_id
    try:
        if new_id:
            req(f'/pages/{new_id}',method='POST',data={'slug':TEMP_SLUG,'status':'draft','title':'おでかけ clean v10（退避）'})
    except Exception: pass
    try:
        if old_backup:
            req(f'/pages/{OLD_ID}',method='POST',data={'slug':OLD_SLUG,'status':'publish','title':OLD_TITLE})
    except Exception: pass

before=counts(); old=get_page(OLD_ID)
if old.get('slug')!=OLD_SLUG or old.get('status')!='publish' or clean(old.get('title'))!=OLD_TITLE: raise RuntimeError('OLD_IDENTITY_CHANGED')
old_backup={'id':OLD_ID,'slug':old['slug'],'status':old['status'],'title':clean(old['title'])}
content,source=build()
# Refuse duplicates from an interrupted previous run.
existing=req('/pages?context=edit&status=publish,draft,private&per_page=100&slug='+TEMP_SLUG+'&_fields=id,slug,status')[0]
if existing: raise RuntimeError('TEMP_SLUG_ALREADY_EXISTS '+json.dumps(existing))
created,_=req('/pages',method='POST',data={'title':'おでかけ clean v10 preview','slug':TEMP_SLUG,'status':'publish','content':content})
new_id=int(created['id'])
# Temporary public render before the swap.
tmpurl=f'{SITE}/{TEMP_SLUG}/'
desk=browser(tmpurl,1440,1000); mob=browser(tmpurl,500,850)
dc,dgap=render_ok(desk); mc,mgap=render_ok(mob)
if not all(dc.values()) or not all(mc.values()):
    req(f'/pages/{new_id}',method='POST',data={'status':'draft'})
    raise RuntimeError('TEMP_RENDER_FAILED '+json.dumps({'desktop':dc,'mobile':mc,'gaps':[dgap,mgap],'metrics':[desk,mob]},ensure_ascii=False))
# Atomic-ish slug handoff: old page retires first, then new page receives /odekake/.
req(f'/pages/{OLD_ID}',method='POST',data={'slug':LEGACY_SLUG,'status':'draft','title':'おでかけ（旧ページ退避）'})
try:
    req(f'/pages/{new_id}',method='POST',data={'slug':OLD_SLUG,'status':'publish','title':OLD_TITLE})
    live=req('/pages?context=edit&slug=odekake&status=publish&per_page=10&_fields=id,slug,status,title')[0]
    if len(live)!=1 or int(live[0]['id'])!=new_id: raise RuntimeError('HANDOFF_IDENTITY_FAILED '+json.dumps(live,ensure_ascii=False))
    finald=browser(f'{SITE}/odekake/',1440,1000); finalm=browser(f'{SITE}/odekake/',500,850)
    fdc,fdg=render_ok(finald); fmc,fmg=render_ok(finalm)
    after=counts()
    if not all(fdc.values()) or not all(fmc.values()) or after!=before:
        raise RuntimeError('FINAL_VERIFY_FAILED '+json.dumps({'desktop':fdc,'mobile':fmc,'gaps':[fdg,fmg],'counts':[before,after]},ensure_ascii=False))
except Exception:
    rollback(); raise
report={'ok':True,'action':'OUTING_V10_CLEAN_REBUILD_SWAP','old_page_retired':OLD_ID,'new_page_live':new_id,'source':source,'desktop':fdc,'mobile':fmc,'gaps':{'desktop':fdg,'mobile':fmg},'public_before':before,'public_after':after,'writes':writes,'delete_count':0}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(report,ensure_ascii=False,indent=2))
