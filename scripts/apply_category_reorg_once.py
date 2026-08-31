#!/usr/bin/env python3
"""Safely reorganize WordPress post categories without touching article content."""
from __future__ import annotations

import argparse
import base64
import html
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

SITE_URL = "https://tsurikue.com"
USER_AGENT = "tsurikue-category-reorg/1.0"


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


def fetch_category(slug: str, authorization: str):
    query = urllib.parse.urlencode(
        {"context": "edit", "slug": slug, "per_page": "100", "_fields": "id,slug,name,parent,count"}
    )
    rows, _ = get_json(f"{SITE_URL}/wp-json/wp/v2/categories?{query}", authorization)
    if len(rows) != 1:
        raise RuntimeError(f"expected exactly one category for slug={slug}, found {len(rows)}")
    return rows[0]


def fetch_post(post_id: int, authorization: str):
    query = urllib.parse.urlencode(
        {
            "context": "edit",
            "_fields": "id,slug,status,link,title,content,excerpt,featured_media,categories",
        }
    )
    row, _ = get_json(f"{SITE_URL}/wp-json/wp/v2/posts/{post_id}?{query}", authorization)
    return row


def protected_snapshot(row: dict[str, Any]):
    return {
        "id": int(row["id"]),
        "slug": row.get("slug") or "",
        "status": row.get("status") or "",
        "link": row.get("link") or "",
        "title": html.unescape(raw_field(row, "title")),
        "content": raw_field(row, "content"),
        "excerpt": raw_field(row, "excerpt"),
        "featured_media": int(row.get("featured_media") or 0),
    }


def load_manifest(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not data.get("categories") or not data.get("operations"):
        raise RuntimeError("manifest requires categories and operations")
    return data


def resolve_categories(manifest: dict[str, Any], authorization: str):
    resolved: dict[str, dict[str, Any]] = {}
    for slug, spec in manifest["categories"].items():
        row = fetch_category(slug, authorization)
        if row.get("slug") != slug:
            raise RuntimeError(f"category slug mismatch for {slug}")
        if row.get("name") != spec.get("name"):
            raise RuntimeError(
                f"category name mismatch for {slug}: expected={spec.get('name')!r} actual={row.get('name')!r}"
            )
        resolved[slug] = row

    for slug, spec in manifest["categories"].items():
        expected_parent_slug = spec.get("parent_slug")
        actual_parent_id = int(resolved[slug].get("parent") or 0)
        expected_parent_id = int(resolved[expected_parent_slug]["id"]) if expected_parent_slug else 0
        if actual_parent_id != expected_parent_id:
            raise RuntimeError(
                f"category parent mismatch for {slug}: expected_parent_slug={expected_parent_slug!r}"
            )
    return resolved


def category_slugs(category_ids: list[int], resolved: dict[str, dict[str, Any]]):
    reverse = {int(row["id"]): slug for slug, row in resolved.items()}
    unknown = [cid for cid in category_ids if int(cid) not in reverse]
    if unknown:
        raise RuntimeError(f"post contains category ids outside guarded set: {unknown}")
    return sorted(reverse[int(cid)] for cid in category_ids)


def preflight(manifest: dict[str, Any], resolved: dict[str, dict[str, Any]], authorization: str):
    plans = []
    for op in manifest["operations"]:
        post_id = int(op["post_id"])
        row = fetch_post(post_id, authorization)
        if int(row.get("id") or 0) != post_id:
            raise RuntimeError(f"post id mismatch for {post_id}")
        if row.get("slug") != op["slug"]:
            raise RuntimeError(
                f"post slug mismatch for id={post_id}: expected={op['slug']} actual={row.get('slug')}"
            )
        if row.get("status") != "publish":
            raise RuntimeError(f"post {op['slug']} is not published; refusing category write")

        current_ids = [int(x) for x in row.get("categories") or []]
        current_slugs = category_slugs(current_ids, resolved)
        expected_slugs = sorted(op["from_category_slugs"])
        desired_slugs = sorted(op["to_category_slugs"])

        if current_slugs == desired_slugs:
            action = "ALREADY_DONE"
        elif current_slugs == expected_slugs:
            action = "UPDATE"
        else:
            raise RuntimeError(
                f"category guard mismatch for {op['slug']}: expected={expected_slugs}, desired={desired_slugs}, actual={current_slugs}"
            )

        desired_ids = [int(resolved[slug]["id"]) for slug in op["to_category_slugs"]]
        plans.append(
            {
                "action": action,
                "post_id": post_id,
                "slug": op["slug"],
                "before_row": row,
                "before_snapshot": protected_snapshot(row),
                "before_category_ids": current_ids,
                "before_category_slugs": current_slugs,
                "desired_category_ids": desired_ids,
                "desired_category_slugs": desired_slugs,
            }
        )
    return plans


def verify_after(plan: dict[str, Any], row: dict[str, Any], resolved: dict[str, dict[str, Any]]):
    if protected_snapshot(row) != plan["before_snapshot"]:
        raise RuntimeError(f"non-category post fields changed for {plan['slug']}")
    actual = category_slugs([int(x) for x in row.get("categories") or []], resolved)
    if actual != plan["desired_category_slugs"]:
        raise RuntimeError(
            f"category verification failed for {plan['slug']}: desired={plan['desired_category_slugs']} actual={actual}"
        )


def rollback(written: list[dict[str, Any]], authorization: str):
    errors = []
    for plan in reversed(written):
        try:
            post_json(
                f"{SITE_URL}/wp-json/wp/v2/posts/{plan['post_id']}",
                authorization,
                {"categories": plan["before_category_ids"]},
            )
        except Exception as exc:  # pragma: no cover - emergency path
            errors.append(f"{plan['slug']}: {exc}")
    return errors


def apply(manifest_path: Path):
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")

    manifest = load_manifest(manifest_path)
    auth = auth_header(user, password)
    before_counts = public_counts(auth)
    resolved = resolve_categories(manifest, auth)

    # All target posts must pass their guards before the first write happens.
    plans = preflight(manifest, resolved, auth)
    written: list[dict[str, Any]] = []
    results = []

    try:
        for plan in plans:
            if plan["action"] == "UPDATE":
                response = post_json(
                    f"{SITE_URL}/wp-json/wp/v2/posts/{plan['post_id']}",
                    auth,
                    {"categories": plan["desired_category_ids"]},
                )
                if int(response.get("id") or 0) != plan["post_id"]:
                    raise RuntimeError(f"update response id mismatch for {plan['slug']}")
                written.append(plan)

            after = fetch_post(plan["post_id"], auth)
            verify_after(plan, after, resolved)
            results.append(
                {
                    "action": plan["action"],
                    "post_id": plan["post_id"],
                    "slug": plan["slug"],
                    "before": plan["before_category_slugs"],
                    "after": plan["desired_category_slugs"],
                }
            )

        after_counts = public_counts(auth)
        if after_counts != before_counts:
            raise RuntimeError("published post/page counts changed during category reorganization")
    except Exception:
        rollback_errors = rollback(written, auth)
        if rollback_errors:
            raise RuntimeError("category reorganization failed and rollback had errors: " + "; ".join(rollback_errors))
        raise

    report = {
        "operation_count": len(plans),
        "updated_count": sum(1 for x in results if x["action"] == "UPDATE"),
        "already_done_count": sum(1 for x in results if x["action"] == "ALREADY_DONE"),
        "wordpress_write_count": len(written),
        "content_write_count": 0,
        "publish_count": 0,
        "public_before": before_counts,
        "public_after": after_counts,
        "results": results,
    }

    out = Path("reports/category-reorganization")
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# Category reorganization",
        "",
        f"- operations: **{report['operation_count']}**",
        f"- updated: **{report['updated_count']}**",
        f"- already_done: **{report['already_done_count']}**",
        f"- wordpress_write_count: **{report['wordpress_write_count']}**",
        "- content_write_count: **0**",
        "- publish_count: **0**",
        f"- public_before: **{before_counts['published_total']}**",
        f"- public_after: **{after_counts['published_total']}**",
        "",
        "## Changes",
        "",
    ]
    for result in results:
        lines.append(
            f"- `{result['slug']}` — **{result['action']}** — "
            f"{', '.join(result['before'])} → {', '.join(result['after'])}"
        )
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()
    apply(Path(args.manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
