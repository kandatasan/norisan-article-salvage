#!/usr/bin/env python3
from __future__ import annotations
import json, os
from pathlib import Path
import apply_ux_koukai_sharpen_once as m

REPORT = Path('reports/ux-koukai-sharpen-diagnose')

def main() -> int:
    out = {'result':'BLOCKED','wordpress_write_count':0,'error':'','ranges':[]}
    try:
        u,p=os.environ.get('TSURIKUE_WP_USER'),os.environ.get('TSURIKUE_WP_APP_PASSWORD')
        if not u or not p: raise RuntimeError('missing WordPress secrets')
        auth=m.auth_header(u,p)
        post=m.retry(lambda:m.fetch_post_by_slug(auth))
        current=m.raw_field(post,'content')
        original=m.repl
        def traced(s,a,b,x,headings=False):
            pick=m.hstart if headings else m.bstart
            i,j=pick(s,a),pick(s,b)
            row={'start':a,'end':b,'headings':headings,'i':i,'j':j,'ok':j>i}
            out['ranges'].append(row)
            if j<=i:
                raise RuntimeError(f'bad range: {a} -> {b}; i={i}; j={j}')
            return s[:i]+x.strip()+'\n\n'+s[j:]
        m.repl=traced
        try:
            m.build(current)
        finally:
            m.repl=original
        out['result']='SUCCESS'
    except Exception as e:
        out['error']=str(e)
    REPORT.mkdir(parents=True,exist_ok=True)
    (REPORT/'result.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# ux-koukai sharpen range diagnosis','',f"- result: **{out['result']}**",'- wordpress_write_count: **0**']
    for n,r in enumerate(out['ranges'],1):
        lines.append(f"- range {n}: {'OK' if r['ok'] else 'BAD'} | `{r['start']}` -> `{r['end']}` | i={r['i']} j={r['j']}")
    if out['error']: lines.append(f"- error: `{out['error']}`")
    (REPORT/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return 0

if __name__=='__main__': raise SystemExit(main())
