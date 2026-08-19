#!/usr/bin/env python3
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

import old_tsurikue_phase4_create_plan_dry_run as planner

SITE_URL = "https://tsurikue.com"
USER_AGENT = "tsurikue-phase4-source-rollback/1.0"
REPORT_ROOT = Path("reports/phase4-restore-apply")


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def get_json(url: str, authorization: str):
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "Authorization": authorization, "User-Agent": USER_AGENT},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.loads(response.read().decode("utf-8")), dict(response.headers)


def post_json(url: str, authorization: str, payload: dict[str, Any]):
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


def media_ids(content: str) -> list[int]:
    result: list[int] = []
    for match in re.finditer(r"wp-image-(\d+)|\"id\"\s*:\s*(\d+)", content):
        media_id = int(match.group(1) or match.group(2))
        if media_id not in result:
            result.append(media_id)
    return result


def fetch_post(cfg: dict[str, Any], authorization: str) -> dict[str, Any]:
    query = urllib.parse.urlencode(
        {"context": "edit", "_fields": "id,slug,status,title,content,featured_media"}
    )
    row, _headers = get_json(
        f"{SITE_URL}/wp-json/wp/v2/posts/{cfg['post_id']}?{query}", authorization
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
    return {"published_posts": posts, "published_pages": pages, "published_total": posts + pages}


def rebuild_restore_source(cfg: dict[str, Any]) -> tuple[str, str, list[int]]:
    articles, _summary = planner.generate_fresh_articles()
    matches = [row for row in articles if row.get("slug") == cfg["slug"]]
    if len(matches) != 1:
        raise RuntimeError(f"expected one Phase 4 source; found {len(matches)}")
    article = matches[0]
    title = article.get("title") or ""
    content = article.get("content") or ""
    full_source = cfg["salvage_marker"] + "\n" + content
    ids = media_ids(content)

    if title != cfg["restore_title"]:
        raise RuntimeError(f"restore title mismatch: {title!r}")
    if ids != cfg["restore_media_ids"]:
        raise RuntimeError(f"restore media mismatch: {ids}")
    source_sha = hashlib.sha256(full_source.encode()).hexdigest()
    if source_sha != cfg["restore_source_sha256"]:
        raise RuntimeError(f"restore source sha mismatch: {source_sha}")
    for snippet in cfg.get("required_restore_snippets", []):
        if snippet not in content:
            raise RuntimeError(f"restore source missing snippet: {snippet}")
    return title, full_source, ids


def apply(config_path: Path) -> dict[str, Any]:
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")
    authorization = auth_header(user, password)

    before_counts = public_counts(authorization)
    before = fetch_post(cfg, authorization)
    current_content = raw_field(before, "content")
    current_title = html.unescape(raw_field(before, "title"))
    current_sha = hashlib.sha256(current_content.encode()).hexdigest()

    if before.get("id") != cfg["post_id"] or before.get("slug") != cfg["slug"]:
        raise RuntimeError("post id/slug mismatch")
    if before.get("status") != "draft":
        raise RuntimeError("target is not draft")
    if current_title != cfg["current_title"]:
        raise RuntimeError(f"current title mismatch: {current_title!r}")
    if int(before.get("featured_media") or 0) != cfg["current_featured_media"]:
        raise RuntimeError("current featured_media mismatch")
    if current_sha != cfg["current_content_sha256"]:
        raise RuntimeError(f"current content sha mismatch: {current_sha}")
    if cfg["editorial_marker"] not in current_content:
        raise RuntimeError("current editorial marker missing")
    if cfg["rollback_marker"] in current_content:
        raise RuntimeError("rollback marker already present")

    restore_title, restore_source, restore_ids = rebuild_restore_source(cfg)
    restored_content = (
        restore_source.rstrip()
        + "\n\n"
        + cfg["editorial_marker"]
        + "\n"
        + cfg["rollback_marker"]
        + "\n"
    )

    payload = {
        "title": restore_title,
        "slug": cfg["slug"],
        "content": restored_content,
        "status": "draft",
        "featured_media": cfg["restore_featured_media"],
    }
    response = post_json(
        f"{SITE_URL}/wp-json/wp/v2/posts/{cfg['post_id']}", authorization, payload
    )
    if response.get("id") != cfg["post_id"] or response.get("slug") != cfg["slug"]:
        raise RuntimeError("rollback response id/slug mismatch")
    if response.get("status") != "draft":
        raise RuntimeError("rollback response is not draft")

    after = fetch_post(cfg, authorization)
    after_counts = public_counts(authorization)
    after_content = raw_field(after, "content")
    after_title = html.unescape(raw_field(after, "title"))

    if after_counts != before_counts:
        raise RuntimeError("published counts changed")
    if after.get("id") != cfg["post_id"] or after.get("slug") != cfg["slug"]:
        raise RuntimeError("post-rollback id/slug mismatch")
    if after.get("status") != "draft":
        raise RuntimeError("post-rollback target is not draft")
    if after_title != restore_title:
        raise RuntimeError("post-rollback title mismatch")
    if int(after.get("featured_media") or 0) != cfg["restore_featured_media"]:
        raise RuntimeError("post-rollback featured_media mismatch")
    if after_content.strip() != restored_content.strip():
        raise RuntimeError("post-rollback content mismatch")
    if media_ids(after_content) != restore_ids:
        raise RuntimeError("post-rollback media ids mismatch")
    if cfg["rollback_marker"] not in after_content:
        raise RuntimeError("rollback marker missing after update")

    report = {
        "action": "ROLLBACK_TO_PHASE4_SOURCE",
        "post_id": cfg["post_id"],
        "slug": cfg["slug"],
        "status": "draft",
        "title": after_title,
        "featured_media": int(after.get("featured_media") or 0),
        "restored_media_ids": restore_ids,
        "restore_source_sha256": cfg["restore_source_sha256"],
        "restored_content_sha256": hashlib.sha256(after_content.encode()).hexdigest(),
        "public_before": before_counts,
        "public_after": after_counts,
        "wordpress_write_count": 1,
        "publish_count": 0,
        "media_upload_count": 0,
    }

    out = REPORT_ROOT / cfg["slug"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        f"# {cfg['slug']} Phase 4 source rollback",
        "",
        "- action: **ROLLBACK_TO_PHASE4_SOURCE**",
        f"- post_id: **{cfg['post_id']}**",
        "- status: **draft**",
        f"- title: {after_title}",
        f"- featured_media: **{report['featured_media']}**",
        f"- restored_media_ids: **{', '.join(map(str, restore_ids))}**",
        f"- public_before: **{before_counts['published_total']}**",
        f"- public_after: **{after_counts['published_total']}**",
        "- wordpress_write_count: **1**",
        "- publish_count: **0**",
        "- media_upload_count: **0**",
        f"- restore_source_sha256: `{cfg['restore_source_sha256']}`",
        f"- restored_content_sha256: `{report['restored_content_sha256']}`",
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
