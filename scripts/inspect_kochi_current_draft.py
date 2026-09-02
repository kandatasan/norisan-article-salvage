#!/usr/bin/env python3
"""Read-only snapshot of the current Kochi WordPress draft for safe reconciliation."""
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
POST_ID = 3384
OUT = Path("reports/kochi-current-draft-audit")
USER_AGENT = "tsurikue-kochi-current-draft-audit/1.0"


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return "Basic " + token


def raw_field(row: dict, field: str) -> str:
    value = row.get(field) or {}
    if isinstance(value, dict):
        return html.unescape(value.get("raw") or value.get("rendered") or "")
    return html.unescape(str(value))


def main() -> int:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")
    auth = auth_header(user, password)
    params = urllib.parse.urlencode({
        "context": "edit",
        "_fields": "id,slug,status,title,content,excerpt,featured_media,categories,modified,link",
    })
    req = urllib.request.Request(
        f"{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}?{params}",
        headers={"Authorization": auth, "Accept": "application/json", "User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        row = json.loads(response.read().decode("utf-8"))

    content = raw_field(row, "content").strip()
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    report = {
        "mode": "READ_ONLY",
        "post_id": int(row.get("id") or 0),
        "status": row.get("status"),
        "slug": row.get("slug"),
        "title": raw_field(row, "title"),
        "modified": row.get("modified"),
        "featured_media": int(row.get("featured_media") or 0),
        "categories": row.get("categories") or [],
        "content_sha256": digest,
        "wordpress_write_count": 0,
    }
    if report["post_id"] != POST_ID or report["status"] != "draft":
        raise RuntimeError(f"unexpected target: {report}")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "current-draft.html").write_text(content + "\n", encoding="utf-8")
    (OUT / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "summary.md").write_text(
        "# Kochi current draft audit\n\n"
        f"- mode: **READ_ONLY**\n- post_id: **{report['post_id']}**\n- status: **{report['status']}**\n"
        f"- slug: `{report['slug']}`\n- modified: `{report['modified']}`\n"
        f"- content_sha256: `{report['content_sha256']}`\n- wordpress_write_count: **0**\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
