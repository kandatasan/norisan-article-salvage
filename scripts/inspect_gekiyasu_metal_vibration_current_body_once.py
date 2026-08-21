#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

SITE_URL = "https://tsurikue.com"
SLUG = "gekiyasu-metal-vibration"
SALVAGE_MARKER = "<!-- old-tsurikue-salvage:v1 slug=gekiyasu-metal-vibration -->"
REPORT_DIR = Path("reports/gekiyasu-metal-vibration-current-body")
USER_AGENT = "tsurikue-gekiyasu-metal-vibration-current-body-inspect/1.0"


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def get_json(url: str, authorization: str):
    req = urllib.request.Request(url, headers={"Accept":"application/json","Authorization":authorization,"User-Agent":USER_AGENT}, method="GET")
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.loads(response.read().decode())


def raw_field(row: dict, key: str) -> str:
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)


def media_ids(content: str) -> list[int]:
    out: list[int] = []
    for match in re.finditer(r"wp-image-(\d+)|\"id\"\s*:\s*(\d+)", content):
        media_id = int(match.group(1) or match.group(2))
        if media_id not in out:
            out.append(media_id)
    return out


def main() -> int:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")
    auth = auth_header(user, password)
    query = urllib.parse.urlencode({"context":"edit","status":"draft","slug":SLUG,"per_page":"100","_fields":"id,slug,status,title,content,featured_media"})
    rows = get_json(f"{SITE_URL}/wp-json/wp/v2/posts?{query}", auth)
    exact = [row for row in rows if row.get("slug") == SLUG]
    if len(exact) != 1:
        raise RuntimeError(f"expected exactly one draft for slug={SLUG}; found {len(exact)}")
    row = exact[0]
    content = raw_field(row, "content")
    if SALVAGE_MARKER not in content:
        raise RuntimeError("salvage marker missing")
    sha = hashlib.sha256(content.encode()).hexdigest()
    ids = media_ids(content)
    title = html.unescape(raw_field(row, "title"))
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "content.html").write_text(content, encoding="utf-8")
    summary = (
        "# gekiyasu-metal-vibration current WordPress draft body\n\n"
        "- mode: **READ ONLY**\n"
        "- wordpress_write_count: **0**\n"
        f"- post_id: **{int(row.get('id') or 0)}**\n"
        f"- slug: **{row.get('slug')}**\n"
        f"- status: **{row.get('status')}**\n"
        f"- title: {title}\n"
        f"- featured_media: **{int(row.get('featured_media') or 0)}**\n"
        f"- article_media_ids: **{', '.join(map(str, ids)) if ids else '(none)'}**\n"
        f"- content_sha256: `{sha}`\n\n"
        "## Current body\n\n```html\n" + content + "\n```\n"
    )
    (REPORT_DIR / "summary.md").write_text(summary, encoding="utf-8")
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
