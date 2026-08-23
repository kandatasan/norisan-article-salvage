#!/usr/bin/env python3
from __future__ import annotations
import re, time, urllib.request
from pathlib import Path

URL='https://tsurikue.com/ux300h/'
REPORT=Path('reports/ux300h-public-cache-probe')
MARKERS=['お宝UX、まだ表に出ていないかも。','非公開在庫も含めて中古UXを探してみる','高く売りたい。でも電話ラッシュはいらない。']

def fetch(url, headers=None):
    req=urllib.request.Request(url,headers=headers or {'User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(req,timeout=30) as r:
        return r.status,dict(r.headers.items()),r.read().decode('utf-8','replace')

def summarize(name,status,headers,body):
    plugins=sorted(set(re.findall(r'/wp-content/plugins/([^/\"\'?#]+)',body,re.I)))
    cache_comments=[x.strip() for x in re.findall(r'<!--(.*?)-->',body,re.S|re.I) if re.search(r'cache|cached|litespeed|rocket|speed',x,re.I)]
    body_classes=re.findall(r'<body[^>]+class=["\']([^"\']+)',body,re.I)
    lines=[f'## {name}',f'- status: **{status}**',f"- cache-control: `{headers.get('Cache-Control','')}`",f"- age: `{headers.get('Age','')}`",f"- x-cache: `{headers.get('X-Cache','')}`",f"- x-cache-status: `{headers.get('X-Cache-Status','')}`",f'- body_length: **{len(body)}**',f"- postid-2329: **{'YES' if 'postid-2329' in body else 'NO'}**',f"- plugins_seen: `{', '.join(plugins)}`",f"- body_class: `{body_classes[0][:300] if body_classes else ''}`"]
    lines += [f"- {'OK' if m in body else 'MISSING'}: {m}" for m in MARKERS]
    if cache_comments:
        lines.append('- cache_comments:')
        for c in cache_comments[:10]: lines.append('  - `'+re.sub(r'\s+',' ',c)[:400]+'`')
    else: lines.append('- cache_comments: `(none found)`')
    return lines

def main():
    REPORT.mkdir(parents=True,exist_ok=True)
    rows=['# UX300h public cache probe','']
    ts=int(time.time())
    tests=[('plain',URL,{'User-Agent':'Mozilla/5.0'}),('cache-bust',URL+f'?cb={ts}',{'User-Agent':'Mozilla/5.0','Cache-Control':'no-cache','Pragma':'no-cache'}),('wordpress-no-cache-cookie',URL,{'User-Agent':'Mozilla/5.0','Cookie':'wordpress_no_cache=1','Cache-Control':'no-cache','Pragma':'no-cache'})]
    for name,url,headers in tests:
        try:
            s,h,b=fetch(url,headers); rows+=summarize(name,s,h,b)+['']
        except Exception as e: rows += [f'## {name}',f'- ERROR: `{type(e).__name__}: {e}`','']
    (REPORT/'summary.md').write_text('\n'.join(rows)+'\n',encoding='utf-8')
    return 0

if __name__=='__main__': raise SystemExit(main())
