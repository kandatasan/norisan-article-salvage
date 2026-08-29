#!/usr/bin/env python3
"""Create the Saijo sakagura-dori article as one guarded WordPress draft."""
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

SITE_URL = "https://tsurikue.com"
USER_AGENT = "tsurikue-saijo-sakagura-create/1.0"
TITLE = "西条酒蔵通りを歩いてみた！亀齢好きが試飲・酒蔵めぐりを写真で紹介"
SLUG = "saijo-sakagura-dori"
CATEGORY_ID = 7
FEATURED_MEDIA_ID = 2940
EXCERPT = "東広島市・西条酒蔵通りを実際に歩いた体験記。普段は人が少なく白壁と赤レンガ煙突を眺めながら酒蔵めぐりや試飲が楽しめます。亀齢好きの筆者が「吉田屋」の感想、賀茂鶴、酒まつり当日の様子まで写真で紹介します。"
CONTENT_PATH = Path("editorial/saijo-sakagura-dori/content.html")
OUT = Path("reports/saijo-sakagura-create")
EDITORIAL_MARKER = "<!-- editorial:saijo-sakagura-dori:create-guard:v1 -->"

EXPECTED_MEDIA = {
    2940: "/wp-content/uploads/2026/08/84925020-bffa-4718-bbd2-f9c1ef2a9ad2.jpg",
    2932: "/wp-content/uploads/2026/08/befe8465-2627-4832-981d-d8f1193e7f4d.jpg",
    2934: "/wp-content/uploads/2026/08/836f3f0b-cdbe-44ea-a1f9-056ac719f316.jpg",
    2931: "/wp-content/uploads/2026/08/fc700358-a71d-4829-bb05-4bc601d9ce0f.jpg",
    2933: "/wp-content/uploads/2026/08/d78d1e43-e39e-49e1-8d79-1e015c468f1a.jpg",
    2935: "/wp-content/uploads/2026/08/039624f5-5844-429f-9fda-4780cdfbdada.jpg",
    2214: "/wp-content/uploads/2026/06/IMG_0948.jpeg",
    2939: "/wp-content/uploads/2026/08/img_2201.jpg",
    2936: "/wp-content/uploads/2026/08/img_2203.jpg",
    2938: "/wp-content/uploads/2026/08/img_2204.jpg",
    2937: "/wp-content/uploads/2026/08/img_2216.jpg",
}


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def request_json(
    url: str,
    authorization: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: int = 60,
) -> tuple[Any, dict[str, str]]:
    data = None
    headers = {
        "Accept": "application/json",
        "Authorization": authorization,
        "User-Agent": USER_AGENT,
    }
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"

    last: Exception | None = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8")), dict(response.headers)
        except Exception as exc:
            last = exc
            if attempt == 2:
                raise
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(str(last))


def raw_field(row: dict[str, Any], key: str) -> str:
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def count_published(endpoint: str, auth: str) -> int:
    q = urllib.parse.urlencode({
        "context": "edit",
        "status": "publish",
        "per_page": "1",
        "_fields": "id",
    })
    _, headers = request_json(f"{SITE_URL}/wp-json/wp/v2/{endpoint}?{q}", auth)
    return int(headers.get("X-WP-Total", "0"))


def public_counts(auth: str) -> dict[str, int]:
    posts = count_published("posts", auth)
    pages = count_published("pages", auth)
    return {
        "published_posts": posts,
        "published_pages": pages,
        "published_total": posts + pages,
    }


def validate_existing_media(auth: str) -> int:
    checked = 0
    for media_id, expected_path in EXPECTED_MEDIA.items():
        q = urllib.parse.urlencode({"context": "edit", "_fields": "id,source_url"})
        row, _ = request_json(f"{SITE_URL}/wp-json/wp/v2/media/{media_id}?{q}", auth)
        if int(row.get("id") or 0) != media_id:
            raise RuntimeError(f"media id mismatch: {media_id}")
        actual = urllib.parse.unquote(urllib.parse.urlparse(row.get("source_url") or "").path)
        if actual.casefold() != expected_path.casefold():
            raise RuntimeError(f"media path mismatch id={media_id}: {actual}")
        checked += 1
    return checked


def build_content() -> str:
    content = CONTENT_PATH.read_text(encoding="utf-8").strip()
    if "<h1" in content.casefold():
        raise RuntimeError("body must not contain H1")
    for media_id, expected_path in EXPECTED_MEDIA.items():
        if f"wp-image-{media_id}" not in content:
            raise RuntimeError(f"confirmed media missing from content: {media_id}")
        if expected_path not in content:
            raise RuntimeError(f"confirmed media path missing from content: {expected_path}")
    if content.count("<!-- editorial:saijo-sakagura-dori:v1 updated=2026-08-29 -->") != 1:
        raise RuntimeError("editorial content marker missing or duplicated")
    return EDITORIAL_MARKER + "\n" + content


def fetch_posts_by_slug(auth: str, status: str) -> list[dict[str, Any]]:
    params = {
        "context": "edit",
        "status": status,
        "slug": SLUG,
        "per_page": "100",
        "_fields": "id,slug,status,title,content,excerpt,featured_media,categories,modified,link",
    }
    rows, _ = request_json(f"{SITE_URL}/wp-json/wp/v2/posts?{urllib.parse.urlencode(params)}", auth)
    return list(rows)


def validate_draft(row: dict[str, Any], expected_content: str) -> None:
    if row.get("status") != "draft":
        raise RuntimeError("target is not draft")
    if str(row.get("slug") or "") != SLUG:
        raise RuntimeError("slug mismatch")
    if html.unescape(raw_field(row, "title")) != TITLE:
        raise RuntimeError("title mismatch")
    if int(row.get("featured_media") or 0) != FEATURED_MEDIA_ID:
        raise RuntimeError("featured media mismatch")
    categories = [int(value) for value in (row.get("categories") or [])]
    if categories != [CATEGORY_ID]:
        raise RuntimeError(f"category mismatch: {categories}")
    actual_content = raw_field(row, "content").strip()
    if actual_content != expected_content.strip():
        raise RuntimeError(
            "existing draft content differs; refusing overwrite: " + sha256_text(actual_content)
        )


def write_report(report: dict[str, Any]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "result.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Saijo sakagura draft creation",
        "",
        f"- action: **{report['action']}**",
        f"- post_id: **{report['post_id']}**",
        f"- status: **{report['status']}**",
        f"- slug: `{SLUG}`",
        f"- title: {TITLE}",
        f"- category_id: **{CATEGORY_ID}**",
        f"- featured_media: **{FEATURED_MEDIA_ID}**",
        f"- confirmed_media_checked: **{report['confirmed_media_checked']}**",
        f"- media_upload_count: **{report['media_upload_count']}**",
        f"- wordpress_write_count: **{report['wordpress_write_count']}**",
        f"- published_before: **{report['public_before']['published_total']}**",
        f"- published_after: **{report['public_after']['published_total']}**",
        f"- content_sha256: `{report['content_sha256']}`",
        "- publish_count: **0**",
    ]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")
    auth = auth_header(user, password)

    before_counts = public_counts(auth)
    confirmed_media_checked = validate_existing_media(auth)
    expected_content = build_content()

    published = fetch_posts_by_slug(auth, "publish")
    if published:
        raise RuntimeError(f"published /{SLUG}/ already exists; refusing create")

    drafts = fetch_posts_by_slug(auth, "draft")
    if len(drafts) > 1:
        raise RuntimeError(f"multiple /{SLUG}/ drafts found: {[row.get('id') for row in drafts]}")

    if drafts:
        row = drafts[0]
        validate_draft(row, expected_content)
        action = "ALREADY_UP_TO_DATE"
        post_id = int(row.get("id") or 0)
        post_write_count = 0
    else:
        payload = {
            "title": TITLE,
            "slug": SLUG,
            "status": "draft",
            "content": expected_content,
            "excerpt": EXCERPT,
            "featured_media": FEATURED_MEDIA_ID,
            "categories": [CATEGORY_ID],
        }
        created, _ = request_json(
            f"{SITE_URL}/wp-json/wp/v2/posts",
            auth,
            method="POST",
            payload=payload,
            timeout=90,
        )
        post_id = int(created.get("id") or 0)
        if not post_id or created.get("status") != "draft":
            raise RuntimeError(
                f"unexpected create response: id={post_id} status={created.get('status')}"
            )
        action = "CREATE_DRAFT"
        post_write_count = 1

    q = urllib.parse.urlencode({
        "context": "edit",
        "_fields": "id,slug,status,title,content,excerpt,featured_media,categories,modified,link",
    })
    after_row, _ = request_json(f"{SITE_URL}/wp-json/wp/v2/posts/{post_id}?{q}", auth)
    validate_draft(after_row, expected_content)

    after_counts = public_counts(auth)
    if before_counts != after_counts:
        raise RuntimeError(f"published counts changed: {before_counts} -> {after_counts}")

    report = {
        "action": action,
        "post_id": post_id,
        "status": after_row.get("status"),
        "slug": SLUG,
        "title": TITLE,
        "category_id": CATEGORY_ID,
        "featured_media": FEATURED_MEDIA_ID,
        "confirmed_media_checked": confirmed_media_checked,
        "media_upload_count": 0,
        "wordpress_write_count": post_write_count,
        "public_before": before_counts,
        "public_after": after_counts,
        "content_sha256": sha256_text(expected_content.strip()),
        "publish_count": 0,
    }
    write_report(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
