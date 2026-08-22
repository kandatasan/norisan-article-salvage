#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

SITE_URL = "https://tsurikue.com"
USER_AGENT = "tsurikue-recent-media-identify/1.2"
REPORT_DIR = Path("reports/gopro-media-identify")
TARGET_SIZES = {(1152, 1536), (1194, 834)}
CATFISH_POST_ID = 2622
CATFISH_EXPECTED_MEDIA = {125, 2825, 2824, 2816, 2815, 2814, 2813, 2809, 2808}


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def get_json(url: str, auth: str):
    req = urllib.request.Request(url, headers={"Accept": "application/json", "Authorization": auth, "User-Agent": USER_AGENT}, method="GET")
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8")), dict(response.headers)


def main() -> int:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise RuntimeError("missing WordPress secrets")
    auth = auth_header(user, password)

    q = urllib.parse.urlencode({
        "context": "edit",
        "per_page": "40",
        "orderby": "date",
        "order": "desc",
        "_fields": "id,date,slug,source_url,alt_text,caption,media_details,mime_type,title",
    })
    rows, _ = get_json(f"{SITE_URL}/wp-json/wp/v2/media?{q}", auth)

    normalized = []
    for row in rows:
        details = row.get("media_details") or {}
        width = int(details.get("width") or 0)
        height = int(details.get("height") or 0)
        item = {
            "id": int(row.get("id") or 0),
            "date": row.get("date") or "",
            "slug": row.get("slug") or "",
            "source_url": row.get("source_url") or "",
            "mime_type": row.get("mime_type") or "",
            "width": width,
            "height": height,
            "alt_text": row.get("alt_text") or "",
        }
        normalized.append(item)

    matches = [r for r in normalized if (r["width"], r["height"]) in TARGET_SIZES]

    post_q = urllib.parse.urlencode({
        "context": "edit",
        "_fields": "id,slug,status,featured_media,title,content",
    })
    post, _ = get_json(f"{SITE_URL}/wp-json/wp/v2/posts/{CATFISH_POST_ID}?{post_q}", auth)
    raw_content = ((post.get("content") or {}).get("raw") or "")
    media_ids = sorted({int(x) for x in re.findall(r"wp-image-(\d+)", raw_content)})
    expected_found = sorted(CATFISH_EXPECTED_MEDIA.intersection(media_ids))
    expected_missing = sorted(CATFISH_EXPECTED_MEDIA.difference(media_ids))
    catfish = {
        "id": int(post.get("id") or 0),
        "slug": post.get("slug") or "",
        "status": post.get("status") or "",
        "featured_media": int(post.get("featured_media") or 0),
        "content_sha256": hashlib.sha256(raw_content.encode("utf-8")).hexdigest(),
        "article_media_ids": media_ids,
        "expected_media_found": expected_found,
        "expected_media_missing": expected_missing,
        "all_expected_media_present": not expected_missing,
    }

    result = {
        "wordpress_write_count": 0,
        "recent_media_checked": len(normalized),
        "matches": matches,
        "recent_media": normalized,
        "catfish_post_verification": catfish,
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Recent media identification",
        "",
        "GET-only. No WordPress write was performed.",
        "",
        "## Catfish draft photo verification",
        "",
        f"- post_id: **{catfish['id']}**",
        f"- slug: **{catfish['slug']}**",
        f"- status: **{catfish['status']}**",
        f"- featured_media: **{catfish['featured_media']}**",
        f"- content_sha256: `{catfish['content_sha256']}`",
        f"- article_media_ids: **{', '.join(str(x) for x in catfish['article_media_ids'])}**",
        f"- expected_media_found: **{', '.join(str(x) for x in catfish['expected_media_found'])}**",
        f"- expected_media_missing: **{', '.join(str(x) for x in catfish['expected_media_missing']) or 'none'}**",
        f"- all_expected_media_present: **{str(catfish['all_expected_media_present']).lower()}**",
        "- wordpress_write_count: **0**",
        "",
        f"- recent_media_checked: **{len(normalized)}**",
        f"- size_matches: **{len(matches)}**",
        "",
        "## Size matches",
        "",
    ]
    for r in matches:
        lines.append(f"- media **#{r['id']}** — `{r['width']}x{r['height']}` — `{r['source_url']}` — slug `{r['slug']}`")
    lines += ["", "## Recent media", ""]
    for r in normalized:
        lines.append(f"- media #{r['id']} — {r['date']} — `{r['width']}x{r['height']}` — `{r['source_url']}`")
    (REPORT_DIR / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"catfish_post_verification": catfish, "wordpress_write_count": 0}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
