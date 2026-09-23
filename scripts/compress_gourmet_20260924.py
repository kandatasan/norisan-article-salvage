#!/usr/bin/env python3
"""User-authorized repetition-only edits to two published restaurant reviews."""
import argparse
import difflib
import html
import re
import remove_wayback_images_20260924 as guard
from pathlib import Path

guard.TARGETS = {2662: ('yakinikucenter', []), 3463: ('ask-the-meat', [])}
guard.OUT = Path('reports/compress-gourmet-20260924')

def paragraph(text):
    return '<!-- wp:paragraph -->\n<p>' + text + '</p>\n<!-- /wp:paragraph -->'

def heading(text):
    return '<!-- wp:heading -->\n<h2 class="wp-block-heading">' + text + '</h2>\n<!-- /wp:heading -->'

DELETIONS = {
    2662: [
        paragraph('昔ながらの焼肉屋さんなのですが、旨い。<br>私はこの店のためだけに東広島から可部まで通っています。'),
        heading('可部焼肉センターを実食レビュー｜わざわざ食べに行きたくなる店'),
        paragraph('国道54号線沿いで、とにかく目立つ店です。<br>赤い牛の看板も含めて、一度見たら覚えます。'),
        paragraph('私も東広島から可部まで距離はあります。<br>それでも焼肉センターを食べたくなると、ここまで行きます。'),
        paragraph('<strong>近いから行くんじゃなく、ここで食べたいから行く。</strong><br>私の中では、そんな店です。'),
        heading('焼肉以外のメニューも多い'),
        paragraph('とはいえ、私が焼肉センターへ行く理由はやっぱり肉。<br>和牛カルビを焼いて、ごはんを食べる。これが好きです。'),
        heading('国道54号で気になっているなら、一度入ってみてほしい'),
        paragraph('私は東広島から、焼肉センターのためだけに可部まで通っています。'),
        paragraph('年季の入った外観。<br>旨い肉。<br>そして和牛カルビで白ごはん。'),
    ],
    3463: [
        paragraph('肉の部位はほとんど覚えていません。<br>でも、写真を見返すと「これ旨かったなあ」と味の記憶はしっかり残っています。'),
        paragraph('食レポはこれ以上うまく言えません。<br><strong>とにかく旨かった。</strong>たぶん、この一言がいちばん正確です。'),
        '<figcaption class="wp-element-caption">部位を説明できなくても、旨かった記憶はしっかり残っています。</figcaption>',
        heading('過去最強クラスかもしれない'),
        paragraph('部位名まで詳しく説明できる記事ではありません。<br>それでも、<strong>「また食べたい」と思えるくらい旨かった</strong>ことは間違いありません。'),
    ],
}
REPLACEMENTS = {
    2662: [],
    3463: [
        ('部位の名前は分かりません。でも、見た瞬間に「これは旨いやつ」と分かる肉でした。', '見た瞬間に「これは旨いやつ」と分かる肉でした。'),
        (heading('アスクザミートを実食レビュー｜肉の名前は分からん。でも、とにかく旨い'), heading('アスクザミートを実食｜柔らかいだけじゃなく、肉の味が濃い')),
        ('最初から肉の迫力がすごい。今回のコースは仕入れによって内容が変わります。', '最初から肉の迫力がすごい。'),
    ],
}

def text_length(content):
    return len(re.sub(r'\s+', '', html.unescape(re.sub(r'<!--.*?-->|<[^>]*>', '', content, flags=re.S))))

def transform(content, post_id):
    fixed = content
    for old in DELETIONS[post_id]:
        guard.require(fixed.count(old) == 1, f'{post_id}: deletion anchor changed: {old[:90]}')
        fixed = fixed.replace(old, '', 1)
    for old, new in REPLACEMENTS[post_id]:
        guard.require(fixed.count(old) == 1, f'{post_id}: replacement anchor changed')
        fixed = fixed.replace(old, new, 1)
    fixed = re.sub(r'\n{3,}', '\n\n', fixed)
    for pattern in [r'<img\b[^>]*>', r'<table\b.*?</table>', r'<a\b[^>]*>']:
        guard.require(re.findall(pattern, fixed, re.S) == re.findall(pattern, content, re.S), 'Images/tables/links must remain unchanged')
    guard.require(text_length(fixed) < text_length(content), 'Text was not compressed')
    for tag in ['paragraph', 'heading', 'image', 'table']:
        guard.require(len(re.findall(r'<!-- wp:' + tag + r'(?:\s|\{)', fixed)) == fixed.count('<!-- /wp:' + tag + ' -->'), f'Unbalanced {tag} blocks')
    return fixed

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['preflight', 'apply'], required=True)
    mode = parser.parse_args().mode
    guard.OUT.mkdir(parents=True, exist_ok=True)
    summary = ['# Compress two restaurant reviews', f'- mode: {mode}', '- scope: 2662 and 3463 only; repetition cleanup; Mitakidera unchanged']
    try:
        public_before = guard.counts()
        plans = []
        for post_id in guard.TARGETS:
            before = guard.get_post(post_id)
            content = before['content']['raw']
            fixed = transform(content, post_id)
            guard.save(f'{post_id}-before.json', before)
            guard.save(f'{post_id}-plan.json', {'content_after': fixed, 'before_sha256': guard.digest(content), 'after_sha256': guard.digest(fixed)})
            (guard.OUT / f'{post_id}.diff').write_text(''.join(difflib.unified_diff(content.splitlines(True), fixed.splitlines(True), fromfile='before', tofile='after')), encoding='utf-8')
            plans.append((post_id, before, fixed))
            summary.append(f'- PREFLIGHT {post_id} / {before["slug"]}: visible text {text_length(content)} -> {text_length(fixed)} chars; image tags, tables, links unchanged')
        if mode == 'apply':
            for post_id, before, fixed in plans:
                fresh = guard.get_post(post_id)
                guard.require(fresh['content']['raw'] == before['content']['raw'] and guard.invariant(fresh) == guard.invariant(before) and fresh['modified_gmt'] == before['modified_gmt'], 'Concurrent edit detected')
                guard.request(f'/posts/{post_id}', 'POST', {'content': fixed})
                after = guard.get_post(post_id)
                guard.save(f'{post_id}-after.json', after)
                guard.require(after['content']['raw'] == fixed and guard.invariant(after) == guard.invariant(before), 'Verification failed')
                summary.append(f'- APPLIED {post_id}: content only; publish retained; featured_media={after["featured_media"]} unchanged')
        public_after = guard.counts()
        guard.require(public_before == public_after, 'Public counts changed')
        summary.extend([f'- public_before={public_before}; public_after={public_after}', '- result: SUCCESS' if mode == 'apply' else '- result: PREFLIGHT_OK (no writes)'])
    except Exception:
        summary.append('- result: STOPPED; review backups and per-post status')
        raise
    finally:
        report = '\n'.join(summary) + '\n'
        (guard.OUT / 'summary.md').write_text(report, encoding='utf-8')
        print(report)

if __name__ == '__main__':
    main()
