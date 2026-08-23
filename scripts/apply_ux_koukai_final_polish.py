#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import time
from pathlib import Path

from apply_ux_koukai_rewrite_once import auth_header, fetch_post_by_slug, public_total, raw_field, post_json

POST_ID = 2517
TITLE = 'レクサスUXはひどい？616万円で買って後悔した欠点と満足している理由'
SOURCE_SHA = '8f8eb8b371f479241ebe31686bd91e0b7733ac8749d9e3e67a003c461644027e'
REPORT = Path('reports/ux-koukai-final-polish')


def replace_once(s: str, old: str, new: str, label: str) -> str:
    count = s.count(old)
    if count != 1:
        raise RuntimeError(f'{label}: expected 1 match, got {count}')
    return s.replace(old, new, 1)


def build(source: str) -> str:
    source_hash = hashlib.sha256(source.encode()).hexdigest()
    if source_hash != SOURCE_SHA:
        raise RuntimeError('source changed after final sharpen: ' + source_hash)

    image_pattern = re.compile(r"<img[^>]+src=['\"]([^'\"]+)['\"]", re.I)
    source_images = set(image_pattern.findall(source))
    out = source

    # User-requested wording cleanup.
    out = out.replace('普通に', '')
    out = out.replace('🤣', '').replace('😏', '')

    # Smooth the most abrupt transitions without removing substance.
    out = replace_once(
        out,
        '<p>ここからは、約616万円で実際に買って乗った私が<strong>「ここは文句あり」</strong>と感じたところを順番にいきます。</p>',
        '<p>では、約616万円で実際に買って乗った私が、<strong>「ここは文句あり」</strong>と感じた6つを順番に見ていきます。</p>',
        'defects bridge',
    )

    out = replace_once(
        out,
        '<p>私のUXはディーラー査定350万円に対して、一括査定では最高500万円近い提示が出ました。<br><strong>この差を見たら、1社だけで決めるのは怖いです。</strong></p>',
        '<p>この査定差を見て、<strong>売るなら1社だけで決めない方がいい</strong>と実感しました。</p>',
        'ctn repetition bridge',
    )

    out = replace_once(
        out,
        '<p>CTNは最大15社で査定し、連絡が来るのは<strong>高額査定の上位3社だけ</strong>。<br>「高く売りたい。でも電話ラッシュはいらない」という人には、かなり使いやすい仕組みです。</p>',
        '<p>そこで候補になるのがCTNです。<br>最大15社で査定し、連絡が来るのは<strong>高額査定の上位3社だけ</strong>。<br>「高く売りたい。でも電話ラッシュはいらない」という人に合いやすい仕組みです。</p>',
        'ctn service bridge',
    )

    out = replace_once(
        out,
        '<p>ここまで文句を並べましたが、<strong>それでも私はUXが好きでした。</strong><br>理由は単純。UXに乗ってから、車で出かけることそのものが楽しくなったからです。</p>',
        '<p>それでも所有満足度は高かったです。<br>UXに乗ってから、<strong>車で出かけることそのものが楽しくなった</strong>からです。</p>',
        'positive section bridge',
    )

    out = out.replace('<strong>私は中古250hも候補です。</strong>', '<strong>私は中古250hも十分候補です。</strong>')
    out = out.replace('<strong>約616万円で買った私は、ここに文句があります</strong>', '<strong>約616万円で買った身としては、この6つには文句があります。</strong>')
    out = out.replace('あります。。', 'あります。')

    if '普通に' in out:
        raise RuntimeError('ordinary wording still present')
    if '🤣' in out or '😏' in out:
        raise RuntimeError('face emoji still present')

    for marker in [
        '荷室でテトリス', 'こぶし1個半', '350万円', '500万円近い', '427万円',
        '山陰', '角島', '淡路島', '非公開在庫', '高額査定の上位3社だけ',
        'まとめ｜616万円なら文句あり。中古UXならかなりアリ',
        '文句はある。でも私はUXが好きだった',
    ]:
        if marker not in out:
            raise RuntimeError('required marker lost: ' + marker)

    expected_counts = {
        '[blog_parts id="2843"]': 1,
        '[blog_parts id="2846"]': 1,
        '[blog_parts id="2184"]': 1,
        'https://px.a8.net/svt/ejp?a8mat=4B65SD+8DUSHE+9QU+NVHCY': 1,
    }
    for marker, expected in expected_counts.items():
        actual = out.count(marker)
        if actual != expected:
            raise RuntimeError(f'affiliate count mismatch: {marker} expected={expected} actual={actual}')

    output_images = set(image_pattern.findall(out))
    lost_images = sorted(source_images - output_images)
    if lost_images:
        raise RuntimeError('existing images lost: ' + repr(lost_images))

    return out


def retry(fn):
    error = None
    for n in range(3):
        try:
            return fn()
        except Exception as exc:
            error = exc
            if n < 2:
                time.sleep(3 * (n + 1))
    raise error


def write_report(data: dict) -> None:
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / 'result.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = [
        '# ux-koukai final prose polish', '',
        f"- result: **{data.get('result')}**",
        f"- post_id: **{data.get('post_id', 'unknown')}**",
        f"- status: **{data.get('status', 'unknown')}**",
        f"- title: {data.get('title', '')}",
        f"- featured_media: **{data.get('featured_media', 'unknown')}**",
        f"- public_before: **{data.get('public_before', 'unknown')}**",
        f"- public_after: **{data.get('public_after', 'unknown')}**",
        f"- wordpress_write_count: **{data.get('wordpress_write_count', 0)}**",
        f"- source_sha256: `{data.get('source_sha', '')}`",
        f"- content_sha256: `{data.get('content_sha', '')}`",
        f"- ordinary_count: **{data.get('ordinary_count', 'unknown')}**",
        f"- face_emoji_count: **{data.get('face_emoji_count', 'unknown')}**",
        f"- gulliver_banner_count: **{data.get('gulliver_banner_count', 'unknown')}**",
        f"- gulliver_button_count: **{data.get('gulliver_button_count', 'unknown')}**",
        f"- ctn_banner_count: **{data.get('ctn_banner_count', 'unknown')}**",
        f"- ctn_button_count: **{data.get('ctn_button_count', 'unknown')}**",
    ]
    if data.get('error'):
        lines.append(f"- error: `{data['error']}`")
    (REPORT / 'summary.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main() -> int:
    data = {'result': 'BLOCKED', 'wordpress_write_count': 0}
    try:
        user = os.environ.get('TSURIKUE_WP_USER')
        password = os.environ.get('TSURIKUE_WP_APP_PASSWORD')
        if not user or not password:
            raise RuntimeError('missing WordPress secrets')

        auth = auth_header(user, password)
        total = retry(lambda: public_total(auth))
        before = retry(lambda: fetch_post_by_slug(auth))
        current = raw_field(before, 'content')
        post_id = int(before.get('id') or 0)
        title = html.unescape(raw_field(before, 'title'))
        status = before.get('status')
        featured_media = int(before.get('featured_media') or 0)
        data.update(
            post_id=post_id,
            status=status,
            title=title,
            featured_media=featured_media,
            public_before=total,
            source_sha=hashlib.sha256(current.encode()).hexdigest(),
        )

        if post_id != POST_ID or status != 'publish' or title != TITLE:
            raise RuntimeError('post identity/state mismatch')

        wanted = build(current)
        response = post_json(
            f'https://tsurikue.com/wp-json/wp/v2/posts/{post_id}',
            auth,
            {'content': wanted, 'status': 'publish'},
        )
        data['wordpress_write_count'] = 1
        if int(response.get('id') or 0) != post_id or response.get('status') != 'publish':
            raise RuntimeError('update response mismatch')

        after = retry(lambda: fetch_post_by_slug(auth))
        after_total = retry(lambda: public_total(auth))
        after_content = raw_field(after, 'content')
        after_title = html.unescape(raw_field(after, 'title'))
        if after_total != total or after.get('status') != 'publish' or after_title != TITLE or int(after.get('featured_media') or 0) != featured_media:
            raise RuntimeError('post-update state mismatch')

        counts = (
            after_content.count('[blog_parts id="2843"]'),
            after_content.count('https://px.a8.net/svt/ejp?a8mat=4B65SD+8DUSHE+9QU+NVHCY'),
            after_content.count('[blog_parts id="2846"]'),
            after_content.count('[blog_parts id="2184"]'),
        )
        if counts != (1, 1, 1, 1):
            raise RuntimeError('post-update affiliate count mismatch')
        if '普通に' in after_content or '🤣' in after_content or '😏' in after_content:
            raise RuntimeError('post-update wording cleanup mismatch')

        data.update(
            result='SUCCESS',
            public_after=after_total,
            content_sha=hashlib.sha256(after_content.encode()).hexdigest(),
            ordinary_count=after_content.count('普通に'),
            face_emoji_count=after_content.count('🤣') + after_content.count('😏'),
            gulliver_banner_count=counts[0],
            gulliver_button_count=counts[1],
            ctn_banner_count=counts[2],
            ctn_button_count=counts[3],
        )
        write_report(data)
        return 0
    except Exception as exc:
        data['error'] = str(exc)
        write_report(data)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
