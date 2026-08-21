#!/usr/bin/env python3
from __future__ import annotations
import base64,hashlib,html,json,os,re,urllib.parse,urllib.request
from pathlib import Path
SITE_URL='https://tsurikue.com'; SLUG='gulpalivepowder'; SALVAGE_MARKER='<!-- old-tsurikue-salvage:v1 slug=gulpalivepowder -->'; REPORT_DIR=Path('reports/gulpalivepowder-current-body'); UA='tsurikue-gulpalivepowder-inspect/1.0'
def auth_header(u,p): return 'Basic '+base64.b64encode(f'{u}:{p}'.encode()).decode()
def get_json(url,a):
    req=urllib.request.Request(url,headers={'Accept':'application/json','Authorization':a,'User-Agent':UA},method='GET')
    with urllib.request.urlopen(req,timeout=45) as r: return json.loads(r.read().decode())
def raw(row,k):
    v=row.get(k) or {}; return (v.get('raw') or v.get('rendered') or '') if isinstance(v,dict) else str(v)
def media_ids(c):
    out=[]
    for m in re.finditer(r'wp-image-(\d+)|\"id\"\s*:\s*(\d+)',c):
        i=int(m.group(1) or m.group(2));
        if i not in out: out.append(i)
    return out
def main():
    u=os.environ.get('TSURIKUE_WP_USER'); p=os.environ.get('TSURIKUE_WP_APP_PASSWORD')
    if not u or not p: raise SystemExit('BLOCKED_MISSING_SECRETS')
    a=auth_header(u,p); q=urllib.parse.urlencode({'context':'edit','status':'draft','slug':SLUG,'per_page':'100','_fields':'id,slug,status,title,content,featured_media'})
    rows=get_json(f'{SITE_URL}/wp-json/wp/v2/posts?{q}',a); exact=[r for r in rows if r.get('slug')==SLUG]
    if len(exact)!=1: raise RuntimeError(f'expected exactly one draft; found {len(exact)}')
    row=exact[0]; content=raw(row,'content')
    if SALVAGE_MARKER not in content: raise RuntimeError('salvage marker missing')
    ids=media_ids(content); sha=hashlib.sha256(content.encode()).hexdigest(); title=html.unescape(raw(row,'title'))
    REPORT_DIR.mkdir(parents=True,exist_ok=True); (REPORT_DIR/'content.html').write_text(content,encoding='utf-8')
    s=f'''# gulpalivepowder current WordPress draft body\n\n- mode: **READ ONLY**\n- wordpress_write_count: **0**\n- post_id: **{row.get('id')}**\n- slug: **{row.get('slug')}**\n- status: **{row.get('status')}**\n- title: {title}\n- featured_media: **{int(row.get('featured_media') or 0)}**\n- article_media_ids: **{', '.join(map(str,ids)) if ids else '(none)'}**\n- content_sha256: `{sha}`\n- youtube_id_present: **{'Q5ePEt5uQYk' in content}**\n\n## Current body\n\n```html\n{content}\n```\n'''
    (REPORT_DIR/'summary.md').write_text(s,encoding='utf-8'); print(s); return 0
if __name__=='__main__': raise SystemExit(main())
