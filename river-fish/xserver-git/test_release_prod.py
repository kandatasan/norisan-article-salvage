#!/usr/bin/env python3
"""Run production release logic against a fake home, never a real server."""
import os
from pathlib import Path
import subprocess
import tempfile

SCRIPT = Path(__file__).with_name('release_prod.sh')


def run(home, operation, rid='123456', expected=0):
    result = subprocess.run(
        ['bash', str(SCRIPT), operation, rid],
        env={**os.environ, 'HOME': str(home)},
        text=True, capture_output=True)
    if expected == 0:
        assert result.returncode == 0, (result.stdout, result.stderr)
    else:
        assert result.returncode != 0, (result.stdout, result.stderr)
    return result


def make_atlas(folder, content='old'):
    for f in ('index.html', 'sitemap.xml', 'river/index.html', 'data/atlas.json'):
        p = folder / f
        p.parent.mkdir(exist_ok=True, parents=True)
        p.write_text(content)


with tempfile.TemporaryDirectory() as tmp:
    home = Path(tmp)
    public = home / 'tsurikue.com' / 'public_html'
    live = public / 'river-fish-atlas'
    preview = public / 'river-fish-atlas-ci-preview'
    make_atlas(live)
    make_atlas(preview, 'new')
    (preview / '.htaccess').write_text('Header always set X-Robots-Tag "noindex, nofollow"')
    state = home / '.tsurikue-river-atlas-releases'
    run(home, 'preflight')
    assert not state.exists(), 'preflight must not write state'
    run(home, 'prepare')
    make_atlas(state / 'candidate-123456', 'new')
    run(home, 'publish')
    assert (live / 'index.html').read_text() == 'new'
    assert (state / 'backup-123456' / 'index.html').read_text() == 'old'
    run(home, 'rollback-auto', '999999', expected=1)
    assert (live / 'index.html').read_text() == 'new'
    run(home, 'rollback-auto')
    assert (live / 'index.html').read_text() == 'old'
    assert (state / 'failed-123456' / 'index.html').read_text() == 'new'
    run(home, 'rollback-auto', expected=1)
    run(home, 'prepare', '123456', expected=1)
    run(home, 'preflight', '555555')
    (live / 'private.php').write_text('nope')
    run(home, 'preflight', '777777', expected=1)
    (live / 'private.php').unlink()
    (live / '.htaccess').write_text('nope')
    run(home, 'preflight', '777777', expected=1)
    (live / '.htaccess').unlink()
    print('Production release fake-home tests passed.')
