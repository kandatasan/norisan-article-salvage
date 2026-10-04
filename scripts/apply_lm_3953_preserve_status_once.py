#!/usr/bin/env python3
"""One-shot exact-state update for LM post 3953. Preserves draft/publish status exactly."""
from __future__ import annotations
import base64, hashlib, html, json, os, urllib.parse, urllib.request
from pathlib import Path

SITE='https://tsurikue.com'
POST_ID=3953
SLUG='lmdrive'
OLD_TITLE='レクサスLMを試乗レビュー｜4人乗りEXECUTIVEは「ぶっ飛んだ高級車」だった'
OLD_HASH='2bd884a7bcd1ff2ac1ec755f4e1a36261c3a4856f31315f7d92a6e61a18d3011'
OLD_FEATURED=1623
PACKAGE=Path('editorial/2026-10-04-lm-immersive-tighten/config.json')
UA='tsurikue-lm-3953-preserve-status/1.0'


def auth_header(user,password):
    return 'Basic '+base64.b64encode(f'{user}:{password}'.encode()).decode()


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
    if isinstance(v,dict): return v.get('raw') or v.get('rendered') or ''
    return str(v)


def public_counts(auth):
    out={}
    for endpoint in ['posts','pages']:
        q=urllib.parse.urlencode({'context':'edit','status':'publish','per_page':1,'_fields':'id'})
        _,h=get_json(f'{SITE}/wp-json/wp/v2/{endpoint}?{q}',auth)
        out[endpoint]=int(h.get('X-WP-Total','0'))
    out['total']=out['posts']+out['pages']
    return out


def fetch_post(auth):
    q=urllib.parse.urlencode({'context':'edit','_fields':'id,slug,status,title,content,featured_media'})
    row,_=get_json(f'{SITE}/wp-json/wp/v2/posts/{POST_ID}?{q}',auth)
    return row


def validate_media(cfg,auth):
    expected={int(k):v for k,v in cfg['expected_media'].items()}
    if int(cfg['featured_media']) not in expected: raise RuntimeError('new featured media not verified')
    for mid,path in expected.items():
        q=urllib.parse.urlencode({'context':'edit','_fields':'id,source_url'})
        row,_=get_json(f'{SITE}/wp-json/wp/v2/media/{mid}?{q}',auth)
        actual=urllib.parse.unquote(urllib.parse.urlparse(row.get('source_url') or '').path).casefold()
        if actual!=path.casefold(): raise RuntimeError(f'media mismatch {mid}: {actual}')
    return len(expected)


def main():
    user=os.environ.get('TSURIKUE_WP_USER'); password=os.environ.get('TSURIKUE_WP_APP_PASSWORD')
    if not user or not password: raise SystemExit('missing WordPress secrets')
    auth=auth_header(user,password)
    cfg=json.loads(PACKAGE.read_text(encoding='utf-8'))
    body=(PACKAGE.parent/cfg['content_file']).read_text(encoding='utf-8').strip()+'\n'
    full=cfg['salvage_marker']+'\n'+cfg['editorial_marker']+'\n'+body
    before_counts=public_counts(auth)
    before=fetch_post(auth)
    before_status=before.get('status')
    before_content=raw(before,'content')
    audit={
        'before_status':before_status,
        'before_hash':hashlib.sha256(before_content.encode()).hexdigest(),
        'before_featured':int(before.get('featured_media') or 0),
        'before_title':html.unescape(raw(before,'title')),
        'before_counts':before_counts,
    }
    print(json.dumps({'audit_before':audit},ensure_ascii=False,indent=2))
    if before.get('id')!=POST_ID or before.get('slug')!=SLUG: raise RuntimeError('id/slug mismatch')
    if before_status not in {'draft','publish'}: raise RuntimeError('status not allowed: '+str(before_status))
    if audit['before_title']!=OLD_TITLE: raise RuntimeError('title changed; refusing overwrite')
    if audit['before_hash'].casefold()!=OLD_HASH: raise RuntimeError('content changed; refusing overwrite')
    if audit['before_featured']!=OLD_FEATURED: raise RuntimeError('featured media changed; refusing overwrite')
    checked=validate_media(cfg,auth)
    payload={'title':cfg['title'],'slug':cfg['slug'],'content':full,'featured_media':int(cfg['featured_media'])}
    updated=post_json(f'{SITE}/wp-json/wp/v2/posts/{POST_ID}',auth,payload)
    if updated.get('status')!=before_status: raise RuntimeError('status changed in update response')
    after=fetch_post(auth); after_counts=public_counts(auth)
    if after_counts!=before_counts: raise RuntimeError('published counts changed')
    if after.get('status')!=before_status: raise RuntimeError('status changed after update')
    if after.get('slug')!=cfg['slug'] or html.unescape(raw(after,'title'))!=cfg['title']: raise RuntimeError('title/slug mismatch after update')
    if int(after.get('featured_media') or 0)!=int(cfg['featured_media']): raise RuntimeError('featured media mismatch after update')
    if raw(after,'content').strip()!=full.strip(): raise RuntimeError('content mismatch after update')
    report={
        'action':'UPDATE_PRESERVE_STATUS',
        'post_id':POST_ID,
        'slug':SLUG,
        'status_before':before_status,
        'status_after':after.get('status'),
        'featured_before':OLD_FEATURED,
        'featured_after':int(cfg['featured_media']),
        'confirmed_media_checked':checked,
        'public_before':before_counts['total'],
        'public_after':after_counts['total'],
        'publish_count':0,
        'status_change_count':0,
        'media_upload_count':0,
        'content_sha256':hashlib.sha256(raw(after,'content').encode()).hexdigest(),
    }
    out=Path('reports/lmdrive-preserve-status-update'); out.mkdir(parents=True,exist_ok=True)
    (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'summary.md').write_text('\n'.join([
        '# lmdrive exact-state update', '',
        f"- action: **{report['action']}**",
        f"- post_id: **{POST_ID}**",
        f"- status_before: **{before_status}**",
        f"- status_after: **{after.get('status')}**",
        f"- featured_before: **{OLD_FEATURED}**",
        f"- featured_after: **{cfg['featured_media']}**",
        f"- confirmed_media_checked: **{checked}**",
        f"- public_before: **{before_counts['total']}**",
        f"- public_after: **{after_counts['total']}**",
        '- publish_count: **0**',
        '- status_change_count: **0**',
        '- media_upload_count: **0**',
        f"- content_sha256: `{report['content_sha256']}`",
    ])+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
