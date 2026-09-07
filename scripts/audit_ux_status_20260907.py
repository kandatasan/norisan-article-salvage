#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

SITE_URL = "https://tsurikue.com"
TARGET_ID = 2517
TARGET_SLUG = "ux-koukai"
REPORT_DIR = Path("reports/audit-ux-status-20260907")
USER_AGENT = "tsurikue-audit-ux-status-20260907/1.1"


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def get_json(url: str, auth: str):
    req = urllib.request.Request(url, headers={"Accept": "application/json", "Authorization": auth, "User-Agent": USER_AGENT}, method="GET")
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.loads(response.read().decode("utf-8")), dict(response.headers)


def raw_field(row, key: str) -> str:
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fetch_status(status: str, auth: str):
    params = urllib.parse.urlencode({
        "context": "edit",
        "status": status,
        "per_page": 100,
        "orderby": "modified",
        "order": "desc",
        "_fields": "id,slug,status,title,content,featured_media,modified,date,categories",
    })
    rows, headers = get_json(f"{SITE_URL}/wp-json/wp/v2/posts?{params}", auth)
    return rows, int(headers.get("X-WP-Total", len(rows)))


def simplify(row):
    content = raw_field(row, "content")
    return {
        "id": row.get("id"),
        "slug": row.get("slug"),
        "status": row.get("status"),
        "title": raw_field(row, "title"),
        "modified": row.get("modified"),
        "date": row.get("date"),
        "featured_media": row.get("featured_media"),
        "categories": row.get("categories") or [],
        "content_length": len(content),
        "content_sha256": sha(content),
        "starts_with": content[:220].replace("\n", " "),
    }


def main():
    user = os.environ["TSURIKUE_WP_USER"]
    password = os.environ["TSURIKUE_WP_APP_PASSWORD"]
    auth = auth_header(user, password)

    all_rows = []
    totals = {}
    errors = {}
    for status in ["publish", "draft", "pending", "private", "future"]:
        try:
            rows, total = fetch_status(status, auth)
            totals[status] = total
            all_rows.extend(rows)
        except Exception as exc:
            totals[status] = None
            errors[status] = f"{type(exc).__name__}: {exc}"

    target_matches = [simplify(r) for r in all_rows if r.get("id") == TARGET_ID or r.get("slug") == TARGET_SLUG]
    ux_related = [simplify(r) for r in all_rows if ("ux" in (r.get("slug") or "").lower()) or ("lexus" in (r.get("slug") or "").lower()) or ("UX" in raw_field(r, "title")) or ("レクサス" in raw_field(r, "title"))]
    ux_related.sort(key=lambda x: x.get("modified") or "", reverse=True)

    recent = [simplify(r) for r in all_rows]
    recent.sort(key=lambda x: x.get("modified") or "", reverse=True)
    recent = recent[:40]

    report = {
        "mode": "GET_ONLY",
        "wordpress_write_count": 0,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "totals": totals,
        "status_fetch_errors": errors,
        "target_matches": target_matches,
        "ux_related": ux_related,
        "recent_modified_posts": recent,
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# UX publish/draft state audit",
        "",
        "- mode: **GET ONLY**",
        "- wordpress_write_count: **0**",
        f"- totals: publish={totals.get('publish')} / draft={totals.get('draft')} / pending={totals.get('pending')} / private={totals.get('private')} / future={totals.get('future')}",
    ]
    if errors:
        lines += ["", "## Non-fatal status fetch errors"]
        for k, v in errors.items():
            lines.append(f"- {k}: {v}")

    lines += ["", "## Target matches"]
    if not target_matches:
        lines.append("- NONE")
    else:
        for x in target_matches:
            lines.append(f"- id={x['id']} slug={x['slug']} status=**{x['status']}** modified={x['modified']} len={x['content_length']} sha={x['content_sha256']} featured_media={x['featured_media']} title={x['title']}")

    lines += ["", "## UX/Lexus related posts"]
    for x in ux_related:
        lines.append(f"- id={x['id']} slug={x['slug']} status=**{x['status']}** modified={x['modified']} len={x['content_length']} sha={x['content_sha256']} title={x['title']}")

    lines += ["", "## Most recently modified posts (top 40)"]
    for x in recent:
        lines.append(f"- {x['modified']} | {x['status']} | id={x['id']} | {x['slug']} | len={x['content_length']} | {x['title']}")

    (REPORT_DIR / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
