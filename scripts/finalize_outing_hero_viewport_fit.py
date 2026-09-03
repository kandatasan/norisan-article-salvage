#!/usr/bin/env python3
from __future__ import annotations
import base64, html, json, os, re, time, urllib.parse, urllib.request
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

SITE='https://tsurikue.com'; BASE=SITE+'/wp-json/wp/v2'; PAGE='odekake'
CSS_MARK='/* tq-outing-v11-fullbleed */'; JS_MARK='<!-- tq-outing-v11-viewport-fit -->'
ROOT='tq-outing-v3'; UA='tsurikue-outing-v11-final/1.0'
GROUPS={'hiroshima':('hiroshima','広島'),'etajima':('etajima','江田島'),'yamaguchi':('yamaguchi','山口'),'sanin':('sanin','山陰'),'far':(None,'ちょっと遠くへ')}
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode()

def req(path,method='GET',payload=None):
    headers={'Authorization':AUTH,'Accept':'application/json','User-Agent':UA}; data=None
    if payload is not None:
        data=json.dumps(payload,ensure_ascii=False).encode(); headers['Content-Type']='application/json; charset=utf-8'
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

def live_page():
    q=urllib.parse.urlencode({'context':'edit','slug':PAGE,'status':'publish','per_page':10,'_fields':'id,slug,status,title,content'})
    rows,_=req('/pages?'+q)
    if len(rows)!=1 or clean(rows[0]['title'])!='おでかけ': raise RuntimeError('LIVE_PAGE_MISMATCH')
    return rows[0]

def all_terms(ep):
    out=[]; p=1
    while True:
        q=urllib.parse.urlencode({'context':'edit','per_page':100,'page':p,'hide_empty':False,'_fields':'id,name,slug,parent,count'})
        rows,h=req('/'+ep+'?'+q); out += rows
        if p>=int(h.get('X-WP-TotalPages','1')): return out
        p+=1

def one_slug(rows,slug):
    m=[x for x in rows if x.get('slug')==slug]
    if len(m)!=1: raise RuntimeError('TERM_SLUG_'+slug)
    return m[0]

def one_name(rows,name):
    m=[x for x in rows if clean(x.get('name'))==name]
    if len(m)!=1: raise RuntimeError('TERM_NAME_'+name)
    return m[0]

def expected_groups():
    cats=all_terms('categories'); tags=all_terms('tags')
    outing=one_slug(cats,'sightseeing-leisure'); drive=one_slug(cats,'drive')
    if int(drive.get('parent') or 0)!=int(outing['id']): raise RuntimeError('DRIVE_PARENT')
    cat_ids=[int(outing['id']),int(drive['id'])]; out={}
    for key,(slug,name) in GROUPS.items():
        t=one_name(tags,name) if key=='far' else one_slug(tags,slug)
        q=urllib.parse.urlencode({'categories':','.join(map(str,cat_ids)),'tags':t['id'],'status':'publish','per_page':100,'orderby':'date','order':'desc','_fields':'slug,link,title'})
        posts,_=req('/posts?'+q)
        if not posts: raise RuntimeError('EMPTY_'+key)
        out[key]={'tag':t,'posts':posts,'archive':f"{SITE}/tag/{t['slug']}/"}
    return cat_ids,out

def inject(raw):
    css=(CSS_MARK+'\n.'+ROOT+'.tq-hero{position:relative!important;max-width:none!important;margin-right:0!important;}\n')
    if CSS_MARK in raw:
        raw=re.sub(r'/\* tq-outing-v11-fullbleed \*/.*?(?=</style>)',css,raw,count=1,flags=re.S)
    else:
        i=raw.find('</style>')
        if i<0: raise RuntimeError('STYLE_END_MISSING')
        raw=raw[:i]+css+raw[i:]
    js=JS_MARK+'''<script>(function(){
function fit(){var h=document.querySelector('.tq-outing-v3.tq-hero');if(!h)return;h.style.setProperty('left','0px','important');h.style.setProperty('margin-left','0px','important');h.style.setProperty('margin-right','0px','important');h.style.setProperty('width',document.documentElement.clientWidth+'px','important');h.style.setProperty('max-width','none','important');requestAnimationFrame(function(){var x=h.getBoundingClientRect().left;h.style.setProperty('left',(-x)+'px','important');document.documentElement.dataset.tqHeroFit='ready';});}
var timer;function schedule(){clearTimeout(timer);timer=setTimeout(fit,60)}
if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',fit,{once:true})}else{fit()}window.addEventListener('load',fit,{once:true});window.addEventListener('resize',schedule);})();</script>'''
    if JS_MARK in raw:
        raw=re.sub(r'<!-- tq-outing-v11-viewport-fit --><script>.*?</script>',js,raw,count=1,flags=re.S)
    else:
        i=raw.find('</style>')
        if i<0: raise RuntimeError('STYLE_END_MISSING_2')
        i+=len('</style>'); raw=raw[:i]+'\n'+js+raw[i:]
    return raw

def norm(xs): return [x.rstrip('/')+'/' for x in xs]

def browser(expected):
    o=Options(); o.add_argument('--headless=new'); o.add_argument('--no-sandbox'); o.add_argument('--disable-dev-shm-usage'); o.add_argument('--window-size=1440,1100')
    d=webdriver.Chrome(options=o)
    try:
        d.get(SITE+'/odekake/?tq_final='+str(int(time.time()))); time.sleep(7)
        m=d.execute_script('''
const h=document.querySelector('.tq-outing-v3.tq-hero'),r=h&&h.getBoundingClientRect();const out={vw:document.documentElement.clientWidth,sw:document.documentElement.scrollWidth,fit:document.documentElement.dataset.tqHeroFit||null,auto:document.documentElement.dataset.tqOutingAuto||null,hero:r?{left:r.left,right:r.right,width:r.width}:null,groups:{}};
for(const k of ['hiroshima','etajima','yamaguchi','sanin','far']){const links=[...document.querySelectorAll('.tq-auto-'+k+' a')].map(a=>a.href),c=document.querySelector('[data-count="'+k+'"]'),a=document.querySelector('.tq-accordion-'+k+' .tq-tag-link a');out.groups[k]={links:links,count:c?c.textContent.trim():null,archive:a?a.href:null}}return out;''')
    finally:d.quit()
    if m['fit']!='ready': raise RuntimeError('HERO_FIT_SCRIPT_NOT_READY')
    if not m['hero'] or abs(m['hero']['left'])>2 or abs(m['hero']['right']-m['vw'])>2 or abs(m['hero']['width']-m['vw'])>2: raise RuntimeError('HERO_GEOMETRY '+json.dumps(m['hero']))
    if m['sw']>m['vw']+2: raise RuntimeError(f'HORIZONTAL_OVERFLOW {m["sw"]}>{m["vw"]}')
    if m['auto']!='ready': raise RuntimeError('AUTO_NOT_READY '+str(m['auto']))
    audit={}
    for k,v in expected.items():
        exp=norm([p['link'] for p in v['posts']]); got=norm(m['groups'][k]['links'])
        if got!=exp: raise RuntimeError('LIST_MISMATCH_'+k+' '+json.dumps({'expected':exp,'got':got},ensure_ascii=False))
        if m['groups'][k]['count']!=f'{len(exp)}記事': raise RuntimeError('COUNT_MISMATCH_'+k)
        if not m['groups'][k]['archive'] or norm([m['groups'][k]['archive']])[0]!=norm([v['archive']])[0]: raise RuntimeError('ARCHIVE_MISMATCH_'+k)
        audit[k]={'count':len(exp),'slugs':[p['slug'] for p in v['posts']],'tag_slug':v['tag']['slug'],'archive':v['archive']}
    return m,audit

def main():
    before=totals(); p=live_page(); cat_ids,expected=expected_groups(); raw=(p.get('content') or {}).get('raw') or ''
    if ROOT not in raw or raw.count('<!-- wp:details')!=5: raise RuntimeError('LIVE_STRUCTURE_CHANGED')
    patched=inject(raw)
    if patched!=raw: req(f"/pages/{p['id']}",method='POST',payload={'content':patched})
    verify=live_page(); vr=(verify.get('content') or {}).get('raw') or ''
    if CSS_MARK not in vr or JS_MARK not in vr: raise RuntimeError('WRITE_VERIFY_FAILED')
    after=totals()
    if before!=after: raise RuntimeError(f'PUBLIC_TOTALS_CHANGED {before}->{after}')
    metrics,audit=browser(expected)
    print(json.dumps({'ok':True,'action':'OUTING_TOP_FINAL','page_id':p['id'],'categories':cat_ids,'hero':metrics['hero'],'viewport':metrics['vw'],'scroll_width':metrics['sw'],'groups':audit,'public_before':before,'public_after':after},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
