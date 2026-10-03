#!/usr/bin/env python3
"""Create one WordPress editorial post as a draft, guarded by slug and markers.

This is intentionally separate from apply_editorial_draft_once.py. Existing update
packages keep their current behavior; new packages opt in with create.json.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

SITE_URL = "https://tsurikue.com"
USER_AGENT = "tsurikue-editorial-draft-create/1.0"
SAFE_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
SEARCH_STATUSES = ("draft", "pending", "private", "future", "publish")


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
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode()), dict(r.headers)


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
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def raw_field(row: dict[str, Any], key: str) -> str:
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)


def load_package(create_path: Path):
    cfg = json.loads(create_path.read_text(encoding="utf-8"))
    required = ("title", "slug", "salvage_marker", "editorial_marker", "content_file")
    missing = [key for key in required if not str(cfg.get(key) or "").strip()]
    if missing:
        raise RuntimeError(f"missing required fields: {', '.join(missing)}")
    if "post_id" in cfg:
        raise RuntimeError("create.json must not contain post_id; use config.json for guarded updates")

    slug = str(cfg["slug"]).strip()
    if not SAFE_SLUG.fullmatch(slug):
        raise RuntimeError("slug must contain only lowercase ASCII letters, digits, and hyphens")

    package_dir = create_path.parent.resolve()
    content_path = (package_dir / str(cfg["content_file"])).resolve()
    if package_dir not in content_path.parents:
        raise RuntimeError("content_file must stay inside the editorial package directory")
    if not content_path.is_file():
        raise RuntimeError(f"content_file not found: {content_path.name}")

    content = content_path.read_text(encoding="utf-8").strip() + "\n"
    salvage = str(cfg["salvage_marker"]).strip()
    editorial = str(cfg["editorial_marker"]).strip()
    if salvage == editorial:
        raise RuntimeError("salvage_marker and editorial_marker must differ")
    if salvage in content or editorial in content:
        raise RuntimeError("content.html must not duplicate package markers")

    full = salvage + "\n" + editorial + "\n" + content
    cfg["slug"] = slug
    cfg["title"] = str(cfg["title"]).strip()
    return cfg, full


def count_published(endpoint: str, authorization: str) -> int:
    q = urllib.parse.urlencode(
        {"context": "edit", "status": "publish", "per_page": "1", "_fields": "id"}
    )
    _, headers = get_json(f"{SITE_URL}/wp-json/wp/v2/{endpoint}?{q}", authorization)
    return int(headers.get("X-WP-Total", "0"))


def public_counts(authorization: str):
    posts = count_published("posts", authorization)
    pages = count_published("pages", authorization)
    return {
        "published_posts": posts,
        "published_pages": pages,
        "published_total": posts + pages,
    }


def validate_media(cfg: dict[str, Any], authorization: str) -> int:
    expected = {int(k): v for k, v in (cfg.get("expected_media") or {}).items()}
    featured = int(cfg.get("featured_media") or 0)
    if featured and featured not in expected:
        raise RuntimeError("non-zero featured_media must be one of expected_media")
    for media_id, path in expected.items():
        q = urllib.parse.urlencode({"context": "edit", "_fields": "id,status,source_url"})
        row, _ = get_json(
            f"{SITE_URL}/wp-json/wp/v2/media/{media_id}?{q}", authorization
        )
        actual = urllib.parse.unquote(
            urllib.parse.urlparse(row.get("source_url") or "").path
        ).casefold()
        if actual != str(path).casefold():
            raise RuntimeError(f"media mismatch id={media_id}: {actual}")
    return len(expected)


def find_existing_by_slug(slug: str, authorization: str):
    found: dict[int, dict[str, Any]] = {}
    for status in SEARCH_STATUSES:
        q = urllib.parse.urlencode(
            {
                "context": "edit",
                "slug": slug,
                "status": status,
                "per_page": "100",
                "_fields": "id,slug,status,link,title,content,featured_media",
            }
        )
        rows, _ = get_json(f"{SITE_URL}/wp-json/wp/v2/posts?{q}", authorization)
        if not isinstance(rows, list):
            raise RuntimeError("unexpected WordPress slug lookup response")
        for row in rows:
            found[int(row["id"])] = row
    if len(found) > 1:
        details = ", ".join(f"{row['id']}:{row.get('status')}" for row in found.values())
        raise RuntimeError(f"multiple posts already use slug {slug}: {details}")
    return next(iter(found.values()), None)


def fetch_post(post_id: int, authorization: str):
    q = urllib.parse.urlencode(
        {"context": "edit", "_fields": "id,slug,status,link,title,content,featured_media"}
    )
    row, _ = get_json(
        f"{SITE_URL}/wp-json/wp/v2/posts/{post_id}?{q}", authorization
    )
    return row


def validate_existing_draft(row: dict[str, Any], cfg: dict[str, Any], full: str):
    if row.get("slug") != cfg["slug"]:
        raise RuntimeError("slug lookup returned a different slug")
    if row.get("status") != "draft":
        raise RuntimeError(
            f"slug already exists as status={row.get('status')}; refusing to create or modify it"
        )
    featured = int(cfg.get("featured_media") or 0)
    current_title = html.unescape(raw_field(row, "title"))
    current_content = raw_field(row, "content")
    current_featured = int(row.get("featured_media") or 0)
    if (
        current_title == cfg["title"]
        and current_content.strip() == full.strip()
        and current_featured == featured
    ):
        return "REUSE_EXISTING_DRAFT"
    raise RuntimeError(
        "draft with this slug already exists but differs; refusing overwrite. "
        "Promote it to config.json and use the guarded update rail."
    )


def validate_created(row: dict[str, Any], cfg: dict[str, Any], full: str):
    featured = int(cfg.get("featured_media") or 0)
    if row.get("slug") != cfg["slug"] or row.get("status") != "draft":
        raise RuntimeError("created post is not the expected draft/slug")
    if int(row.get("featured_media") or 0) != featured:
        raise RuntimeError("created post featured_media mismatch")
    if html.unescape(raw_field(row, "title")) != cfg["title"]:
        raise RuntimeError("created post title mismatch")
    if raw_field(row, "content").strip() != full.strip():
        raise RuntimeError("created post content mismatch")


def create(create_path: Path):
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")

    cfg, full = load_package(create_path)
    auth = auth_header(user, password)
    featured = int(cfg.get("featured_media") or 0)

    before_counts = public_counts(auth)
    checked = validate_media(cfg, auth)
    existing = find_existing_by_slug(cfg["slug"], auth)

    if existing is not None:
        action = validate_existing_draft(existing, cfg, full)
        post_id = int(existing["id"])
        write_count = 0
    else:
        action = "CREATE_DRAFT"
        payload = {
            "title": cfg["title"],
            "slug": cfg["slug"],
            "content": full,
            "status": "draft",
            "featured_media": featured,
        }
        response = post_json(f"{SITE_URL}/wp-json/wp/v2/posts", auth, payload)
        post_id = int(response.get("id") or 0)
        if not post_id:
            raise RuntimeError("WordPress create response did not include a post id")
        write_count = 1

    after = fetch_post(post_id, auth)
    validate_created(after, cfg, full)
    after_counts = public_counts(auth)
    if after_counts != before_counts:
        raise RuntimeError("published counts changed; draft-only invariant violated")

    report = {
        "action": action,
        "post_id": post_id,
        "slug": cfg["slug"],
        "status": "draft",
        "title": cfg["title"],
        "featured_media": featured,
        "confirmed_media_checked": checked,
        "public_before": before_counts,
        "public_after": after_counts,
        "content_sha256": hashlib.sha256(raw_field(after, "content").encode()).hexdigest(),
        "wordpress_write_count": write_count,
        "publish_count": 0,
        "media_upload_count": 0,
    }

    out = Path("reports") / f"{cfg['slug']}-draft-create"
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        f"# {cfg['slug']} draft creation",
        "",
        f"- action: **{action}**",
        f"- post_id: **{post_id}**",
        "- status: **draft**",
        f"- title: {cfg['title']}",
        f"- featured_media: **{featured}**",
        f"- confirmed_media_checked: **{checked}**",
        f"- public_before: **{before_counts['published_total']}**",
        f"- public_after: **{after_counts['published_total']}**",
        f"- content_sha256: `{report['content_sha256']}`",
        "",
        "To make later guarded edits, copy create.json to config.json and add",
        f"`\"post_id\": {post_id}` plus the expected current hash when required.",
    ]
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"POST_ID={post_id}")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--create", required=True, help="Path to editorial/*/create.json")
    args = parser.parse_args()
    create(Path(args.create))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
