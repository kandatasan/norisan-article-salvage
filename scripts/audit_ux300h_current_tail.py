#!/usr/bin/env python3
from __future__ import annotations
import hashlib, html, os, re, time
from pathlib import Path
import apply_ux_koukai_rewrite_once as wp

wp.SLUG='ux300h'
REPORT=Path('reports/ux300h-current-tail')

def retry(fn):
    err=None
    for n in range(3):
        try:return fn()
        except Exception as e:
            err=e
            if n<2:time.sleep(3*(n+1))
    raise err

def clean(s):
    s=re.sub(r'<br\s*/?>',' / ',s,flags=re.I)
    s=re.sub(r'<[^>]+>','',s)
    return re.sub(r'\s+',' ',html.unescape(s)).strip()

def main():
    REPORT.mkdir(parents=True,exist_ok=True)
    u=os.environ.get('TSURIKUE_WP_USER');p=os.environ.get('TSURIKUE_WP_APP_PASSWORD')
    if not u or not p:raise RuntimeError('missing WordPress secrets')
    auth=wp.auth_header(u,p); row=retry(lambda:wp.fetch_post_by_slug(auth)); raw=wp.raw_field(row,'content')
    items=[]
    pat=re.compile(r'<(h2|h3|p)(?:\s[^>]*)?>(.*?)</\1>',re.I|re.S)
    for m in pat.finditer(raw):
        text=clean(m.group(2))
        if text:items.append((m.start(),m.group(1).upper(),text))
    lines=['# UX300h current tail audit','', '- result: **SUCCESS**','- wordpress_write_count: **0**',f'- content_sha256: `{hashlib.sha256(raw.encode()).hexdigest()}`',f'- content_length: **{len(raw)}**','', '## Last 45 text blocks']
    for pos,tag,text in items[-45:]: lines.append(f'- [{pos}] {tag}: {text[:500]}')
    (REPORT/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return 0

if __name__=='__main__':raise SystemExit(main())
