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
