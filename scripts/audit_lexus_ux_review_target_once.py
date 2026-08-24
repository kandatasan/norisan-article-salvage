#!/usr/bin/env python3
from __future__ import annotations
import base64, html, json, os, re, urllib.parse, urllib.request
from pathlib import Path

SITE='https://tsurikue.com'
SOURCE_POST_ID=2517
REPORT=Path('reports/lexus-ux-review-audit')
STATUSES=['draft','publish','pending','private','future']
SLUGS=['ux','lexus-ux-review','ux-review','lexus-ux-evaluation']


def auth_header(user,password):
    token=base64.b64encode(f'{user}:{password}'.encode()).decode()
    return f'Basic {token}'


def get_json(url,auth):
    req=urllib.request.Request(url,headers={'Accept':'application/json','Authorization':auth,'User-Agent':'lexus-ux-review-audit/1.0'},method='GET')
    with urllib.request.urlopen(req,timeout=45) as r:
        return json.loads(r.read().decode()),dict(r.headers)


def raw(row,key):
    v=row.get(key) or {}
    return html.unescape(v.get('raw') or v.get('rendered') or '') if isinstance(v,dict) else str(v)


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


def main():
    user=os.environ.get('TSURIKUE_WP_USER'); password=os.environ.get('TSURIKUE_WP_APP_PASSWORD')
    if not user or not password: raise SystemExit('BLOCKED_MISSING_SECRETS')
    auth=auth_header(user,password)
    counts=public_counts(auth)
    found={}
    seen={}
    for status in STATUSES:
        rows=qposts(auth,{'context':'edit','status':status,'search':'レクサスUX','per_page':100,'orderby':'modified','order':'desc','_fields':'id,slug,status,title,featured_media'})
        found[status]=[]
        for r in rows:
            item={'id':r.get('id'),'slug':r.get('slug'),'status':r.get('status'),'title':raw(r,'title'),'featured_media':int(r.get('featured_media') or 0)}
            found[status].append(item); seen[item['id']]=item
        for slug in SLUGS:
            rows2=qposts(auth,{'context':'edit','status':status,'slug':slug,'per_page':20,'_fields':'id,slug,status,title,featured_media'})
            for r in rows2:
                item={'id':r.get('id'),'slug':r.get('slug'),'status':r.get('status'),'title':raw(r,'title'),'featured_media':int(r.get('featured_media') or 0)}
                if item['id'] not in seen:
                    found[status].append(item); seen[item['id']]=item

    q=urllib.parse.urlencode({'context':'edit','_fields':'id,slug,status,title,content,featured_media'})
    src,_=get_json(f'{SITE}/wp-json/wp/v2/posts/{SOURCE_POST_ID}?{q}',auth)
    if src.get('status')!='publish' or src.get('slug')!='ux-koukai':
        raise RuntimeError('source UX post identity mismatch')
    content=raw(src,'content')
    ids=[]
    feat=int(src.get('featured_media') or 0)
    if feat: ids.append(feat)
    ids += [int(x) for x in re.findall(r'wp-image-(\d+)',content)]
    ids=list(dict.fromkeys(ids))
    media=[]
    for mid in ids[:40]:
        mq=urllib.parse.urlencode({'context':'edit','_fields':'id,status,source_url,alt_text,caption,title,media_details'})
        m,_=get_json(f'{SITE}/wp-json/wp/v2/media/{mid}?{mq}',auth)
        details=m.get('media_details') or {}
        media.append({'id':mid,'source_url':m.get('source_url') or '', 'alt_text':m.get('alt_text') or '', 'title':raw(m,'title'), 'width':details.get('width'), 'height':details.get('height'), 'is_featured':mid==feat})

    result={'result':'SUCCESS','wordpress_write_count':0,'public_counts':counts,'candidate_posts':found,'source_post':{'id':src.get('id'),'slug':src.get('slug'),'status':src.get('status'),'title':raw(src,'title'),'featured_media':feat},'source_media':media}
    REPORT.mkdir(parents=True,exist_ok=True)
    (REPORT/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# Lexus UX review target/media audit','',f'- result: **SUCCESS**',f'- wordpress_write_count: **0**',f"- public_total: **{counts['total']}**",'', '## Candidate posts']
    for st in STATUSES:
        lines.append(f'### {st}')
        if not found[st]: lines.append('- none')
        for x in found[st]: lines.append(f"- id={x['id']} slug={x['slug']} title={x['title']} featured_media={x['featured_media']}")
    lines += ['', '## Verified media referenced by published ux-koukai']
    for m in media:
        lines.append(f"- id={m['id']} featured={m['is_featured']} {m['width']}x{m['height']} alt={m['alt_text']} title={m['title']} url={m['source_url']}")
    (REPORT/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0

if __name__=='__main__': raise SystemExit(main())
