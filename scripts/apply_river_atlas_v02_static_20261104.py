#!/usr/bin/env python3
"""Surgically switch published post 4240 to the reviewed v02 atlas loader."""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import urllib.parse
import urllib.request
from xml.etree import ElementTree


SITE = "https://tsurikue.com"
POST_ID = 4240
TITLE = "日本の河川図鑑｜全国の河川名・水系・生き物を都道府県から探す"
CURRENT_WIDGET_SHA256 = "1d3113fecb0b911831c75023b1070264594bd9da37dfb7abcb690335b6fb171b"
TARGET_WIDGET_SHA256 = "637e562e990baef27b6b6fea7d11807373668e244f56ac8a1edaa5fae8bda4e4"
SOURCE_HTML = Path(__file__).resolve().parent.parent / "river-fish/xserver-git/source/index.html"
PROTECTED = ("id", "slug", "status", "title", "excerpt", "featured_media", "categories", "author", "template")
WHITE_RIVER_ID = "official21_fdc6d47052822bd6ac413caa"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def get_script(body: str) -> re.Match[str]:
    matches = [m for m in re.finditer(r"<script>([\s\S]*?)</script>", body) if "const DATA_ROOT" in m.group(1)]
    if len(matches) != 1:
        raise ValueError("Atlas script missing or ambiguous")
    return matches[0]


def target_script() -> str:
    script = get_script(SOURCE_HTML.read_text(encoding="utf-8")).group(1)
    replacements = [
        ('const DATA_ROOT = "data/";', 'const DATA_ROOT = "/river-fish-atlas/data/";'),
        ('detail.href="river/"+encodeURIComponent(current.id)+"/";',
         'detail.href="/river-fish-atlas/river/"+encodeURIComponent(current.id)+"/";'),
    ]
    for old, new in replacements:
        if script.count(old) != 1:
            raise ValueError(f"Pinned source widget fragment missing or ambiguous: {old}")
        script = script.replace(old, new, 1)
    if TARGET_WIDGET_SHA256 != "TO_BE_PINNED" and sha(script) != TARGET_WIDGET_SHA256:
        raise ValueError("Generated target widget SHA changed; no write")
    return script


def edit_body(body: str) -> tuple[str, str]:
    match = get_script(body)
    before = match.group(1)
    target = target_script()
    if before == target:
        return body, "ALREADY_CURRENT"
    if sha(before) != CURRENT_WIDGET_SHA256:
        raise ValueError("Pinned live widget changed; no write")
    after = body[:match.start(1)] + target + body[match.end(1):]
    if body[:match.start(1)] != after[:match.start(1)]:
        raise ValueError("Content before widget changed")
    if body[match.end(1):] != after[match.start(1) + len(target):]:
        raise ValueError("Content after widget changed")
    return after, "UPDATED_WIDGET_SCRIPT_ONLY"


def request(path: str, auth: str | None = None, body: dict | None = None):
    headers = {"Accept": "application/json", "User-Agent": "tsurikue-river-atlas-v02/1.0"}
    if auth:
        headers["Authorization"] = auth
    if body is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(
        SITE + path,
        headers=headers,
        method="GET" if body is None else "POST",
        data=None if body is None else json.dumps(body, ensure_ascii=False).encode(),
    )
    with urllib.request.urlopen(req, timeout=90) as response:
        data = response.read()
        if "json" in response.headers.get("content-type", ""):
            return json.loads(data)
        return data.decode()


def fetch_post(auth: str) -> dict:
    fields = ",".join(PROTECTED + ("modified_gmt", "content"))
    return request(f"/wp-json/wp/v2/posts/{POST_ID}?" + urllib.parse.urlencode({"context": "edit", "_fields": fields}), auth)


def verify_production_assets() -> dict:
    additions = request("/river-fish-atlas/data/fish_source_connections_v02_additions.json?v=20261030b")
    details = request("/river-fish-atlas/data/river_detail_page_ids_v01.json?v=20261104")
    page = request(f"/river-fish-atlas/river/{WHITE_RIVER_ID}/")
    sitemap = request("/river-fish-atlas/sitemap.xml")
    if (additions.get("schema") != "tsurikue-source-fish-additions-v02"
            or additions.get("group_count") != 103 or additions.get("record_count") != 375):
        raise ValueError("Production v02 fish additions are not ready")
    if (details.get("schema") != "river-detail-page-ids-v01" or len(details.get("ids", [])) != 280
            or WHITE_RIVER_ID not in details["ids"]):
        raise ValueError("Production detail page inventory is not ready")
    if "白石川の魚類資料記録" not in page or WHITE_RIVER_ID not in page:
        raise ValueError("Production supplemental detail page is not ready")
    xml = ElementTree.fromstring(sitemap)
    ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    urls = [node.text for node in xml.findall(f".//{ns}loc")]
    if len(urls) != 281 or len(urls) != len(set(urls)):
        raise ValueError("Production sitemap is not ready")
    return {"v02_groups": 103, "v02_records": 375, "detail_pages": 280, "sitemap_urls": 281}


def identity_ok(post: dict) -> bool:
    return (post["id"], post["slug"], post["status"], post["featured_media"], post["title"]["raw"]) == (
        POST_ID, "japan-river-atlas", "publish", 4238, TITLE)


def main(mode: str) -> None:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise ValueError("WordPress connection is unavailable")
    auth = "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()
    current = fetch_post(auth)
    if not identity_ok(current):
        raise ValueError("Article identity or protected metadata changed")
    before = current["content"]["raw"]
    after, action = edit_body(before)
    production = None
    production_error = None
    try:
        production = verify_production_assets()
    except Exception as exc:  # check mode reports readiness without writing
        production_error = str(exc)
    print("RIVER_ATLAS_V02_PREFLIGHT", json.dumps({
        "post_id": POST_ID,
        "status": current["status"],
        "action": action,
        "before_content_sha256": sha(before),
        "after_content_sha256": sha(after),
        "before_widget_sha256": sha(get_script(before).group(1)),
        "target_widget_sha256": sha(target_script()),
        "production_ready": production is not None,
        "production": production,
        "production_error": production_error,
    }, ensure_ascii=False), flush=True)
    if mode == "check":
        return
    if production is None:
        raise ValueError(f"Production static atlas is not ready; no WordPress write: {production_error}")
    latest = fetch_post(auth)
    if latest != current:
        raise ValueError("Concurrent WordPress edit detected; no write")
    if action != "ALREADY_CURRENT":
        request(f"/wp-json/wp/v2/posts/{POST_ID}", auth, {"content": after})
    saved = fetch_post(auth)
    if any(saved[key] != current[key] for key in PROTECTED):
        raise ValueError("Protected WordPress metadata changed")
    if saved["content"]["raw"] != after:
        raise ValueError("Saved body differs from exact patch")
    if get_script(saved["content"]["rendered"]).group(1) != target_script():
        raise ValueError("Rendered widget differs from saved source")
    print("RIVER_ATLAS_V02_WORDPRESS_VERIFIED", json.dumps({
        "action": action,
        "post_id": POST_ID,
        "slug": saved["slug"],
        "status": saved["status"],
        "title": saved["title"]["raw"],
        "featured_media": saved["featured_media"],
        "protected_metadata_unchanged": True,
        "prose_and_other_html_unchanged": True,
        "content_sha256": sha(after),
        "widget_sha256": sha(target_script()),
        **production,
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    selected = sys.argv[1] if len(sys.argv) > 1 else "check"
    if selected not in ("check", "apply"):
        raise SystemExit("check or apply")
    main(selected)
