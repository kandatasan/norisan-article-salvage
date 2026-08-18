#!/usr/bin/env python3
"""Update only the salvaged `yamaguchi-drive` WordPress draft."""
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
POST_ID = 2664
SLUG = "yamaguchi-drive"
TITLE = '山口観光1泊2日モデルコース｜広島発ドライブでムーバレー・萩・元乃隅・角島へ'
SALVAGE_MARKER = '<!-- old-tsurikue-salvage:v1 slug=yamaguchi-drive -->'
EDITORIAL_MARKER = '<!-- tsurikue-editorial:yamaguchi-drive:v1 -->'
EXPECTED_MEDIA = {1032: '/wp-content/uploads/2026/05/img_2138.jpg', 1016: '/wp-content/uploads/2026/05/img_2140.jpg', 1021: '/wp-content/uploads/2026/05/img_2142.jpg', 1025: '/wp-content/uploads/2026/05/img_2146.jpg', 36: '/wp-content/uploads/2026/05/gptempdownload-1.jpg', 1022: '/wp-content/uploads/2026/05/img_2147.jpg', 1024: '/wp-content/uploads/2026/05/img_2153.jpg', 1018: '/wp-content/uploads/2026/05/img_2148.jpg', 1023: '/wp-content/uploads/2026/05/img_2149.jpg', 1014: '/wp-content/uploads/2026/05/img_2150.jpg'}
CONTENT_PATH = Path(__file__).with_name("yamaguchi_drive_final_content.html")
USER_AGENT = "tsurikue-yamaguchi-drive-editorial-update/1.0"
REPORT_DIR = Path("reports/yamaguchi-drive-draft-update")


def article_content() -> str:
    return CONTENT_PATH.read_text(encoding="utf-8").strip() + "\n"


def full_content() -> str:
    return SALVAGE_MARKER + "\n" + EDITORIAL_MARKER + "\n" + article_content()


def basic_auth(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def get_json(url: str, authorization: str) -> tuple[Any, dict[str, str]]:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "Authorization": authorization, "User-Agent": USER_AGENT},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.loads(response.read().decode("utf-8")), dict(response.headers)


def post_json(url: str, authorization: str, payload: dict[str, str]) -> dict[str, Any]:
    request = urllib.request.Request(
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
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def raw_field(row: dict[str, Any], key: str) -> str:
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)


def fetch_post(authorization: str) -> dict[str, Any]:
    query = urllib.parse.urlencode({"context": "edit", "_fields": "id,slug,status,link,title,content"})
    row, _headers = get_json(f"{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}?{query}", authorization)
    return row


def count_published(endpoint: str, authorization: str) -> int:
    query = urllib.parse.urlencode({"context": "edit", "status": "publish", "per_page": "1", "_fields": "id"})
    _rows, headers = get_json(f"{SITE_URL}/wp-json/wp/v2/{endpoint}?{query}", authorization)
    return int(headers.get("X-WP-Total", "0"))


def public_counts(authorization: str) -> dict[str, int]:
    posts = count_published("posts", authorization)
    pages = count_published("pages", authorization)
    return {"published_posts": posts, "published_pages": pages, "published_total": posts + pages}


def validate_media(authorization: str) -> int:
    checked = 0
    for media_id, expected_path in EXPECTED_MEDIA.items():
        query = urllib.parse.urlencode({"context": "edit", "_fields": "id,status,source_url"})
        row, _headers = get_json(f"{SITE_URL}/wp-json/wp/v2/media/{media_id}?{query}", authorization)
        actual_path = urllib.parse.unquote(urllib.parse.urlparse(row.get("source_url") or "").path).casefold()
        if actual_path != expected_path.casefold():
            raise RuntimeError(f"media mismatch id={media_id} expected={expected_path} actual={actual_path}")
        checked += 1
    return checked


def build_payload() -> dict[str, str]:
    return {"title": TITLE, "slug": SLUG, "content": full_content(), "status": "draft"}


def validate_target(row: dict[str, Any]) -> str:
    if row.get("id") != POST_ID or row.get("slug") != SLUG:
        raise RuntimeError("post id/slug mismatch")
    if row.get("status") != "draft":
        raise RuntimeError(f"target is not draft; refusing update: {row.get('status')!r}")
    current = raw_field(row, "content")
    if EDITORIAL_MARKER in current:
        if current.strip() == full_content().strip() and html.unescape(raw_field(row, "title")) == TITLE:
            return "ALREADY_UP_TO_DATE"
        raise RuntimeError("editorial marker exists but content/title differs; refusing to overwrite later edits")
    if SALVAGE_MARKER not in current:
        raise RuntimeError("salvage marker missing; refusing to update an unexpected draft")
    return "UPDATE"


def write_report(report: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# yamaguchi-drive draft editorial update", "",
        f"- action: **{report['action']}**",
        f"- post_id: **{report['post_id']}**",
        f"- slug: **{report['slug']}**",
        f"- status: **{report['status']}**",
        f"- title: {report['title']}",
        f"- confirmed_media_checked: **{report['confirmed_media_checked']}**",
        f"- public_before: **{report['public_before']['published_total']}**",
        f"- public_after: **{report['public_after']['published_total']}**",
        f"- content_sha256: `{report['content_sha256']}`",
    ]
    (REPORT_DIR / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")
    authorization = basic_auth(user, password)

    before_counts = public_counts(authorization)
    before = fetch_post(authorization)
    action = validate_target(before)
    checked = validate_media(authorization)

    if action == "UPDATE":
        response = post_json(f"{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}", authorization, build_payload())
        if response.get("id") != POST_ID or response.get("slug") != SLUG or response.get("status") != "draft":
            raise RuntimeError("WordPress update response failed draft/id/slug validation")

    after = fetch_post(authorization)
    after_counts = public_counts(authorization)
    if after_counts != before_counts:
        raise RuntimeError(f"published content count changed: before={before_counts} after={after_counts}")
    if after.get("id") != POST_ID or after.get("slug") != SLUG or after.get("status") != "draft":
        raise RuntimeError("post-update GET failed draft/id/slug validation")
    if html.unescape(raw_field(after, "title")) != TITLE:
        raise RuntimeError("post-update title mismatch")
    after_content = raw_field(after, "content")
    if after_content.strip() != full_content().strip():
        raise RuntimeError("post-update content mismatch")

    report = {
        "action": action, "post_id": POST_ID, "slug": SLUG, "status": after["status"], "title": TITLE,
        "confirmed_media_checked": checked,
        "public_before": before_counts, "public_after": after_counts,
        "content_sha256": hashlib.sha256(after_content.encode("utf-8")).hexdigest(),
        "wordpress_write_count": 1 if action == "UPDATE" else 0,
        "publish_count": 0, "media_upload_count": 0,
    }
    write_report(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
