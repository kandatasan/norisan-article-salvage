#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

SITE_URL = "https://tsurikue.com"
SLUG = "ux-koukai"
EXPECTED_TITLE = "レクサスUXはひどい？616万円で買って後悔した欠点と満足している理由"
REPORT_DIR = Path("reports/ux-koukai-rewrite-audit")
USER_AGENT = "tsurikue-ux-koukai-rewrite-audit/1.0"

NEW_MARKERS = [
    "結論｜レクサスUXはひどくない。でも616万円で見ると気になる",
    "今からレクサスUXを買うなら、私は中古を選ぶ",
    "200〜300万円台なら、UXの弱点がかなり許せる",
    "手持ちの車が高く売れれば、中古UXはさらに狙いやすい",
    "まとめ｜UXは高くて狭い。でも中古なら話が変わる",
    "200〜300万円台のUX、ちょっと見てみる？",
    "今の車、思ったより高く売れるかも。",
]
OLD_MARKERS = [
    "結論｜レクサスUXはひどい車ではない。でも後悔する人はいる",
    "レクサスUXで後悔しやすい人・満足しやすい人",
    "レクサスUXで後悔しないために購入前に確認したいこと",
    "まとめ｜レクサスUXは広さで選ぶと後悔する。でも小さな高級車としては魅力的",
]


def auth_header(user: str, password: str) -> str:
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()


def get_json(url: str, auth: str):
    req = urllib.request.Request(url, headers={"Accept": "application/json", "Authorization": auth, "User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.loads(response.read().decode("utf-8")), dict(response.headers)


def raw_field(row, key: str) -> str:
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)


def count_published(endpoint: str, auth: str) -> int:
    q = urllib.parse.urlencode({"context": "edit", "status": "publish", "per_page": "1", "_fields": "id"})
    _, headers = get_json(f"{SITE_URL}/wp-json/wp/v2/{endpoint}?{q}", auth)
    return int(headers.get("X-WP-Total", "0"))


def main() -> int:
    report = {"result": "BLOCKED", "wordpress_write_count": 0}
    try:
        user = os.environ.get("TSURIKUE_WP_USER")
        password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
        if not user or not password:
            raise RuntimeError("missing WordPress secrets")
        auth = auth_header(user, password)
        q = urllib.parse.urlencode({"context": "edit", "slug": SLUG, "per_page": "10", "_fields": "id,slug,status,title,content,featured_media,modified"})
        rows, _ = get_json(f"{SITE_URL}/wp-json/wp/v2/posts?{q}", auth)
        rows = [x for x in rows if x.get("slug") == SLUG]
        if len(rows) != 1:
            raise RuntimeError(f"expected one post, got {len(rows)}")
        row = rows[0]
        content = raw_field(row, "content")
        title = html.unescape(raw_field(row, "title"))
        public_total = count_published("posts", auth) + count_published("pages", auth)

        new_presence = {x: (x in content) for x in NEW_MARKERS}
        old_presence = {x: (x in content) for x in OLD_MARKERS}
        counts = {
            "gulliver_banner": content.count('[blog_parts id="2843"]'),
            "gulliver_button": content.count("https://px.a8.net/svt/ejp?a8mat=4B65SD+8DUSHE+9QU+NVHCY"),
            "ctn_banner": content.count('[blog_parts id="2846"]'),
            "ctn_button": content.count('[blog_parts id="2184"]'),
        }
        applied = all(new_presence.values()) and not any(old_presence.values()) and counts == {
            "gulliver_banner": 1,
            "gulliver_button": 1,
            "ctn_banner": 1,
            "ctn_button": 1,
        }
        if row.get("status") != "publish":
            raise RuntimeError(f"status changed: {row.get('status')}")
        if title != EXPECTED_TITLE:
            raise RuntimeError(f"title changed: {title!r}")

        report.update({
            "result": "SUCCESS" if applied else "NEEDS_REVIEW",
            "post_id": row.get("id"),
            "slug": row.get("slug"),
            "status": row.get("status"),
            "title": title,
            "featured_media": row.get("featured_media"),
            "modified": row.get("modified"),
            "public_total": public_total,
            "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
            "new_markers": new_presence,
            "old_markers": old_presence,
            **counts,
        })
    except Exception as exc:
        report["error"] = str(exc)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# ux-koukai rewrite GET-only audit",
        "",
        f"- result: **{report.get('result')}**",
        f"- post_id: **{report.get('post_id', 'unknown')}**",
        f"- slug: **{report.get('slug', SLUG)}**",
        f"- status: **{report.get('status', 'unknown')}**",
        f"- title: {report.get('title', '')}",
        f"- featured_media: **{report.get('featured_media', 'unknown')}**",
        f"- public_total: **{report.get('public_total', 'unknown')}**",
        f"- wordpress_write_count: **0**",
        f"- gulliver_banner_count: **{report.get('gulliver_banner', 0)}**",
        f"- gulliver_button_count: **{report.get('gulliver_button', 0)}**",
        f"- ctn_banner_count: **{report.get('ctn_banner', 0)}**",
        f"- ctn_button_count: **{report.get('ctn_button', 0)}**",
        f"- content_sha256: `{report.get('content_sha256', '')}`",
        "",
        "## New markers",
    ]
    for marker, present in report.get("new_markers", {}).items():
        lines.append(f"- {'OK' if present else 'MISSING'}: {marker}")
    lines.append("")
    lines.append("## Old markers")
    for marker, present in report.get("old_markers", {}).items():
        lines.append(f"- {'STILL_PRESENT' if present else 'REMOVED'}: {marker}")
    if report.get("error"):
        lines += ["", f"- error: `{report['error']}`"]
    (REPORT_DIR / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("result") == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
