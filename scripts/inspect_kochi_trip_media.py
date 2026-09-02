#!/usr/bin/env python3
"""Read-only audit for the user-owned Kochi trip media in WordPress."""
from __future__ import annotations

import base64
import html
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

SITE_URL = "https://tsurikue.com"
USER_AGENT = "tsurikue-kochi-trip-media-audit/1.1"
OUT = Path("reports/kochi-trip-media-audit")

# Chat uploads may gain '(1)' style suffixes. Match the original iPhone filename key.
WANTED = [
    "IMG_4537", "IMG_4544", "IMG_4545", "IMG_4547", "IMG_4548", "IMG_4550",
    "IMG_4551", "IMG_4555", "IMG_4556", "IMG_4558", "IMG_4561", "IMG_4565",
    "IMG_4568", "IMG_4570", "IMG_4574", "IMG_4575", "IMG_4577", "IMG_4579",
    "IMG_4583", "IMG_4588", "IMG_4600", "IMG_4603", "IMG_4605", "IMG_4606",
    "IMG_4607", "IMG_4611", "IMG_4612", "IMG_4622", "IMG_4623", "IMG_4624",
    "IMG_4626", "IMG_4629", "IMG_4632", "IMG_4636", "IMG_4641", "IMG_4642",
    "IMG_4643", "IMG_4652", "IMG_4653", "IMG_4656", "IMG_4658", "IMG_4659",
    "IMG_4660", "IMG_4665",
    "49C84656-D80C-445F-8D6E-0871A7A9B7F6",
]


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return "Basic " + token


def get_json(url: str, auth: str) -> tuple[Any, dict[str, str]]:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": auth,
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8")), dict(response.headers)


def rendered(row: dict[str, Any], field: str) -> str:
    value = row.get(field) or {}
    if isinstance(value, dict):
        return html.unescape(value.get("rendered") or value.get("raw") or "")
    return html.unescape(str(value))


def fetch_all_media(auth: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 1
    while page <= 60:
        params = urllib.parse.urlencode({
            "context": "edit",
            "per_page": 100,
            "page": page,
            "orderby": "date",
            "order": "desc",
            "_fields": "id,date,slug,source_url,mime_type,media_details,title,caption",
        })
        try:
            batch, headers = get_json(f"{SITE_URL}/wp-json/wp/v2/media?{params}", auth)
        except urllib.error.HTTPError as exc:
            if exc.code == 400 and page > 1:
                break
            raise
        if not batch:
            break
        rows.extend(batch)
        total_pages = int(headers.get("X-WP-TotalPages", str(page)))
        if page >= total_pages:
            break
        page += 1
    return rows


def key_matches(key: str, row: dict[str, Any]) -> bool:
    source = urllib.parse.unquote(row.get("source_url") or "")
    basename = Path(urllib.parse.urlparse(source).path).name
    haystack = " ".join([basename, str(row.get("slug") or ""), rendered(row, "title")]).casefold()
    if key.startswith("IMG_"):
        number = key.split("_", 1)[1]
        return re.search(rf"(?:^|[^0-9])img[-_ ]?{re.escape(number)}(?:[^0-9]|$)", haystack, re.I) is not None
    return key.casefold() in haystack


def compact_media(row: dict[str, Any]) -> dict[str, Any]:
    details = row.get("media_details") or {}
    return {
        "id": int(row.get("id") or 0),
        "date": row.get("date"),
        "slug": row.get("slug"),
        "source_url": row.get("source_url"),
        "mime_type": row.get("mime_type"),
        "width": details.get("width"),
        "height": details.get("height"),
        "title": rendered(row, "title"),
    }


def fetch_categories(auth: str) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode({
        "context": "edit",
        "per_page": 100,
        "hide_empty": "false",
        "_fields": "id,name,slug,parent,count",
    })
    rows, _ = get_json(f"{SITE_URL}/wp-json/wp/v2/categories?{params}", auth)
    return list(rows)


def search_posts(auth: str) -> list[dict[str, Any]]:
    found: dict[int, dict[str, Any]] = {}
    for term in ("高知", "桂浜", "仁淀", "四国カルスト", "ひろめ市場", "OMO7"):
        for status in ("publish", "draft", "pending", "private", "future"):
            params = urllib.parse.urlencode({
                "context": "edit",
                "search": term,
                "status": status,
                "per_page": 100,
                "_fields": "id,slug,status,title,link,modified",
            })
            try:
                rows, _ = get_json(f"{SITE_URL}/wp-json/wp/v2/posts?{params}", auth)
            except urllib.error.HTTPError as exc:
                if exc.code == 400:
                    continue
                raise
            for row in rows:
                found[int(row["id"])] = {
                    "id": int(row["id"]),
                    "slug": row.get("slug"),
                    "status": row.get("status"),
                    "title": rendered(row, "title"),
                    "link": row.get("link"),
                    "modified": row.get("modified"),
                }
    return sorted(found.values(), key=lambda x: x["id"])


def main() -> int:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")
    auth = auth_header(user, password)

    media = fetch_all_media(auth)
    matches: dict[str, list[dict[str, Any]]] = {}
    for key in WANTED:
        candidates = [compact_media(row) for row in media if key_matches(key, row)]
        matches[key] = sorted(candidates, key=lambda x: x.get("id") or 0, reverse=True)

    missing = [key for key, values in matches.items() if not values]
    ambiguous = [key for key, values in matches.items() if len(values) > 1]
    recent_media = [compact_media(row) for row in media[:30]]
    categories = fetch_categories(auth)
    relevant_categories = [
        row for row in categories
        if any(word in str(row.get("name") or "") for word in ("旅行", "おでかけ", "観光", "モデル"))
        or any(word in str(row.get("slug") or "") for word in ("travel", "outing", "sightseeing", "model"))
    ]
    possible_duplicates = search_posts(auth)

    report = {
        "mode": "READ_ONLY",
        "wanted_count": len(WANTED),
        "matched_count": len(WANTED) - len(missing),
        "missing": missing,
        "ambiguous": ambiguous,
        "matches": matches,
        "recent_media": recent_media,
        "relevant_categories": relevant_categories,
        "possible_duplicate_posts": possible_duplicates,
        "media_rows_scanned": len(media),
        "wordpress_write_count": 0,
    }

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Kochi trip WordPress media audit",
        "",
        "- mode: **READ_ONLY**",
        f"- wanted_count: **{report['wanted_count']}**",
        f"- matched_count: **{report['matched_count']}**",
        f"- media_rows_scanned: **{report['media_rows_scanned']}**",
        f"- missing_count: **{len(missing)}**",
        f"- ambiguous_count: **{len(ambiguous)}**",
        "- wordpress_write_count: **0**",
        "",
        "## Missing",
    ]
    lines.extend([f"- `{key}`" for key in missing] or ["- none"])
    lines += ["", "## Ambiguous"]
    lines.extend([f"- `{key}`: {len(matches[key])} candidates" for key in ambiguous] or ["- none"])
    lines += ["", "## Matches"]
    for key in WANTED:
        vals = matches[key]
        if not vals:
            continue
        for row in vals:
            lines.append(
                f"- `{key}` -> media **{row['id']}**, `{row['mime_type']}`, "
                f"{row.get('width')}x{row.get('height')}, `{urllib.parse.urlparse(row['source_url']).path}`"
            )
    lines += ["", "## Recent media (latest 30)"]
    for row in recent_media:
        lines.append(
            f"- media **{row['id']}** | `{row['date']}` | `{row['mime_type']}` | "
            f"{row.get('width')}x{row.get('height')} | `{row.get('slug')}` | "
            f"`{urllib.parse.urlparse(row['source_url']).path}` | {row.get('title')}"
        )
    lines += ["", "## Relevant categories"]
    for row in relevant_categories:
        lines.append(f"- id **{row['id']}** | {row['name']} | `{row['slug']}` | parent={row['parent']}")
    if not relevant_categories:
        lines.append("- none")
    lines += ["", "## Possible duplicate posts"]
    for row in possible_duplicates:
        lines.append(f"- post **{row['id']}** | `{row['status']}` | `{row['slug']}` | {row['title']}")
    if not possible_duplicates:
        lines.append("- none")

    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "mode": report["mode"],
        "wanted_count": report["wanted_count"],
        "matched_count": report["matched_count"],
        "missing": report["missing"],
        "ambiguous": report["ambiguous"],
        "recent_media": recent_media[:10],
        "relevant_categories": report["relevant_categories"],
        "possible_duplicate_posts": report["possible_duplicate_posts"],
        "media_rows_scanned": report["media_rows_scanned"],
        "wordpress_write_count": report["wordpress_write_count"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
