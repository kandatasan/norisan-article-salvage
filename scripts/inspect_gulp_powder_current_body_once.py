#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

SITE_URL = "https://tsurikue.com"
POST_ID = 2629
SLUG = "gulp-powder"
EXPECTED_TITLE = "ガルプはワームだけじゃない！？粉系フォーミュラ、ガルプ！アライブパウダーと塩で鳥ササミを漬けてみた。"
SALVAGE_MARKER = "<!-- old-tsurikue-salvage:v1 slug=gulp-powder -->"
REPORT_DIR = Path("reports/gulp-powder-current-body")
USER_AGENT = "tsurikue-gulp-powder-current-body-inspect/1.0"


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


def main() -> int:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")
    auth = auth_header(user, password)
    query = urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,content,featured_media"})
    row = get_json(f"{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}?{query}", auth)
    if int(row.get("id") or 0) != POST_ID or row.get("slug") != SLUG or row.get("status") != "draft":
        raise RuntimeError("draft identity mismatch")
    if html.unescape(raw_field(row,"title")) != EXPECTED_TITLE:
        raise RuntimeError("title mismatch")
    content = raw_field(row,"content")
    if SALVAGE_MARKER not in content:
        raise RuntimeError("salvage marker missing")
    sha = hashlib.sha256(content.encode()).hexdigest()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "content.html").write_text(content, encoding="utf-8")
    summary = (
        "# gulp-powder current WordPress draft body\n\n"
        "- mode: **READ ONLY**\n"
        "- wordpress_write_count: **0**\n"
        f"- post_id: **{POST_ID}**\n"
        "- status: **draft**\n"
        f"- title: {EXPECTED_TITLE}\n"
        f"- featured_media: **{int(row.get('featured_media') or 0)}**\n"
        f"- content_sha256: `{sha}`\n\n"
        "## Current body\n\n```html\n" + content + "\n```\n"
    )
    (REPORT_DIR / "summary.md").write_text(summary, encoding="utf-8")
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
