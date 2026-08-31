#!/usr/bin/env python3
"""Create or guarded-update one WordPress experimental fixed page as draft only."""
from __future__ import annotations

import argparse
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
USER_AGENT = "tsurikue-experimental-page-once/1.1"
PAGE_STATUSES = ("draft", "publish", "pending", "private", "future", "trash")


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def get_json(url: str, authorization: str):
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": authorization,
            "User-Agent": USER_AGENT,
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.loads(response.read().decode()), dict(response.headers)


def post_json(url: str, authorization: str, payload: dict[str, Any]):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": authorization,
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode())


def raw_field(row: dict[str, Any], key: str) -> str:
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)


def load_package(config_path: Path):
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    required = ("slug", "title", "marker", "content_file")
    missing = [key for key in required if not cfg.get(key)]
    if missing:
        raise RuntimeError(f"missing config keys: {', '.join(missing)}")
    content = (config_path.parent / cfg["content_file"]).read_text(encoding="utf-8").strip()
    full = cfg["marker"] + "\n" + content + "\n"
    return cfg, full


def count_published(endpoint: str, authorization: str) -> int:
    query = urllib.parse.urlencode(
        {"context": "edit", "status": "publish", "per_page": "1", "_fields": "id"}
    )
    _, headers = get_json(f"{SITE_URL}/wp-json/wp/v2/{endpoint}?{query}", authorization)
    return int(headers.get("X-WP-Total", "0"))


def public_counts(authorization: str):
    posts = count_published("posts", authorization)
    pages = count_published("pages", authorization)
    return {
        "published_posts": posts,
        "published_pages": pages,
        "published_total": posts + pages,
    }


def find_pages_by_slug(slug: str, authorization: str):
    found: dict[int, dict[str, Any]] = {}
    for status in PAGE_STATUSES:
        query = urllib.parse.urlencode(
            {
                "context": "edit",
                "slug": slug,
                "status": status,
                "per_page": "100",
                "_fields": "id,slug,status,link,title,content",
            }
        )
        rows, _ = get_json(f"{SITE_URL}/wp-json/wp/v2/pages?{query}", authorization)
        for row in rows:
            found[int(row["id"])] = row
    return list(found.values())


def fetch_page(page_id: int, authorization: str):
    query = urllib.parse.urlencode(
        {"context": "edit", "_fields": "id,slug,status,link,title,content"}
    )
    row, _ = get_json(
        f"{SITE_URL}/wp-json/wp/v2/pages/{page_id}?{query}", authorization
    )
    return row


def validate_existing(rows, cfg, full):
    if not rows:
        return "CREATE", None
    if len(rows) != 1:
        raise RuntimeError("multiple pages already use the requested slug; refusing sync")

    row = rows[0]
    title = html.unescape(raw_field(row, "title"))
    content = raw_field(row, "content")

    if row.get("slug") != cfg["slug"]:
        raise RuntimeError("existing page slug mismatch; refusing sync")
    if row.get("status") != "draft":
        raise RuntimeError("existing page is not draft; refusing sync")
    if title != cfg["title"]:
        raise RuntimeError("existing page title differs; refusing sync")
    if cfg["marker"] not in content:
        raise RuntimeError("experimental marker missing; refusing sync")

    if content.strip() == full.strip():
        return "ALREADY_EXISTS", row

    expected_current = (cfg.get("expected_current_content_sha256") or "").strip().casefold()
    actual_current = hashlib.sha256(content.encode()).hexdigest().casefold()
    if expected_current and actual_current == expected_current:
        return "UPDATE", row

    raise RuntimeError("existing draft differs from the guarded expected content; refusing overwrite")


def validate_synced(row, cfg, full):
    if row.get("slug") != cfg["slug"]:
        raise RuntimeError("synced page slug mismatch")
    if row.get("status") != "draft":
        raise RuntimeError("synced page is not draft")
    if html.unescape(raw_field(row, "title")) != cfg["title"]:
        raise RuntimeError("synced page title mismatch")
    if raw_field(row, "content").strip() != full.strip():
        raise RuntimeError("synced page content mismatch")
    if cfg["marker"] not in raw_field(row, "content"):
        raise RuntimeError("synced page marker missing")


def apply(config_path: Path):
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")

    cfg, full = load_package(config_path)
    auth = auth_header(user, password)
    before_counts = public_counts(auth)
    rows = find_pages_by_slug(cfg["slug"], auth)
    action, existing = validate_existing(rows, cfg, full)

    payload = {
        "title": cfg["title"],
        "slug": cfg["slug"],
        "content": full,
        "status": "draft",
    }

    if action == "CREATE":
        created = post_json(f"{SITE_URL}/wp-json/wp/v2/pages", auth, payload)
        page_id = int(created["id"])
    elif action == "UPDATE":
        page_id = int(existing["id"])
        updated = post_json(f"{SITE_URL}/wp-json/wp/v2/pages/{page_id}", auth, payload)
        if int(updated.get("id") or 0) != page_id:
            raise RuntimeError("update response page id mismatch")
    else:
        page_id = int(existing["id"])

    after_page = fetch_page(page_id, auth)
    validate_synced(after_page, cfg, full)

    after_counts = public_counts(auth)
    if after_counts != before_counts:
        raise RuntimeError("published counts changed; refusing success")

    report = {
        "action": action,
        "page_id": page_id,
        "slug": cfg["slug"],
        "status": "draft",
        "title": cfg["title"],
        "link": after_page.get("link") or "",
        "public_before": before_counts,
        "public_after": after_counts,
        "content_sha256": hashlib.sha256(raw_field(after_page, "content").encode()).hexdigest(),
        "wordpress_write_count": 1 if action in ("CREATE", "UPDATE") else 0,
        "publish_count": 0,
    }

    out = Path("reports") / f"{cfg['slug']}-experimental-page-create"
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        f"# {cfg['slug']} experimental fixed page",
        "",
        f"- action: **{action}**",
        f"- page_id: **{page_id}**",
        "- post_type: **page**",
        "- status: **draft**",
        f"- title: {cfg['title']}",
        f"- link: {report['link']}",
        f"- public_before: **{before_counts['published_total']}**",
        f"- public_after: **{after_counts['published_total']}**",
        f"- wordpress_write_count: **{report['wordpress_write_count']}**",
        f"- publish_count: **{report['publish_count']}**",
        f"- content_sha256: `{report['content_sha256']}`",
    ]
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    apply(Path(args.config))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
