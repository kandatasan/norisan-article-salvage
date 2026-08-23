#!/usr/bin/env python3
from __future__ import annotations
import re
import apply_ux_koukai_sharpen_v2_once as v2

m = v2.m
DEFECTS_H2 = 'レクサスUXを買って「ひどい」と感じた6つの欠点'
FIRST_DEFECT_H3 = '後部座席は広くない。というか正直狭い'


def heading_tag_start(s: str, text: str) -> int:
    for match in re.finditer(r'<h([1-6])[^>]*>(.*?)</h\1>', s, re.S):
        plain = re.sub(r'<[^>]+>', '', match.group(2)).strip()
        if plain == text:
            block = s.rfind('<!-- wp:heading', 0, match.start())
            if block >= 0:
                next_block = s.find('<!-- wp:', block + 1)
                if next_block < 0 or match.start() < next_block:
                    return block
            return match.start()
    raise RuntimeError('actual heading element missing: ' + text)


def fixed_repl(s: str, a: str, b: str, x: str, headings: bool = False) -> str:
    if not headings:
        i, j = m.bstart(s, a), m.bstart(s, b)
    else:
        i = heading_tag_start(s, a)
        # The defect H2 is also referenced elsewhere in stored content. For this one range,
        # consume its short re-introduction and stop at the first real defect H3.
        j = heading_tag_start(s, FIRST_DEFECT_H3 if b == DEFECTS_H2 else b)
    if j <= i:
        raise RuntimeError(f'bad fixed range: {a} -> {b}; i={i}; j={j}')
    return s[:i] + x.strip() + '\n\n' + s[j:]


m.hstart = heading_tag_start
m.repl = fixed_repl
m.CONCLUSION = m.CONCLUSION.rstrip() + '''

<!-- wp:heading -->
<h2 class="wp-block-heading">レクサスUXを買って「ひどい」と感じた6つの欠点</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>ここからは、約616万円で実際に買って乗った私が<strong>「ここは文句あり🤣」</strong>と感じたところを順番にいきます。</p>
<!-- /wp:paragraph -->
'''

if __name__ == '__main__':
    raise SystemExit(m.main())
