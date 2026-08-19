#!/usr/bin/env python3
"""Guarded one-off media/content patcher for an existing salvaged WordPress draft.

This intentionally patches the current draft in place instead of replacing its whole body.
It never publishes and never uploads/deletes media.
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
USER_AGENT = "tsurikue-editorial-media-patch-once/1.0"


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def get_json(url: str, authorization: str) -> tuple[Any, dict[str, str]]:
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
        return json.loads(response.read().decode("utf-8")), dict(response.headers)


def post_json(url: str, authorization: str, payload: dict[str, Any]) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": authorization,
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def raw_field(row: dict[str, Any], key: str) -> str:
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)


def fetch_post(post_id: int, authorization: str) -> dict[str, Any]:
    query = urllib.parse.urlencode(
        {"context": "edit", "_fields": "id,slug,status,title,content,featured_media"}
    )
    row, _headers = get_json(
        f"{SITE_URL}/wp-json/wp/v2/posts/{post_id}?{query}", authorization
    )
    return row


def count_published(endpoint: str, authorization: str) -> int:
    query = urllib.parse.urlencode(
        {"context": "edit", "status": "publish", "per_page": "1", "_fields": "id"}
    )
    _rows, headers = get_json(
        f"{SITE_URL}/wp-json/wp/v2/{endpoint}?{query}", authorization
    )
    return int(headers.get("X-WP-Total", "0"))


def public_counts(authorization: str) -> dict[str, int]:
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
    if featured not in expected:
        raise RuntimeError("featured_media must be present in expected_media")

    for media_id, spec in expected.items():
        query = urllib.parse.urlencode(
            {"context": "edit", "_fields": "id,source_url,media_details"}
        )
        row, _headers = get_json(
            f"{SITE_URL}/wp-json/wp/v2/media/{media_id}?{query}", authorization
        )
        if int(row.get("id") or 0) != media_id:
            raise RuntimeError(f"media id mismatch: expected {media_id}")
        actual_path = urllib.parse.unquote(
            urllib.parse.urlparse(row.get("source_url") or "").path
        ).casefold()
        expected_path = str(spec["path"]).casefold()
        if actual_path != expected_path:
            raise RuntimeError(
                f"media path mismatch id={media_id}: {actual_path} != {expected_path}"
            )
        details = row.get("media_details") or {}
        if int(details.get("width") or 0) != int(spec["width"]):
            raise RuntimeError(f"media width mismatch id={media_id}")
        if int(details.get("height") or 0) != int(spec["height"]):
            raise RuntimeError(f"media height mismatch id={media_id}")
    return len(expected)


def image_id_present(content: str, media_id: int) -> bool:
    return bool(
        re.search(rf"wp-image-{media_id}\b", content)
        or re.search(rf'\"id\"\s*:\s*{media_id}\b', content)
    )


def build_patched_content(content: str, cfg: dict[str, Any]) -> str:
    patch_marker = cfg["patch_marker"]
    required_editorial_marker = cfg["required_editorial_marker"]

    if patch_marker in content:
        return content

    if required_editorial_marker not in content:
        raise RuntimeError("required editorial marker missing")

    patched = content.replace(
        required_editorial_marker,
        required_editorial_marker + "\n" + patch_marker,
        1,
    )

    for insertion in cfg.get("insertions") or []:
        anchor = insertion["anchor"]
        block = insertion["html"].strip()
        position = insertion.get("position", "after")
        if patched.count(anchor) != 1:
            raise RuntimeError(
                f"anchor must occur exactly once; found {patched.count(anchor)}: {anchor[:80]!r}"
            )
        if position == "after":
            replacement = anchor + "\n\n" + block
        elif position == "before":
            replacement = block + "\n\n" + anchor
        else:
            raise RuntimeError(f"unsupported insertion position: {position}")
        patched = patched.replace(anchor, replacement, 1)

    return patched


def apply(config_path: Path) -> dict[str, Any]:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")

    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    authorization = auth_header(user, password)
    post_id = int(cfg["post_id"])
    featured = int(cfg["featured_media"])
    expected_title = cfg["expected_title"]
    expected_media_ids = {int(k) for k in (cfg.get("expected_media") or {}).keys()}

    before_counts = public_counts(authorization)
    before = fetch_post(post_id, authorization)

    if int(before.get("id") or 0) != post_id:
        raise RuntimeError("post id mismatch")
    if before.get("slug") != cfg["slug"]:
        raise RuntimeError("post slug mismatch")
    if before.get("status") != "draft":
        raise RuntimeError("target is not draft; refusing media patch")
    if html.unescape(raw_field(before, "title")) != expected_title:
        raise RuntimeError("title changed; refusing media patch")

    current = raw_field(before, "content")
    if cfg["salvage_marker"] not in current:
        raise RuntimeError("salvage marker missing")
    if cfg["required_editorial_marker"] not in current:
        raise RuntimeError("required editorial marker missing")

    checked_media = validate_media(cfg, authorization)
    patch_marker = cfg["patch_marker"]

    if patch_marker in current:
        if int(before.get("featured_media") or 0) != featured:
            raise RuntimeError("patch marker exists but featured media differs")
        if not all(image_id_present(current, media_id) for media_id in expected_media_ids):
            raise RuntimeError("patch marker exists but expected images are missing")
        action = "ALREADY_UP_TO_DATE"
        patched = current
    else:
        if any(image_id_present(current, media_id) for media_id in expected_media_ids):
            raise RuntimeError("expected media already present without patch marker; refusing")
        patched = build_patched_content(current, cfg)
        action = "UPDATE"
        response = post_json(
            f"{SITE_URL}/wp-json/wp/v2/posts/{post_id}",
            authorization,
            {
                "content": patched,
                "status": "draft",
                "featured_media": featured,
            },
        )
        if int(response.get("id") or 0) != post_id:
            raise RuntimeError("update response post id mismatch")
        if response.get("slug") != cfg["slug"]:
            raise RuntimeError("update response slug mismatch")
        if response.get("status") != "draft":
            raise RuntimeError("update response status mismatch")
        if int(response.get("featured_media") or 0) != featured:
            raise RuntimeError("update response featured media mismatch")

    after = fetch_post(post_id, authorization)
    after_counts = public_counts(authorization)
    after_content = raw_field(after, "content")

    if after_counts != before_counts:
        raise RuntimeError("published counts changed")
    if after.get("status") != "draft" or after.get("slug") != cfg["slug"]:
        raise RuntimeError("post-update draft identity mismatch")
    if html.unescape(raw_field(after, "title")) != expected_title:
        raise RuntimeError("title changed during media patch")
    if int(after.get("featured_media") or 0) != featured:
        raise RuntimeError("post-update featured media mismatch")
    if patch_marker not in after_content:
        raise RuntimeError("patch marker missing after update")
    if not all(image_id_present(after_content, media_id) for media_id in expected_media_ids):
        raise RuntimeError("expected images missing after update")
    if after_content.strip() != patched.strip():
        raise RuntimeError("post-update content differs from patched content")

    report = {
        "action": action,
        "post_id": post_id,
        "slug": cfg["slug"],
        "status": "draft",
        "title": expected_title,
        "featured_media": featured,
        "inserted_media": sorted(expected_media_ids),
        "confirmed_media_checked": checked_media,
        "public_before": before_counts,
        "public_after": after_counts,
        "content_sha256": hashlib.sha256(after_content.encode("utf-8")).hexdigest(),
        "wordpress_write_count": 1 if action == "UPDATE" else 0,
        "publish_count": 0,
        "media_upload_count": 0,
        "media_delete_count": 0,
    }

    out = Path("reports") / f"{cfg['slug']}-media-patch"
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        f"# {cfg['slug']} draft media patch",
        "",
        f"- action: **{action}**",
        f"- post_id: **{post_id}**",
        "- status: **draft**",
        f"- title: {expected_title}",
        f"- featured_media: **{featured}**",
        f"- inserted_media: **{', '.join(str(x) for x in sorted(expected_media_ids))}**",
        f"- confirmed_media_checked: **{checked_media}**",
        f"- public_before: **{before_counts['published_total']}**",
        f"- public_after: **{after_counts['published_total']}**",
        f"- content_sha256: `{report['content_sha256']}`",
        "- media_upload_count: **0**",
        "- publish_count: **0**",
    ]
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    apply(Path(args.config))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
