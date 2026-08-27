#!/usr/bin/env python3
"""Read-only audit for the current spindle-grille/carwash WordPress draft and recovered media."""
from __future__ import annotations

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
USER_AGENT = "tsurikue-spindle-carwash-audit/1.0"
OUT = Path("reports/spindle-carwash-audit")
MEDIA_PATTERNS = [
    "img_1901-1.jpg",
    "img_1375-1.jpg",
    "img_1374-1.jpg",
    "img_2750-1.jpg",
    "img_2752-1.jpg",
]


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


def fetch_all_drafts(authorization: str) -> list[dict[str, Any]]:
    params = {
        "context": "edit",
        "status": "draft",
        "per_page": "100",
        "page": "1",
        "_fields": "id,slug,status,title,content,featured_media,date,modified",
    }
    rows, headers = get_json(
        f"{SITE_URL}/wp-json/wp/v2/posts?{urllib.parse.urlencode(params)}", authorization
    )
    total_pages = int(headers.get("X-WP-TotalPages", "1"))
    result = list(rows)
    for page in range(2, total_pages + 1):
        params["page"] = str(page)
        page_rows, _ = get_json(
            f"{SITE_URL}/wp-json/wp/v2/posts?{urllib.parse.urlencode(params)}", authorization
        )
        result.extend(page_rows)
    return result


def is_target(row: dict[str, Any]) -> bool:
    title = html.unescape(raw_field(row, "title"))
    content = raw_field(row, "content")
    slug = str(row.get("slug") or "")
    haystack = f"{title}\n{content}\n{slug}".casefold()
    if "carwash" in slug.casefold():
        return True
    if "スピンドルグリル" in haystack:
        return True
    if "スピンドル" in haystack and ("洗車" in haystack or "グリル" in haystack):
        return True
    return False


def normalized_stem(filename: str) -> str:
    stem = Path(filename).stem.casefold()
    stem = re.sub(r"-\d+x\d+$", "", stem)
    stem = re.sub(r"-scaled$", "", stem)
    return stem


def media_record(row: dict[str, Any]) -> dict[str, Any]:
    details = row.get("media_details") or {}
    source_url = row.get("source_url") or ""
    return {
        "id": int(row.get("id") or 0),
        "date": row.get("date") or "",
        "source_url": source_url,
        "filename": Path(urllib.parse.urlparse(source_url).path).name,
        "alt_text": row.get("alt_text") or "",
        "caption": html.unescape(raw_field(row, "caption")),
        "width": details.get("width"),
        "height": details.get("height"),
    }


def scan_media_library(authorization: str) -> list[dict[str, Any]]:
    wanted = {normalized_stem(name): name for name in MEDIA_PATTERNS}
    params = {
        "context": "edit",
        "per_page": "100",
        "page": "1",
        "_fields": "id,date,source_url,alt_text,caption,media_details",
    }
    rows, headers = get_json(
        f"{SITE_URL}/wp-json/wp/v2/media?{urllib.parse.urlencode(params)}", authorization
    )
    total_pages = int(headers.get("X-WP-TotalPages", "1"))
    all_rows = list(rows)
    for page in range(2, total_pages + 1):
        params["page"] = str(page)
        page_rows, _ = get_json(
            f"{SITE_URL}/wp-json/wp/v2/media?{urllib.parse.urlencode(params)}", authorization
        )
        all_rows.extend(page_rows)

    matches = []
    for row in all_rows:
        item = media_record(row)
        stem = normalized_stem(item["filename"])
        if stem in wanted:
            item["matched_pattern"] = wanted[stem]
            matches.append(item)
    order = {normalized_stem(name): i for i, name in enumerate(MEDIA_PATTERNS)}
    matches.sort(key=lambda item: (order.get(normalized_stem(item["filename"]), 999), item["id"]))
    return matches


def marker_snippets(content: str) -> list[str]:
    return re.findall(r"<!--\s*[^>]*(?:salvage|editorial)[^>]*-->", content, flags=re.I)[:20]


def main() -> None:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")
    authorization = auth_header(user, password)

    drafts = fetch_all_drafts(authorization)
    targets = [row for row in drafts if is_target(row)]
    media = scan_media_library(authorization)

    OUT.mkdir(parents=True, exist_ok=True)
    candidates = []
    for row in targets:
        content = raw_field(row, "content")
        candidates.append(
            {
                "id": int(row.get("id") or 0),
                "slug": row.get("slug") or "",
                "status": row.get("status") or "",
                "title": html.unescape(raw_field(row, "title")),
                "featured_media": int(row.get("featured_media") or 0),
                "date": row.get("date") or "",
                "modified": row.get("modified") or "",
                "content_length": len(content),
                "markers": marker_snippets(content),
            }
        )

    result = {
        "mode": "read-only",
        "wordpress_write_count": 0,
        "draft_count_scanned": len(drafts),
        "candidate_count": len(candidates),
        "candidates": candidates,
        "media_patterns": MEDIA_PATTERNS,
        "candidate_media_count": len(media),
        "candidate_media": media,
    }
    (OUT / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    if len(targets) == 1:
        (OUT / "current-content.html").write_text(
            raw_field(targets[0], "content"), encoding="utf-8"
        )
    else:
        for row in targets:
            (OUT / f"current-content-{row.get('id')}.html").write_text(
                raw_field(row, "content"), encoding="utf-8"
            )

    lines = [
        "# Spindle grille / carwash draft audit",
        "",
        "- mode: **READ ONLY**",
        "- wordpress_write_count: **0**",
        f"- draft_count_scanned: **{len(drafts)}**",
        f"- candidate_count: **{len(candidates)}**",
        f"- candidate_media_count: **{len(media)}**",
        "",
        "## Candidate drafts",
    ]
    if not candidates:
        lines.append("(none)")
    for item in candidates:
        lines.extend(
            [
                f"### post #{item['id']} — {item['title']}",
                f"- slug: `{item['slug']}`",
                f"- status: **{item['status']}**",
                f"- featured_media: **{item['featured_media']}**",
                f"- modified: {item['modified']}",
                f"- content_length: {item['content_length']}",
                f"- markers: {item['markers'] or '(none)'}",
                "",
            ]
        )
    lines.append("## Recovered-filename media matches")
    if not media:
        lines.append("(none)")
    for item in media:
        lines.extend(
            [
                f"### media #{item['id']} — {item['filename']}",
                f"- matched_pattern: `{item['matched_pattern']}`",
                f"- size: {item['width']}x{item['height']}",
                f"- source_url: {item['source_url']}",
                f"- alt: {item['alt_text'] or '(empty)'}",
                f"- caption: {item['caption'] or '(empty)'}",
                "",
            ]
        )
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
