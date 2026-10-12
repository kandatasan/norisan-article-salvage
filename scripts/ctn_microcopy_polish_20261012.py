#!/usr/bin/env python3
"""Only six CTA microcopy replacements; no other article edits. Live preflight + QA."""
from __future__ import annotations
import base64,hashlib,importlib.util,json,os,sys,urllib.parse,urllib.request
from pathlib import Path

CHANGES=[[2240,"ux-mitsumori","9e004747da93b15ec981521de26203ba19924ff9f0ec5a572ea925a8d42d6a6d","やり取りは最大3社。売却は査定額を見てから。","売るかどうかは、査定額を見てから。"],[2329,"ux300h","d206b74cc65ade9b6701f219c363cb13f5d5a223ddbe123fa29db3ba869dbb92","やり取りは最大3社。電話の負担を抑えて比較。","売るかどうかは、金額を見てから決めればOK。"],[2962,"lexus-ux-discount","ba4e38b0594f2deb03509e2523a76ae9f0b308b94b4c726097443a7bba38120d","やり取りは最大3社。売却は納得してから。","売却を決めるのは、査定額を見てから。"],[3570,"lexus-ux-emotional-explorer","e2fa856b99e1239ac12ac37307dd4a5c7f61ca14a0b85d779be096e11cd27f11","やり取りは最大3社。買い替えは予算を見てから。","売るかどうかは、査定額に納得してから。"],[3604,"lexus-ux-vs-nx","4ae2c1e61aa8a935e439e48c603178703c4d57d958c693a17749121b2eaaa6b6","やり取りは最大3社。売却するかは金額を見てから。","売るかどうかは、査定額を見てから。"],[3767,"landcruiser-fj-price","5c53b28ddfe1c8a33460290a9948510f6c09c2a414bfefabb83b45d7e4d2f599","やり取りは最大3社。売却は査定額を見てから。","CTNはやり取りする買取店が最大3社。売却は金額を見てから。"]]
SITE='https://tsurikue.com'
TEMPLATE='<!-- wp:paragraph {"align":"center"} -->\n<p class="has-text-align-center"><strong>%s</strong></p>\n<!-- /wp:paragraph -->'
def sha(s):return hashlib.sha256(s.encode('utf-8')).hexdigest()
def req(url,auth,payload=None):
    headers={'Authorization':auth,'User-Agent':'tsurikue-ctn-final-polish/1.0','Accept':'application/json'}
    if payload is not None:headers['Content-Type']='application/json; charset=utf-8'
    r=urllib.request.Request(SITE+url,method='POST' if payload is not None else 'GET',
        data=json.dumps(payload,ensure_ascii=False).encode('utf-8') if payload is not None else None,headers=headers)
    with urllib.request.urlopen(r,timeout=60) as res:return json.loads(res.read()),dict(res.headers)
def get(pid,auth):
    q=urllib.parse.urlencode({'context':'edit','_fields':'id,slug,status,title,content,featured_media,categories,author'})
    return req(f'/wp-json/wp/v2/posts/{pid}?{q}',auth)[0]
def count(auth):
    q=urllib.parse.urlencode({'context':'edit','status':'publish','per_page':'1','_fields':'id'})
    return int(req('/wp-json/wp/v2/posts?'+q,auth)[1]['X-WP-Total'])
def transform(s,key):
    pid,slug,expected,old,new=key
    before,after=TEMPLATE%old,TEMPLATE%new
    if s.count(before)!=1:raise RuntimeError(f'{slug}: exact original microcopy not found once')
    out=s.replace(before,after,1)
    if out.count(TEMPLATE%new)!=1:raise RuntimeError(f'{slug}: duplicate new microcopy')
    if s.count('<!-- wp:')!=out.count('<!-- wp:') or s.count('<!-- /wp:')!=out.count('<!-- /wp:'):
        raise RuntimeError(f'{slug}: Gutenberg count changed')
    return out
def execute(mode):
    user=os.environ.get('TSURIKUE_WP_USER');password=os.environ.get('TSURIKUE_WP_APP_PASSWORD')
    if not user or not password:raise RuntimeError('Missing WordPress secrets')
    auth='Basic '+base64.b64encode((user+':'+password).encode()).decode()
    total=count(auth)
    if mode=='inspect':
        for key in CHANGES:
            row=get(key[0],auth)
            content=row['content']['raw']
            print('CURRENT_SHA',key[0],key[1],sha(content),'OLD_MICRO_COUNT',content.count(TEMPLATE%key[3]),'STATUS',row['status'],'LEN',len(content),flush=True)
        return
    prepared=[]
    for key in CHANGES:
        r=get(key[0],auth)
        if (r['id'],r['slug'],r['status'])!=(key[0],key[1],'publish'):raise RuntimeError(f'{key[1]}: identity or status mismatch')
        old=r['content']['raw']
        if sha(old)!=key[2]:raise RuntimeError(f'{key[1]}: old SHA mismatch; no edits made')
        new=transform(old,key)
        prepared.append((key,r,new))
    print(f'PREFLIGHT_OK six exact replacements; published posts={total}',flush=True)
    if mode=='check':return
    done=[]
    try:
        for key,oldrow,content in prepared:
            current=get(key[0],auth)
            if sha(current['content']['raw'])!=key[2] or current['status']!='publish':
                raise RuntimeError(f'{key[1]}: concurrent edit; stop')
            done.append((key,oldrow,content))
            req(f'/wp-json/wp/v2/posts/{key[0]}',auth,{'content':content})
            check=get(key[0],auth)
            for field in ('id','slug','status','title','featured_media','categories','author'):
                if check[field]!=oldrow[field]:raise RuntimeError(f'{key[1]}: protected field changed')
            if check['content']['raw']!=content:raise RuntimeError(f'{key[1]}: exact after-content mismatch')
            if key[4] not in check['content']['rendered']:raise RuntimeError(f'{key[1]}: new microcopy missing from rendered HTML')
            print('POLISH_LIVE_VERIFIED',key[0],key[1],flush=True)
        if count(auth)!=total:raise RuntimeError('published post count changed')
    except Exception:
        for key,oldrow,content in reversed(done):
            try:
                if sha(get(key[0],auth)['content']['raw'])==sha(content):
                    req(f'/wp-json/wp/v2/posts/{key[0]}',auth,{'content':oldrow['content']['raw']})
                    print('ROLLBACK',key[1],flush=True)
            except Exception as e:print('ROLLBACK_ERROR',key[1],str(e),flush=True)
        raise
    # Verify all 19 CTA posts and all four preserve-only posts remain published and render their correct microcopy.
    spec=importlib.util.spec_from_file_location('ctn_campaign','scripts/ctn_microcopy_safe_20261012.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    final={x[0]:x[4] for x in CHANGES}
    for target in mod.TARGETS:
        pid,slug,_,microcopy,part=target
        row=get(pid,auth)
        if row['status']!='publish' or row['slug']!=slug:raise RuntimeError(f'{slug}: QA identity/status')
        rendered=row['content']['rendered']
        if final.get(pid,microcopy) not in rendered:raise RuntimeError(f'{slug}: QA rendered microcopy missing')
        if (f'[blog_parts id="{2184 if pid==3863 else part}"]' not in row['content']['raw']):
            raise RuntimeError(f'{slug}: QA blog part missing')
        print('QA_19_OK',pid,slug,flush=True)
    for pid,slug in mod.UNCHANGED:
        row=get(pid,auth)
        if row['status']!='publish' or row['slug']!=slug:raise RuntimeError(f'{slug}: preserve QA failed')
        print('QA_PRESERVE_OK',pid,slug,flush=True)
    print('FINAL_SUCCESS 19 optimized 4 preserved 0 state changes',flush=True)
if __name__=='__main__':
    mode=sys.argv[1] if len(sys.argv)>1 else 'check'
    if mode not in ('check','apply','inspect'):raise SystemExit('Expected check, apply, or inspect')
    execute(mode)
