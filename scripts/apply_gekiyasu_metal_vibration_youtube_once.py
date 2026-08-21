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
POST_ID = 2625
SLUG = "gekiyasu-metal-vibration"
EXPECTED_TITLE = "激安メタルバイブ「ゲキブルブレード」を実釣インプレ｜安くても魚は釣れる！"
EXPECTED_CURRENT_SHA256 = "ec40d604d42bcf53d300c5b4344a0fd4fe1e563a6e2196e504bb1082251e79a6"
EXPECTED_FEATURED_MEDIA = 274
EXPECTED_MEDIA_IDS = [274, 276, 217]
EDITORIAL_MARKER = "<!-- tsurikue-editorial:gekiyasu-metal-vibration:v1 -->"
PATCH_MARKER = "<!-- tsurikue-patch:gekiyasu-metal-vibration:youtube-v1 -->"
YOUTUBE_URL = "https://www.youtube.com/watch?v=74_cHVH9Csw"
USER_AGENT = "tsurikue-gekiyasu-youtube-once/1.0"
REPORT_DIR = Path("reports/gekiyasu-metal-vibration-youtube-once")

ANCHOR = """<!-- wp:heading -->
<h2 class=\"wp-block-heading\">で、本当に魚は釣れたの？</h2>
<!-- /wp:heading -->"""

SECTION = f"""{PATCH_MARKER}

<!-- wp:heading {{\"level\":3}} -->
<h3 class=\"wp-block-heading\">水中で見るとこんな動き</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>上から見ているだけだと分かりにくいので、水中でも実際に動かして撮ってみました。</p>
<!-- /wp:paragraph -->

<!-- wp:embed {{\"url\":\"{YOUTUBE_URL}\",\"type\":\"video\",\"providerNameSlug\":\"youtube\",\"responsive\":true,\"className\":\"wp-embed-aspect-16-9 wp-has-aspect-ratio\"}} -->
<figure class=\"wp-block-embed is-type-video is-provider-youtube wp-block-embed-youtube wp-embed-aspect-16-9 wp-has-aspect-ratio\"><div class=\"wp-block-embed__wrapper\">{YOUTUBE_URL}</div></figure>
<!-- /wp:embed -->

<!-- wp:paragraph -->
<p>水中で見ると、後ろのブレードがしっかり動いてキラキラ。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>うん。これなら釣れそう。</strong></p>
<!-- /wp:paragraph -->"""


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def get_json(url: str, auth: str):
    req = urllib.request.Request(url, headers={"Accept":"application/json","Authorization":auth,"User-Agent":USER_AGENT}, method="GET")
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.loads(response.read().decode("utf-8")), dict(response.headers)


def post_json(url: str, auth: str, payload: dict[str, Any]):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Accept":"application/json","Content-Type":"application/json; charset=utf-8","Authorization":auth,"User-Agent":USER_AGENT},
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
    query = urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,content,featured_media"})
    row, _ = get_json(f"{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}?{query}", auth)
    return row


def count_published(endpoint: str, auth: str) -> int:
    query = urllib.parse.urlencode({"context":"edit","status":"publish","per_page":"1","_fields":"id"})
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


def write_report(report: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# gekiyasu-metal-vibration YouTube patch",
        "",
        f"- result: **{report['result']}**",
        f"- post_id: **{POST_ID}**",
        f"- status: **{report.get('status', 'unknown')}**",
        f"- title: {report.get('title', '')}",
        f"- featured_media: **{report.get('featured_media', 0)}**",
        f"- article_media_ids: **{', '.join(map(str, report.get('article_media_ids', [])))}**",
        f"- youtube_url: {YOUTUBE_URL}",
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
        "result": "BLOCKED", "status":"unknown", "title":"", "featured_media":0,
        "article_media_ids":[], "public_before":"unknown", "public_after":"unknown",
        "wordpress_write_count":0, "source_content_sha256":"", "content_sha256":"",
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
        current_sha = hashlib.sha256(current.encode()).hexdigest()
        report["source_content_sha256"] = current_sha
        title = html.unescape(raw_field(before, "title"))

        if int(before.get("id") or 0) != POST_ID or before.get("slug") != SLUG:
            raise RuntimeError("post id/slug mismatch")
        if before.get("status") != "draft":
            raise RuntimeError("target is not draft")
        if title != EXPECTED_TITLE:
            raise RuntimeError(f"title mismatch: {title!r}")
        if int(before.get("featured_media") or 0) != EXPECTED_FEATURED_MEDIA:
            raise RuntimeError("featured_media mismatch")
        if current_sha != EXPECTED_CURRENT_SHA256:
            raise RuntimeError(f"current content hash changed: {current_sha}")
        if EDITORIAL_MARKER not in current:
            raise RuntimeError("editorial marker missing")
        if PATCH_MARKER in current or "74_cHVH9Csw" in current:
            raise RuntimeError("YouTube patch already present")
        before_media = media_ids(current)
        if before_media != EXPECTED_MEDIA_IDS:
            raise RuntimeError(f"unexpected article media ids: {before_media}")
        if current.count(ANCHOR) != 1:
            raise RuntimeError(f"anchor count is not 1: {current.count(ANCHOR)}")

        desired = current.replace(ANCHOR, SECTION + "\n\n" + ANCHOR, 1)
        response = post_json(f"{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}", auth, {"content":desired,"status":"draft"})
        if int(response.get("id") or 0) != POST_ID or response.get("status") != "draft":
            raise RuntimeError("update response validation failed")

        after = fetch_post(auth)
        after_total = public_total(auth)
        after_content = raw_field(after, "content")
        after_media = media_ids(after_content)
        after_title = html.unescape(raw_field(after, "title"))
        if after_total != before_total:
            raise RuntimeError("published counts changed")
        if after.get("status") != "draft" or after.get("slug") != SLUG:
            raise RuntimeError("post-update state mismatch")
        if after_title != EXPECTED_TITLE:
            raise RuntimeError("post-update title changed")
        if int(after.get("featured_media") or 0) != EXPECTED_FEATURED_MEDIA:
            raise RuntimeError("post-update featured_media changed")
        if after_media != EXPECTED_MEDIA_IDS:
            raise RuntimeError(f"article media ids changed: {after_media}")
        if PATCH_MARKER not in after_content or "74_cHVH9Csw" not in after_content:
            raise RuntimeError("YouTube patch missing after update")
        if after_content.strip() != desired.strip():
            raise RuntimeError("post-update content mismatch")

        report.update({
            "result":"SUCCESS", "status":"draft", "title":after_title,
            "featured_media":EXPECTED_FEATURED_MEDIA, "article_media_ids":after_media,
            "public_before":before_total, "public_after":after_total, "wordpress_write_count":1,
            "content_sha256":hashlib.sha256(after_content.encode()).hexdigest(),
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
