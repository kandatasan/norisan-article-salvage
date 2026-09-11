#!/usr/bin/env python3
"""Create the Okunoshima rabbit-island experience article as one guarded WordPress draft."""
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

SITE_URL = "https://tsurikue.com"
USER_AGENT = "tsurikue-okunoshima-create/1.0"
TITLE = "大久野島へ行ってきた！うさぎはどこにいる？紅葉・廃墟・釣りまで島を一周"
SLUG = "okunoshima-rabbit-island"
CATEGORY_ID = 7
EXPECTED_CATEGORY = ("おでかけ", "sightseeing-leisure")
EXCERPT = "広島のうさぎ島・大久野島を妻と2人で時計回りに散策。フェリーを降りてもすぐにうさぎがいなかった体験、キャンプ場付近のうさぎ、11月の紅葉、毒ガス関連の遺構、意外だった釣りまで写真追加予定で紹介します。"
CONTENT_PATH = Path("editorial/okunoshima-rabbit-island/content.html")
OUT = Path("reports/okunoshima-rabbit-island-create")
EDITORIAL_MARKER = "<!-- editorial:okunoshima-rabbit-island:create-guard:v1 -->"
PHOTO_SLOT_COUNT = 8


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def request_json(
    url: str,
    authorization: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: int = 60,
) -> tuple[Any, dict[str, str]]:
    data = None
    headers = {
        "Accept": "application/json",
        "Authorization": authorization,
        "User-Agent": USER_AGENT,
    }
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"

    last: Exception | None = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8")), dict(response.headers)
        except Exception as exc:
            last = exc
            if attempt == 2:
                raise
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(str(last))


def raw_field(row: dict[str, Any], key: str) -> str:
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def count_published(endpoint: str, auth: str) -> int:
    q = urllib.parse.urlencode({
        "context": "edit",
        "status": "publish",
        "per_page": "1",
        "_fields": "id",
    })
    _, headers = request_json(f"{SITE_URL}/wp-json/wp/v2/{endpoint}?{q}", auth)
    return int(headers.get("X-WP-Total", "0"))


def public_counts(auth: str) -> dict[str, int]:
    posts = count_published("posts", auth)
    pages = count_published("pages", auth)
    return {
        "published_posts": posts,
        "published_pages": pages,
        "published_total": posts + pages,
    }


def validate_category(auth: str) -> None:
    q = urllib.parse.urlencode({"context": "edit", "_fields": "id,name,slug"})
    row, _ = request_json(f"{SITE_URL}/wp-json/wp/v2/categories/{CATEGORY_ID}?{q}", auth)
    expected_name, expected_slug = EXPECTED_CATEGORY
    if int(row.get("id") or 0) != CATEGORY_ID:
        raise RuntimeError(f"category id mismatch: {row}")
    if row.get("name") != expected_name or row.get("slug") != expected_slug:
        raise RuntimeError(f"category mismatch: {row}")


def build_content() -> str:
    content = CONTENT_PATH.read_text(encoding="utf-8").strip()
    if "<h1" in content.casefold():
        raise RuntimeError("body must not contain H1")
    if content.count("<!-- editorial:okunoshima-rabbit-island:v1 updated=2026-09-11 -->") != 1:
        raise RuntimeError("editorial marker missing or duplicated")
    slot_count = content.count("<!-- photo-slot:")
    if slot_count != PHOTO_SLOT_COUNT:
        raise RuntimeError(f"photo slot count mismatch: {slot_count} != {PHOTO_SLOT_COUNT}")
    if any(x in content for x in ("😀", "🔥", "🚀", "🤣", "😏")):
        raise RuntimeError("article body contains emoji")
    return EDITORIAL_MARKER + "\n" + content


def fetch_exact_slug(auth: str) -> list[dict[str, Any]]:
    params = {
        "context": "edit",
        "status": "any",
        "slug": SLUG,
        "per_page": "100",
        "_fields": "id,slug,status,title,content,excerpt,featured_media,categories,modified,link",
    }
    rows, _ = request_json(f"{SITE_URL}/wp-json/wp/v2/posts?{urllib.parse.urlencode(params)}", auth)
    return list(rows)


def fetch_title_search(auth: str) -> list[dict[str, Any]]:
    params = {
        "context": "edit",
        "status": "any",
        "search": "大久野島",
        "per_page": "100",
        "_fields": "id,slug,status,title,link",
    }
    rows, _ = request_json(f"{SITE_URL}/wp-json/wp/v2/posts?{urllib.parse.urlencode(params)}", auth)
    return list(rows)


def validate_draft(row: dict[str, Any], expected_content: str) -> None:
    if row.get("status") != "draft":
        raise RuntimeError("target is not draft")
    if str(row.get("slug") or "") != SLUG:
        raise RuntimeError("slug mismatch")
    if html.unescape(raw_field(row, "title")) != TITLE:
        raise RuntimeError("title mismatch")
    if int(row.get("featured_media") or 0) != 0:
        raise RuntimeError("unexpected featured media; photo patch has not run yet")
    categories = [int(value) for value in (row.get("categories") or [])]
    if categories != [CATEGORY_ID]:
        raise RuntimeError(f"category mismatch: {categories}")
    actual_content = raw_field(row, "content").strip()
    if actual_content != expected_content.strip():
        raise RuntimeError(
            "existing draft content differs; refusing overwrite: " + sha256_text(actual_content)
        )


def write_report(report: dict[str, Any]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "result.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Okunoshima rabbit-island draft creation",
        "",
        f"- action: **{report['action']}**",
        f"- post_id: **{report['post_id']}**",
        f"- status: **{report['status']}**",
        f"- slug: `{SLUG}`",
        f"- title: {TITLE}",
        f"- category_id: **{CATEGORY_ID}**",
        "- featured_media: **0**",
        f"- photo_slots_pending: **{PHOTO_SLOT_COUNT}**",
        "- confirmed_media_checked: **0**",
        "- media_upload_count: **0**",
        f"- wordpress_write_count: **{report['wordpress_write_count']}**",
        f"- published_before: **{report['public_before']['published_total']}**",
        f"- published_after: **{report['public_after']['published_total']}**",
        f"- content_sha256: `{report['content_sha256']}`",
        "- publish_count: **0**",
    ]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")
    auth = auth_header(user, password)

    before_counts = public_counts(auth)
    validate_category(auth)
    expected_content = build_content()

    exact = fetch_exact_slug(auth)
    if len(exact) > 1:
        raise RuntimeError(f"multiple exact-slug posts found: {[row.get('id') for row in exact]}")

    if exact:
        row = exact[0]
        if row.get("status") != "draft":
            raise RuntimeError(f"/{SLUG}/ already exists with status={row.get('status')}; refusing create")
        validate_draft(row, expected_content)
        action = "ALREADY_UP_TO_DATE"
        post_id = int(row.get("id") or 0)
        post_write_count = 0
    else:
        possible = fetch_title_search(auth)
        if possible:
            raise RuntimeError(
                "possible 大久野島 duplicate(s) found; refusing create: "
                + json.dumps(possible, ensure_ascii=False)
            )

        payload = {
            "title": TITLE,
            "slug": SLUG,
            "status": "draft",
            "content": expected_content,
            "excerpt": EXCERPT,
            "categories": [CATEGORY_ID],
        }
        created, _ = request_json(
            f"{SITE_URL}/wp-json/wp/v2/posts",
            auth,
            method="POST",
            payload=payload,
            timeout=90,
        )
        post_id = int(created.get("id") or 0)
        if not post_id or created.get("status") != "draft":
            raise RuntimeError(
                f"unexpected create response: id={post_id} status={created.get('status')}"
            )
        action = "CREATE_DRAFT"
        post_write_count = 1

    q = urllib.parse.urlencode({
        "context": "edit",
        "_fields": "id,slug,status,title,content,excerpt,featured_media,categories,modified,link",
    })
    after_row, _ = request_json(f"{SITE_URL}/wp-json/wp/v2/posts/{post_id}?{q}", auth)
    validate_draft(after_row, expected_content)

    after_counts = public_counts(auth)
    if before_counts != after_counts:
        raise RuntimeError(f"published counts changed: {before_counts} -> {after_counts}")

    report = {
        "action": action,
        "post_id": post_id,
        "status": after_row.get("status"),
        "wordpress_write_count": post_write_count,
        "public_before": before_counts,
        "public_after": after_counts,
        "content_sha256": sha256_text(expected_content.strip()),
    }
    write_report(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
