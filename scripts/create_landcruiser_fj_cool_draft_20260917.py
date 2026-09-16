#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SITE = "https://tsurikue.com"
UA = "tsurikue-create-fj-cool-20260917/1.0"
TITLE = "ランドクルーザーFJはオシャレでカッコイイ！無骨なのにかわいいって反則じゃない？"
SLUG = "landcruiser-fj-cool"
EXCERPT = "ランドクルーザーFJは、四角く重厚感のある本格オフローダーなのに、なぜかオシャレでかわいい。ランクル250をギュッと詰めたようなデザイン、ラダーフレーム、Freedom & Joyの意味まで、FJを買った僕が好きな理由を語ります。"
CONTENT_PATH = Path("packages/landcruiser-fj-cool/content.html")
FEATURED = 3757
BODY_MEDIA = {3756: "/wp-content/uploads/2026/09/img_8129.jpg"}
FEATURED_PATH = "/wp-content/uploads/2026/09/img_8130.jpg"
CATEGORY_SLUGS = ["car", "landcruiser-fj"]
SOURCE_FJ_POST_ID = 3767
SOURCE_FJ_SLUG = "landcruiser-fj-price"
REPORT = Path("reports/landcruiser-fj-cool-create-20260917")

TOKEN = re.compile(r"<!--\s+/?wp:[\s\S]*?-->")
OPEN = re.compile(r"<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->")
CLOSE = re.compile(r"<!--\s+/wp:([\w\-/]+)\s+-->")
IMAGE_ID = re.compile(r"wp-image-(\d+)")
H2_RE = re.compile(r"<h2[^>]*>(.*?)</h2>", re.I | re.S)
EXPECTED_H2 = [
    "ランクル250をギュッと詰めたようなデザインがたまらない",
    "そもそもラダーフレームってなに？",
    "見た目はかわいい。でも中身は本格オフローダー",
    "FJの意味は「Freedom &amp; Joy」",
    "MODELLISTAを付けると、さらに僕好みになった",
    "問題は、見てると欲しくなること",
    "まとめ｜FJは無骨・オシャレ・かわいいを全部持ってる",
]


def auth_header() -> str:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise RuntimeError("missing WordPress secrets")
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()


def request(method: str, path: str, payload=None):
    headers = {
        "Authorization": auth_header(),
        "Accept": "application/json",
        "User-Agent": UA,
    }
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    last = None
    for attempt in range(8):
        req = urllib.request.Request(SITE + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                body = resp.read().decode("utf-8")
                return (json.loads(body) if body else None), dict(resp.headers.items())
        except urllib.error.HTTPError as exc:
            last = exc
            if 400 <= exc.code < 500 and exc.code not in {408, 429}:
                raise
        except (urllib.error.URLError, TimeoutError, socket.gaierror, OSError) as exc:
            last = exc
        if attempt < 7:
            time.sleep(min(3 + attempt, 10))
    raise last


def raw(row: dict, key: str) -> str:
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)


def sha256(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def gutenberg_problems(text: str) -> int:
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


def validate_content(content: str) -> None:
    if "<h1" in content.casefold() or '"level":1' in content:
        raise RuntimeError("body h1 forbidden")
    if gutenberg_problems(content) != 0:
        raise RuntimeError("Gutenberg block mismatch")
    if any(x in content for x in ["普通に", "🔥", "🤣", "😁", "😏", "😂", "😊"]):
        raise RuntimeError("banned wording/emoji present")
    if content.count("かなり") > 1 or content.count("めちゃくちゃ") > 1:
        raise RuntimeError("intensifier overuse")

    h2 = [re.sub(r"<[^>]+>", "", x).strip() for x in H2_RE.findall(content)]
    if h2 != EXPECTED_H2:
        raise RuntimeError(f"H2 mismatch: {h2}")

    used = {int(x) for x in IMAGE_ID.findall(content)}
    if used != set(BODY_MEDIA):
        raise RuntimeError(f"body media mismatch: {used}")

    required = [
        "SDガンダムの魅力",
        "サイコロをモチーフとしたアイコニックなデザイン",
        "ランクル250より270mm短く",
        "車体の下にハシゴ状の頑丈な骨組み",
        "見た目だけSUVじゃなく",
        "Freedom＆Joy",
        "支払総額550万516円",
        "https://tsurikue.com/landcruiser-fj-price/",
        "https://tsurikue.com/landcruiser-fj-cheap/",
        "ランドクルーザーFJを安く買う方法を見る",
        "https://global.toyota/jp/newsroom/toyota/44331089.html",
        "https://toyota.jp/landcruiserfj/performance/",
    ]
    for phrase in required:
        if phrase not in content:
            raise RuntimeError(f"required phrase missing: {phrase}")


def public_count(endpoint: str) -> int:
    q = urllib.parse.urlencode({"status": "publish", "per_page": 1, "_fields": "id"})
    _, headers = request("GET", f"/wp-json/wp/v2/{endpoint}?{q}")
    for key, value in headers.items():
        if key.lower() == "x-wp-total":
            return int(value)
    raise RuntimeError(f"missing X-WP-Total for {endpoint}")


def public_counts() -> dict:
    return {"posts": public_count("posts"), "pages": public_count("pages")}


def source_author() -> int:
    q = urllib.parse.urlencode({"context": "edit", "_fields": "id,slug,status,author"})
    row, _ = request("GET", f"/wp-json/wp/v2/posts/{SOURCE_FJ_POST_ID}?{q}")
    if int(row.get("id") or 0) != SOURCE_FJ_POST_ID or row.get("slug") != SOURCE_FJ_SLUG:
        raise RuntimeError("source FJ post identity mismatch")
    author = int(row.get("author") or 0)
    if author <= 0:
        raise RuntimeError("source FJ author missing")
    return author


def resolve_category(slug: str) -> int:
    q = urllib.parse.urlencode({
        "context": "edit",
        "slug": slug,
        "per_page": 10,
        "_fields": "id,slug,name",
    })
    rows, _ = request("GET", f"/wp-json/wp/v2/categories?{q}")
    if len(rows) != 1 or rows[0].get("slug") != slug:
        raise RuntimeError(f"category resolution failed for {slug}: {rows}")
    return int(rows[0]["id"])


def validate_media(media_id: int, expected_path: str) -> None:
    q = urllib.parse.urlencode({"context": "edit", "_fields": "id,status,source_url"})
    row, _ = request("GET", f"/wp-json/wp/v2/media/{media_id}?{q}")
    path = urllib.parse.unquote(urllib.parse.urlparse(row.get("source_url") or "").path)
    if int(row.get("id") or 0) != media_id or path.casefold() != expected_path.casefold():
        raise RuntimeError(f"media mismatch {media_id}: {path} != {expected_path}")


def find_post():
    q = urllib.parse.urlencode({
        "context": "edit",
        "slug": SLUG,
        "status": "any",
        "per_page": 10,
        "_fields": "id,slug,status,title,content,author,featured_media,categories,excerpt",
    })
    rows, _ = request("GET", f"/wp-json/wp/v2/posts?{q}")
    return rows


def normalized_excerpt(value: str) -> str:
    return re.sub(r"<[^>]+>", "", html.unescape(value or "")).strip()


def write_report(data: dict) -> None:
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / "result.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        "# Land Cruiser FJ cool article create 2026-09-17",
        "",
        f"- result: **{data['result']}**",
        f"- article_action: **{data['article_action']}**",
        f"- post_id: **{data['post_id']}**",
        f"- status: **{data['status']}**",
        f"- slug: **{data['slug']}**",
        f"- title: **{TITLE}**",
        f"- published posts before/after: **{data['public_before']['posts']} / {data['public_after']['posts']}**",
        f"- published pages before/after: **{data['public_before']['pages']} / {data['public_after']['pages']}**",
        f"- content sha256: **{data['content_sha256']}**",
    ]
    (REPORT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def main() -> None:
    content = CONTENT_PATH.read_text(encoding="utf-8").strip() + "\n"
    validate_content(content)

    before = public_counts()
    author = source_author()
    categories = [resolve_category(slug) for slug in CATEGORY_SLUGS]
    validate_media(FEATURED, FEATURED_PATH)
    for mid, expected in BODY_MEDIA.items():
        validate_media(mid, expected)

    rows = find_post()
    if rows:
        if len(rows) != 1:
            raise RuntimeError(f"slug collision: {len(rows)}")
        row = rows[0]
        if row.get("status") != "draft":
            raise RuntimeError(f"existing slug is not a draft: {row.get('status')}")
        if html.unescape(raw(row, "title")) != TITLE:
            raise RuntimeError("existing draft title mismatch")
        if raw(row, "content").strip() != content.strip():
            raise RuntimeError("existing draft content mismatch")
        if int(row.get("author") or 0) != author:
            raise RuntimeError("existing draft author mismatch")
        if int(row.get("featured_media") or 0) != FEATURED:
            raise RuntimeError("existing draft featured media mismatch")
        if sorted(row.get("categories") or []) != sorted(categories):
            raise RuntimeError("existing draft categories mismatch")
        post = row
        action = "REUSE_EXACT_DRAFT"
    else:
        post, _ = request("POST", "/wp-json/wp/v2/posts", {
            "title": TITLE,
            "slug": SLUG,
            "content": content,
            "excerpt": EXCERPT,
            "status": "draft",
            "author": author,
            "featured_media": FEATURED,
            "categories": categories,
        })
        action = "CREATE_DRAFT"

    post_id = int(post.get("id") or 0)
    if post_id <= 0:
        raise RuntimeError("invalid post ID")

    q = urllib.parse.urlencode({
        "context": "edit",
        "_fields": "id,slug,status,title,content,author,featured_media,categories,excerpt",
    })
    check, _ = request("GET", f"/wp-json/wp/v2/posts/{post_id}?{q}")

    if check.get("slug") != SLUG or check.get("status") != "draft":
        raise RuntimeError("final post identity/status mismatch")
    if html.unescape(raw(check, "title")) != TITLE:
        raise RuntimeError("final title mismatch")
    if raw(check, "content").strip() != content.strip():
        raise RuntimeError("final content mismatch")
    if normalized_excerpt(raw(check, "excerpt")) != EXCERPT:
        raise RuntimeError("final excerpt mismatch")
    if int(check.get("author") or 0) != author:
        raise RuntimeError("final author mismatch")
    if int(check.get("featured_media") or 0) != FEATURED:
        raise RuntimeError("final featured media mismatch")
    if sorted(check.get("categories") or []) != sorted(categories):
        raise RuntimeError("final categories mismatch")

    after = public_counts()
    if after != before:
        raise RuntimeError(f"public counts changed: {before} -> {after}")

    write_report({
        "result": "SUCCESS",
        "article_action": action,
        "post_id": post_id,
        "status": check.get("status"),
        "slug": check.get("slug"),
        "public_before": before,
        "public_after": after,
        "content_sha256": sha256(raw(check, "content")),
    })


if __name__ == "__main__":
    main()
