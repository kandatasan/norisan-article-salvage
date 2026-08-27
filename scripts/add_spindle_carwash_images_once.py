#!/usr/bin/env python3
"""Insert four already-existing WordPress media images into the spindle-grille draft, once and safely."""
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
USER_AGENT = "tsurikue-spindle-carwash-images/1.2"
POST_ID = 2530
EXPECTED_TITLE = "レクサスのスピンドルグリル洗車は簡単？傷を付けにくいブラシとブロワーの使い方"
EXPECTED_SLUG = "lexus-spindle-grille-carwash"
IMAGE_MARKER = "<!-- lexus-editorial-images:v1 media=1428,1446,1335,1386 -->"
OUT = Path("reports/spindle-carwash-image-insert")

MEDIA = {
    1428: {
        "path": "/wp-content/uploads/2026/05/img_2949.jpg",
        "src": "https://tsurikue.com/wp-content/uploads/2026/05/img_2949.jpg",
        "alt": "レクサスUX F SPORTのスピンドルグリルを洗車ブラシで洗っている様子",
        "caption": "ブラシをスピンドルグリルへ差し込んで洗っているところ。",
    },
    1446: {
        "path": "/wp-content/uploads/2026/05/img_2950.jpg",
        "src": "https://tsurikue.com/wp-content/uploads/2026/05/img_2950.jpg",
        "alt": "スピンドルグリルに洗車ブラシの毛を入れて洗っているアップ写真",
        "caption": "アップで見るとこんな感じ。毛先だけでなく、毛の中腹まで使っています。",
    },
    1335: {
        "path": "/wp-content/uploads/2026/05/img_2750.jpg",
        "src": "https://tsurikue.com/wp-content/uploads/2026/05/img_2750.jpg",
        "alt": "レクサスUX F SPORTのスピンドルグリルにブロワーを当てて水滴を飛ばしている様子",
        "caption": "細かいスキマの水滴は、ブロワーでまとめて飛ばします。",
    },
    1386: {
        "path": "/wp-content/uploads/2026/05/img_2751.jpg",
        "src": "https://tsurikue.com/wp-content/uploads/2026/05/img_2751.jpg",
        "alt": "洗車後のレクサスUX F SPORTのスピンドルグリル",
        "caption": "ブラシとブロワーで洗い終えたスピンドルグリル。",
    },
}


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


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fetch_post(auth: str) -> dict[str, Any]:
    q = urllib.parse.urlencode(
        {"context": "edit", "_fields": "id,slug,status,title,content,featured_media,modified"}
    )
    row, _ = get_json(f"{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}?{q}", auth)
    return row


def count_published(endpoint: str, auth: str) -> int:
    q = urllib.parse.urlencode({"context": "edit", "status": "publish", "per_page": "1", "_fields": "id"})
    _, headers = get_json(f"{SITE_URL}/wp-json/wp/v2/{endpoint}?{q}", auth)
    return int(headers.get("X-WP-Total", "0"))


def public_counts(auth: str) -> dict[str, int]:
    posts = count_published("posts", auth)
    pages = count_published("pages", auth)
    return {"published_posts": posts, "published_pages": pages, "published_total": posts + pages}


def validate_media(auth: str) -> int:
    for media_id, expected in MEDIA.items():
        q = urllib.parse.urlencode({"context": "edit", "_fields": "id,status,source_url"})
        row, _ = get_json(f"{SITE_URL}/wp-json/wp/v2/media/{media_id}?{q}", auth)
        if int(row.get("id") or 0) != media_id:
            raise RuntimeError(f"media id mismatch: {media_id}")
        actual_path = urllib.parse.unquote(urllib.parse.urlparse(row.get("source_url") or "").path).casefold()
        if actual_path != expected["path"].casefold():
            raise RuntimeError(f"media path mismatch id={media_id}: {actual_path}")
    return len(MEDIA)


def image_block(media_id: int) -> str:
    item = MEDIA[media_id]
    return (
        f'<!-- wp:image {{"id":{media_id},"sizeSlug":"full","linkDestination":"none"}} -->\n'
        f'<figure class="wp-block-image size-full"><img src="{item["src"]}" alt="{item["alt"]}" class="wp-image-{media_id}"/>'
        f'<figcaption class="wp-element-caption">{item["caption"]}</figcaption></figure>\n'
        '<!-- /wp:image -->'
    )


def replace_once(content: str, anchor: str, addition: str, label: str) -> str:
    count = content.count(anchor)
    if count != 1:
        raise RuntimeError(f"anchor {label} expected once, found {count}")
    return content.replace(anchor, anchor + "\n\n" + addition, 1)


def build_content(current: str) -> str:
    if IMAGE_MARKER in current:
        return current
    for media_id in MEDIA:
        if f"wp-image-{media_id}" in current:
            raise RuntimeError(f"partial image insertion detected: {media_id}")

    marker_anchor = "<!-- lexus-editorial:v1 slug=lexus-spindle-grille-carwash updated=2026-08-27 -->"
    if marker_anchor not in current:
        raise RuntimeError("editorial marker missing")
    content = current.replace(marker_anchor, marker_anchor + "\n" + IMAGE_MARKER, 1)

    content = replace_once(
        content,
        '<!-- wp:paragraph -->\n<p>カーシャンプーをしっかり泡立て、ブラシにも泡をなじませます。</p>\n<!-- /wp:paragraph -->',
        image_block(1428),
        "brush-overview",
    )
    content = replace_once(
        content,
        '<!-- wp:paragraph -->\n<p>ブラシをグリルへ優しく差し込み、毛の中腹あたりを使って洗うイメージです。</p>\n<!-- /wp:paragraph -->',
        image_block(1446),
        "brush-closeup",
    )
    content = replace_once(
        content,
        '<!-- wp:paragraph -->\n<p><strong>容赦なく風の力を借りて、水滴を飛ばします。</strong></p>\n<!-- /wp:paragraph -->',
        image_block(1335),
        "blower",
    )
    content = replace_once(
        content,
        '<!-- wp:paragraph -->\n<p>うん、キレイになった。</p>\n<!-- /wp:paragraph -->',
        image_block(1386),
        "finish",
    )
    return content


def validate_post_shape(row: dict[str, Any]) -> str:
    if int(row.get("id") or 0) != POST_ID:
        raise RuntimeError("post id mismatch")
    if row.get("status") != "draft":
        raise RuntimeError("target is not draft; refusing update")
    if str(row.get("slug") or "") != EXPECTED_SLUG:
        raise RuntimeError("slug changed; refusing update")
    if html.unescape(raw_field(row, "title")) != EXPECTED_TITLE:
        raise RuntimeError("title changed; refusing update")
    return raw_field(row, "content")


def write_report(report: dict[str, Any]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# spindle carwash image insertion",
        "",
        f"- action: **{report['action']}**",
        f"- post_id: **{POST_ID}**",
        "- status: **draft**",
        f"- featured_media_before: **{report['featured_media_before']}**",
        f"- featured_media_after: **{report['featured_media_after']}**",
        f"- media_checked: **{report['media_checked']}**",
        f"- inserted_media_ids: **{', '.join(map(str, report['inserted_media_ids']))}**",
        f"- public_before: **{report['public_before']['published_total']}**",
        f"- public_after: **{report['public_after']['published_total']}**",
        f"- content_sha256_before: `{report['content_sha256_before']}`",
        f"- content_sha256_after: `{report['content_sha256_after']}`",
        f"- wordpress_write_count: **{report['wordpress_write_count']}**",
        "- publish_count: **0**",
        "- media_upload_count: **0**",
    ]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")
    auth = auth_header(user, password)

    before_counts = public_counts(auth)
    before = fetch_post(auth)
    current = validate_post_shape(before)
    featured_before = int(before.get("featured_media") or 0)
    before_sha = sha256_text(current)
    media_checked = validate_media(auth)

    if IMAGE_MARKER in current:
        missing = [mid for mid in MEDIA if f"wp-image-{mid}" not in current]
        if missing:
            raise RuntimeError(f"image marker exists but media missing: {missing}")
        action = "ALREADY_UP_TO_DATE"
        updated = current
        write_count = 0
    else:
        updated = build_content(current)
        response = post_json(
            f"{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}",
            auth,
            {"content": updated, "status": "draft"},
        )
        if int(response.get("id") or 0) != POST_ID or response.get("status") != "draft":
            raise RuntimeError("update response id/status mismatch")
        action = "UPDATE"
        write_count = 1

    after = fetch_post(auth)
    after_content = validate_post_shape(after)
    featured_after = int(after.get("featured_media") or 0)
    after_counts = public_counts(auth)
    if before_counts != after_counts:
        raise RuntimeError("published counts changed")
    if featured_before != featured_after:
        raise RuntimeError("featured media changed during image insertion")
    if after_content.strip() != updated.strip():
        raise RuntimeError("post-update content mismatch")
    for media_id in MEDIA:
        if f"wp-image-{media_id}" not in after_content:
            raise RuntimeError(f"inserted image missing after update: {media_id}")

    report = {
        "action": action,
        "post_id": POST_ID,
        "status": "draft",
        "featured_media_before": featured_before,
        "featured_media_after": featured_after,
        "media_checked": media_checked,
        "inserted_media_ids": list(MEDIA.keys()),
        "public_before": before_counts,
        "public_after": after_counts,
        "content_sha256_before": before_sha,
        "content_sha256_after": sha256_text(after_content),
        "wordpress_write_count": write_count,
        "publish_count": 0,
        "media_upload_count": 0,
    }
    write_report(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
