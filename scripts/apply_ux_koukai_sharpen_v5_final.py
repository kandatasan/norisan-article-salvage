#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import re
import apply_ux_koukai_sharpen_once as m

SOURCE_SHA = '8321162a52e27f6c3f669bd29733d74dda515299e01c499848971e58a32c48a3'
DEFECTS_H2 = 'レクサスUXを買って「ひどい」と感じた6つの欠点'
FIRST_DEFECT_H3 = '後部座席は広くない。というか正直狭い'
CURRENT_CONCLUSION_H2 = '結論｜レクサスUXはひどくない。でも616万円で見ると気になる'
CURRENT_POSITIVE_H2 = 'それでもレクサスUXを買って後悔していない理由'
NEW_POSITIVE_H2 = '文句はある。でも私はUXが好きだった'
CURRENT_USED_H2 = '今からレクサスUXを買うなら、私は中古を選ぶ'
FAQ_H2 = 'レクサスUXに関するよくある質問'
CURRENT_SUMMARY_H2 = 'まとめ｜UXは高くて狭い。でも中古なら話が変わる'


def block_start(s: str, anchor: str) -> int:
    pos = s.find(anchor)
    if pos < 0:
        raise RuntimeError('anchor missing: ' + anchor)
    start = s.rfind('<!-- wp:', 0, pos)
    if start < 0:
        raise RuntimeError('block start missing: ' + anchor)
    return start


def heading_start(s: str, text: str) -> int:
    for match in re.finditer(r'<h([1-6])[^>]*>(.*?)</h\1>', s, re.S):
        plain = re.sub(r'<[^>]+>', '', match.group(2)).strip()
        if plain == text:
            start = s.rfind('<!-- wp:heading', 0, match.start())
            if start >= 0:
                next_block = s.find('<!-- wp:', start + 1)
                if next_block < 0 or match.start() < next_block:
                    return start
            return match.start()
    raise RuntimeError('actual heading missing: ' + text)


def replace_range(s: str, start: int, end: int, replacement: str) -> str:
    if start < 0 or end <= start:
        raise RuntimeError(f'bad replacement range: {start} -> {end}')
    return s[:start] + replacement.strip() + '\n\n' + s[end:]


def replace_para(s: str, anchor: str, replacement: str | None) -> str:
    pos = s.find(anchor)
    if pos < 0:
        return s
    start = s.rfind('<!-- wp:paragraph', 0, pos)
    if start < 0:
        raise RuntimeError('paragraph start missing: ' + anchor)
    end = s.find('<!-- /wp:paragraph -->', pos)
    if end < 0:
        raise RuntimeError('paragraph end missing: ' + anchor)
    end += len('<!-- /wp:paragraph -->')
    insert = '' if replacement is None else replacement.strip()
    return s[:start] + insert + s[end:]


def replace_heading_text(s: str, old: str, new: str) -> str:
    start = heading_start(s, old)
    close = s.find('<!-- /wp:heading -->', start)
    if close >= 0:
        end = close + len('<!-- /wp:heading -->')
    else:
        tag = re.search(r'<h([1-6])[^>]*>.*?</h\1>', s[start:], re.S)
        if not tag:
            raise RuntimeError('heading end missing: ' + old)
        end = start + tag.end()
    block = s[start:end]
    if old not in block:
        raise RuntimeError('heading text not in selected block: ' + old)
    return s[:start] + block.replace(old, new, 1) + s[end:]


def final_build(source: str) -> str:
    source_hash = hashlib.sha256(source.encode()).hexdigest()
    if source_hash != SOURCE_SHA:
        raise RuntimeError('source changed after audit: ' + source_hash)

    image_pattern = re.compile(r"<img[^>]+src=['\"]([^'\"]+)['\"]", re.I)
    source_images = set(image_pattern.findall(source))
    out = source

    out = replace_range(
        out,
        block_start(out, '「レクサスUXはひどい」と検索している人は、購入前に不安になっている人だと思います。'),
        block_start(out, 'この記事で紹介する車両'),
        m.INTRO,
    )

    defects_intro = m.CONCLUSION.rstrip() + '''

<!-- wp:heading -->
<h2 class="wp-block-heading">レクサスUXを買って「ひどい」と感じた6つの欠点</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>ここからは、約616万円で実際に買って乗った私が<strong>「ここは文句あり🤣」</strong>と感じたところを順番にいきます。</p>
<!-- /wp:paragraph -->
'''
    out = replace_range(
        out,
        heading_start(out, CURRENT_CONCLUSION_H2),
        heading_start(out, FIRST_DEFECT_H3),
        defects_intro,
    )

    out = replace_para(out, 'ふざけているようですが、実際に使うとこういう場面があります。', None)
    out = out.replace('ここは無理にかばえません。', 'ここは、かばえません🤣')
    out = replace_para(
        out,
        '走りにも安全性にも関係ありません。',
        '''<!-- wp:paragraph -->
<p>走りにも安全性にも関係ありません。<br><strong>でも一度気づくと、洗車するたびに目に入る🤣</strong><br>私は最後まで気になりました。</p>
<!-- /wp:paragraph -->''',
    )
    out = replace_para(
        out,
        'これは車そのものの欠点ではありません。',
        '''<!-- wp:paragraph -->
<p><strong>約1年待って納車。その約半年後にUX300h。いや、タイミング悪すぎるって🤣</strong></p>
<!-- /wp:paragraph -->''',
    )
    out = replace_para(out, '新型が出ること自体は珍しくありません。', None)
    out = replace_para(
        out,
        'UX250hを選んだこと自体は後悔していません。',
        '''<!-- wp:paragraph -->
<p><strong>250hは好き。でも、このタイミングだけは悔しい。</strong></p>
<!-- /wp:paragraph -->''',
    )

    out = replace_range(
        out,
        block_start(out, 'そしてもうひとつ。'),
        heading_start(out, CURRENT_POSITIVE_H2),
        m.CTN,
    )
    out = replace_heading_text(out, CURRENT_POSITIVE_H2, NEW_POSITIVE_H2)

    out = replace_range(
        out,
        block_start(out, 'ここまで欠点を並べると、不満の多い車に見えるかもしれません。'),
        block_start(out, '納車後は、広島県内だけでなく、山陰、角島、淡路島へも出かけました。'),
        m.POSITIVE_OPEN,
    )
    out = replace_range(
        out,
        block_start(out, 'UXの魅力は、小さい高級車として見たときに分かりやすいです。'),
        heading_start(out, CURRENT_USED_H2),
        m.POSITIVE_TAIL,
    )

    out = replace_range(
        out,
        heading_start(out, CURRENT_USED_H2),
        heading_start(out, FAQ_H2),
        m.USED,
    )

    summary_at = heading_start(out, CURRENT_SUMMARY_H2)
    out = out[:summary_at] + m.SUMMARY.strip() + '\n'

    expected_counts = {
        '[blog_parts id="2843"]': 1,
        '[blog_parts id="2846"]': 1,
        '[blog_parts id="2184"]': 1,
        'https://px.a8.net/svt/ejp?a8mat=4B65SD+8DUSHE+9QU+NVHCY': 1,
        'https://www15.a8.net/0.gif?a8mat=4B65SD+8DUSHE+9QU+NVHCY': 1,
    }
    for marker, expected in expected_counts.items():
        actual = out.count(marker)
        if actual != expected:
            raise RuntimeError(f'affiliate count mismatch: {marker} expected={expected} actual={actual}')

    required = [
        '荷室でテトリス', 'こぶし1個半', '350万円', '500万円近い', '427万円',
        '山陰', '角島', '淡路島', '非公開在庫', '高額査定の上位3社だけ',
        '高かっただけに、文句もあります🤣', 'お宝UX、まだ表に出てないかも。',
        '前の車を高く売れれば、そのぶん次のUXを安く買えたのと同じ。',
        'まとめ｜616万円なら文句あり。中古UXならかなりアリ',
    ]
    missing = [x for x in required if x not in out]
    if missing:
        raise RuntimeError('required fact/marker lost: ' + repr(missing))

    output_images = set(image_pattern.findall(out))
    lost_images = sorted(source_images - output_images)
    if lost_images:
        raise RuntimeError('existing images lost: ' + repr(lost_images))

    if CURRENT_CONCLUSION_H2 in out or CURRENT_SUMMARY_H2 in out:
        raise RuntimeError('old sharpen headings still present')
    if NEW_POSITIVE_H2 not in out or DEFECTS_H2 not in out:
        raise RuntimeError('new heading missing')

    return out


m.build = final_build

if __name__ == '__main__':
    raise SystemExit(m.main())
