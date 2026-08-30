#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

SITE = "https://tsurikue.com"
POST_ID = 2948
SLUG = "lexus-ux-used"
TITLE = "レクサスUXの中古は狙い目？新車と比べて中古をおすすめしたい理由"
MEDIA_ID = 2954
MEDIA_PATH = "/wp-content/uploads/2026/08/08eca467-15bf-4b43-88b5-8d1785313cca.jpg"
MEDIA_WIDTH = 1447
MEDIA_HEIGHT = 825
SALVAGE_MARKER = "<!-- lexus-salvage:v1 slug=lexus-ux-used source=lexus-diary.com/used-car/ -->"
EDITORIAL_MARKER = "<!-- tsurikue-editorial:v1 slug=lexus-ux-used -->"
PATCH_MARKER = "<!-- tsurikue-media-patch:v1 slug=lexus-ux-used key=interior-comparison-20260830 -->"
ANCHOR = '''<!-- wp:paragraph -->
<p>この変更内容は<a href="https://global.toyota/jp/newsroom/lexus/37299828.html" target="_blank" rel="noopener">LEXUSの2022年公式発表</a>で確認できます。</p>
<!-- /wp:paragraph -->'''
BLOCK = '''<!-- wp:image {"id":2954,"sizeSlug":"large","linkDestination":"none"} -->
<figure class="wp-block-image size-large"><img src="https://tsurikue.com/wp-content/uploads/2026/08/08eca467-15bf-4b43-88b5-8d1785313cca.jpg" alt="レクサスUX250h前期・後期とUX300hの内装比較" class="wp-image-2954"/></figure>
<!-- /wp:image -->

<!-- wp:paragraph -->
<p>写真は左から<strong>UX250h前期 → UX250h後期 → UX300h</strong>です。<br>前期から後期ではモニターサイズの違いが分かりやすく、前期にあるアナログ時計は今見てもかっこいいです。<br>250h後期と300hを比べると、メーターパネルとシフトノブの違いが目につきます。</p>
<!-- /wp:paragraph -->'''
OUT = Path("reports/lexus-ux-used-interior-comparison")


def auth_header(user: str, password: str) -> str:
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()


def get_json(url: str, auth: str) -> tuple[Any, dict[str, str]]:
    req = urllib.request.Request(url, headers={"Accept": "application/json", "Authorization": auth, "User-Agent": "tsurikue-ux-used-interior-patch/1.2"}, method="GET")
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode("utf-8")), dict(r.headers)


def post_json(url: str, auth: str, payload: dict[str, Any]) -> dict[str, Any]:
    req = urllib.request.Request(url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), headers={"Accept": "application/json", "Content-Type": "application/json; charset=utf-8", "Authorization": auth, "User-Agent": "tsurikue-ux-used-interior-patch/1.2"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def raw_field(row: dict[str, Any], key: str) -> str:
    value = row.get(key) or {}
    return (value.get("raw") or value.get("rendered") or "") if isinstance(value, dict) else str(value)


def count_published(endpoint: str, auth: str) -> int:
    q = urllib.parse.urlencode({"context": "edit", "status": "publish", "per_page": "1", "_fields": "id"})
    _rows, headers = get_json(f"{SITE}/wp-json/wp/v2/{endpoint}?{q}", auth)
    return int(headers.get("X-WP-Total", "0"))


def public_counts(auth: str) -> dict[str, int]:
    posts = count_published("posts", auth)
    pages = count_published("pages", auth)
    return {"published_posts": posts, "published_pages": pages, "published_total": posts + pages}


def fetch_post(auth: str) -> dict[str, Any]:
    q = urllib.parse.urlencode({"context": "edit", "_fields": "id,slug,status,title,content,featured_media"})
    row, _ = get_json(f"{SITE}/wp-json/wp/v2/posts/{POST_ID}?{q}", auth)
    return row


def has_image(content: str, media_id: int) -> bool:
    return f"wp-image-{media_id}" in content or f'"id":{media_id}' in content or f'"id": {media_id}' in content


def validate_media(auth: str) -> None:
    q = urllib.parse.urlencode({"context": "edit", "_fields": "id,source_url,media_details"})
    row, _ = get_json(f"{SITE}/wp-json/wp/v2/media/{MEDIA_ID}?{q}", auth)
    actual_path = urllib.parse.unquote(urllib.parse.urlparse(row.get("source_url") or "").path).casefold()
    details = row.get("media_details") or {}
    if int(row.get("id") or 0) != MEDIA_ID:
        raise RuntimeError("media id mismatch")
    if actual_path != MEDIA_PATH.casefold():
        raise RuntimeError(f"media path mismatch: {actual_path}")
    if int(details.get("width") or 0) != MEDIA_WIDTH or int(details.get("height") or 0) != MEDIA_HEIGHT:
        raise RuntimeError("media dimensions mismatch")


def main() -> int:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")
    auth = auth_header(user, password)
    before_counts = public_counts(auth)
    before = fetch_post(auth)

    if int(before.get("id") or 0) != POST_ID or before.get("slug") != SLUG:
        raise RuntimeError("target identity mismatch")
    if before.get("status") != "draft":
        raise RuntimeError("target is not draft")
    if html.unescape(raw_field(before, "title")) != TITLE:
        raise RuntimeError("title changed; refusing")

    featured_before = int(before.get("featured_media") or 0)
    current = raw_field(before, "content")
    if SALVAGE_MARKER not in current or EDITORIAL_MARKER not in current:
        raise RuntimeError("required salvage/editorial marker missing")
    validate_media(auth)

    if PATCH_MARKER in current:
        if not has_image(current, MEDIA_ID):
            raise RuntimeError("patch marker exists but comparison image missing")
        patched = current
        action = "ALREADY_UP_TO_DATE"
    else:
        if has_image(current, MEDIA_ID):
            raise RuntimeError("comparison image already present without patch marker")
        if current.count(ANCHOR) != 1:
            raise RuntimeError(f"anchor count mismatch: {current.count(ANCHOR)}")
        marked = current.replace(EDITORIAL_MARKER, EDITORIAL_MARKER + "\n" + PATCH_MARKER, 1)
        patched = marked.replace(ANCHOR, ANCHOR + "\n\n" + BLOCK, 1)
        response = post_json(f"{SITE}/wp-json/wp/v2/posts/{POST_ID}", auth, {"content": patched, "status": "draft"})
        if int(response.get("id") or 0) != POST_ID or response.get("slug") != SLUG or response.get("status") != "draft":
            raise RuntimeError("update response identity/status mismatch")
        action = "UPDATE"

    after = fetch_post(auth)
    after_counts = public_counts(auth)
    after_content = raw_field(after, "content")
    featured_after = int(after.get("featured_media") or 0)
    if after_counts != before_counts:
        raise RuntimeError("published counts changed")
    if after.get("status") != "draft" or after.get("slug") != SLUG:
        raise RuntimeError("post-update identity/status mismatch")
    if html.unescape(raw_field(after, "title")) != TITLE:
        raise RuntimeError("title changed during patch")
    if featured_after != featured_before:
        raise RuntimeError("featured media changed during patch")
    if PATCH_MARKER not in after_content or not has_image(after_content, MEDIA_ID):
        raise RuntimeError("comparison patch missing after update")
    if after_content.strip() != patched.strip():
        raise RuntimeError("post-update content differs from patched content")

    report = {
        "action": action,
        "post_id": POST_ID,
        "slug": SLUG,
        "status": "draft",
        "title": TITLE,
        "featured_media_preserved": featured_before,
        "comparison_media": MEDIA_ID,
        "comparison_media_path": MEDIA_PATH,
        "comparison_media_dimensions": f"{MEDIA_WIDTH}x{MEDIA_HEIGHT}",
        "public_before": before_counts,
        "public_after": after_counts,
        "content_sha256": hashlib.sha256(after_content.encode("utf-8")).hexdigest(),
        "wordpress_write_count": 1 if action == "UPDATE" else 0,
        "publish_count": 0,
        "media_upload_count": 0,
        "media_delete_count": 0,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# lexus-ux-used interior comparison patch", "",
        f"- action: **{action}**", f"- post_id: **{POST_ID}**", "- status: **draft**",
        f"- comparison_media: **{MEDIA_ID}**", f"- dimensions: **{MEDIA_WIDTH}x{MEDIA_HEIGHT}**",
        f"- featured_media preserved: **{featured_before}**",
        f"- public_before: **{before_counts['published_total']}**", f"- public_after: **{after_counts['published_total']}**",
        "- publish_count: **0**", "- media_upload_count: **0**", "- media_delete_count: **0**",
        f"- content_sha256: `{report['content_sha256']}`",
    ]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
