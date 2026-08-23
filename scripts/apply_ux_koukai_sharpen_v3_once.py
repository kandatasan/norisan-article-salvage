#!/usr/bin/env python3
from __future__ import annotations
import re
import apply_ux_koukai_sharpen_v2_once as v2

m = v2.m


def strict_hstart(s: str, text: str) -> int:
    pattern = re.compile(
        r'<h([1-6])[^>]*>\s*' + re.escape(text) + r'\s*</h\1>',
        re.S,
    )
    match = pattern.search(s)
    if not match:
        # Allow simple inline markup around the heading text while still requiring a real heading element.
        pattern = re.compile(r'<h([1-6])[^>]*>(.*?)</h\1>', re.S)
        for candidate in pattern.finditer(s):
            plain = re.sub(r'<[^>]+>', '', candidate.group(2)).strip()
            if plain == text:
                match = candidate
                break
    if not match:
        raise RuntimeError('actual heading element missing: ' + text)
    block = s.rfind('<!-- wp:heading', 0, match.start())
    if block >= 0:
        next_block = s.find('<!-- wp:', block + 1)
        if next_block < 0 or match.start() < next_block:
            return block
    return match.start()


m.hstart = strict_hstart

if __name__ == '__main__':
    raise SystemExit(m.main())
