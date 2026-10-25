#!/usr/bin/env python3
"""Check actual ZIP bytes, all retained files, JSON references and bootstrap."""
import argparse
import json
import re
import zipfile
from build_release import SOURCE_NAME, digest, external_script, patch_widget


def verify(path):
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        names = z.namelist()
        assert len(names) == len(set(names))
        manifest = json.loads(z.read('river-fish-atlas/release-v028.json'))
        data = {n.removeprefix('river-fish-atlas/data/'): z.read(n) for n in names if n.startswith('river-fish-atlas/data/')}
        assert {n: digest(raw) for n, raw in data.items()} == manifest['data_sha256']
        assert all(digest(data[n]) == sha for n, sha in manifest['baseline_sha256'].items())
        assert data[SOURCE_NAME] == (patch_widget.ROOT / SOURCE_NAME).read_bytes()
        missing = set()
        def walk(value):
            if isinstance(value, dict):
                for x in value.values():
                    walk(x)
            elif isinstance(value, list):
                for x in value:
                    walk(x)
            elif isinstance(value, str) and value.endswith('.json') and '://' not in value and not value.startswith('/'):
                if value not in data:
                    missing.add(value)
        # These two indexes provide the per-river and reference pack paths used by the UI.
        for n in ('atlas.json', 'fish_master.json'):
            walk(json.loads(data[n]))
        assert not missing, sorted(missing)
        html = z.read('river-fish-atlas/index.html').decode()
        scripts = re.findall(r'<script>([\s\S]*?)</script>', html)
        assert scripts == [external_script()]
        assert 'const SOURCE_FISH_V01 = {' not in html
        assert 'noindex,follow' in html
        assert manifest['coverage_when_loaded']['fish_evidence_groups'] == 359
        assert manifest['coverage_when_loaded']['river_name_display_groups'] == 1143
        return {'data_files': len(data), 'all_baseline_bytes_retained': True, 'runtime_references_resolve': True, 'external_json_bootstrap': True}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('zip')
    print(json.dumps(verify(p.parse_args().zip)))
