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
POST_ID = 2621
SLUG = "agetate-tenpura-hongo"
EXPECTED_TITLE = "あつあつ揚立てっちゃん本郷店へ｜揚げたて天ぷらが熱々すぎて最高！"
EXPECTED_CURRENT_SHA256 = "8998dc7ba4518ab1a0ab2c5311b5effaee36372d4374fc6fb70de1d7d207685d"
EXPECTED_FEATURED_MEDIA = 569
EXPECTED_MEDIA_IDS = [569, 526, 530, 529, 533, 532, 531]
SALVAGE_MARKER = "<!-- old-tsurikue-salvage:v1 slug=agetate-tenpura-hongo -->"
EDITORIAL_MARKER = "<!-- tsurikue-editorial:agetate-tenpura-hongo:v1 -->"
CONTENT_FILE = Path("editorial/agetate-tenpura-hongo/content.html")
USER_AGENT = "tsurikue-agetate-tenpura-hongo-tone-once/1.0"
REPORT_DIR = Path("reports/agetate-tenpura-hongo-tone-once")


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


def public_total(auth: str) -> int:
    return count_published("posts", auth) + count_published("pages", auth)


def media_ids(content: str) -> list[int]:
    out: list[int] = []
    for match in re.finditer(r"wp-image-(\d+)|\"id\"\s*:\s*(\d+)", content):
        media_id = int(match.group(1) or match.group(2))
        if media_id not in out:
            out.append(media_id)
    return out


def desired_content() -> str:
    body = CONTENT_FILE.read_text(encoding="utf-8").strip() + "\n"
    return SALVAGE_MARKER + "\n" + EDITORIAL_MARKER + "\n" + body


def write_report(report: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# agetate-tenpura-hongo tone patch",
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

        before_total = public_total(auth)
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
            raise RuntimeError(f"current content hash changed: {current_sha}")
        if SALVAGE_MARKER not in current or EDITORIAL_MARKER not in current:
            raise RuntimeError("required markers missing")
        before_media = media_ids(current)
        if before_media != EXPECTED_MEDIA_IDS:
            raise RuntimeError(f"unexpected article media ids: {before_media}")

        desired = desired_content()
        response = post_json(
            f"{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}",
            auth,
            {"content": desired, "status": "draft"},
        )
        if int(response.get("id") or 0) != POST_ID or response.get("status") != "draft":
            raise RuntimeError("update response validation failed")

        after = fetch_post(auth)
        after_total = public_total(auth)
        after_content = raw_field(after, "content")
        after_title = html.unescape(raw_field(after, "title"))
        after_media = media_ids(after_content)

        if before_total != after_total:
            raise RuntimeError("published counts changed")
        if after.get("status") != "draft" or after.get("slug") != SLUG:
            raise RuntimeError("post-update state mismatch")
        if after_title != EXPECTED_TITLE:
            raise RuntimeError("post-update title changed")
        if int(after.get("featured_media") or 0) != EXPECTED_FEATURED_MEDIA:
            raise RuntimeError("post-update featured_media changed")
        if after_content.strip() != desired.strip():
            raise RuntimeError("post-update content mismatch")
        if after_media != EXPECTED_MEDIA_IDS:
            raise RuntimeError(f"article media ids changed: {after_media}")

        report.update({
            "result": "SUCCESS",
            "status": "draft",
            "title": after_title,
            "featured_media": EXPECTED_FEATURED_MEDIA,
            "article_media_ids": after_media,
            "public_before": before_total,
            "public_after": after_total,
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
