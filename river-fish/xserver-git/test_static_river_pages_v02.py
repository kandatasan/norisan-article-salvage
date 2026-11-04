#!/usr/bin/env python3
"""Regression checks for reviewed supplemental static river pages."""
from pathlib import Path
import json
from xml.etree import ElementTree

ROOT = Path(__file__).with_name("source")
DATA = ROOT / "data"

additions = json.loads((DATA / "fish_source_connections_v02_additions.json").read_text(encoding="utf-8"))
eligible = {g["navigation_target_id"]: g for g in additions["groups"] if len(g["records"]) >= 10}
assert len(eligible) == 7

for river_id, group in eligible.items():
    page = (ROOT / "river" / river_id / "index.html").read_text(encoding="utf-8")
    assert f"river/{river_id}/" in page
    assert group["prefecture"] in page and group["river"] in page
    assert all(record["recorded_name"] in page for record in group["records"])
    assert all(record["source_url"] in page for record in group["records"])
    assert "現在の生息" in page and "自動統合していません" in page

below_threshold = {g["navigation_target_id"] for g in additions["groups"] if len(g["records"]) < 10}
assert not any((ROOT / "river" / river_id / "index.html").exists() for river_id in below_threshold)

index = (ROOT / "river/index.html").read_text(encoding="utf-8")
assert index.count("<!-- v02-static-start -->") == 1
assert index.count("<!-- v02-static-end -->") == 1
assert all(f'data-river-group-id="{g["navigation_target_id"]}"' in index for g in additions["groups"])
assert all(record["recorded_name"] in index for g in additions["groups"] for record in g["records"])
assert all(record["source_title"] in index for g in additions["groups"] for record in g["records"])
assert "個別ページ、1〜9件の96グループ" in index

detail_ids = json.loads((DATA / "river_detail_page_ids_v01.json").read_text(encoding="utf-8"))["ids"]
assert len(detail_ids) == 280
assert set(eligible).issubset(detail_ids)

ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
tree = ElementTree.parse(ROOT / "sitemap.xml")
urls = [n.text for n in tree.findall(f".//{ns}loc")]
assert len(urls) == 281 and len(set(urls)) == 281
assert all(f"https://tsurikue.com/river-fish-atlas/river/{river_id}/" in urls for river_id in eligible)

manifest = json.loads((ROOT / "seo-build-manifest-v029.json").read_text(encoding="utf-8"))
assert manifest["number_of_indexable_data_groups"] == 280
assert manifest["v02_supplemental_summary"]["aggregate_list_only_groups"] == 96
app = (ROOT / "index.html").read_text(encoding="utf-8")
assert 'river_detail_page_ids_v01.json?v=20261104' in app
assert 'result[4].ids.length!==280' in app
print("Supplemental static river page tests passed: 7 detail pages, 103 aggregate groups, 281 sitemap URLs.")
