#!/usr/bin/env python3
from __future__ import annotations
import re
import scripts.fix_karato_market_flow_20260909 as m

OPENER='<!-- wp:image {"id":1003,"sizeSlug":"large","linkDestination":"none"} -->'
IMAGE_CLOSE='<!-- /wp:image -->'
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

    # v1 left two structural artifacts when moving the whale image:
    # 1) the original image opener near the article intro
    # 2) an extra paragraph closer immediately after the moved whale image
    content=content.replace(OPENER,'',1)

    valid_idx=content.find(OPENER)
    if valid_idx<0:
        raise RuntimeError('valid whale image opener missing after orphan removal')
    close_idx=content.find(IMAGE_CLOSE,valid_idx)
    if close_idx<0:
        raise RuntimeError('valid whale image closer missing')
    tail_start=close_idx+len(IMAGE_CLOSE)
    tail=content[tail_start:]
    extra=re.match(r'(\s*)<!--\s+/wp:paragraph\s+-->',tail)
    if not extra:
        raise RuntimeError('expected extra paragraph closer after moved whale image')
    # Preserve whitespace, remove only the duplicate closing marker.
    content=content[:tail_start]+extra.group(1)+tail[extra.end():]

    return _orig_fix(content)


m.replace_once=tolerant_replace_once
m.fix=fixed_fix

if __name__=='__main__':
    m.main()
