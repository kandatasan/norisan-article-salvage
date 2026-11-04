#!/usr/bin/env python3
"""Offline regression checks for the post-4240 v02 widget replacement."""
from pathlib import Path
import importlib.util
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "river-fish/source-connections-v01"))
import patch_widget

path = ROOT / "scripts/apply_river_atlas_v02_static_20261104.py"
spec = importlib.util.spec_from_file_location("wp_v02", path)
wp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wp)

target = wp.target_script()
assert 'const DATA_ROOT = "/river-fish-atlas/data/";' in target
assert 'fish_source_connections_v02_additions.json?v=20261030b' in target
assert 'river_detail_page_ids_v01.json?v=20261104' in target
assert 'result[4].ids.length!==280' in target
assert 'detail.href="/river-fish-atlas/river/"+encodeURIComponent(current.id)+"/";' in target

draft = (ROOT / "content/drafts/river-atlas-seo-20261021.html").read_text(encoding="utf-8")
match = wp.get_script(draft)
v01 = patch_widget.patch_script(match.group(1))
assert wp.sha(v01) == wp.CURRENT_WIDGET_SHA256
fixture = draft[:match.start(1)] + v01 + draft[match.end(1):]
fixture_match = wp.get_script(fixture)
updated, action = wp.edit_body(fixture)
assert action == "UPDATED_WIDGET_SCRIPT_ONLY"
updated_match = wp.get_script(updated)
assert updated_match.group(1) == target
assert fixture[:fixture_match.start(1)] == updated[:updated_match.start(1)]
assert fixture[fixture_match.end(1):] == updated[updated_match.end(1):]
same, action = wp.edit_body(updated)
assert same == updated and action == "ALREADY_CURRENT"

tampered = fixture[:fixture_match.start(1)] + v01 + "\n// unexpected" + fixture[fixture_match.end(1):]
try:
    wp.edit_body(tampered)
except ValueError as exc:
    assert "changed" in str(exc)
else:
    raise AssertionError("Changed live widget was accepted")

assert len(re.findall(r"<script>[\s\S]*?const DATA_ROOT[\s\S]*?</script>", updated)) == 1
print("WordPress v02 widget surgical replacement tests passed.")
