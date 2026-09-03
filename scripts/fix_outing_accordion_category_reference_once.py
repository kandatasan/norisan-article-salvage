#!/usr/bin/env python3
from __future__ import annotations
import base64, html, json, os, re, time, urllib.parse, urllib.request
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

SITE='https://tsurikue.com'; BASE=SITE+'/wp-json/wp/v2'; PAGE_SLUG='odekake'; ROOT='tq-outing-v3'
UA='tsurikue-outing-accordion-reference/1.0'
GROUPS={'hiroshima':('hiroshima','広島'),'etajima':('etajima','江田島'),'yamaguchi':('yamaguchi','山口'),'sanin':('sanin','山陰'),'far':(None,'ちょっと遠くへ')}
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode()

def req(path,method='GET',payload=None):
    headers={'Authorization':AUTH,'Accept':'application/json','User-Agent':UA}; data=None
    if payload is not None:
        data=json.dumps(payload,ensure_ascii=False).encode('utf-8'); headers['Content-Type']='application/json; charset=utf-8'
    r=urllib.request.Request(BASE+path,data=data,headers=headers,method=method)
    with urllib.request.urlopen(r,timeout=60) as x: return json.loads(x.read().decode()),dict(x.headers)

def clean(v):
    if isinstance(v,dict): v=v.get('raw') or v.get('rendered') or ''
    return html.unescape(re.sub(r'<[^>]+>','',v or '')).strip()

def totals():
    out={}
    for ep in ('posts','pages'):
        _,h=req(f'/{ep}?status=publish&per_page=1&_fields=id'); out[ep]=int(h.get('X-WP-Total','0'))
    return out

def page():
    q=urllib.parse.urlencode({'context':'edit','slug':PAGE_SLUG,'status':'publish','per_page':10,'_fields':'id,title,status,content'})
    rows,_=req('/pages?'+q)
    if len(rows)!=1 or clean(rows[0]['title'])!='おでかけ': raise RuntimeError('PAGE_MISMATCH')
    return rows[0]

def terms(ep):
    out=[]; p=1
    while True:
        q=urllib.parse.urlencode({'context':'edit','per_page':100,'page':p,'hide_empty':False,'_fields':'id,name,slug,parent,count'})
        rows,h=req('/'+ep+'?'+q); out+=rows
        if p>=int(h.get('X-WP-TotalPages','1')): return out
        p+=1

def exact_slug(rows,slug):
    m=[x for x in rows if x.get('slug')==slug]
    if len(m)!=1: raise RuntimeError('TERM_SLUG_'+slug)
    return m[0]

def exact_name(rows,name):
    m=[x for x in rows if clean(x.get('name'))==name]
    if len(m)!=1: raise RuntimeError('TERM_NAME_'+name)
    return m[0]

def source_truth():
    cats=terms('categories'); tags=terms('tags')
    outing=exact_slug(cats,'sightseeing-leisure'); drive=exact_slug(cats,'drive')
    if int(drive.get('parent') or 0)!=int(outing['id']): raise RuntimeError('DRIVE_PARENT_MISMATCH')
    cat_ids=[int(outing['id']),int(drive['id'])]; groups={}
    for key,(slug,name) in GROUPS.items():
        tag=exact_name(tags,name) if key=='far' else exact_slug(tags,slug)
        q=urllib.parse.urlencode({'categories':','.join(map(str,cat_ids)),'tags':tag['id'],'status':'publish','per_page':100,'orderby':'date','order':'desc','_fields':'slug,link,title'})
        posts,_=req('/posts?'+q)
        if not posts: raise RuntimeError('EMPTY_'+key)
        groups[key]={'tag':tag,'posts':posts,'archive':f"{SITE}/tag/{tag['slug']}/"}
    return cat_ids,groups

def patch(raw,cat_ids):
    if '/* tq-outing-auto-index:v3 */' not in raw: raise RuntimeError('AUTO_SCRIPT_MISSING')
    target='categories='+','.join(map(str,cat_ids))+'&tags='
    # Only modify the auto-index REST request; tolerate either one or two old category IDs.
    pat=r"(fetch\(API\+'/posts\?categories=)\d+(?:,\d+)?(&tags='\+tag\+'&status=publish&per_page=100)"
    raw2,n=re.subn(pat,lambda m:m.group(1)+','.join(map(str,cat_ids))+m.group(2),raw,count=1)
    if n!=1: raise RuntimeError('AUTO_CATEGORY_QUERY_NOT_FOUND')
    if target not in raw2: raise RuntimeError('AUTO_CATEGORY_QUERY_VERIFY_FAILED')
    return raw2

def norm(xs): return [x.rstrip('/')+'/' for x in xs]

def browser(groups):
    o=Options(); o.add_argument('--headless=new'); o.add_argument('--no-sandbox'); o.add_argument('--disable-dev-shm-usage'); o.add_argument('--window-size=1440,1100')
    d=webdriver.Chrome(options=o)
    try:
        d.get(SITE+'/odekake/?tq_accordion_final='+str(int(time.time()))); time.sleep(8)
        m=d.execute_script('''
const h=document.querySelector('.tq-outing-v3.tq-hero'),r=h&&h.getBoundingClientRect();
const out={vw:document.documentElement.clientWidth,sw:document.documentElement.scrollWidth,fit:document.documentElement.dataset.tqHeroFit||null,auto:document.documentElement.dataset.tqOutingAuto||null,hero:r?{left:r.left,right:r.right,width:r.width}:null,groups:{}};
for(const k of ['hiroshima','etajima','yamaguchi','sanin','far']){const links=[...document.querySelectorAll('.tq-auto-'+k+' a')].map(a=>a.href),c=document.querySelector('[data-count="'+k+'"]'),a=document.querySelector('.tq-accordion-'+k+' .tq-tag-link a');out.groups[k]={links,count:c?c.textContent.trim():null,archive:a?a.href:null}}return out;''')
    finally: d.quit()
    if m['fit']!='ready': raise RuntimeError('HERO_FIT_NOT_READY')
    if not m['hero'] or abs(m['hero']['left'])>2 or abs(m['hero']['right']-m['vw'])>2 or abs(m['hero']['width']-m['vw'])>2: raise RuntimeError('HERO_NOT_FULL '+json.dumps(m['hero']))
    if m['sw']>m['vw']+2: raise RuntimeError(f'HORIZONTAL_OVERFLOW {m["sw"]}>{m["vw"]}')
    if m['auto']!='ready': raise RuntimeError('AUTO_NOT_READY '+str(m['auto']))
    audit={}
    for key,v in groups.items():
        expected=norm([p['link'] for p in v['posts']]); got=norm(m['groups'][key]['links'])
        if got!=expected: raise RuntimeError('LIST_MISMATCH_'+key+' '+json.dumps({'expected':expected,'got':got},ensure_ascii=False))
        if m['groups'][key]['count']!=f'{len(expected)}記事': raise RuntimeError('COUNT_MISMATCH_'+key)
        if not m['groups'][key]['archive'] or norm([m['groups'][key]['archive']])[0]!=norm([v['archive']])[0]: raise RuntimeError('ARCHIVE_MISMATCH_'+key)
        audit[key]={'count':len(expected),'slugs':[p['slug'] for p in v['posts']],'tag_id':v['tag']['id'],'tag_slug':v['tag']['slug'],'archive':v['archive']}
    return m,audit

def main():
    before=totals(); p=page(); cat_ids,groups=source_truth(); raw=(p.get('content') or {}).get('raw') or ''
    if ROOT not in raw or raw.count('<!-- wp:details')!=5: raise RuntimeError('LIVE_STRUCTURE_CHANGED')
    patched=patch(raw,cat_ids)
    if patched!=raw: req(f"/pages/{p['id']}",method='POST',payload={'content':patched})
    p2=page(); raw2=(p2.get('content') or {}).get('raw') or ''
    expected_query='categories='+','.join(map(str,cat_ids))+'&tags='
    if expected_query not in raw2: raise RuntimeError('POSTWRITE_QUERY_MISSING')
    after=totals()
    if after!=before: raise RuntimeError(f'PUBLIC_TOTALS_CHANGED {before}->{after}')
    metrics,audit=browser(groups)
    print(json.dumps({'ok':True,'action':'OUTING_HERO_AND_ACCORDIONS_COMPLETE','page_id':p['id'],'category_ids':cat_ids,'hero':metrics['hero'],'viewport':metrics['vw'],'scroll_width':metrics['sw'],'groups':audit,'public_before':before,'public_after':after},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
