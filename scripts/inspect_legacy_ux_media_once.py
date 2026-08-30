#!/usr/bin/env python3
from __future__ import annotations
import base64, json, os, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

SITE='https://tsurikue.com'
OUT=Path('reports/legacy-ux-media-inspection')
AFTER='2026-07-01T00:00:00'
BEFORE='2026-08-30T14:30:00'

def auth_header(user,password):
    return 'Basic '+base64.b64encode(f'{user}:{password}'.encode()).decode()

def get_json(url,auth):
    req=urllib.request.Request(url,headers={'Accept':'application/json','Authorization':auth,'User-Agent':'tsurikue-jul-aug-ux-media-inspector/1.0'},method='GET')
    with urllib.request.urlopen(req,timeout=45) as r:
        return json.loads(r.read().decode()),dict(r.headers)

def preview_url(row):
    sizes=((row.get('media_details') or {}).get('sizes') or {})
    for key in ('medium','medium_large','thumbnail'):
        u=(sizes.get(key) or {}).get('source_url')
        if u: return u
    return row.get('source_url') or ''

def fetch_preview(item):
    row,dest=item
    url=preview_url(row)
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'tsurikue-jul-aug-ux-media-inspector/1.0'},method='GET')
        with urllib.request.urlopen(req,timeout=20) as r: dest.write_bytes(r.read())
        return 'ok'
    except Exception as exc:
        return f'error:{type(exc).__name__}'

def main():
    user=os.environ.get('TSURIKUE_WP_USER'); password=os.environ.get('TSURIKUE_WP_APP_PASSWORD')
    if not user or not password: raise SystemExit('BLOCKED_MISSING_SECRETS')
    auth=auth_header(user,password)
    params={'context':'edit','per_page':'100','page':'1','orderby':'date','order':'asc','media_type':'image','after':AFTER,'before':BEFORE,'_fields':'id,date,slug,source_url,alt_text,caption,media_details'}
    rows,h=get_json(f'{SITE}/wp-json/wp/v2/media?{urllib.parse.urlencode(params)}',auth)
    rows=list(rows)
    pages=int(h.get('X-WP-TotalPages','1'))
    for page in range(2,pages+1):
        params['page']=str(page); part,_=get_json(f'{SITE}/wp-json/wp/v2/media?{urllib.parse.urlencode(params)}',auth); rows.extend(part)
    OUT.mkdir(parents=True,exist_ok=True); img=OUT/'images'; img.mkdir(exist_ok=True)
    jobs=[]; manifest=[]
    for row in rows:
        src=row.get('source_url') or ''; prev=preview_url(row)
        if not src or not prev: continue
        fn=Path(urllib.parse.urlparse(src).path).name; pfn=Path(urllib.parse.urlparse(prev).path).name; dest=img/f"{row.get('id')}_{pfn}"
        jobs.append((row,dest)); details=row.get('media_details') or {}; cap=row.get('caption') or {}
        manifest.append({'id':row.get('id'),'date':row.get('date'),'slug':row.get('slug'),'filename':fn,'source_url':src,'preview_url':prev,'alt_text':row.get('alt_text') or '','caption':(cap.get('raw') or cap.get('rendered') or '') if isinstance(cap,dict) else str(cap),'width':details.get('width'),'height':details.get('height'),'artifact_file':str(dest),'download':'pending'})
    by_id={int(x['id']):x for x in manifest}
    with ThreadPoolExecutor(max_workers=12) as ex:
        futures={ex.submit(fetch_preview,j):int(j[0]['id']) for j in jobs}
        for f in as_completed(futures): by_id[futures[f]]['download']=f.result()
    result={'mode':'READ_ONLY','wordpress_write_count':0,'date_window':f'{AFTER}..{BEFORE}','media_scanned':len(rows),'downloaded':sum(x['download']=='ok' for x in manifest),'items':manifest}
    (OUT/'manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# July-August UX media inspection','','- mode: **READ ONLY**','- wordpress_write_count: **0**',f"- media_scanned: **{len(rows)}**",f"- downloaded: **{result['downloaded']}**",'', '## Media']
    for x in manifest: lines.append(f"- #{x['id']} `{x['filename']}` | {x['date']} | {x['width']}x{x['height']} | alt: {x['alt_text'] or '(empty)'} | {x['download']}")
    (OUT/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'mode':'READ_ONLY','media_scanned':len(rows),'downloaded':result['downloaded'],'wordpress_write_count':0},ensure_ascii=False))
if __name__=='__main__': main()
