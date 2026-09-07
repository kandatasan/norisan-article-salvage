#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

SITE_URL = "https://tsurikue.com"
POST_ID = 2517
SLUG = "ux-koukai"
EXPECTED_TITLE = "レクサスUXはひどい？616万円で買って後悔した欠点と満足している理由"
USER_AGENT = "tsurikue-ux-koukai-ctn-curiosity/1.0"
REPORT_DIR = Path("reports/ux-koukai-ctn-curiosity")
MARKER = "<!-- tsurikue-ctn-curiosity:ux-koukai:20260907 -->"

BANNER_BLOCK = '''<!-- wp:shortcode -->
[blog_parts id="2846"]
<!-- /wp:shortcode -->'''

NEXT_HEADING = '<h2 class="wp-block-heading">文句はある。でも私はUXが好きだった</h2>'

CTA_BLOCK = '''<!-- tsurikue-ctn-curiosity:ux-koukai:20260907 -->
<!-- wp:paragraph -->
<p>ちなみに、このとき私がUXを査定に出したきっかけは、<strong>売却ではなく、ただの好奇心</strong>でした。<br>「これ、いくらになるんだろ？」</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>その好奇心で試してみたら、ディーラー350万円に対して一括査定では最高500万円近い提示。<br><strong>約150万円の差を知ることになりました。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>私みたいに「売る気はないけど、愛車の値段はちょっと気になる」という人もいるはずです。</p>
<!-- /wp:paragraph -->

<!-- wp:shortcode -->
[blog_parts id="2184"]
<!-- /wp:shortcode -->'''


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
    query = urllib.parse.urlencode({
        "context": "edit",
        "slug": SLUG,
        "per_page": "10",
        "_fields": "id,slug,status,title,content,featured_media,modified",
    })
    rows, _ = get_json(f"{SITE_URL}/wp-json/wp/v2/posts?{query}", auth)
    matches = [row for row in rows if row.get("slug") == SLUG]
    if len(matches) != 1:
        raise RuntimeError(f"expected one post for slug {SLUG!r}, got {len(matches)}")
    return matches[0]


def count_published(endpoint: str, auth: str) -> int:
    query = urllib.parse.urlencode({"context": "edit", "status": "publish", "per_page": "1", "_fields": "id"})
    _, headers = get_json(f"{SITE_URL}/wp-json/wp/v2/{endpoint}?{query}", auth)
    return int(headers.get("X-WP-Total", "0"))


def public_total(auth: str) -> int:
    return count_published("posts", auth) + count_published("pages", auth)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_summary(lines: list[str]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    user = os.environ["TSURIKUE_WP_USER"]
    password = os.environ["TSURIKUE_WP_APP_PASSWORD"]
    auth = auth_header(user, password)

    summary = ["# UX koukai CTN curiosity CTA", ""]
    try:
        before = fetch_post(auth)
        title = raw_field(before, "title")
        content = raw_field(before, "content")
        featured_before = int(before.get("featured_media") or 0)
        public_before = public_total(auth)

        if before.get("id") != POST_ID:
            raise RuntimeError(f"post id mismatch: {before.get('id')} != {POST_ID}")
        if before.get("slug") != SLUG:
            raise RuntimeError(f"slug mismatch: {before.get('slug')!r}")
        if before.get("status") != "publish":
            raise RuntimeError(f"status mismatch: {before.get('status')!r}")
        if title != EXPECTED_TITLE:
            raise RuntimeError(f"title mismatch: {title!r}")

        if MARKER in content:
            summary += [
                "- result: already_applied",
                f"- post_id: {POST_ID}",
                f"- slug: {SLUG}",
                "- status: publish",
                f"- public_before: {public_before}",
                f"- public_after: {public_before}",
            ]
            write_summary(summary)
            return

        anchor = BANNER_BLOCK + "\n\n" + NEXT_HEADING
        if content.count(anchor) != 1:
            raise RuntimeError(f"expected exactly one CTN banner/heading anchor, got {content.count(anchor)}")

        updated = content.replace(anchor, BANNER_BLOCK + "\n\n" + CTA_BLOCK + "\n\n" + NEXT_HEADING, 1)
        if updated.count(MARKER) != 1:
            raise RuntimeError("marker insertion check failed")
        if updated.count('[blog_parts id="2846"]') != content.count('[blog_parts id="2846"]'):
            raise RuntimeError("CTN banner count changed unexpectedly")
        if updated.count('[blog_parts id="2184"]') != content.count('[blog_parts id="2184"]') + 1:
            raise RuntimeError("CTN button count did not increase by exactly one")

        post_json(f"{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}", auth, {"content": updated})

        after = fetch_post(auth)
        after_content = raw_field(after, "content")
        public_after = public_total(auth)

        checks = {
            "id": after.get("id") == POST_ID,
            "slug": after.get("slug") == SLUG,
            "status": after.get("status") == "publish",
            "title": raw_field(after, "title") == EXPECTED_TITLE,
            "featured_media": int(after.get("featured_media") or 0) == featured_before,
            "marker": MARKER in after_content,
            "public_total": public_after == public_before,
        }
        failed = [name for name, ok in checks.items() if not ok]
        if failed:
            raise RuntimeError("post-write verification failed: " + ", ".join(failed))

        summary += [
            "- result: applied",
            f"- post_id: {POST_ID}",
            f"- slug: {SLUG}",
            "- status: publish",
            f"- title: {EXPECTED_TITLE}",
            f"- featured_media: {featured_before}",
            f"- public_before: {public_before}",
            f"- public_after: {public_after}",
            f"- content_sha_before: {sha256(content)}",
            f"- content_sha_after: {sha256(after_content)}",
            "- ctn_banner_count: unchanged",
            "- ctn_button_count: +1",
            "- copy: curiosity-led CTA after the existing CTN banner",
        ]
        write_summary(summary)
    except Exception as exc:
        summary += ["- result: failed", f"- error: {type(exc).__name__}: {exc}"]
        write_summary(summary)
        raise


if __name__ == "__main__":
    main()
