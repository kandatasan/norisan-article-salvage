#!/usr/bin/env python3
from __future__ import annotations
import base64, html, json, os, re, time, urllib.parse, urllib.request
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

SITE='https://tsurikue.com'
BASE=SITE+'/wp-json/wp/v2'
PAGE_SLUG='odekake'
PAGE_TITLE='おでかけ'
MARK='/* tq-outing-v11-fullbleed */'
UA='tsurikue-outing-v11/1.0'
GROUPS={
    'hiroshima':('hiroshima','広島'),
    'etajima':('etajima','江田島'),
    'yamaguchi':('yamaguchi','山口'),
    'sanin':('sanin','山陰'),
    'far':(None,'ちょっと遠くへ'),
}
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode()


def req(path,method='GET',payload=None):
    headers={'Authorization':AUTH,'Accept':'application/json','User-Agent':UA}
    data=None
    if payload is not None:
        data=json.dumps(payload,ensure_ascii=False).encode(); headers['Content-Type']='application/json; charset=utf-8'
    r=urllib.request.Request(BASE+path,data=data,headers=headers,method=method)
    with urllib.request.urlopen(r,timeout=60) as x:
        return json.loads(x.read().decode()),dict(x.headers)


def clean(v):
    if isinstance(v,dict): v=v.get('raw') or v.get('rendered') or ''
    return html.unescape(re.sub(r'<[^>]+>','',v or '')).strip()


def counts():
    out={}
    for ep in ('posts','pages'):
        _,h=req(f'/{ep}?status=publish&per_page=1&_fields=id')
        out[ep]=int(h.get('X-WP-Total','0'))
    return out


def exact_page():
    q=urllib.parse.urlencode({'context':'edit','slug':PAGE_SLUG,'status':'publish','per_page':10,'_fields':'id,slug,status,title,content,link'})
    rows,_=req('/pages?'+q)
    if len(rows)!=1: raise RuntimeError(f'PAGE_MATCHES={len(rows)}')
    if clean(rows[0]['title'])!=PAGE_TITLE: raise RuntimeError('PAGE_TITLE_MISMATCH')
    return rows[0]


def terms(kind):
    rows=[]; page=1
    while True:
        q=urllib.parse.urlencode({'context':'edit','per_page':100,'page':page,'hide_empty':False,'_fields':'id,name,slug,parent,count'})
        batch,h=req(f'/{kind}?'+q); rows.extend(batch)
        if page>=int(h.get('X-WP-TotalPages','1')): return rows
        page+=1


def exact_slug(rows,slug):
    m=[x for x in rows if x.get('slug')==slug]
    if len(m)!=1: raise RuntimeError(f'TERM_SLUG_{slug}={len(m)}')
    return m[0]


def exact_name(rows,name):
    m=[x for x in rows if clean(x.get('name'))==name]
    if len(m)!=1: raise RuntimeError(f'TERM_NAME_{name}={len(m)}')
    return m[0]


def query_posts(cat_ids,tag_id):
    q=urllib.parse.urlencode({'categories':','.join(map(str,cat_ids)),'tags':tag_id,'status':'publish','per_page':100,'orderby':'date','order':'desc','_fields':'id,slug,link,title,date'})
    rows,_=req('/posts?'+q)
    return rows


def li_html(posts):
    return ''.join(f'<li><a href="{html.escape(p["link"],quote=True)}">{html.escape(clean(p["title"]))}</a></li>' for p in posts)


def inject_fullbleed(raw):
    css=(MARK+'\n'
         '.tq-outing-clean.tq-hero{max-width:none!important;width:auto!important;'
         'margin-left:calc(50% - 50vw)!important;margin-right:calc(50% - 50vw)!important;}\n'
         '@supports(width:100dvw){.tq-outing-clean.tq-hero{margin-left:calc(50% - 50dvw)!important;margin-right:calc(50% - 50dvw)!important;}}\n')
    if MARK in raw:
        return re.sub(r'/\* tq-outing-v11-fullbleed \*/.*?(?=</style>)',css,raw,count=1,flags=re.S)
    pos=raw.find('</style>')
    if pos<0: raise RuntimeError('STYLE_END_NOT_FOUND')
    return raw[:pos]+css+raw[pos:]


def patch_group(raw,key,tag_id,posts,cat_ids,tag_slug):
    raw=re.sub(r"\['"+re.escape(key)+r"',\s*\d+\]",f"['{key}',{tag_id}]",raw,count=1)
    raw=re.sub(r'categories=\d+,\d+&tags=',f'categories={cat_ids[0]},{cat_ids[1]}&tags=',raw)
    count_pat=r'(<span class="tq-count" data-count="'+re.escape(key)+r'">)\d+記事(</span>)'
    raw,n=re.subn(count_pat,rf'\g<1>{len(posts)}記事\g<2>',raw,count=1)
    if n!=1: raise RuntimeError('COUNT_NOT_FOUND_'+key)
    list_pat=r'(<ul class="wp-block-list tq-auto-list tq-auto-'+re.escape(key)+r'">).*?(</ul>)'
    raw,n=re.subn(list_pat,lambda m:m.group(1)+li_html(posts)+m.group(2),raw,count=1,flags=re.S)
    if n!=1: raise RuntimeError('LIST_NOT_FOUND_'+key)
    archive=f'{SITE}/tag/{tag_slug}/'
    text=f'「{GROUPS[key][1]}」の記事を全部見る →'
    details_pat=r'(<details class="wp-block-details tq-accordion tq-accordion-'+re.escape(key)+r'">.*?)(</details><!-- /wp:details -->)'
    m=re.search(details_pat,raw,re.S)
    if not m: raise RuntimeError('DETAILS_NOT_FOUND_'+key)
    block=m.group(1)
    block=re.sub(r'\n?<!-- tq-outing-far-tag-link:v1 -->\n?','\n',block)
    block=re.sub(r'<!-- wp:paragraph \{"className":"tq-(?:far-)?tag-link"\} --><p class="tq-(?:far-)?tag-link"><a href="[^"]+">.*?</a></p><!-- /wp:paragraph -->\n?','',block,flags=re.S)
    archive_block=(f'\n<!-- wp:paragraph {{"className":"tq-tag-link"}} -->'
                   f'<p class="tq-tag-link"><a href="{archive}">{text}</a></p><!-- /wp:paragraph -->\n')
    new=block+archive_block+m.group(2)
    raw=raw[:m.start()]+new+raw[m.end():]
    return raw,archive


def browser_metrics():
    o=Options(); o.add_argument('--headless=new'); o.add_argument('--no-sandbox'); o.add_argument('--disable-dev-shm-usage'); o.add_argument('--window-size=1440,1100')
    d=webdriver.Chrome(options=o)
    try:
        d.get(SITE+'/odekake/?tq_v11='+str(int(time.time()))); time.sleep(5)
        return d.execute_script('''
const out={vw:document.documentElement.clientWidth,sw:document.documentElement.scrollWidth};
const h=document.querySelector('.tq-outing-clean.tq-hero'); const r=h&&h.getBoundingClientRect();
out.hero=r?{left:r.left,right:r.right,width:r.width}:null; out.auto=document.documentElement.dataset.tqOutingAuto||null; out.groups={};
for (const key of ['hiroshima','etajima','yamaguchi','sanin','far']) {
 const links=[...document.querySelectorAll('.tq-auto-'+key+' a')].map(a=>a.href);
 const count=document.querySelector('[data-count="'+key+'"]'); const archive=document.querySelector('.tq-accordion-'+key+' .tq-tag-link a');
 out.groups[key]={links:links,count:count?count.textContent.trim():null,archive:archive?archive.href:null};
}
return out;''')
    finally: d.quit()


def normalize_links(xs):
    return [x.rstrip('/')+'/' for x in xs]


def main():
    before=counts(); page=exact_page(); cats=terms('categories'); tags=terms('tags')
    outing=exact_slug(cats,'sightseeing-leisure'); drive=exact_slug(cats,'drive')
    if int(drive.get('parent') or 0)!=int(outing['id']): raise RuntimeError('DRIVE_PARENT_MISMATCH')
    cat_ids=[int(outing['id']),int(drive['id'])]
    resolved={}
    for key,(slug,name) in GROUPS.items():
        term=exact_name(tags,name) if key=='far' else exact_slug(tags,slug)
        posts=query_posts(cat_ids,int(term['id']))
        if not posts: raise RuntimeError('EMPTY_'+key)
        resolved[key]={'term':term,'posts':posts}
    raw=(page.get('content') or {}).get('raw') or ''
    if 'tq-outing-clean' not in raw or raw.count('tq-accordion-')<5: raise RuntimeError('UNEXPECTED_LIVE_STRUCTURE')
    patched=inject_fullbleed(raw); archives={}
    for key,v in resolved.items():
        patched,archives[key]=patch_group(patched,key,int(v['term']['id']),v['posts'],cat_ids,v['term']['slug'])
    if patched==raw: raise RuntimeError('NO_CHANGES')
    req(f"/pages/{page['id']}",method='POST',payload={'content':patched})
    after_page=exact_page(); after_raw=(after_page.get('content') or {}).get('raw') or ''
    if MARK not in after_raw: raise RuntimeError('FULLBLEED_MARK_MISSING')
    after_counts=counts()
    if after_counts!=before: raise RuntimeError(f'PUBLIC_COUNTS_CHANGED {before}->{after_counts}')
    metrics=browser_metrics()
    if not metrics['hero'] or abs(metrics['hero']['left'])>2 or abs(metrics['hero']['right']-metrics['vw'])>2: raise RuntimeError('HERO_NOT_FULLBLEED '+json.dumps(metrics['hero']))
    if metrics['sw']>metrics['vw']+2: raise RuntimeError('HORIZONTAL_OVERFLOW')
    if metrics['auto']!='ready': raise RuntimeError('AUTO_INDEX_NOT_READY '+str(metrics['auto']))
    audit={}
    for key,v in resolved.items():
        expected=normalize_links([p['link'] for p in v['posts']]); got=normalize_links(metrics['groups'][key]['links'])
        if got!=expected: raise RuntimeError('LIST_MISMATCH_'+key+' '+json.dumps({'expected':expected,'got':got},ensure_ascii=False))
        if metrics['groups'][key]['count']!=f'{len(expected)}記事': raise RuntimeError('COUNT_MISMATCH_'+key)
        if not metrics['groups'][key]['archive'] or normalize_links([metrics['groups'][key]['archive']])[0]!=normalize_links([archives[key]])[0]: raise RuntimeError('ARCHIVE_MISMATCH_'+key)
        audit[key]={'tag_id':v['term']['id'],'tag_slug':v['term']['slug'],'count':len(expected),'slugs':[p['slug'] for p in v['posts']],'archive':archives[key]}
    print(json.dumps({'ok':True,'action':'OUTING_V11_FULL_HERO_PERFECT_ACCORDIONS','page_id':page['id'],'categories':cat_ids,'groups':audit,'hero':metrics['hero'],'viewport':metrics['vw'],'public_before':before,'public_after':after_counts},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
