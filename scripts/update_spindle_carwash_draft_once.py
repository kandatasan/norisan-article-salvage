#!/usr/bin/env python3
"""Guarded one-off updater for the existing spindle-grille WordPress draft."""
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

SITE_URL = "https://tsurikue.com"
USER_AGENT = "tsurikue-spindle-carwash-updater/1.0"
POST_ID = 2530
EXPECTED_CURRENT_TITLE = "レクサスのスピンドルグリル洗車は大変？ブラシとブロワーで簡単に洗う方法"
EXPECTED_CURRENT_SLUG = ""
EXPECTED_CURRENT_FEATURED_MEDIA = 0
EXPECTED_CURRENT_CONTENT_SHA256 = "55a2564c33508f71d9bf6026cdd0cddac2296838cc6755d865bfdd8c037c24a2"
NEW_TITLE = "レクサスのスピンドルグリル洗車は簡単？傷を付けにくいブラシとブロワーの使い方"
NEW_SLUG = "lexus-spindle-grille-carwash"
CONTENT_PATH = Path("lexus-editorial-update/spindle-carwash/content.html")
OUT = Path("reports/spindle-carwash-draft-update")


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def get_json(url: str, authorization: str) -> tuple[Any, dict[str, str]]:
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "Authorization": authorization, "User-Agent": USER_AGENT},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.loads(response.read().decode("utf-8")), dict(response.headers)


def post_json(url: str, authorization: str, payload: dict[str, Any]) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": authorization,
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def raw_field(row: dict[str, Any], key: str) -> str:
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)


def fetch_post(authorization: str) -> dict[str, Any]:
    query = urllib.parse.urlencode(
        {"context": "edit", "_fields": "id,slug,status,title,content,featured_media,modified"}
    )
    row, _ = get_json(f"{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}?{query}", authorization)
    return row


def count_published(endpoint: str, authorization: str) -> int:
    query = urllib.parse.urlencode(
        {"context": "edit", "status": "publish", "per_page": "1", "_fields": "id"}
    )
    _, headers = get_json(f"{SITE_URL}/wp-json/wp/v2/{endpoint}?{query}", authorization)
    return int(headers.get("X-WP-Total", "0"))


def public_counts(authorization: str) -> dict[str, int]:
    posts = count_published("posts", authorization)
    pages = count_published("pages", authorization)
    return {"published_posts": posts, "published_pages": pages, "published_total": posts + pages}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_current(row: dict[str, Any]) -> None:
    if int(row.get("id") or 0) != POST_ID:
        raise RuntimeError("post id mismatch")
    if row.get("status") != "draft":
        raise RuntimeError("target is not draft; refusing update")
    if str(row.get("slug") or "") != EXPECTED_CURRENT_SLUG:
        raise RuntimeError(f"current slug changed: {row.get('slug')!r}")
    if html.unescape(raw_field(row, "title")) != EXPECTED_CURRENT_TITLE:
        raise RuntimeError("current title changed; refusing overwrite")
    if int(row.get("featured_media") or 0) != EXPECTED_CURRENT_FEATURED_MEDIA:
        raise RuntimeError("current featured media changed; refusing overwrite")
    current = raw_field(row, "content")
    actual_sha = sha256_text(current)
    if actual_sha != EXPECTED_CURRENT_CONTENT_SHA256:
        raise RuntimeError(f"current content changed; refusing overwrite: {actual_sha}")


def load_new_content() -> str:
    content = CONTENT_PATH.read_text(encoding="utf-8").strip() + "\n"
    required = [
        "<!-- lexus-salvage:v1 slug=lexus-spindle-grille-carwash source=lexus-diary.com/carwash/ -->",
        "<!-- lexus-editorial:v1 slug=lexus-spindle-grille-carwash updated=2026-08-27 -->",
        "レクサスグリル地獄",
        "容赦なく風の力を借りて",
        "洗車を早く終わらせて、出かける時間にしよう",
    ]
    for token in required:
        if token not in content:
            raise RuntimeError(f"required content token missing: {token}")
    forbidden = ["<h1", "lexus-diary.com/wp-content", "MoshimoAffiliateEasyLink", "<div id=\"msmaflink-"]
    for token in forbidden:
        if token in content:
            raise RuntimeError(f"forbidden token present: {token}")
    return content


def main() -> int:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")
    auth = auth_header(user, password)
    content = load_new_content()

    before_counts = public_counts(auth)
    before = fetch_post(auth)
    validate_current(before)

    payload = {
        "title": NEW_TITLE,
        "slug": NEW_SLUG,
        "content": content,
        "status": "draft",
        "featured_media": 0,
    }
    response = post_json(f"{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}", auth, payload)
    if int(response.get("id") or 0) != POST_ID or response.get("status") != "draft":
        raise RuntimeError("update response id/status mismatch")
    if str(response.get("slug") or "") != NEW_SLUG:
        raise RuntimeError("update response slug mismatch")
    if int(response.get("featured_media") or 0) != 0:
        raise RuntimeError("update response featured_media mismatch")

    after = fetch_post(auth)
    after_counts = public_counts(auth)
    if before_counts != after_counts:
        raise RuntimeError("published counts changed")
    if after.get("status") != "draft":
        raise RuntimeError("post no longer draft")
    if str(after.get("slug") or "") != NEW_SLUG:
        raise RuntimeError("post-update slug mismatch")
    if html.unescape(raw_field(after, "title")) != NEW_TITLE:
        raise RuntimeError("post-update title mismatch")
    if int(after.get("featured_media") or 0) != 0:
        raise RuntimeError("post-update featured media mismatch")
    if raw_field(after, "content").strip() != content.strip():
        raise RuntimeError("post-update content mismatch")

    report = {
        "action": "UPDATE",
        "post_id": POST_ID,
        "slug": NEW_SLUG,
        "status": "draft",
        "title": NEW_TITLE,
        "featured_media": 0,
        "confirmed_media_checked": 0,
        "removed_external_legacy_images": True,
        "removed_broken_moshimo_placeholders": True,
        "public_before": before_counts,
        "public_after": after_counts,
        "content_sha256": sha256_text(raw_field(after, "content")),
        "wordpress_write_count": 1,
        "publish_count": 0,
        "media_upload_count": 0,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# spindle carwash draft editorial update",
        "",
        "- action: **UPDATE**",
        f"- post_id: **{POST_ID}**",
        f"- slug: `{NEW_SLUG}`",
        "- status: **draft**",
        f"- title: {NEW_TITLE}",
        "- featured_media: **0**",
        "- confirmed_media_checked: **0**",
        "- removed_external_legacy_images: **true**",
        "- removed_broken_moshimo_placeholders: **true**",
        f"- public_before: **{before_counts['published_total']}**",
        f"- public_after: **{after_counts['published_total']}**",
        f"- content_sha256: `{report['content_sha256']}`",
    ]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
