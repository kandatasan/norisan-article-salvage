#!/usr/bin/env python3
from __future__ import annotations

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
POST_ID = 2660
SLUG = "tsureruurawaza"
EXPECTED_TITLE = "ルアー・ワームで魚が釣れない？裏技！ガルプ粉＋特撰えび粉を試してみた"
EXPECTED_CURRENT_SHA256 = "1b7302ca51cbe587a8d43fb4c9813202bc818420bc3a3488aaf072164c593cdd"
EXPECTED_FEATURED_MEDIA = 67
CURRENT_EDITORIAL_MARKER = "<!-- tsurikue-editorial:tsureruurawaza:v2 -->"
PATCH_MARKER = "<!-- tsurikue-patch:tsureruurawaza:disadvantages-v1 -->"
USER_AGENT = "tsurikue-tsureruurawaza-disadvantages-once/1.2"
REPORT_DIR = Path("reports/tsureruurawaza-disadvantages-once")

ANCHOR = """<!-- wp:heading -->
<h2 class=\"wp-block-heading\">で、本当に釣れるの？近くの海で実験してみた</h2>
<!-- /wp:heading -->"""

SECTION = """<!-- tsurikue-patch:tsureruurawaza:disadvantages-v1 -->

<!-- wp:heading -->
<h2 class=\"wp-block-heading\">使ってみると、ちゃんとデメリットもある</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>この組み合わせ、面白いんですが良いことばかりではありません。</p>
<!-- /wp:paragraph -->

<!-- wp:list -->
<ul class=\"wp-block-list\">
<li>手がぬるぬるになる</li>
<li>特撰えび粉を車内にこぼすと臭い</li>
<li>巻き物系のルアーだと粉が落ちるのが早い</li>
<li>私が使った時は5〜6投くらいで、かなり流れ落ちた</li>
</ul>
<!-- /wp:list -->

<!-- wp:paragraph -->
<p>特に、えび粉を車内にぶちまけるのはオススメしません。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>帰りの車が、ずっとエビです。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>ジップ袋はしっかり閉めときましょう。</p>
<!-- /wp:paragraph -->"""


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def get_json(url: str, auth: str):
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "Authorization": auth, "User-Agent": USER_AGENT},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.loads(response.read().decode("utf-8")), dict(response.headers)


def post_json(url: str, auth: str, payload: dict[str, Any]):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": auth,
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


def fetch_post(auth: str) -> dict[str, Any]:
    query = urllib.parse.urlencode({"context": "edit", "_fields": "id,slug,status,title,content,featured_media"})
    row, _ = get_json(f"{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}?{query}", auth)
    return row


def count_published(endpoint: str, auth: str) -> int:
    query = urllib.parse.urlencode({"context": "edit", "status": "publish", "per_page": "1", "_fields": "id"})
    _, headers = get_json(f"{SITE_URL}/wp-json/wp/v2/{endpoint}?{query}", auth)
    return int(headers.get("X-WP-Total", "0"))


def public_counts(auth: str) -> dict[str, int]:
    posts = count_published("posts", auth)
    pages = count_published("pages", auth)
    return {"posts": posts, "pages": pages, "total": posts + pages}


def media_ids(content: str) -> list[int]:
    out: list[int] = []
    for match in re.finditer(r"wp-image-(\d+)|\"id\"\s*:\s*(\d+)", content):
        media_id = int(match.group(1) or match.group(2))
        if media_id not in out:
            out.append(media_id)
    return out


def write_report(report: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# tsureruurawaza disadvantages patch",
        "",
        f"- result: **{report['result']}**",
        f"- post_id: **{POST_ID}**",
        f"- status: **{report.get('status', 'unknown')}**",
        f"- title: {report.get('title', '')}",
        f"- featured_media: **{report.get('featured_media', 0)}**",
        f"- article_media_ids: **{', '.join(map(str, report.get('article_media_ids', [])))}**",
        f"- public_before: **{report.get('public_before', 'unknown')}**",
        f"- public_after: **{report.get('public_after', 'unknown')}**",
        f"- wordpress_write_count: **{report.get('wordpress_write_count', 0)}**",
        f"- source_content_sha256: `{report.get('source_content_sha256', '')}`",
        f"- content_sha256: `{report.get('content_sha256', '')}`",
    ]
    if report.get("error"):
        lines.append(f"- error: `{report['error']}`")
    (REPORT_DIR / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    report: dict[str, Any] = {
        "result": "BLOCKED",
        "status": "unknown",
        "title": "",
        "featured_media": 0,
        "article_media_ids": [],
        "public_before": "unknown",
        "public_after": "unknown",
        "wordpress_write_count": 0,
        "source_content_sha256": "",
        "content_sha256": "",
    }
    try:
        user = os.environ.get("TSURIKUE_WP_USER")
        password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
        if not user or not password:
            raise RuntimeError("missing WordPress secrets")
        auth = auth_header(user, password)

        before_counts = public_counts(auth)
        before = fetch_post(auth)
        current = raw_field(before, "content")
        current_title = html.unescape(raw_field(before, "title"))
        current_sha = hashlib.sha256(current.encode()).hexdigest()
        report["source_content_sha256"] = current_sha

        if int(before.get("id") or 0) != POST_ID or before.get("slug") != SLUG:
            raise RuntimeError("post id/slug mismatch")
        if before.get("status") != "draft":
            raise RuntimeError("target is not draft")
        if current_title != EXPECTED_TITLE:
            raise RuntimeError(f"title mismatch: {current_title!r}")
        if int(before.get("featured_media") or 0) != EXPECTED_FEATURED_MEDIA:
            raise RuntimeError("featured_media mismatch")
        if current_sha != EXPECTED_CURRENT_SHA256:
            raise RuntimeError(f"current content hash changed again: {current_sha}")
        if CURRENT_EDITORIAL_MARKER not in current:
            raise RuntimeError("v2 editorial marker missing")
        if PATCH_MARKER in current:
            raise RuntimeError("disadvantages patch already present")
        if current.count(ANCHOR) != 1:
            raise RuntimeError(f"anchor count is not 1: {current.count(ANCHOR)}")
        before_media = media_ids(current)
        if before_media != [46, 59, 67]:
            raise RuntimeError(f"unexpected current article media ids: {before_media}")

        desired = current.replace(ANCHOR, SECTION + "\n\n" + ANCHOR, 1)
        response = post_json(
            f"{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}",
            auth,
            {"content": desired, "status": "draft"},
        )
        if int(response.get("id") or 0) != POST_ID or response.get("status") != "draft":
            raise RuntimeError("update response validation failed")

        after = fetch_post(auth)
        after_counts = public_counts(auth)
        after_content = raw_field(after, "content")
        after_title = html.unescape(raw_field(after, "title"))
        after_media = media_ids(after_content)

        if after_counts != before_counts:
            raise RuntimeError("published counts changed")
        if after.get("status") != "draft" or after.get("slug") != SLUG:
            raise RuntimeError("post-update state mismatch")
        if after_title != EXPECTED_TITLE:
            raise RuntimeError("post-update title changed")
        if int(after.get("featured_media") or 0) != EXPECTED_FEATURED_MEDIA:
            raise RuntimeError("post-update featured_media changed")
        if after_content.strip() != desired.strip():
            raise RuntimeError("post-update content mismatch")
        if after_media != before_media:
            raise RuntimeError(f"article media ids changed: {after_media}")
        if PATCH_MARKER not in after_content:
            raise RuntimeError("patch marker missing after update")

        report.update({
            "result": "SUCCESS",
            "status": "draft",
            "title": after_title,
            "featured_media": EXPECTED_FEATURED_MEDIA,
            "article_media_ids": after_media,
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
