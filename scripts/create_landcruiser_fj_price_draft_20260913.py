#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

SITE = "https://tsurikue.com"
UA = "tsurikue-create-landcruiser-fj-price-20260913/1.0"
TITLE = "ランドクルーザーFJの乗り出し価格はいくら？実際の支払総額は550万516円"
SLUG = "landcruiser-fj-price"
CONTENT_PATH = Path("packages/landcruiser-fj-price/content.html")
EXCERPT = "ランドクルーザーFJ VXは車両価格450万100円。実際に購入したFJはオプション・用品・諸費用を含めて現金販売時の支払総額550万516円でした。購入時の価格明細メモをもとに、約100万円増えた内訳や支払いプランを紹介します。"
FEATURED = 3757
CATEGORY_SLUGS = ["car"]
EXPECTED_MEDIA = {
    3757: "/wp-content/uploads/2026/09/img_8130.jpg",
    3756: "/wp-content/uploads/2026/09/img_8129.jpg",
    3765: "/wp-content/uploads/2026/09/img_8318.jpg",
}
BODY_MEDIA = {3756, 3765}
SOURCE_MARKER = "<!-- tsurikue-original:v1 slug=landcruiser-fj-price source=user-provided-20260913 -->"
EDITORIAL_MARKER = "<!-- tsurikue-editorial:v1 slug=landcruiser-fj-price -->"
EXPECTED_H2 = [
    "ランドクルーザーFJの新車価格は450万100円",
    "実際の購入メモでは支払総額550万516円",
    "約100万円増えた大きな理由はオプションと付属品",
    "支払いプランのメモは頭金200万円・60回払い",
    "550万円のFJに乗ってみてどうだった？",
    "FJを買うならカタログ価格だけで予算を決めない",
]
REQUIRED_SHORTCODE = '[blog_parts id="2184"]'

TOKEN = re.compile(r"<!--\s+/?wp:[\s\S]*?-->")
OPEN = re.compile(r"<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->")
CLOSE = re.compile(r"<!--\s+/wp:([\w\-/]+)\s+-->")
IMAGE_ID = re.compile(r"wp-image-(\d+)")
H2_RE = re.compile(r"<h2[^>]*>(.*?)</h2>", re.I | re.S)


def auth():
    user = os.environ.get("TSURIKUE_WP_USER")
    pw = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not pw:
        raise SystemExit("BLOCKED_MISSING_SECRETS")
    return "Basic " + base64.b64encode(f"{user}:{pw}".encode()).decode()


def req(url, method="GET", payload=None, timeout=60):
    headers = {
        "Authorization": auth(),
        "Accept": "application/json",
        "User-Agent": UA,
    }
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode()
        headers["Content-Type"] = "application/json; charset=utf-8"

    last = None
    for n in range(3):
        try:
            r = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(r, timeout=timeout) as resp:
                raw = resp.read().decode()
                return (json.loads(raw) if raw else None), dict(resp.headers)
        except Exception as exc:
            last = exc
            if n < 2:
                time.sleep(3 * (n + 1))
    raise last


def raw(row, key):
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)


def gutenberg_problems(text):
    stack = []
    for match in TOKEN.finditer(text):
        token = match.group(0)
        opened = OPEN.fullmatch(token)
        closed = CLOSE.fullmatch(token)
        if opened:
            if not opened.group(2):
                stack.append(opened.group(1))
        elif closed:
            if not stack or stack[-1] != closed.group(1):
                return 1
            stack.pop()
    return len(stack)


def count_published(endpoint):
    q = urllib.parse.urlencode({"status": "publish", "per_page": 1, "_fields": "id"})
    _, headers = req(f"{SITE}/wp-json/wp/v2/{endpoint}?{q}", timeout=45)
    return int(headers.get("X-WP-Total", "0"))


def public_counts():
    posts = count_published("posts")
    pages = count_published("pages")
    return {"published_posts": posts, "published_pages": pages, "published_total": posts + pages}


def resolve_term(endpoint, slug):
    q = urllib.parse.urlencode({
        "context": "edit",
        "slug": slug,
        "per_page": 10,
        "_fields": "id,slug,name",
    })
    rows, _ = req(f"{SITE}/wp-json/wp/v2/{endpoint}?{q}", timeout=45)
    if len(rows) != 1 or rows[0].get("slug") != slug:
        raise RuntimeError(f"term resolution failed endpoint={endpoint} slug={slug}: {rows}")
    return int(rows[0]["id"])


def validate_media():
    for mid, expected_path in EXPECTED_MEDIA.items():
        q = urllib.parse.urlencode({"context": "edit", "_fields": "id,status,source_url"})
        row, _ = req(f"{SITE}/wp-json/wp/v2/media/{mid}?{q}", timeout=45)
        actual_path = urllib.parse.unquote(urllib.parse.urlparse(row.get("source_url") or "").path)
        if int(row.get("id") or 0) != mid or actual_path.casefold() != expected_path.casefold():
            raise RuntimeError(f"media mismatch id={mid}: {actual_path} != {expected_path}")


def find_existing():
    q = urllib.parse.urlencode({
        "context": "edit",
        "slug": SLUG,
        "status": "any",
        "per_page": 10,
        "_fields": "id,slug,status,title,content,featured_media,categories,excerpt",
    })
    rows, _ = req(f"{SITE}/wp-json/wp/v2/posts?{q}", timeout=45)
    return rows


def validate_content(content):
    if "<h1" in content.casefold() or '"level":1' in content:
        raise RuntimeError("body h1 is forbidden")
    if gutenberg_problems(content) != 0:
        raise RuntimeError("Gutenberg block balance failed")
    if content.count(SOURCE_MARKER) != 1:
        raise RuntimeError("source marker count mismatch")
    if content.count(EDITORIAL_MARKER) != 1:
        raise RuntimeError("editorial marker count mismatch")

    for banned in ["普通に", "🤣", "😏", "🔥"]:
        if banned in content:
            raise RuntimeError("banned wording/emoji present: " + banned)
    if content.count("かなり") > 1 or content.count("めちゃくちゃ") > 1:
        raise RuntimeError("intensifier overuse")

    h2 = [
        re.sub(r"<[^>]+>", "", item).strip()
        for item in H2_RE.findall(content)
    ]
    if h2 != EXPECTED_H2:
        raise RuntimeError("H2 structure mismatch: " + repr(h2))

    used = {int(x) for x in IMAGE_ID.findall(content)}
    if used != BODY_MEDIA:
        raise RuntimeError(f"body media mismatch used={sorted(used)} expected={sorted(BODY_MEDIA)}")

    if content.count(REQUIRED_SHORTCODE) != 1:
        raise RuntimeError("CTN shortcode count mismatch")

    required_phrases = [
        "現金販売時の支払総額が550万516円",
        "100万416円",
        "この書面はメモであり見積ではありません",
        "購入時の価格明細メモ",
        "付属品だけで<strong>74万171円</strong>",
        "頭金200万円・60回払い",
        "最終回支払額",
        "実質年率",
        "https://toyota.jp/landcruiserfj/",
        "https://toyota.jp/request/webcatalog/landcruiserfj/",
    ]
    for phrase in required_phrases:
        if phrase not in content:
            raise RuntimeError("missing required phrase: " + phrase)


def normalized_excerpt(value):
    return re.sub(r"<[^>]+>", "", html.unescape(value or "")).strip()


def same_draft(row, content, category_ids):
    return (
        row.get("status") == "draft"
        and html.unescape(raw(row, "title")) == TITLE
        and raw(row, "content").strip() == content.strip()
        and int(row.get("featured_media") or 0) == FEATURED
        and sorted(row.get("categories") or []) == sorted(category_ids)
        and normalized_excerpt(raw(row, "excerpt")) == EXCERPT
    )


def main():
    content = CONTENT_PATH.read_text(encoding="utf-8").strip() + "\n"
    validate_content(content)
    validate_media()
    categories = [resolve_term("categories", slug) for slug in CATEGORY_SLUGS]

    before = public_counts()
    existing = find_existing()
    action = "CREATE"

    if existing:
        if len(existing) != 1:
            raise RuntimeError(f"multiple slug collisions: {len(existing)}")
        row = existing[0]
        if not same_draft(row, content, categories):
            raise RuntimeError(
                f"slug already exists but differs: id={row.get('id')} status={row.get('status')}"
            )
        created = row
        action = "ALREADY_UP_TO_DATE"
    else:
        payload = {
            "title": TITLE,
            "slug": SLUG,
            "content": content,
            "status": "draft",
            "featured_media": FEATURED,
            "categories": categories,
            "excerpt": EXCERPT,
        }
        created, _ = req(
            f"{SITE}/wp-json/wp/v2/posts",
            method="POST",
            payload=payload,
            timeout=90,
        )
        if created.get("status") != "draft" or created.get("slug") != SLUG:
            raise RuntimeError("create response validation failed")

    post_id = int(created["id"])
    q = urllib.parse.urlencode({
        "context": "edit",
        "_fields": "id,slug,status,link,title,content,featured_media,categories,excerpt",
    })
    after, _ = req(f"{SITE}/wp-json/wp/v2/posts/{post_id}?{q}", timeout=60)
    after_counts = public_counts()

    if before != after_counts:
        raise RuntimeError(f"published counts changed: {before} -> {after_counts}")
    if after.get("id") != post_id or after.get("slug") != SLUG or after.get("status") != "draft":
        raise RuntimeError("post state mismatch")
    if html.unescape(raw(after, "title")) != TITLE:
        raise RuntimeError("title mismatch")
    if raw(after, "content").strip() != content.strip():
        raise RuntimeError("content mismatch")
    if int(after.get("featured_media") or 0) != FEATURED:
        raise RuntimeError("featured media mismatch")
    if sorted(after.get("categories") or []) != sorted(categories):
        raise RuntimeError("category mismatch")
    if normalized_excerpt(raw(after, "excerpt")) != EXCERPT:
        raise RuntimeError("excerpt mismatch")

    report = {
        "result": "SUCCESS",
        "action": action,
        "post_id": post_id,
        "slug": SLUG,
        "status": "draft",
        "title": TITLE,
        "featured_media": FEATURED,
        "categories": categories,
        "media_checked": len(EXPECTED_MEDIA),
        "body_images": len(BODY_MEDIA),
        "gutenberg_problems": 0,
        "published_before": before,
        "published_after": after_counts,
        "content_sha256": hashlib.sha256(raw(after, "content").encode()).hexdigest(),
        "wordpress_write_count": 1 if action == "CREATE" else 0,
        "publish_count": 0,
        "media_upload_count": 0,
    }

    print("# Land Cruiser FJ price draft creation")
    for key, value in report.items():
        print(f"- {key}: **{value}**")


if __name__ == "__main__":
    main()
