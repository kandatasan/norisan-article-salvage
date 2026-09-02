#!/usr/bin/env python3
"""Guarded add-only WordPress tag updater.

This tool intentionally changes only the ``tags`` field of one exact WordPress
post. Existing tags are preserved. Missing tags may be created only when the
config explicitly opts in with ``allow_create_tags: true``.
"""
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
USER_AGENT = "tsurikue-tag-patch-once/1.0"
ALLOWED_STATUSES = {"draft", "publish"}


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


def content_sha256(row: dict[str, Any]) -> str:
    return hashlib.sha256(raw_field(row, "content").encode()).hexdigest()


def normalize_tag_specs(cfg: dict[str, Any]) -> list[dict[str, str]]:
    if cfg.get("mode", "add_only") != "add_only":
        raise RuntimeError("only mode=add_only is supported")

    specs = cfg.get("tags")
    if not isinstance(specs, list) or not specs:
        raise RuntimeError("tags must be a non-empty list")

    normalized: list[dict[str, str]] = []
    seen_names: set[str] = set()
    seen_slugs: set[str] = set()

    for item in specs:
        if isinstance(item, str):
            name = item.strip()
            slug = ""
        elif isinstance(item, dict):
            name = str(item.get("name") or "").strip()
            slug = str(item.get("slug") or "").strip()
        else:
            raise RuntimeError("each tag must be a string or an object")

        if not name:
            raise RuntimeError("tag name must not be empty")

        name_key = html.unescape(name).casefold()
        if name_key in seen_names:
            raise RuntimeError(f"duplicate tag name in config: {name}")
        seen_names.add(name_key)

        if slug:
            slug_key = slug.casefold()
            if slug_key in seen_slugs:
                raise RuntimeError(f"duplicate tag slug in config: {slug}")
            seen_slugs.add(slug_key)

        normalized.append({"name": name, "slug": slug})

    return normalized


def fetch_post(cfg: dict[str, Any], authorization: str) -> dict[str, Any]:
    query = urllib.parse.urlencode(
        {
            "context": "edit",
            "_fields": "id,slug,status,title,content,featured_media,tags",
        }
    )
    row, _ = get_json(
        f"{SITE_URL}/wp-json/wp/v2/posts/{cfg['post_id']}?{query}", authorization
    )
    return row


def count_published(endpoint: str, authorization: str) -> int:
    query = urllib.parse.urlencode(
        {"context": "edit", "status": "publish", "per_page": "1", "_fields": "id"}
    )
    _, headers = get_json(
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


def validate_target(row: dict[str, Any], cfg: dict[str, Any]) -> None:
    if row.get("id") != cfg.get("post_id") or row.get("slug") != cfg.get("slug"):
        raise RuntimeError("post id/slug mismatch")

    status = row.get("status")
    if status not in ALLOWED_STATUSES:
        raise RuntimeError(f"target status is not allowed: {status}")

    expected_status = str(cfg.get("expected_status") or "").strip()
    if expected_status and status != expected_status:
        raise RuntimeError(
            f"post status mismatch: expected {expected_status}, got {status}"
        )


def fetch_tags_by_slug(slug: str, authorization: str) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode(
        {"context": "edit", "slug": slug, "per_page": "100", "_fields": "id,name,slug"}
    )
    rows, _ = get_json(f"{SITE_URL}/wp-json/wp/v2/tags?{query}", authorization)
    return rows


def fetch_tags_by_name(name: str, authorization: str) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode(
        {
            "context": "edit",
            "search": name,
            "per_page": "100",
            "_fields": "id,name,slug",
        }
    )
    rows, _ = get_json(f"{SITE_URL}/wp-json/wp/v2/tags?{query}", authorization)
    wanted = html.unescape(name).strip().casefold()
    return [
        row
        for row in rows
        if html.unescape(str(row.get("name") or "")).strip().casefold() == wanted
    ]


def validate_existing_tag(
    row: dict[str, Any], spec: dict[str, str]
) -> dict[str, Any]:
    actual_name = html.unescape(str(row.get("name") or "")).strip()
    if actual_name.casefold() != html.unescape(spec["name"]).strip().casefold():
        raise RuntimeError(
            f"tag name mismatch for id={row.get('id')}: {actual_name!r}"
        )
    if spec["slug"] and str(row.get("slug") or "").casefold() != spec["slug"].casefold():
        raise RuntimeError(
            f"tag slug mismatch for {spec['name']}: {row.get('slug')!r}"
        )
    return row


def resolve_or_create_tag(
    spec: dict[str, str], authorization: str, allow_create: bool
) -> tuple[dict[str, Any], bool]:
    if spec["slug"]:
        slug_rows = fetch_tags_by_slug(spec["slug"], authorization)
        if len(slug_rows) > 1:
            raise RuntimeError(f"ambiguous tag slug: {spec['slug']}")
        if len(slug_rows) == 1:
            return validate_existing_tag(slug_rows[0], spec), False

    name_rows = fetch_tags_by_name(spec["name"], authorization)
    if len(name_rows) > 1:
        raise RuntimeError(f"ambiguous exact tag name: {spec['name']}")
    if len(name_rows) == 1:
        row = name_rows[0]
        if spec["slug"] and str(row.get("slug") or "").casefold() != spec["slug"].casefold():
            raise RuntimeError(
                f"existing tag name has different slug: {spec['name']} -> {row.get('slug')}"
            )
        return validate_existing_tag(row, spec), False

    if not allow_create:
        raise RuntimeError(f"tag does not exist and creation is disabled: {spec['name']}")

    payload: dict[str, Any] = {"name": spec["name"]}
    if spec["slug"]:
        payload["slug"] = spec["slug"]
    row = post_json(f"{SITE_URL}/wp-json/wp/v2/tags", authorization, payload)
    validate_existing_tag(row, spec)
    if not int(row.get("id") or 0):
        raise RuntimeError(f"created tag has invalid id: {spec['name']}")
    return row, True


def stable_post_state(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "slug": row.get("slug"),
        "status": row.get("status"),
        "title": html.unescape(raw_field(row, "title")),
        "content_sha256": content_sha256(row),
        "featured_media": int(row.get("featured_media") or 0),
    }


def apply(config_path: Path):
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")

    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    specs = normalize_tag_specs(cfg)
    allow_create = bool(cfg.get("allow_create_tags", False))
    authorization = auth_header(user, password)

    before_counts = public_counts(authorization)
    initial = fetch_post(cfg, authorization)
    validate_target(initial, cfg)

    resolved: list[dict[str, Any]] = []
    created: list[dict[str, Any]] = []
    for spec in specs:
        row, was_created = resolve_or_create_tag(spec, authorization, allow_create)
        resolved.append(row)
        if was_created:
            created.append(row)

    # Re-fetch immediately before writing so existing human-added tags are preserved.
    latest = fetch_post(cfg, authorization)
    validate_target(latest, cfg)
    latest_state = stable_post_state(latest)
    current_tag_ids = {int(tag_id) for tag_id in (latest.get("tags") or [])}
    requested_tag_ids = {int(row["id"]) for row in resolved}
    desired_tag_ids = sorted(current_tag_ids | requested_tag_ids)

    action = "ALREADY_UP_TO_DATE"
    if set(desired_tag_ids) != current_tag_ids:
        action = "UPDATE"
        response = post_json(
            f"{SITE_URL}/wp-json/wp/v2/posts/{cfg['post_id']}",
            authorization,
            {"tags": desired_tag_ids},
        )
        if response.get("id") != cfg["post_id"] or response.get("slug") != cfg["slug"]:
            raise RuntimeError("tag update response validation failed")

    after = fetch_post(cfg, authorization)
    after_counts = public_counts(authorization)
    validate_target(after, cfg)

    if after_counts != before_counts:
        raise RuntimeError("published counts changed")

    after_state = stable_post_state(after)
    if after_state != latest_state:
        raise RuntimeError("non-tag post fields changed; refusing success")

    after_tag_ids = {int(tag_id) for tag_id in (after.get("tags") or [])}
    if after_tag_ids != set(desired_tag_ids):
        raise RuntimeError("post-update tag set mismatch")

    report = {
        "action": action,
        "post_id": cfg["post_id"],
        "slug": cfg["slug"],
        "status": after.get("status"),
        "mode": "add_only",
        "requested_tags": [
            {"id": int(row["id"]), "name": row.get("name"), "slug": row.get("slug")}
            for row in resolved
        ],
        "created_tags": [
            {"id": int(row["id"]), "name": row.get("name"), "slug": row.get("slug")}
            for row in created
        ],
        "tags_before_write": sorted(current_tag_ids),
        "tags_after": sorted(after_tag_ids),
        "public_before": before_counts,
        "public_after": after_counts,
        "content_sha256": after_state["content_sha256"],
        "wordpress_post_write_count": 1 if action == "UPDATE" else 0,
        "wordpress_tag_create_count": len(created),
        "publish_count": 0,
        "content_write_count": 0,
        "media_upload_count": 0,
    }

    out = Path("reports") / f"{cfg['slug']}-tag-patch"
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    tag_summary = ", ".join(
        f"{row.get('name')} (#{int(row['id'])})" for row in resolved
    )
    created_summary = (
        ", ".join(f"{row.get('name')} (#{int(row['id'])})" for row in created)
        if created
        else "none"
    )
    lines = [
        f"# {cfg['slug']} tag patch",
        "",
        f"- action: **{action}**",
        f"- post_id: **{cfg['post_id']}**",
        f"- status: **{after.get('status')}**",
        "- mode: **add_only**",
        f"- requested_tags: {tag_summary}",
        f"- created_tags: {created_summary}",
        f"- public_before: **{before_counts['published_total']}**",
        f"- public_after: **{after_counts['published_total']}**",
        f"- content_sha256: `{after_state['content_sha256']}`",
        f"- content_write_count: **0**",
        f"- wordpress_post_write_count: **{report['wordpress_post_write_count']}**",
        f"- wordpress_tag_create_count: **{len(created)}**",
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
