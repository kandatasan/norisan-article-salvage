#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

SITE_URL = "https://tsurikue.com"
USER_AGENT = "tsurikue-saijo-sakagura-inspect/1.0"
OUT = Path("reports/saijo-sakagura-inspect")
SLUG = "saijo-sakagura-dori"
SEARCH_TEXT = "西条 酒蔵"

EXPECTED_STEMS = [
    "img_2197",
    "84925020-bffa-4718-bbd2-f9c1ef2a9ad2",
    "befe8465-2627-4832-981d-d8f1193e7f4d",
    "836f3f0b-cdbe-44ea-a1f9-056ac719f316",
    "fc700358-a71d-4829-bb05-4bc601d9ce0f",
    "d78d1e43-e39e-49e1-8d79-1e015c468f1a",
    "039624f5-5844-429f-9fda-4780cdfbdada",
    "img_0948",
    "img_0952",
    "img_2201",
    "img_2203",
    "img_2204",
    "img_2216",
]


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def request_json(url: str, authorization: str, *, timeout: int = 60) -> tuple[Any, dict[str, str]]:
    headers = {"Accept": "application/json", "Authorization": authorization, "User-Agent": USER_AGENT}
    last: Exception | None = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8")), dict(response.headers)
        except Exception as exc:
            last = exc
            if attempt == 2:
                raise
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(str(last))


def canonical_stem(url: str) -> str:
    filename = Path(urllib.parse.unquote(urllib.parse.urlparse(url).path)).name
    stem = Path(filename).stem.casefold()
    stem = re.sub(r"-\d+x\d+$", "", stem)
    stem = re.sub(r"-scaled$", "", stem)
    stem = re.sub(r"-\d+$", "", stem)
    return stem


def count_published(endpoint: str, auth: str) -> int:
    q = urllib.parse.urlencode({"context": "edit", "status": "publish", "per_page": "1", "_fields": "id"})
    _, headers = request_json(f"{SITE_URL}/wp-json/wp/v2/{endpoint}?{q}", auth)
    return int(headers.get("X-WP-Total", "0"))


def public_counts(auth: str) -> dict[str, int]:
    posts = count_published("posts", auth)
    pages = count_published("pages", auth)
    return {"published_posts": posts, "published_pages": pages, "published_total": posts + pages}


def inspect_posts(auth: str) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for status in ["publish", "draft", "pending", "private", "future"]:
        params = {
            "context": "edit",
            "status": status,
            "per_page": "100",
            "search": SEARCH_TEXT,
            "_fields": "id,slug,status,title,modified,link,featured_media,categories",
        }
        rows, _ = request_json(f"{SITE_URL}/wp-json/wp/v2/posts?{urllib.parse.urlencode(params)}", auth)
        matches = []
        for row in rows:
            title = row.get("title") or {}
            title_text = title.get("raw") or title.get("rendered") or "" if isinstance(title, dict) else str(title)
            if row.get("slug") == SLUG or "酒蔵" in title_text or "西条" in title_text:
                matches.append(row)
        if matches:
            out[status] = matches
    return out


def inspect_media(auth: str) -> tuple[dict[str, list[dict[str, Any]]], int]:
    wanted = {stem.casefold() for stem in EXPECTED_STEMS}
    matches: dict[str, list[dict[str, Any]]] = {stem: [] for stem in EXPECTED_STEMS}
    scanned = 0
    for page in range(1, 11):
        params = {
            "context": "edit",
            "per_page": "100",
            "page": str(page),
            "orderby": "date",
            "order": "desc",
            "_fields": "id,date,slug,source_url,alt_text,caption,media_details",
        }
        try:
            rows, _ = request_json(f"{SITE_URL}/wp-json/wp/v2/media?{urllib.parse.urlencode(params)}", auth)
        except Exception as exc:
            if "400" in str(exc) and page > 1:
                break
            raise
        if not rows:
            break
        scanned += len(rows)
        for row in rows:
            stem = canonical_stem(row.get("source_url") or "")
            if stem in wanted:
                key = next(s for s in EXPECTED_STEMS if s.casefold() == stem)
                matches[key].append(row)
        if all(matches[s] for s in EXPECTED_STEMS):
            break
    return matches, scanned


def main() -> int:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")
    auth = auth_header(user, password)

    counts = public_counts(auth)
    posts = inspect_posts(auth)
    media, scanned = inspect_media(auth)

    report = {
        "mode": "GET_ONLY",
        "slug": SLUG,
        "public_counts": counts,
        "post_matches": posts,
        "media_scanned": scanned,
        "media_matches": media,
        "missing_stems": [s for s in EXPECTED_STEMS if not media[s]],
        "ambiguous_stems": {s: [r.get("id") for r in rows] for s, rows in media.items() if len(rows) > 1},
        "wordpress_write_count": 0,
        "publish_count": 0,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Saijo sakagura media inspection",
        "",
        "- mode: **GET_ONLY**",
        f"- slug candidate: `{SLUG}`",
        f"- published_total: **{counts['published_total']}**",
        f"- media_scanned: **{scanned}**",
        f"- missing_stems: **{len(report['missing_stems'])}**",
        f"- ambiguous_stems: **{len(report['ambiguous_stems'])}**",
        "- wordpress_write_count: **0**",
        "- publish_count: **0**",
        "",
        "## Media",
    ]
    for stem in EXPECTED_STEMS:
        rows = media[stem]
        if not rows:
            lines.append(f"- `{stem}`: MISSING")
        else:
            for row in rows:
                lines.append(f"- `{stem}`: media **{row.get('id')}** — {row.get('source_url')}")
    if posts:
        lines += ["", "## Related post matches"]
        for status, rows in posts.items():
            for row in rows:
                title = row.get("title") or {}
                title_text = title.get("raw") or title.get("rendered") or "" if isinstance(title, dict) else str(title)
                lines.append(f"- {status}: post **{row.get('id')}** `{row.get('slug')}` — {title_text}")
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
