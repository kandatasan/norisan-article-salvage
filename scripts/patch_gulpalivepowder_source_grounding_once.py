#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os
from pathlib import Path
import apply_editorial_draft_once as updater

CONFIG = Path('editorial/gulpalivepowder/config.json')
CONTENT = Path('editorial/gulpalivepowder/content.html')
EXPECTED_WP_SHA = '884d07c1bcb5e395bce5ed3feffc1f3d3716cfdd6ac6ae64bc8f7e641bfd4bb1'
TARGET = '<!-- wp:paragraph -->\n<p>だからガルプ粉の実験も、ずっとやってみたかったんですよね。</p>\n<!-- /wp:paragraph -->\n\n'


def main():
    user = os.environ.get('TSURIKUE_WP_USER')
    password = os.environ.get('TSURIKUE_WP_APP_PASSWORD')
    if not user or not password:
        raise SystemExit('BLOCKED_MISSING_SECRETS')

    source = CONTENT.read_text(encoding='utf-8')
    if source.count(TARGET) != 1:
        raise RuntimeError(f'expected exact target paragraph once; found {source.count(TARGET)}')
    CONTENT.write_text(source.replace(TARGET, '', 1), encoding='utf-8')

    cfg, full = updater.load_package(CONFIG)
    auth = updater.auth_header(user, password)
    before_counts = updater.public_counts(auth)
    before = updater.fetch_post(cfg, auth)
    if before.get('id') != 2630 or before.get('slug') != 'gulpalivepowder' or before.get('status') != 'draft':
        raise RuntimeError('target post identity/status changed')
    current = updater.raw_field(before, 'content')
    current_sha = hashlib.sha256(current.encode()).hexdigest()

    if current.strip() == full.strip():
        action = 'ALREADY_UP_TO_DATE'
        write_count = 0
    else:
        if current_sha != EXPECTED_WP_SHA:
            raise RuntimeError(f'current WordPress content changed: {current_sha}')
        if 'ずっとやってみたかった' not in current:
            raise RuntimeError('target phrase missing from guarded WordPress body')
        updater.validate_media(cfg, auth)
        updater.post_json(
            f"{updater.SITE_URL}/wp-json/wp/v2/posts/{cfg['post_id']}",
            auth,
            {
                'title': cfg['title'],
                'slug': cfg['slug'],
                'content': full,
                'status': 'draft',
                'featured_media': int(cfg.get('featured_media') or 0),
            },
        )
        action = 'UPDATE'
        write_count = 1

    after = updater.fetch_post(cfg, auth)
    after_counts = updater.public_counts(auth)
    after_content = updater.raw_field(after, 'content')
    if after_counts != before_counts:
        raise RuntimeError('published counts changed')
    if after.get('status') != 'draft' or after.get('slug') != cfg['slug']:
        raise RuntimeError('post-update identity/status mismatch')
    if after_content.strip() != full.strip():
        raise RuntimeError('post-update body does not match grounded package')
    if 'ずっとやってみたかった' in after_content:
        raise RuntimeError('unsupported phrase still present')
    if 'Q5ePEt5uQYk' not in after_content or 'wp-image-13' not in after_content:
        raise RuntimeError('video or recovered image was lost')

    report = {
        'action': action,
        'post_id': 2630,
        'slug': 'gulpalivepowder',
        'status': 'draft',
        'featured_media': int(after.get('featured_media') or 0),
        'youtube_id_present': True,
        'article_media_13_present': True,
        'unsupported_phrase_present': False,
        'public_before': before_counts['published_total'],
        'public_after': after_counts['published_total'],
        'wordpress_write_count': write_count,
        'content_sha256': hashlib.sha256(after_content.encode()).hexdigest(),
    }
    out = Path('reports/gulpalivepowder-source-grounding')
    out.mkdir(parents=True, exist_ok=True)
    (out / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (out / 'summary.md').write_text(
        '# gulpalivepowder source-grounding patch\n\n'
        + '\n'.join(f'- {k}: **{v}**' for k, v in report.items())
        + '\n',
        encoding='utf-8',
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
