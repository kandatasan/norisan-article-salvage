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
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SITE_URL = "https://tsurikue.com"
USER_AGENT = "tsurikue-public-internal-link-audit/1.0"
REPORT_DIR = Path("reports/public-internal-links-audit")


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def get_json(url: str, auth: str):
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "Authorization": auth, "User-Agent": USER_AGENT},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8")), dict(response.headers)


def raw_field(row: dict[str, Any], key: str) -> str:
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)


def fetch_all_published_posts(auth: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        query = urllib.parse.urlencode({
            "context": "edit",
            "status": "publish",
            "per_page": "100",
            "page": str(page),
            "orderby": "id",
            "order": "asc",
            "_fields": "id,slug,status,title,content,featured_media,link",
        })
        batch, headers = get_json(f"{SITE_URL}/wp-json/wp/v2/posts?{query}", auth)
        rows.extend(batch)
        total_pages = int(headers.get("X-WP-TotalPages", "1"))
        if page >= total_pages:
            break
        page += 1
    return rows


def count_published(endpoint: str, auth: str) -> int:
    query = urllib.parse.urlencode({"context": "edit", "status": "publish", "per_page": "1", "_fields": "id"})
    _, headers = get_json(f"{SITE_URL}/wp-json/wp/v2/{endpoint}?{query}", auth)
    return int(headers.get("X-WP-Total", "0"))


def normalize_internal_slug(href: str) -> str | None:
    href = html.unescape(href.strip())
    if href.startswith("/"):
        parsed = urllib.parse.urlsplit(SITE_URL + href)
    else:
        parsed = urllib.parse.urlsplit(href)
        host = (parsed.hostname or "").lower()
        if host not in {"tsurikue.com", "www.tsurikue.com"}:
            return None
    path = parsed.path.strip("/")
    if not path:
        return ""
    parts = [p for p in path.split("/") if p]
    if not parts:
        return ""
    # Ignore category/tag/admin-like endpoints when building post-to-post graph.
    if parts[0] in {"category", "tag", "wp-json", "wp-admin", "wp-content"}:
        return None
    return parts[-1]


def extract_internal_links(content: str) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    pattern = re.compile(r"<a\b[^>]*\bhref=(['\"])(.*?)\1[^>]*>(.*?)</a>", re.I | re.S)
    for match in pattern.finditer(content):
        href = html.unescape(match.group(2)).strip()
        slug = normalize_internal_slug(href)
        if slug is None:
            continue
        anchor_html = match.group(3)
        anchor = re.sub(r"<[^>]+>", "", anchor_html)
        anchor = html.unescape(re.sub(r"\s+", " ", anchor)).strip()
        links.append({"slug": slug, "anchor": anchor, "href": href})
    return links


def media_ids(content: str) -> list[int]:
    out: list[int] = []
    for match in re.finditer(r"wp-image-(\d+)|\"id\"\s*:\s*(\d+)", content):
        mid = int(match.group(1) or match.group(2))
        if mid not in out:
            out.append(mid)
    return out


def main() -> int:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise RuntimeError("missing WordPress secrets")
    auth = auth_header(user, password)

    posts = fetch_all_published_posts(auth)
    published_posts = count_published("posts", auth)
    published_pages = count_published("pages", auth)

    slug_set = {str(row.get("slug") or "") for row in posts}
    indegree: Counter[str] = Counter()
    outdegree: Counter[str] = Counter()
    incoming: dict[str, list[dict[str, str]]] = defaultdict(list)

    normalized: list[dict[str, Any]] = []
    for row in posts:
        content = raw_field(row, "content")
        title = html.unescape(raw_field(row, "title"))
        slug = str(row.get("slug") or "")
        links = extract_internal_links(content)
        post_links: list[dict[str, str]] = []
        for link in links:
            target = link["slug"]
            if target in slug_set and target != slug:
                post_links.append(link)
                outdegree[slug] += 1
                indegree[target] += 1
                incoming[target].append({"from": slug, "anchor": link["anchor"]})
        normalized.append({
            "id": int(row.get("id") or 0),
            "slug": slug,
            "status": row.get("status"),
            "title": title,
            "link": row.get("link") or f"{SITE_URL}/{slug}/",
            "featured_media": int(row.get("featured_media") or 0),
            "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
            "media_ids": media_ids(content),
            "internal_links": post_links,
        })

    for row in normalized:
        slug = row["slug"]
        row["outdegree"] = outdegree[slug]
        row["indegree"] = indegree[slug]
        row["incoming"] = incoming.get(slug, [])

    normalized.sort(key=lambda x: x["id"])
    zero_out = [r for r in normalized if r["outdegree"] == 0]
    zero_in = [r for r in normalized if r["indegree"] == 0]
    isolated = [r for r in normalized if r["outdegree"] == 0 and r["indegree"] == 0]

    result = {
        "wordpress_write_count": 0,
        "published_posts": published_posts,
        "published_pages": published_pages,
        "published_total": published_posts + published_pages,
        "fetched_posts": len(normalized),
        "zero_out_count": len(zero_out),
        "zero_in_count": len(zero_in),
        "isolated_count": len(isolated),
        "posts": normalized,
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def line_for(r: dict[str, Any]) -> str:
        return f"- `{r['slug']}` — {r['title']} (in {r['indegree']} / out {r['outdegree']})"

    lines = [
        "# Public internal-link audit",
        "",
        "GET-only audit. No WordPress write was performed.",
        "",
        f"- published_posts: **{published_posts}**",
        f"- published_pages: **{published_pages}**",
        f"- published_total: **{published_posts + published_pages}**",
        f"- fetched_posts: **{len(normalized)}**",
        f"- zero_out_count: **{len(zero_out)}**",
        f"- zero_in_count: **{len(zero_in)}**",
        f"- isolated_count: **{len(isolated)}**",
        "- wordpress_write_count: **0**",
        "",
        "## Isolated published posts",
        "",
        *(line_for(r) for r in isolated),
        "",
        "## Published posts with no outgoing post link",
        "",
        *(line_for(r) for r in zero_out),
        "",
        "## Current published post inventory / hashes",
        "",
        *(f"- `{r['id']}` `{r['slug']}` sha `{r['content_sha256']}` — {r['title']}" for r in normalized),
    ]
    (REPORT_DIR / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({
        "published_posts": published_posts,
        "published_pages": published_pages,
        "zero_out_count": len(zero_out),
        "zero_in_count": len(zero_in),
        "isolated_count": len(isolated),
        "wordpress_write_count": 0,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
