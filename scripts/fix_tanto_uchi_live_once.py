#!/usr/bin/env python3
"""Surgically keep only the first literal 'うちの' in live WP draft 4004.

Reads the current WordPress draft first so manual edits made after the last GitHub
sync are preserved. Only the repeated literal token is removed; nothing else is
rebuilt from repository content.
"""
from __future__ import annotations

import hashlib
import html
import json
import os
from pathlib import Path

from apply_editorial_draft_once import (
    SITE_URL,
    auth_header,
    fetch_post_by_id,
    post_json,
    public_counts,
    raw_field,
)

POST_ID = 4004
SLUG = "tanto-model-history"
TOKEN = "うちの"
REPORT_DIR = Path("reports/tanto-model-history-uchi-live-fix")


def main() -> int:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")

    auth = auth_header(user, password)
    before_public = public_counts(auth)
    before = fetch_post_by_id(POST_ID, auth)

    if int(before.get("id") or 0) != POST_ID:
        raise RuntimeError("post id mismatch")
    if before.get("slug") != SLUG:
        raise RuntimeError("slug mismatch")
    if before.get("status") != "draft":
        raise RuntimeError("target is not draft; refusing update")

    before_title = html.unescape(raw_field(before, "title"))
    before_featured = int(before.get("featured_media") or 0)
    before_content = raw_field(before, "content")
    before_count = before_content.count(TOKEN)

    if before_count <= 1:
        action = "NO_CHANGE"
        new_content = before_content
        write_count = 0
    else:
        first = before_content.find(TOKEN)
        keep_through = first + len(TOKEN)
        new_content = before_content[:keep_through] + before_content[keep_through:].replace(TOKEN, "")
        if new_content.count(TOKEN) != 1:
            raise RuntimeError("replacement validation failed before write")

        response = post_json(
            f"{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}",
            auth,
            {"content": new_content, "status": "draft"},
        )
        if int(response.get("id") or 0) != POST_ID or response.get("status") != "draft":
            raise RuntimeError("WordPress update response validation failed")
        action = "UPDATE"
        write_count = 1

    after = fetch_post_by_id(POST_ID, auth)
    after_public = public_counts(auth)
    after_content = raw_field(after, "content")
    after_title = html.unescape(raw_field(after, "title"))
    after_featured = int(after.get("featured_media") or 0)
    after_count = after_content.count(TOKEN)

    if after_public != before_public:
        raise RuntimeError("published counts changed")
    if after.get("status") != "draft" or after.get("slug") != SLUG:
        raise RuntimeError("post state changed unexpectedly")
    if after_title != before_title:
        raise RuntimeError("title changed unexpectedly")
    if after_featured != before_featured:
        raise RuntimeError("featured media changed unexpectedly")
    if after_content != new_content:
        raise RuntimeError("content mismatch after update")
    if before_count > 1 and after_count != 1:
        raise RuntimeError("expected exactly one remaining literal 'うちの'")
    if before_count <= 1 and after_count != before_count:
        raise RuntimeError("unexpected token count change")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "action": action,
        "post_id": POST_ID,
        "slug": SLUG,
        "status": "draft",
        "title": after_title,
        "featured_media": after_featured,
        "uchi_no_before": before_count,
        "uchi_no_after": after_count,
        "public_before": before_public,
        "public_after": after_public,
        "content_sha256_before": hashlib.sha256(before_content.encode()).hexdigest(),
        "content_sha256_after": hashlib.sha256(after_content.encode()).hexdigest(),
        "wordpress_write_count": write_count,
        "publish_count": 0,
        "media_upload_count": 0,
        "manual_edits_preserved_by_live_read": True,
    }
    (REPORT_DIR / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = "\n".join([
        "# tanto-model-history live wording cleanup",
        "",
        f"- action: **{action}**",
        f"- post_id: **{POST_ID}**",
        "- status: **draft**",
        f"- title: {after_title}",
        f"- literal `うちの` before: **{before_count}**",
        f"- literal `うちの` after: **{after_count}**",
        f"- public_before: **{before_public['published_total']}**",
        f"- public_after: **{after_public['published_total']}**",
        f"- content_sha256_after: `{report['content_sha256_after']}`",
        "- source: **current WordPress draft read at execution time**",
        "- manual edits: **preserved; repository article body was not used for replacement**",
    ]) + "\n"
    (REPORT_DIR / "summary.md").write_text(summary, encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
