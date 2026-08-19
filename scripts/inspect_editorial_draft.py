#!/usr/bin/env python3
"""Read-only inspector for a salvaged WordPress draft and its attached article images."""
from __future__ import annotations

import argparse
import base64
import html
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

SITE_URL = "https://tsurikue.com"
USER_AGENT = "tsurikue-editorial-draft-inspector/1.0"
REPORT_ROOT = Path("reports/editorial-inspect")


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def get_json(url: str, authorization: str) -> tuple[Any, dict[str, str]]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": authorization,
            "User-Agent": USER_AGENT,
        },
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.loads(response.read().decode("utf-8")), dict(response.headers)


def raw_field(row: dict[str, Any], key: str) -> str:
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)


def find_draft(slug: str, authorization: str) -> dict[str, Any]:
    query = urllib.parse.urlencode(
        {
            "context": "edit",
            "status": "draft",
            "slug": slug,
            "per_page": "100",
            "_fields": "id,slug,status,title,content,featured_media",
        }
    )
    rows, _headers = get_json(f"{SITE_URL}/wp-json/wp/v2/posts?{query}", authorization)
    exact = [row for row in rows if row.get("slug") == slug]
    if len(exact) != 1:
        raise RuntimeError(f"expected exactly one draft for slug={slug!r}; found {len(exact)}")
    return exact[0]


def media_ids_in_order(content: str) -> list[int]:
    ids: list[int] = []
    for match in re.finditer(r"wp-image-(\d+)|\"id\"\s*:\s*(\d+)", content):
        media_id = int(match.group(1) or match.group(2))
        if media_id not in ids:
            ids.append(media_id)
    return ids


def nearby_text(content: str, media_id: int) -> str:
    patterns = [rf"wp-image-{media_id}", rf'\"id\"\s*:\s*{media_id}']
    positions = [content.find(pattern.replace("\\", "")) for pattern in patterns]
    positions = [p for p in positions if p >= 0]
    if not positions:
        return ""
    pos = min(positions)
    start = max(0, pos - 350)
    end = min(len(content), pos + 450)
    chunk = content[start:end]
    chunk = re.sub(r"<!--.*?-->", " ", chunk, flags=re.S)
    chunk = re.sub(r"<[^>]+>", " ", chunk)
    chunk = html.unescape(chunk)
    chunk = re.sub(r"\s+", " ", chunk).strip()
    return chunk[:500]


def fetch_media(media_id: int, authorization: str) -> dict[str, Any]:
    query = urllib.parse.urlencode(
        {"context": "edit", "_fields": "id,source_url,alt_text,caption,media_details"}
    )
    row, _headers = get_json(f"{SITE_URL}/wp-json/wp/v2/media/{media_id}?{query}", authorization)
    details = row.get("media_details") or {}
    return {
        "id": row.get("id"),
        "source_url": row.get("source_url") or "",
        "filename": Path(urllib.parse.urlparse(row.get("source_url") or "").path).name,
        "alt_text": row.get("alt_text") or "",
        "caption": raw_field(row, "caption"),
        "width": details.get("width"),
        "height": details.get("height"),
    }


def inspect(config_path: Path) -> dict[str, Any]:
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    slug = cfg["slug"]
    salvage_marker = cfg["salvage_marker"]

    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")
    authorization = auth_header(user, password)

    post = find_draft(slug, authorization)
    if post.get("status") != "draft":
        raise RuntimeError("target is not draft")
    content = raw_field(post, "content")
    if salvage_marker not in content:
        raise RuntimeError("salvage marker missing; refusing to inspect an unexpected draft")

    image_ids = media_ids_in_order(content)
    images = []
    for media_id in image_ids:
        item = fetch_media(media_id, authorization)
        item["nearby_text"] = nearby_text(content, media_id)
        images.append(item)

    report = {
        "mode": "read-only",
        "wordpress_write_count": 0,
        "post_id": post.get("id"),
        "slug": post.get("slug"),
        "status": post.get("status"),
        "title": html.unescape(raw_field(post, "title")),
        "current_featured_media": int(post.get("featured_media") or 0),
        "image_count": len(images),
        "images": images,
    }

    out = REPORT_ROOT / slug
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    lines = [
        f"# {slug} draft media inspection",
        "",
        "- mode: **READ ONLY**",
        "- wordpress_write_count: **0**",
        f"- post_id: **{report['post_id']}**",
        f"- status: **{report['status']}**",
        f"- title: {report['title']}",
        f"- current_featured_media: **{report['current_featured_media']}**",
        f"- article_image_count: **{report['image_count']}**",
        "",
        "## Images",
    ]
    for index, item in enumerate(images, 1):
        lines.extend(
            [
                f"### {index}. media #{item['id']} — {item['filename']}",
                f"- size: {item['width']}x{item['height']}",
                f"- source_url: {item['source_url']}",
                f"- alt: {item['alt_text'] or '(empty)'}",
                f"- nearby_text: {item['nearby_text'] or '(none)'}",
                "",
            ]
        )
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    inspect(Path(args.config))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
