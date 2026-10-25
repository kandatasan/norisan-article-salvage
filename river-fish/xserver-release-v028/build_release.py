#!/usr/bin/env python3
"""Build the Xserver upload bundle; never edit WordPress or server files."""
import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'river-fish/source-connections-v01'))
import patch_widget
from audit_connections import coverage

SOURCE_NAME = 'fish_source_connections_v01.json'
CORE_SHA256 = {
    'atlas.json': '0816715449455560dcf1e1c22e834108f415d28fec99aa008c024fbe03bd8e05',
    'fish_master.json': '2faaa794799c2991116fa264a8fa2b07b667def81e252ef49b3464909f4a8ca5',
    'river_fish_label_counts_v25.json': 'c8b3403478c2be13b534d1cd765b536e2000eac0f480ac9989cf5bb5d57d56ba',
    'fish_to_river_reverse_v24.json': 'e7cd13b08067e9f981b25ca373ca93049732625aba1a4088b78a367aabeb4181',
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def external_script():
    body = (ROOT / 'content/drafts/river-atlas-seo-20261021.html').read_text()
    scripts = [s for s in re.findall(r'<script>([\s\S]*?)</script>', body) if 'const DATA_ROOT' in s]
    if len(scripts) != 1:
        raise ValueError('Expected one reviewed widget')
    script = patch_widget.patch_script(scripts[0])
    script, count = re.subn(r'const SOURCE_FISH_V01 = \{[^\n]+\};', 'let SOURCE_FISH_V01 = null;', script)
    if count != 1:
        raise ValueError('Expected one embedded source layer')
    revision = digest((patch_widget.ROOT / SOURCE_NAME).read_bytes())[:16]
    old = 'const result=await Promise.all([load("atlas.json"),load("fish_master.json")]);\n  atlas=mergeSourceFishV01(result[0]);master=result[1];'
    new = ('const result=await Promise.all([load("atlas.json"),load("fish_master.json"),'
           f'load("{SOURCE_NAME}?v={revision}")]);\n'
           '  SOURCE_FISH_V01=result[2];atlas=mergeSourceFishV01(result[0]);master=result[1];')
    if script.count(old) != 1:
        raise ValueError('Widget setup changed')
    return script.replace(old, new)


def standalone_html():
    body = (ROOT / 'content/drafts/river-atlas-seo-20261021.html').read_text()
    blocks = [b for b in re.findall(r'<!-- wp:html -->([\s\S]*?)<!-- /wp:html -->', body)
              if 'id="tsurikue-river-atlas-inline-v26"' in b]
    if len(blocks) != 1:
        raise ValueError('Expected one widget block')
    block, count = re.subn(r'<script>[\s\S]*?</script>', lambda _: '<script>' + external_script() + '</script>', blocks[0])
    if count != 1:
        raise ValueError('Unexpected executable scripts')
    return ('<!doctype html>\n<html lang="ja"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="robots" content="noindex,follow">'
            '<title>つりくえ！日本の河川図鑑</title></head>'
            '<body style="margin:0;padding:16px;background:#f4f8f6">'
            '<main style="max-width:1100px;margin:auto">' + block + '</main></body></html>\n')


def read_baseline(archive):
    data = {}
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            path = PurePosixPath(info.filename)
            if info.is_dir():
                continue
            if path.is_absolute() or '..' in path.parts or '\\' in info.filename:
                raise ValueError('Unsafe archive path')
            if info.filename in ('index.html', 'readme_preview.txt'):
                continue
            if not info.filename.endswith(('.json', '.csv')):
                raise ValueError('Unexpected baseline file: ' + info.filename)
            if info.filename in data:
                raise ValueError('Duplicate baseline path')
            data[info.filename] = z.read(info)
    for name, expected in CORE_SHA256.items():
        if name not in data or digest(data[name]) != expected:
            raise ValueError('Core data differs from the verified live release: ' + name)
    return data


def build(archive, output):
    data = read_baseline(archive)
    baseline_hashes = {name: digest(raw) for name, raw in data.items()}
    data[SOURCE_NAME] = (patch_widget.ROOT / SOURCE_NAME).read_bytes()
    report = coverage(json.loads(data['atlas.json']), json.loads(data['river_fish_label_counts_v25.json']), json.loads(data[SOURCE_NAME]))
    manifest = {
        'release': 'xserver-v0.28-20261025',
        'upload_directory': 'public_html/river-fish-atlas/',
        'wordpress_migration_status': 'CURRENT_ARTICLE_USES_EMBEDDED_SOURCE_LAYER',
        'source_data_is_external_json': True,
        'baseline_files_unchanged': True,
        'baseline_sha256': baseline_hashes,
        'data_sha256': {name: digest(raw) for name, raw in data.items()},
        'coverage_when_loaded': {k: report[k] for k in ('fish_evidence_groups', 'river_name_display_groups', 'coverage_percent', 'additional_qualifying_groups_needed')},
        'coverage_is_display_name_groups_not_physical_rivers': True,
    }
    html = standalone_html().encode()
    instructions = (ROOT / 'river-fish/xserver-release-v028/UPLOAD.txt').read_bytes()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for name, raw in sorted(data.items()):
            z.writestr('river-fish-atlas/data/' + name, raw)
        z.writestr('river-fish-atlas/index.html', html)
        z.writestr('river-fish-atlas/release-v028.json', json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
        z.writestr('UPLOAD.txt', instructions)
    return manifest


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--baseline-zip', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    manifest = build(args.baseline_zip, args.out)
    print(json.dumps({'file': str(args.out), 'data_files': len(manifest['data_sha256']), 'coverage_when_loaded': manifest['coverage_when_loaded']}, ensure_ascii=False))
