#!/usr/bin/env python3
from __future__ import annotations
import re
import apply_ux_koukai_sharpen_once as m


def robust_hstart(s: str, text: str) -> int:
    for hit in re.finditer(re.escape(text), s):
        pos = hit.start()
        start = s.rfind('<!-- wp:heading', 0, pos)
        if start < 0:
            continue
        close = s.find('<!-- /wp:heading -->', start)
        if close >= 0 and pos < close:
            return start
        # Some normalized blocks may omit the explicit closing comment.
        next_block = s.find('<!-- wp:', start + 1)
        if next_block < 0:
            next_block = len(s)
        if pos < next_block and re.search(r'<h[1-6][^>]*>.*?' + re.escape(text) + r'.*?</h[1-6]>', s[start:next_block], re.S):
            return start
    raise RuntimeError('heading block missing: ' + text)


def replace_paragraph_containing(s: str, anchor: str, replacement_html: str) -> str:
    pos = s.find(anchor)
    if pos < 0:
        return s
    start = s.rfind('<!-- wp:paragraph', 0, pos)
    if start < 0:
        return s
    end = s.find('<!-- /wp:paragraph -->', pos)
    if end < 0:
        return s
    end += len('<!-- /wp:paragraph -->')
    return s[:start] + replacement_html.strip() + s[end:]


m.hstart = robust_hstart
_original_build = m.build


def polished_build(s: str) -> str:
    out = _original_build(s)

    out = replace_paragraph_containing(
        out,
        '走りにも安全性にも関係ありません。',
        '''<!-- wp:paragraph -->\n<p>走りにも安全性にも関係ありません。<br><strong>でも一度気づくと、洗車するたびに目に入る🤣</strong><br>私は最後まで気になりました。</p>\n<!-- /wp:paragraph -->''',
    )
    out = replace_paragraph_containing(
        out,
        'これは車そのものの欠点ではありません。',
        '''<!-- wp:paragraph -->\n<p>車の性能とは関係ありません。<br><strong>ただ、1年近く待って納車された約半年後にUX300h。いや、タイミング悪すぎるって🤣</strong></p>\n<!-- /wp:paragraph -->''',
    )
    out = replace_paragraph_containing(
        out,
        'UX250hを選んだこと自体は後悔していません。',
        '''<!-- wp:paragraph -->\n<p><strong>250hは好き。でも、このタイミングだけは悔しい。</strong></p>\n<!-- /wp:paragraph -->''',
    )

    # Final guard: the second pass should reduce hedging, not erase firsthand information.
    required = [
        '荷室でテトリス', 'こぶし1個半', '350万円', '500万円近い', '427万円',
        '山陰', '角島', '淡路島', '非公開在庫', '高額査定の上位3社だけ',
        '高かっただけに、文句もあります🤣',
        'まとめ｜616万円なら文句あり。中古UXならかなりアリ',
    ]
    missing = [x for x in required if x not in out]
    if missing:
        raise RuntimeError('v2 fact/marker missing: ' + repr(missing))
    return out


m.build = polished_build

if __name__ == '__main__':
    raise SystemExit(m.main())
