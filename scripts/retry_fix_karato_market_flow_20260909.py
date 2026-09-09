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


def fixed_fix(content):
    count=content.count(OPENER)
    if count!=2:
        raise RuntimeError(f'expected two whale image openers before repair, got {count}')
    # Remove only the first opener: this is the orphan left near the article intro.
    content=content.replace(OPENER,'',1)
    return _orig_fix(content)


m.replace_once=tolerant_replace_once
m.fix=fixed_fix

if __name__=='__main__':
    m.main()
