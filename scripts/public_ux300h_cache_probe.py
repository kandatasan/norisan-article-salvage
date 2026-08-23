#!/usr/bin/env python3
from __future__ import annotations
import time, urllib.request, urllib.error
from pathlib import Path

URL='https://tsurikue.com/ux300h/'
REPORT=Path('reports/ux300h-public-cache-probe')
MARKERS=[
    'お宝UX、まだ表に出ていないかも。',
    '非公開在庫も含めて中古UXを探してみる',
    '高く売りたい。でも電話ラッシュはいらない。',
]

def fetch(url, headers=None):
    req=urllib.request.Request(url, headers=headers or {'User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        body=r.read().decode('utf-8','replace')
        return r.status, dict(r.headers.items()), body

def summarize(name, status, headers, body):
    return [
        f'## {name}',
        f'- status: **{status}**',
        f"- cache-control: `{headers.get('Cache-Control','')}`",
        f"- age: `{headers.get('Age','')}`",
        f"- x-cache: `{headers.get('X-Cache','')}`",
        f"- x-cache-status: `{headers.get('X-Cache-Status','')}`",
        f"- cf-cache-status: `{headers.get('CF-Cache-Status','')}`",
        f'- body_length: **{len(body)}**',
        *[f"- {'OK' if m in body else 'MISSING'}: {m}" for m in MARKERS],
    ]

def main():
    REPORT.mkdir(parents=True, exist_ok=True)
    rows=['# UX300h public cache probe','']
    ts=int(time.time())
    tests=[
        ('plain', URL, {'User-Agent':'Mozilla/5.0'}),
        ('cache-bust', URL+f'?cb={ts}', {'User-Agent':'Mozilla/5.0','Cache-Control':'no-cache','Pragma':'no-cache'}),
        ('wordpress-no-cache-cookie', URL, {'User-Agent':'Mozilla/5.0','Cookie':'wordpress_no_cache=1','Cache-Control':'no-cache','Pragma':'no-cache'}),
    ]
    for name,url,headers in tests:
        try:
            status,h,b=fetch(url,headers)
            rows += summarize(name,status,h,b)+['']
        except Exception as e:
            rows += [f'## {name}',f'- ERROR: `{type(e).__name__}: {e}`','']
    (REPORT/'summary.md').write_text('\n'.join(rows)+'\n',encoding='utf-8')
    return 0

if __name__=='__main__': raise SystemExit(main())
