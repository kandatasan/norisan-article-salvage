#!/usr/bin/env python3
"""Create one Lexus editorial WordPress post as draft only. Never updates/deletes/publishes."""
from __future__ import annotations
import argparse, base64, hashlib, html, json, os, re, urllib.parse, urllib.request
from pathlib import Path

SITE='https://tsurikue.com'
UA='tsurikue-lexus-editorial-create/1.0'
STATUSES=['draft','publish','pending','private','future']


def auth_header(user,password):
    token=base64.b64encode(f'{user}:{password}'.encode()).decode()
    return f'Basic {token}'


def get_json(url,auth):
    req=urllib.request.Request(url,headers={'Accept':'application/json','Authorization':auth,'User-Agent':UA},method='GET')
    with urllib.request.urlopen(req,timeout=45) as r:
        return json.loads(r.read().decode()),dict(r.headers)


def post_json(url,auth,payload):
    req=urllib.request.Request(url,data=json.dumps(payload,ensure_ascii=False).encode(),headers={'Accept':'application/json','Content-Type':'application/json; charset=utf-8','Authorization':auth,'User-Agent':UA},method='POST')
    with urllib.request.urlopen(req,timeout=60) as r:
        return json.loads(r.read().decode())


def raw(row,key):
    v=row.get(key) or {}
    if isinstance(v,dict): return html.unescape(v.get('raw') or v.get('rendered') or '')
    return str(v)


def norm(s):
    return re.sub(r'\s+','',html.unescape(s or '')).casefold()


def load(config_path):
    cfg=json.loads(config_path.read_text(encoding='utf-8'))
    body=(config_path.parent/cfg['content_file']).read_text(encoding='utf-8').strip()+'\n'
    full=cfg['salvage_marker']+'\n'+cfg['editorial_marker']+'\n'+body
    return cfg,body,full


def qposts(auth,params):
    q=urllib.parse.urlencode(params)
    rows,_=get_json(f'{SITE}/wp-json/wp/v2/posts?{q}',auth)
    return rows


def public_counts(auth):
    out={}
    for endpoint in ['posts','pages']:
        q=urllib.parse.urlencode({'context':'edit','status':'publish','per_page':1,'_fields':'id'})
        _,h=get_json(f'{SITE}/wp-json/wp/v2/{endpoint}?{q}',auth)
        out[endpoint]=int(h.get('X-WP-Total','0'))
    out['total']=out['posts']+out['pages']
    return out


def validate_content(cfg,body):
    if '<h1' in body.casefold() or '"level":1' in body:
        raise RuntimeError('body H1 is forbidden')
    for banned in ['普通に','🤣','😏','🔥']:
        if banned in body: raise RuntimeError('banned wording/emoji present: '+banned)
    if body.count('かなり')>1 or body.count('めちゃくちゃ')>1:
        raise RuntimeError('intensifier overuse')
    h2=re.findall(r'<h2[^>]*>(.*?)</h2>',body,re.I|re.S)
    h2=[re.sub('<[^>]+>','',x).strip() for x in h2]
    if h2 != cfg.get('expected_h2',[]):
        raise RuntimeError('H2 structure mismatch: '+repr(h2))
    for marker,expected in (cfg.get('required_affiliate_counts') or {}).items():
        actual=body.count(marker)
        if actual!=int(expected): raise RuntimeError(f'affiliate count mismatch {marker}: {actual}!={expected}')
    for mid in (cfg.get('expected_media') or {}):
        if int(mid)!=int(cfg.get('featured_media') or 0) and f'wp-image-{mid}' not in body:
            raise RuntimeError('expected body media missing: '+str(mid))


def validate_media(cfg,auth):
    expected={int(k):v for k,v in (cfg.get('expected_media') or {}).items()}
    featured=int(cfg.get('featured_media') or 0)
    if featured not in expected: raise RuntimeError('featured_media is not verified')
    for mid,path in expected.items():
        q=urllib.parse.urlencode({'context':'edit','_fields':'id,status,source_url'})
        row,_=get_json(f'{SITE}/wp-json/wp/v2/media/{mid}?{q}',auth)
        actual=urllib.parse.unquote(urllib.parse.urlparse(row.get('source_url') or '').path).casefold()
        if actual!=path.casefold(): raise RuntimeError(f'media mismatch id={mid}: {actual}')
    return len(expected)


def all_exact_slug(auth,slug):
    out=[]
    for status in STATUSES:
        out += qposts(auth,{'context':'edit','status':status,'slug':slug,'per_page':20,'_fields':'id,slug,status,title,content,featured_media'})
    return out


def exact_title_conflicts(auth,title,allowed_ids):
    found=[]
    for status in STATUSES:
        rows=qposts(auth,{'context':'edit','status':status,'search':title,'per_page':100,'_fields':'id,slug,status,title'})
        for r in rows:
            if int(r.get('id') or 0) in allowed_ids: continue
            if norm(raw(r,'title'))==norm(title): found.append(r)
    return found


def write_report(slug,data):
    out=Path('reports')/f'{slug}-create-draft'; out.mkdir(parents=True,exist_ok=True)
    (out/'result.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=[f'# {slug} Lexus editorial create', '', f"- action: **{data.get('action')}**", f"- post_id: **{data.get('post_id','unknown')}**", f"- slug: **{slug}**", f"- status: **{data.get('status','unknown')}**", f"- title: {data.get('title','')}", f"- featured_media: **{data.get('featured_media','unknown')}**", f"- confirmed_media_checked: **{data.get('confirmed_media_checked','unknown')}**", f"- public_before: **{data.get('public_before','unknown')}**", f"- public_after: **{data.get('public_after','unknown')}**", f"- wordpress_create_count: **{data.get('wordpress_create_count',0)}**", '- wordpress_update_count: **0**', '- wordpress_delete_count: **0**', '- publish_count: **0**']
    if data.get('content_sha256'): lines.append(f"- content_sha256: `{data['content_sha256']}`")
    if data.get('error'): lines.append(f"- error: `{data['error']}`")
    (out/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def apply(config_path):
    cfg,body,full=load(config_path); slug=cfg['slug']; title=cfg['title']
    data={'action':'BLOCKED','slug':slug,'title':title,'wordpress_create_count':0}
    try:
        validate_content(cfg,body)
        user=os.environ.get('TSURIKUE_WP_USER'); password=os.environ.get('TSURIKUE_WP_APP_PASSWORD')
        if not user or not password: raise RuntimeError('missing WordPress secrets')
        auth=auth_header(user,password)
        before_counts=public_counts(auth)
        checked=validate_media(cfg,auth)
        existing=all_exact_slug(auth,slug)
        if existing:
            if len(existing)==1:
                row=existing[0]
                same=(row.get('status')=='draft' and raw(row,'title')==title and raw(row,'content').strip()==full.strip() and int(row.get('featured_media') or 0)==int(cfg['featured_media']))
                if same:
                    data.update(action='ALREADY_CREATED',post_id=int(row['id']),status='draft',featured_media=int(cfg['featured_media']),confirmed_media_checked=checked,public_before=before_counts['total'],public_after=before_counts['total'],content_sha256=hashlib.sha256(raw(row,'content').encode()).hexdigest())
                    write_report(slug,data); return data
            raise RuntimeError('exact slug already exists with different state/content')
        allowed={int(x) for x in (cfg.get('allowed_related_post_ids') or [])}
        conflicts=exact_title_conflicts(auth,title,allowed)
        if conflicts: raise RuntimeError('exact title conflict exists: '+repr([(r.get('id'),r.get('slug'),r.get('status')) for r in conflicts]))
        payload={'title':title,'slug':slug,'content':full,'status':'draft','featured_media':int(cfg['featured_media'])}
        created=post_json(f'{SITE}/wp-json/wp/v2/posts',auth,payload)
        data['wordpress_create_count']=1
        post_id=int(created.get('id') or 0)
        if not post_id or created.get('status')!='draft' or created.get('slug')!=slug:
            raise RuntimeError('create response validation failed')
        q=urllib.parse.urlencode({'context':'edit','_fields':'id,slug,status,title,content,featured_media'})
        after,_=get_json(f'{SITE}/wp-json/wp/v2/posts/{post_id}?{q}',auth)
        after_counts=public_counts(auth)
        if after_counts!=before_counts: raise RuntimeError('published counts changed')
        if after.get('status')!='draft' or after.get('slug')!=slug or raw(after,'title')!=title or raw(after,'content').strip()!=full.strip() or int(after.get('featured_media') or 0)!=int(cfg['featured_media']):
            raise RuntimeError('post-create GET validation failed')
        data.update(action='CREATE_DRAFT',post_id=post_id,status='draft',featured_media=int(cfg['featured_media']),confirmed_media_checked=checked,public_before=before_counts['total'],public_after=after_counts['total'],content_sha256=hashlib.sha256(raw(after,'content').encode()).hexdigest())
        write_report(slug,data); return data
    except Exception as exc:
        data['error']=str(exc); write_report(slug,data); raise


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--config',required=True); args=ap.parse_args();
    result=apply(Path(args.config)); print(json.dumps(result,ensure_ascii=False,indent=2)); return 0

if __name__=='__main__': raise SystemExit(main())
