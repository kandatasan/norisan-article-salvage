#!/usr/bin/env python3
"""One-off guarded updater for the restored tsureruurawaza draft.

This exists because the generic editorial updater did not apply after the article was
rolled back to the Phase 4 source. It will write only when the current WordPress
body exactly matches the known rollback state.
"""
from __future__ import annotations

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
POST_ID = 2660
SLUG = "tsureruurawaza"
EXPECTED_CURRENT_TITLE = "ルアー・ワームで魚が釣れない？裏技！この組み合わせを試してみて！"
EXPECTED_CURRENT_SHA256 = "e2b6af4fb0cb13a9da9e0f068183c85502651650670504bdd41be9afa132062a"
CONFIG_PATH = Path("editorial/tsureruurawaza/config.json")
USER_AGENT = "tsurikue-tsureruurawaza-v2-once/1.1"
REPORT_DIR = Path("reports/tsureruurawaza-v2-once")


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def get_json(url: str, auth: str):
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "Authorization": auth, "User-Agent": USER_AGENT},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode()), dict(r.headers)


def post_json(url: str, auth: str, payload: dict[str, Any]):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": auth,
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


def fetch_post(auth: str):
    q = urllib.parse.urlencode({"context": "edit", "_fields": "id,slug,status,title,content,featured_media"})
    row, _ = get_json(f"{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}?{q}", auth)
    return row


def count_published(endpoint: str, auth: str) -> int:
    q = urllib.parse.urlencode({"context": "edit", "status": "publish", "per_page": "1", "_fields": "id"})
    _, headers = get_json(f"{SITE_URL}/wp-json/wp/v2/{endpoint}?{q}", auth)
    return int(headers.get("X-WP-Total", "0"))


def public_counts(auth: str) -> dict[str, int]:
    posts = count_published("posts", auth)
    pages = count_published("pages", auth)
    return {"posts": posts, "pages": pages, "total": posts + pages}


def validate_media(cfg: dict[str, Any], auth: str) -> int:
    expected = {int(k): v for k, v in cfg["expected_media"].items()}
    featured = int(cfg["featured_media"])
    if featured not in expected:
        raise RuntimeError("featured media is not in expected_media")
    for media_id, expected_path in expected.items():
        q = urllib.parse.urlencode({"context": "edit", "_fields": "id,source_url"})
        row, _ = get_json(f"{SITE_URL}/wp-json/wp/v2/media/{media_id}?{q}", auth)
        actual = urllib.parse.unquote(urllib.parse.urlparse(row.get("source_url") or "").path).casefold()
        if int(row.get("id") or 0) != media_id or actual != expected_path.casefold():
            raise RuntimeError(f"media mismatch for #{media_id}: {actual}")
    return len(expected)


def write_report(data: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "result.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# tsureruurawaza v2 one-off apply",
        "",
        f"- result: **{data['result']}**",
        f"- post_id: **{POST_ID}**",
        f"- status: **{data.get('status', 'unknown')}**",
        f"- title: {data.get('title', '')}",
        f"- featured_media: **{data.get('featured_media', 0)}**",
        f"- confirmed_media_checked: **{data.get('confirmed_media_checked', 0)}**",
        f"- public_before: **{data.get('public_before', 'unknown')}**",
        f"- public_after: **{data.get('public_after', 'unknown')}**",
        f"- wordpress_write_count: **{data.get('wordpress_write_count', 0)}**",
        f"- content_sha256: `{data.get('content_sha256', '')}`",
    ]
    if data.get("error"):
        lines.append(f"- error: `{data['error']}`")
    (REPORT_DIR / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    report: dict[str, Any] = {
        "result": "BLOCKED",
        "status": "unknown",
        "title": "",
        "featured_media": 0,
        "confirmed_media_checked": 0,
        "public_before": "unknown",
        "public_after": "unknown",
        "wordpress_write_count": 0,
        "content_sha256": "",
    }
    try:
        user = os.environ.get("TSURIKUE_WP_USER")
        password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
        if not user or not password:
            raise RuntimeError("missing WordPress secrets")
        auth = auth_header(user, password)
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if cfg.get("post_id") != POST_ID or cfg.get("slug") != SLUG:
            raise RuntimeError("editorial config target mismatch")
        if cfg.get("editorial_marker") != "<!-- tsurikue-editorial:tsureruurawaza:v2 -->":
            raise RuntimeError("unexpected editorial marker")
        body = (CONFIG_PATH.parent / cfg["content_file"]).read_text(encoding="utf-8").strip() + "\n"
        desired = cfg["salvage_marker"] + "\n" + cfg["editorial_marker"] + "\n" + body

        before_counts = public_counts(auth)
        before = fetch_post(auth)
        current = raw_field(before, "content")
        current_sha = hashlib.sha256(current.encode()).hexdigest()

        if int(before.get("id") or 0) != POST_ID or before.get("slug") != SLUG:
            raise RuntimeError("post id/slug mismatch")
        if before.get("status") != "draft":
            raise RuntimeError("target is not draft")
        if html.unescape(raw_field(before, "title")) != EXPECTED_CURRENT_TITLE:
            raise RuntimeError("current title no longer matches restored source")
        if current_sha != EXPECTED_CURRENT_SHA256:
            raise RuntimeError(f"current content hash changed: {current_sha}")
        if cfg["salvage_marker"] not in current:
            raise RuntimeError("salvage marker missing")
        if cfg["editorial_marker"] in current:
            raise RuntimeError("v2 marker already exists unexpectedly")

        checked = validate_media(cfg, auth)
        featured = int(cfg["featured_media"])
        response = post_json(
            f"{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}",
            auth,
            {
                "title": cfg["title"],
                "slug": SLUG,
                "content": desired,
                "status": "draft",
                "featured_media": featured,
            },
        )
        if int(response.get("id") or 0) != POST_ID or response.get("status") != "draft":
            raise RuntimeError("update response validation failed")

        after = fetch_post(auth)
        after_counts = public_counts(auth)
        if after_counts != before_counts:
            raise RuntimeError("published counts changed")
        after_content = raw_field(after, "content")
        if after.get("status") != "draft" or after.get("slug") != SLUG:
            raise RuntimeError("post-update target state mismatch")
        if html.unescape(raw_field(after, "title")) != cfg["title"]:
            raise RuntimeError("post-update title mismatch")
        if int(after.get("featured_media") or 0) != featured:
            raise RuntimeError("post-update featured image mismatch")
        if after_content.strip() != desired.strip():
            raise RuntimeError("post-update content mismatch")

        report.update({
            "result": "SUCCESS",
            "status": "draft",
            "title": cfg["title"],
            "featured_media": featured,
            "confirmed_media_checked": checked,
            "public_before": before_counts["total"],
            "public_after": after_counts["total"],
            "wordpress_write_count": 1,
            "content_sha256": hashlib.sha256(after_content.encode()).hexdigest(),
        })
        write_report(report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        report["error"] = str(exc)
        write_report(report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
