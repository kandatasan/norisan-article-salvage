#!/usr/bin/env python3
"""Read-only audit for Dragon Quest Island salvage target and existing WordPress media."""
from __future__ import annotations

import base64
import html
import json
import os
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

SITE_URL = "https://tsurikue.com"
USER_AGENT = "tsurikue-dqisland-audit/1.0"
OUT = Path("reports/dqisland-audit")
PHOTO_STEMS = [
    "img_3058", "img_3059", "img_3060", "img_3061", "img_3062", "img_3063",
    "img_3065", "img_3067", "img_3068", "img_3069", "img_3071", "img_3072",
    "img_3073", "img_3074", "img_3075", "img_3076", "img_3077", "img_3081",
    "img_3084", "img_3085", "img_3122",
]


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def get_json(url: str, authorization: str, timeout: int = 60) -> tuple[Any, dict[str, str]]:
    last: Exception | None = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/json",
                    "Authorization": authorization,
                    "User-Agent": USER_AGENT,
                },
                method="GET",
            )
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


def fetch_posts(status: str, authorization: str) -> list[dict[str, Any]]:
    params = {
        "context": "edit",
        "status": status,
        "per_page": "100",
        "page": "1",
        "_fields": "id,slug,status,link,title,content,featured_media,date,modified",
    }
    rows, headers = get_json(
        f"{SITE_URL}/wp-json/wp/v2/posts?{urllib.parse.urlencode(params)}", authorization
    )
    pages = int(headers.get("X-WP-TotalPages", "1"))
    result = list(rows)
    for page in range(2, pages + 1):
        params["page"] = str(page)
        more, _ = get_json(
            f"{SITE_URL}/wp-json/wp/v2/posts?{urllib.parse.urlencode(params)}", authorization
        )
        result.extend(more)
    return result


def is_target(row: dict[str, Any]) -> bool:
    title = html.unescape(raw_field(row, "title"))
    content = raw_field(row, "content")
    slug = str(row.get("slug") or "")
    haystack = f"{title}\n{content}\n{slug}".casefold()
    return any(
        token in haystack
        for token in ("dqisland", "ドラクエアイランド", "ドラゴンクエストアイランド", "ドラゴンクエスト アイランド")
    )


def canonical_photo_key(filename: str) -> str:
    stem = Path(filename).stem.casefold()
    stem = re.sub(r"-\d+x\d+$", "", stem)
    stem = re.sub(r"-scaled$", "", stem)
    stem = re.sub(r"-\d+$", "", stem)
    return stem


def scan_media(authorization: str) -> list[dict[str, Any]]:
    wanted = set(PHOTO_STEMS)
    params = {
        "context": "edit",
        "per_page": "100",
        "page": "1",
        "_fields": "id,date,source_url,alt_text,caption,media_details",
    }
    rows, headers = get_json(
        f"{SITE_URL}/wp-json/wp/v2/media?{urllib.parse.urlencode(params)}", authorization
    )
    pages = int(headers.get("X-WP-TotalPages", "1"))
    all_rows = list(rows)
    for page in range(2, pages + 1):
        params["page"] = str(page)
        more, _ = get_json(
            f"{SITE_URL}/wp-json/wp/v2/media?{urllib.parse.urlencode(params)}", authorization
        )
        all_rows.extend(more)

    matches: list[dict[str, Any]] = []
    for row in all_rows:
        source_url = row.get("source_url") or ""
        filename = Path(urllib.parse.urlparse(source_url).path).name
        key = canonical_photo_key(filename)
        if key not in wanted:
            continue
        details = row.get("media_details") or {}
        matches.append(
            {
                "key": key,
                "id": int(row.get("id") or 0),
                "filename": filename,
                "source_url": source_url,
                "date": row.get("date") or "",
                "alt_text": row.get("alt_text") or "",
                "caption": html.unescape(raw_field(row, "caption")),
                "width": details.get("width"),
                "height": details.get("height"),
            }
        )
    order = {key: i for i, key in enumerate(PHOTO_STEMS)}
    matches.sort(key=lambda item: (order.get(item["key"], 999), item["id"]))
    return matches


def post_record(row: dict[str, Any]) -> dict[str, Any]:
    content = raw_field(row, "content")
    return {
        "id": int(row.get("id") or 0),
        "slug": row.get("slug") or "",
        "status": row.get("status") or "",
        "link": row.get("link") or "",
        "title": html.unescape(raw_field(row, "title")),
        "featured_media": int(row.get("featured_media") or 0),
        "date": row.get("date") or "",
        "modified": row.get("modified") or "",
        "content_length": len(content),
        "markers": re.findall(r"<!--\s*[^>]*(?:salvage|editorial)[^>]*-->", content, flags=re.I)[:20],
    }


def main() -> None:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")
    authorization = auth_header(user, password)

    drafts = fetch_posts("draft", authorization)
    published = fetch_posts("publish", authorization)
    draft_targets = [row for row in drafts if is_target(row)]
    published_targets = [row for row in published if is_target(row)]
    media = scan_media(authorization)

    OUT.mkdir(parents=True, exist_ok=True)
    result = {
        "mode": "read-only",
        "wordpress_write_count": 0,
        "drafts_scanned": len(drafts),
        "published_scanned": len(published),
        "draft_candidates": [post_record(row) for row in draft_targets],
        "published_candidates": [post_record(row) for row in published_targets],
        "photo_stems": PHOTO_STEMS,
        "media_matches": media,
        "matched_photo_keys": sorted({row["key"] for row in media}),
        "missing_photo_keys": [key for key in PHOTO_STEMS if key not in {row["key"] for row in media}],
    }
    (OUT / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for row in draft_targets:
        (OUT / f"draft-{row.get('id')}-content.html").write_text(raw_field(row, "content"), encoding="utf-8")

    lines = [
        "# Dragon Quest Island salvage audit",
        "",
        "- mode: **READ ONLY**",
        "- wordpress_write_count: **0**",
        f"- draft_candidates: **{len(draft_targets)}**",
        f"- published_candidates: **{len(published_targets)}**",
        f"- media_matches: **{len(media)}** / {len(PHOTO_STEMS)} requested stems",
        "",
        "## Draft candidates",
    ]
    for item in result["draft_candidates"] or [None]:
        if item is None:
            lines.append("(none)")
            break
        lines.extend([
            f"### post #{item['id']} — {item['title']}",
            f"- slug: `{item['slug']}`",
            f"- status: **{item['status']}**",
            f"- featured_media: **{item['featured_media']}**",
            f"- modified: {item['modified']}",
            f"- content_length: {item['content_length']}",
            f"- markers: {item['markers'] or '(none)'}",
            "",
        ])
    lines.append("## Published candidates")
    for item in result["published_candidates"] or [None]:
        if item is None:
            lines.append("(none)")
            break
        lines.extend([
            f"### post #{item['id']} — {item['title']}",
            f"- slug: `{item['slug']}`",
            f"- link: {item['link']}",
            "",
        ])
    lines.append("## Media matches")
    for item in media:
        lines.extend([
            f"### {item['key']} → media #{item['id']} — {item['filename']}",
            f"- size: {item['width']}x{item['height']}",
            f"- source_url: {item['source_url']}",
            f"- alt: {item['alt_text'] or '(empty)'}",
            f"- caption: {item['caption'] or '(empty)'}",
            "",
        ])
    lines.append("## Missing photo keys")
    lines.append(", ".join(result["missing_photo_keys"]) or "(none)")
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
