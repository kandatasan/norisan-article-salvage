#!/usr/bin/env python3
from __future__ import annotations
import scripts.fix_karato_market_flow_20260909 as m

OPENER='<!-- wp:image {"id":1003,"sizeSlug":"large","linkDestination":"none"} -->'
_orig_fix=m.fix
_orig_replace_once=m.replace_once


def tolerant_replace_once(text, old, new, label):
    if label=='remove dangling whale block opener' and text.count(old)==0:
        return text
    return _orig_replace_once(text, old, new, label)


def unmatched_closers(text):
    stack=[]; bad=[]
    for match in m.TOKEN.finditer(text):
        token=match.group(0); o=m.OPEN.fullmatch(token); c=m.CLOSE.fullmatch(token)
        if o:
            if not o.group(2):
                stack.append(o.group(1))
        elif c:
            name=c.group(1)
            if stack and stack[-1]==name:
                stack.pop()
            else:
                bad.append((match.start(),match.end(),name,stack[-1] if stack else None,token))
    return bad,stack


def fixed_fix(content):
    count=content.count(OPENER)
    if count!=2:
        raise RuntimeError(f'expected two whale image openers before repair, got {count}')

    # Remove only the first whale image opener: it was left behind in the intro by the prior move.
    content=content.replace(OPENER,'',1)

    # After that repair the old draft has exactly one unmatched paragraph closer.
    # Find it from the Gutenberg token stream rather than relying on whitespace/location.
    bad,stack=unmatched_closers(content)
    if len(bad)!=1 or bad[0][2]!='paragraph' or stack:
        raise RuntimeError(f'unexpected Gutenberg state after opener repair: bad={[(x[2],x[3]) for x in bad]} stack={stack}')
    start,end,_,_,_=bad[0]
    content=content[:start]+content[end:]
    bad2,stack2=unmatched_closers(content)
    if bad2 or stack2 or m.gb_problems(content)!=0:
        raise RuntimeError(f'Gutenberg repair did not reach balance: bad={[(x[2],x[3]) for x in bad2]} stack={stack2}')

    return _orig_fix(content)


m.replace_once=tolerant_replace_once
m.fix=fixed_fix

if __name__=='__main__':
    m.main()
