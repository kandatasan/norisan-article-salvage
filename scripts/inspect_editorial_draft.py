#!/usr/bin/env python3
"""Read-only inspector for a salvaged WordPress draft and candidate media-library images."""
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
USER_AGENT = "tsurikue-editorial-draft-inspector/1.2"
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
    candidates = [f"wp-image-{media_id}", f'"id":{media_id}', f'"id": {media_id}']
    positions = [content.find(token) for token in candidates]
    positions = [p for p in positions if p >= 0]
    if not positions:
        return ""
    pos = min(positions)
    chunk = content[max(0, pos - 350) : min(len(content), pos + 450)]
    chunk = re.sub(r"<!--.*?-->", " ", chunk, flags=re.S)
    chunk = re.sub(r"<[^>]+>", " ", chunk)
    chunk = html.unescape(chunk)
    chunk = re.sub(r"\s+", " ", chunk).strip()
    return chunk[:500]


def media_record(row: dict[str, Any]) -> dict[str, Any]:
    details = row.get("media_details") or {}
    source_url = row.get("source_url") or ""
    return {
        "id": row.get("id"),
        "date": row.get("date") or "",
        "source_url": source_url,
        "filename": Path(urllib.parse.urlparse(source_url).path).name,
        "alt_text": row.get("alt_text") or "",
        "caption": raw_field(row, "caption"),
        "width": details.get("width"),
        "height": details.get("height"),
    }


def fetch_media(media_id: int, authorization: str) -> dict[str, Any]:
    query = urllib.parse.urlencode(
        {"context": "edit", "_fields": "id,date,source_url,alt_text,caption,media_details"}
    )
    row, _headers = get_json(f"{SITE_URL}/wp-json/wp/v2/media/{media_id}?{query}", authorization)
    return media_record(row)


def normalized_stem(filename: str) -> str:
    stem = Path(filename).stem.casefold()
    stem = re.sub(r"-\d+x\d+$", "", stem)
    stem = re.sub(r"-scaled$", "", stem)
    return stem


def scan_media_library(patterns: list[str], authorization: str) -> list[dict[str, Any]]:
    wanted = {normalized_stem(pattern): pattern for pattern in patterns}
    if not wanted:
        return []

    base_params = {
        "context": "edit",
        "per_page": "100",
        "_fields": "id,date,source_url,alt_text,caption,media_details",
    }
    first_query = urllib.parse.urlencode({**base_params, "page": "1"})
    rows, headers = get_json(f"{SITE_URL}/wp-json/wp/v2/media?{first_query}", authorization)
    total_pages = int(headers.get("X-WP-TotalPages", "1"))

    all_rows = list(rows)
    for page in range(2, total_pages + 1):
        query = urllib.parse.urlencode({**base_params, "page": str(page)})
        page_rows, _headers = get_json(f"{SITE_URL}/wp-json/wp/v2/media?{query}", authorization)
        all_rows.extend(page_rows)

    matches: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    for row in all_rows:
        item = media_record(row)
        stem = normalized_stem(item["filename"])
        if stem not in wanted:
            continue
        media_id = int(item["id"])
        if media_id in seen_ids:
            continue
        seen_ids.add(media_id)
        item["matched_pattern"] = wanted[stem]
        matches.append(item)

    order = {normalized_stem(pattern): index for index, pattern in enumerate(patterns)}
    matches.sort(key=lambda item: (order.get(normalized_stem(item["filename"]), 9999), int(item["id"])))
    return matches


def scan_recent_media(limit: int, authorization: str) -> list[dict[str, Any]]:
    """Return the newest media-library rows for read-only human identification."""
    if limit <= 0:
        return []
    limit = max(1, min(limit, 100))
    query = urllib.parse.urlencode(
        {
            "context": "edit",
            "per_page": str(limit),
            "page": "1",
            "orderby": "date",
            "order": "desc",
            "_fields": "id,date,source_url,alt_text,caption,media_details",
        }
    )
    rows, _headers = get_json(f"{SITE_URL}/wp-json/wp/v2/media?{query}", authorization)
    return [media_record(row) for row in rows]


def inspect(config_path: Path) -> dict[str, Any]:
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    slug = cfg["slug"]
    salvage_marker = cfg["salvage_marker"]
    filename_patterns = list(cfg.get("filename_patterns") or [])
    recent_media_limit = int(cfg.get("recent_media_limit") or 0)

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

    candidates = scan_media_library(filename_patterns, authorization)
    recent_media = scan_recent_media(recent_media_limit, authorization)

    report = {
        "mode": "read-only",
        "wordpress_write_count": 0,
        "post_id": post.get("id"),
        "slug": post.get("slug"),
        "status": post.get("status"),
        "title": html.unescape(raw_field(post, "title")),
        "current_featured_media": int(post.get("featured_media") or 0),
        "article_image_count": len(images),
        "article_images": images,
        "filename_patterns": filename_patterns,
        "candidate_media_count": len(candidates),
        "candidate_media": candidates,
        "recent_media_limit": recent_media_limit,
        "recent_media_count": len(recent_media),
        "recent_media": recent_media,
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
        f"- article_image_count: **{report['article_image_count']}**",
        f"- candidate_media_count: **{report['candidate_media_count']}**",
        f"- recent_media_count: **{report['recent_media_count']}**",
        "",
        "## Images already in draft",
    ]
    for index, item in enumerate(images, 1):
        lines.extend(
            [
                f"### {index}. media #{item['id']} — {item['filename']}",
                f"- date: {item['date'] or '(unknown)'}",
                f"- size: {item['width']}x{item['height']}",
                f"- source_url: {item['source_url']}",
                f"- alt: {item['alt_text'] or '(empty)'}",
                f"- nearby_text: {item['nearby_text'] or '(none)'}",
                "",
            ]
        )
    if not images:
        lines.extend(["(none)", ""])

    lines.append("## Candidate media matched from recovered filenames")
    for index, item in enumerate(candidates, 1):
        lines.extend(
            [
                f"### {index}. media #{item['id']} — {item['filename']}",
                f"- matched_pattern: {item['matched_pattern']}",
                f"- date: {item['date'] or '(unknown)'}",
                f"- size: {item['width']}x{item['height']}",
                f"- source_url: {item['source_url']}",
                f"- alt: {item['alt_text'] or '(empty)'}",
                "",
            ]
        )
    if not candidates:
        lines.extend(["(none)", ""])

    lines.append("## Most recent media (read-only identification aid)")
    for index, item in enumerate(recent_media, 1):
        lines.extend(
            [
                f"### {index}. media #{item['id']} — {item['filename']}",
                f"- date: {item['date'] or '(unknown)'}",
                f"- size: {item['width']}x{item['height']}",
                f"- source_url: {item['source_url']}",
                f"- alt: {item['alt_text'] or '(empty)'}",
                "",
            ]
        )
    if not recent_media:
        lines.extend(["(not requested)", ""])

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
