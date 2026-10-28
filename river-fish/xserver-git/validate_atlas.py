#!/usr/bin/env python3
"""Fail closed before importing or deploying the Xserver river atlas static tree."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlparse
from xml.etree import ElementTree

ALLOWED_SUFFIXES = {'.html', '.json', '.xml', '.csv', '.txt'}
REQUIRED = {'index.html', 'data/atlas.json', 'river/index.html', 'sitemap.xml'}
CANONICAL_PREFIX = 'https://tsurikue.com/river-fish-atlas/'


def validate(root: Path) -> dict:
    root = root.absolute()
    if not root.is_dir() or root.is_symlink():
        raise ValueError('Source directory is missing or a symlink')
    seen = set()
    total_size = 0
    for base, dirs, files in os.walk(root, followlinks=False):
        parent = Path(base)
        for name in dirs + files:
            p = parent / name
            rel = p.relative_to(root)
            if p.is_symlink() or name.startswith('.') or '\\' in name or ':' in name:
                raise ValueError(f'Unsafe path or symlink: {rel}')
            if not p.is_dir() and not p.is_file():
                raise ValueError(f'Unsupported file type: {rel}')
        for filename in files:
            p = parent / filename
            rel = p.relative_to(root).as_posix()
            if p.suffix.lower() not in ALLOWED_SUFFIXES:
                raise ValueError(f'Unsupported extension: {rel}')
            if rel in seen:
                raise ValueError(f'Duplicate path: {rel}')
            seen.add(rel)
            total_size += p.stat().st_size
            if total_size > 100_000_000:
                raise ValueError('Atlas exceeds size cap of 100 MB')
            if p.suffix.lower() == '.json':
                json.loads(p.read_text(encoding='utf-8'))
    if not REQUIRED.issubset(seen):
        raise ValueError(f'Missing required files: {sorted(REQUIRED - seen)}')
    if not (100 <= len(seen) <= 10000):
        raise ValueError(f'Unexpected number of files: {len(seen)}')
    atlas = json.loads((root / 'data/atlas.json').read_text(encoding='utf-8'))
    if not isinstance(atlas, (dict, list)):
        raise ValueError('data/atlas.json must be structured JSON')
    additions_path = root / 'data/fish_source_connections_v02_additions.json'
    if additions_path.exists():
        additions = json.loads(additions_path.read_text(encoding='utf-8'))
        prior = json.loads((root / 'data/fish_source_connections_v01.json').read_text(encoding='utf-8'))
        survey_counts = {e['survey_river_group_id']: e for e in json.loads((root / 'data/river_fish_label_counts_v25.json').read_text(encoding='utf-8'))['entries']}
        by_id = {entry['id']: entry for entry in atlas['entries']}
        used = {g['navigation_target_id'] for g in prior['groups'] if g['navigation_target_id']}
        documented_source_watersheds = {('東京都', '善福寺川'): '荒川', ('東京都', '妙正寺川'): '荒川', ('東京都', '黒目川'): '荒川',
                                   ('東京都', '落合川'): '荒川', ('東京都', '石神井川'): '荒川', ('東京都', '呑川'): '呑川', ('東京都', '目黒川'): '目黒川',
                                   ('東京都', '柳瀬川'): '荒川', ('東京都', '空堀川'): '荒川', ('東京都', '奈良橋川'): '荒川',
                                   ('東京都', '新河岸川'): '荒川', ('東京都', '白子川'): '荒川', ('東京都', '旧中川'): '荒川',
                                   ('東京都', '北十間川'): '荒川', ('東京都', '小名木川'): '荒川',
                                   ('東京都', '旧江戸川'): '利根川', ('東京都', '新川'): '利根川', ('東京都', '中川'): '利根川',
                                   ('東京都', '新中川'): '利根川', ('東京都', '大場川'): '利根川', ('東京都', '伝右川'): '利根川',
                                   **{('岐阜県', river): '木曽川' for river in ('可児川', '坂本川', '飛騨川', '矢戸川', '久々利川', '唐沢川', '加茂川', '大江川')}}
        documented_source_river_labels = {('滋賀県', '山賀川'): '山賀川(新守山川)'}
        if additions.get('schema') != 'tsurikue-source-fish-additions-v02' or not additions.get('no_precise_locations_or_river_codes') or not additions.get('held_records_excluded'):
            raise ValueError('Fish additions schema or safety flags invalid')
        if additions.get('group_count') != len(additions['groups']) or additions.get('record_count') != sum(len(g['records']) for g in additions['groups']):
            raise ValueError('Fish additions counts invalid')
        for group in additions['groups']:
            target = group['navigation_target_id']
            entry = by_id.get(target)
            official_match = entry and entry['kind'] == 'official_river_name_only_v21' and (entry['source_prefecture'], entry['water'], entry['name']) == (group['prefecture'], group['watershed'], group['river'])
            survey_match = entry and target == 'rn_51c8995e0adad93e3f85603c' and entry['kind'] == 'historical_national_river_survey' and entry['region'] == 'tohoku' and (group['prefecture'], group['watershed'], group['river']) == ('青森県', '岩木川', '浅瀬石川') and (entry['water'], entry['name']) == (group['watershed'], group['river']) and not survey_counts[target]['fish_name_in_source_records']
            if target in used or not (official_match or survey_match):
                raise ValueError(f'Fish addition has ambiguous or duplicate target: {target}')
            used.add(target)
            source_watershed = documented_source_watersheds.get((group['prefecture'], group['river']))
            source_watershed_match = source_watershed is not None
            if source_watershed_match:
                if group['watershed'] != '水系未確認（公式資料の川名）' or group.get('documented_watershed') != source_watershed:
                    raise ValueError(f'Source watershed was conflated with the existing group: {target}')
            elif 'documented_watershed' in group:
                raise ValueError(f'Unexpected source watershed: {target}')
            source_river_label = documented_source_river_labels.get((group['prefecture'], group['river']))
            source_river_label_match = source_river_label is not None
            if source_river_label_match:
                if group.get('documented_river_label') != source_river_label:
                    raise ValueError(f'Source river label alias was not retained: {target}')
            elif 'documented_river_label' in group:
                raise ValueError(f'Unexpected source river label alias: {target}')
            if group['literal_fish_label_count'] != len(group['records']) or not group['records']:
                raise ValueError(f'Fish addition record count invalid: {target}')
            for record in group['records']:
                if record['evidence_class'] not in ('A', 'B') or not record['source_url'].startswith('https://') or not all(record.get(k) for k in ('recorded_name', 'source_title', 'publisher', 'source_locator', 'evidence_summary')):
                    raise ValueError(f'Fish addition lacks publishable evidence: {target}')
                identity_flag = ('EXISTING_PREFECTURE_WATERSHED_RIVER_LABEL_WITH_DOCUMENTED_ALIAS' if source_river_label_match else ('EXACT_EXISTING_PREFECTURE_RIVER_LABEL_WITH_SOURCE_WATERSHED' if source_watershed_match else 'EXACT_EXISTING_PREFECTURE_WATERSHED_RIVER_LABEL')) if official_match else 'SOURCE_PREFECTURE_AND_EXISTING_REGION_WATERSHED_RIVER_LABEL'
                if record['river_identity_review'] != identity_flag or record['conservation_review'] != 'NO_PRECISE_SITE_OR_SENSITIVE_FISH_PUBLISHED' or record['publication_status'] != 'STAGING_CANDIDATE':
                    raise ValueError(f'Fish addition review incomplete: {target}')
        detail_path = root / 'data/river_detail_page_ids_v01.json'
        details = json.loads(detail_path.read_text(encoding='utf-8'))
        actual = sorted(p.parent.name for p in (root / 'river').glob('*/index.html'))
        if details.get('schema') != 'river-detail-page-ids-v01' or details.get('ids') != actual:
            raise ValueError('River detail page link inventory differs from filesystem')
    for rel in ('index.html', 'river/index.html'):
        if '<html' not in (root / rel).read_text(encoding='utf-8').lower():
            raise ValueError(f'Not an HTML document: {rel}')
    xml = ElementTree.parse(root / 'sitemap.xml').getroot()
    ns = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
    locs = [e.text for e in xml.findall(f'.//{ns}loc')]
    if not locs or len(locs) != len(set(locs)):
        raise ValueError('Sitemap has no URLs or has duplicates')
    for url in locs:
        if not url or not url.startswith(CANONICAL_PREFIX):
            raise ValueError(f'Unexpected canonical URL: {url}')
        parsed = urlparse(url)
        rel = parsed.path.removeprefix('/river-fish-atlas/').rstrip('/')
        if parsed.query or parsed.fragment or '..' in Path(rel).parts:
            raise ValueError(f'Unsafe sitemap URL: {url}')
        candidate = rel + '/index.html' if rel else 'index.html'
        if candidate not in seen and rel not in seen:
            raise ValueError(f'Sitemap target missing: {url}')
    return {'files': len(seen), 'bytes': total_size, 'sitemap_urls': len(locs), 'required_files': 'ok'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(validate(args.directory), ensure_ascii=False, sort_keys=True))
    except Exception as exc:
        print(f'Atlas validation failed: {exc}', file=sys.stderr)
        sys.exit(1)
