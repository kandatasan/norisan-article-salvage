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

SITE_URL = "https://tsurikue.com"
USER_AGENT = "tsurikue-recent-media-identify/1.3"
REPORT_DIR = Path("reports/gopro-media-identify")
TARGET_SIZES = {(1152, 1536), (1194, 834)}
CATFISH_CONFIG = Path("editorial/catfish/config.json")


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def get_json(url: str, auth: str):
    req = urllib.request.Request(url, headers={"Accept": "application/json", "Authorization": auth, "User-Agent": USER_AGENT}, method="GET")
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8")), dict(response.headers)


def raw_field(row, key: str) -> str:
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)


def main() -> int:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise RuntimeError("missing WordPress secrets")
    auth = auth_header(user, password)
    cfg = json.loads(CATFISH_CONFIG.read_text(encoding="utf-8"))
    expected_media = {int(k): v for k, v in (cfg.get("expected_media") or {}).items()}
    expected_media_ids = set(expected_media)

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
        normalized.append({
            "id": int(row.get("id") or 0),
            "date": row.get("date") or "",
            "slug": row.get("slug") or "",
            "source_url": row.get("source_url") or "",
            "mime_type": row.get("mime_type") or "",
            "width": width,
            "height": height,
            "alt_text": row.get("alt_text") or "",
        })

    matches = [r for r in normalized if (r["width"], r["height"]) in TARGET_SIZES]

    post_q = urllib.parse.urlencode({"context": "edit", "_fields": "id,slug,status,featured_media,title,content"})
    post, _ = get_json(f"{SITE_URL}/wp-json/wp/v2/posts/{cfg['post_id']}?{post_q}", auth)
    raw_content = raw_field(post, "content")
    content_sha = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()
    media_ids = sorted({int(x) for x in re.findall(r"wp-image-(\d+)", raw_content)})
    found = sorted(expected_media_ids.intersection(media_ids))
    missing = sorted(expected_media_ids.difference(media_ids))

    target_guard = {
        "id_matches": int(post.get("id") or 0) == int(cfg["post_id"]),
        "slug_matches": (post.get("slug") or "") == cfg["slug"],
        "status_is_draft": (post.get("status") or "") == "draft",
        "title_matches": html.unescape(raw_field(post, "title")) == cfg["title"],
        "featured_media_matches": int(post.get("featured_media") or 0) == int(cfg.get("expected_current_featured_media", cfg.get("featured_media", 0)) or 0),
        "content_sha_matches": content_sha.casefold() == (cfg.get("expected_current_content_sha256") or "").strip().casefold(),
    }
    target_guard["all_pass"] = all(target_guard.values())

    media_guard_checks = []
    for media_id, expected_path in expected_media.items():
        mq = urllib.parse.urlencode({"context": "edit", "_fields": "id,status,source_url"})
        media, _ = get_json(f"{SITE_URL}/wp-json/wp/v2/media/{media_id}?{mq}", auth)
        source_url = media.get("source_url") or ""
        actual_path = urllib.parse.unquote(urllib.parse.urlparse(source_url).path)
        media_guard_checks.append({
            "id": media_id,
            "expected_path": expected_path,
            "actual_path": actual_path,
            "matches": actual_path.casefold() == expected_path.casefold(),
        })
    media_guard_pass = all(x["matches"] for x in media_guard_checks)

    catfish = {
        "id": int(post.get("id") or 0),
        "slug": post.get("slug") or "",
        "status": post.get("status") or "",
        "featured_media": int(post.get("featured_media") or 0),
        "content_sha256": content_sha,
        "article_media_ids": media_ids,
        "expected_media_found": found,
        "expected_media_missing": missing,
        "all_expected_media_present": not missing,
        "target_guard": target_guard,
        "media_guard_checks": media_guard_checks,
        "media_guard_all_pass": media_guard_pass,
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
        "## Catfish draft guard diagnosis",
        "",
        f"- post_id: **{catfish['id']}**",
        f"- status: **{catfish['status']}**",
        f"- featured_media: **{catfish['featured_media']}**",
        f"- content_sha256: `{catfish['content_sha256']}`",
        f"- target_guard_all_pass: **{str(target_guard['all_pass']).lower()}**",
        f"- media_guard_all_pass: **{str(media_guard_pass).lower()}**",
        f"- article_media_ids: **{', '.join(str(x) for x in media_ids)}**",
        f"- expected_media_missing_from_body: **{', '.join(str(x) for x in missing) or 'none'}**",
        "- wordpress_write_count: **0**",
        "",
        "### Target guard details",
        "",
    ]
    for key, value in target_guard.items():
        lines.append(f"- {key}: **{str(value).lower()}**")
    lines += ["", "### Media guard details", ""]
    for item in media_guard_checks:
        lines.append(f"- media #{item['id']}: **{'match' if item['matches'] else 'MISMATCH'}** — expected `{item['expected_path']}` — actual `{item['actual_path']}`")
    lines += ["", f"- recent_media_checked: **{len(normalized)}**", f"- size_matches: **{len(matches)}**", "", "## Recent media", ""]
    for r in normalized:
        lines.append(f"- media #{r['id']} — {r['date']} — `{r['width']}x{r['height']}` — `{r['source_url']}`")
    (REPORT_DIR / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"catfish_post_verification": catfish, "wordpress_write_count": 0}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
