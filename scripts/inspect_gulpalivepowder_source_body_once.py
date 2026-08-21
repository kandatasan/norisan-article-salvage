#!/usr/bin/env python3
from __future__ import annotations
import hashlib
from pathlib import Path
import old_tsurikue_phase4_create_plan_dry_run as planner
SLUG='gulpalivepowder'
EXPECTED_TITLE='『ガルプアライブパウダー』集魚剤で本当に釣果は変わる？検証動画つき記事'
REPORT_DIR=Path('reports/gulpalivepowder-source-body')
def main():
    articles,_=planner.generate_fresh_articles()
    matches=[x for x in articles if x.get('slug')==SLUG]
    if len(matches)!=1: raise RuntimeError(f'expected one source article; found {len(matches)}')
    a=matches[0]; title=a.get('title') or ''; content=a.get('content') or ''
    if title!=EXPECTED_TITLE: raise RuntimeError(f'title mismatch: {title!r}')
    sha=hashlib.sha256(content.encode()).hexdigest(); REPORT_DIR.mkdir(parents=True,exist_ok=True)
    (REPORT_DIR/'content.html').write_text(content,encoding='utf-8')
    s=f'''# gulpalivepowder preserved source body\n\n- mode: **LOCAL SOURCE ONLY**\n- wordpress_read_count: **0**\n- wordpress_write_count: **0**\n- title: {title}\n- content_sha256: `{sha}`\n\n## Preserved source body\n\n```html\n{content}\n```\n'''
    (REPORT_DIR/'summary.md').write_text(s,encoding='utf-8'); print(s); return 0
if __name__=='__main__': raise SystemExit(main())
