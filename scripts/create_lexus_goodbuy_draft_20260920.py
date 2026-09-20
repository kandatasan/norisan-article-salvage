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
UA = "tsurikue-create-lexus-goodbuy-20260920/1.0"
TITLE = "レクサスを安く買う方法5選｜値引きなしでも購入負担を減らすコツ"
SLUG = "goodbuy"
EXCERPT = "レクサスを安く買う方法を、UXを615万6,510円・値引き0円で購入した実体験から解説。下取り50万円→75万円の25万円差、ローン金利、自動車保険、オプション、中古・CPOまで、値引き以外で購入負担を減らす5つの方法をまとめます。"
CONTENT_PATH = Path("packages/lexus-goodbuy/content.html")
SOURCE_POST_ID = 2962
SOURCE_SLUG = "lexus-ux-discount"
REPORT = Path("reports/lexus-goodbuy-create-20260920")

TOKEN = re.compile(r"<!--\s+/?wp:[\s\S]*?-->")
OPEN = re.compile(r"<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->")
CLOSE = re.compile(r"<!--\s+/wp:([\w\-/]+)\s+-->")


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


def gutenberg_ok(text: str) -> bool:
    stack = []
    for match in TOKEN.finditer(text):
        token = match.group(0)
        opened = OPEN.fullmatch(token)
        closed = CLOSE.fullmatch(token)
        if opened and not opened.group(2):
            stack.append(opened.group(1))
        elif closed:
            if not stack or stack[-1] != closed.group(1):
                return False
            stack.pop()
    return not stack


def validate_content(content: str) -> None:
    if "<h1" in content.casefold() or '"level":1' in content:
        raise RuntimeError("body h1 forbidden")
    if not gutenberg_ok(content):
        raise RuntimeError("Gutenberg block mismatch")
    banned = ["普通に", "🔥", "🤣", "😁", "😏", "😂", "😊"]
    for word in banned:
        if word in content:
            raise RuntimeError(f"banned wording/emoji: {word}")

    required = [
        "6,156,510円",
        "3人もレクサスの新車購入につないだ友人",
        "50万円",
        "75万円",
        "25万円差",
        "350万円",
        "500万円前後",
        "427万円",
        '[blog_parts id="2184"]',
        "https://crowdloan.jp/",
        "40行以上",
        "私はクラウドローンで実際に借り入れをした利用者ではありません",
        "3Z0TXU+5GH2EQ+2PS+15OZHU",
        '[blog_parts id="2843"]',
        '[blog_parts id="2890"]',
        "https://tsurikue.com/lexus-ux-discount/",
        "https://tsurikue.com/car-sell-high/",
        "https://tsurikue.com/ux-resale/",
        "https://tsurikue.com/ux-mitsumori/",
        "https://tsurikue.com/lexus-ux-used/",
    ]
    for phrase in required:
        if phrase not in content:
            raise RuntimeError(f"required phrase missing: {phrase}")

    if "ac.crowdloan.jp" in content:
        raise RuntimeError("CloudLoan affiliate URL must not be used before approval")
    if content.count("https://crowdloan.jp/") != 1:
        raise RuntimeError("CloudLoan normal URL must appear exactly once")


def public_count(endpoint: str) -> int:
    query = urllib.parse.urlencode({"status": "publish", "per_page": 1, "_fields": "id"})
    _, headers = request("GET", f"/wp-json/wp/v2/{endpoint}?{query}")
    for key, value in headers.items():
        if key.lower() == "x-wp-total":
            return int(value)
    raise RuntimeError(f"missing X-WP-Total for {endpoint}")


def public_counts() -> dict:
    return {"posts": public_count("posts"), "pages": public_count("pages")}


def source_metadata() -> dict:
    query = urllib.parse.urlencode({
        "context": "edit",
        "_fields": "id,slug,status,author,featured_media,categories",
    })
    row, _ = request("GET", f"/wp-json/wp/v2/posts/{SOURCE_POST_ID}?{query}")
    if int(row.get("id") or 0) != SOURCE_POST_ID:
        raise RuntimeError("source post id mismatch")
    if row.get("slug") != SOURCE_SLUG or row.get("status") != "publish":
        raise RuntimeError(f"source post mismatch: {row.get('slug')} / {row.get('status')}")
    featured = int(row.get("featured_media") or 0)
    categories = sorted(row.get("categories") or [])
    author = int(row.get("author") or 0)
    if not author or not featured or not categories:
        raise RuntimeError("source metadata incomplete")
    return {
        "author": author,
        "featured_media": featured,
        "categories": categories,
    }


def find_post() -> list:
    query = urllib.parse.urlencode({
        "context": "edit",
        "slug": SLUG,
        "status": "any",
        "per_page": 10,
        "_fields": "id,slug,status,title,content,author,featured_media,categories,excerpt",
    })
    rows, _ = request("GET", f"/wp-json/wp/v2/posts?{query}")
    return rows


def norm_excerpt(value: str) -> str:
    return re.sub(r"<[^>]+>", "", html.unescape(value or "")).strip()


def write_report(data: dict) -> None:
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / "result.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        "# Lexus goodbuy revival 2026-09-20",
        "",
        f"- result: **{data['result']}**",
        f"- article_action: **{data['action']}**",
        f"- post_id: **{data['post_id']}**",
        f"- status: **{data['status']}**",
        f"- slug: **{SLUG}**",
        f"- published posts before/after: **{data['before']['posts']} / {data['after']['posts']}**",
        f"- published pages before/after: **{data['before']['pages']} / {data['after']['pages']}**",
        f"- content sha256: **{data['sha']}**",
        "- CloudLoan: **normal official link only**",
        "- legacy friend referrals: **owner-corrected to 3**",
    ]
    (REPORT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def main() -> None:
    content = CONTENT_PATH.read_text(encoding="utf-8").strip() + "\n"
    validate_content(content)

    before = public_counts()
    metadata = source_metadata()
    rows = find_post()

    if rows:
        if len(rows) != 1:
            raise RuntimeError("slug collision")
        row = rows[0]
        if row.get("status") != "draft":
            raise RuntimeError(f"existing goodbuy slug is not draft: {row.get('status')}")
        if html.unescape(raw(row, "title")) != TITLE:
            raise RuntimeError("existing draft title differs")
        if raw(row, "content").strip() != content.strip():
            raise RuntimeError("existing draft content differs")
        post = row
        action = "REUSE_EXACT_DRAFT"
    else:
        payload = {
            "title": TITLE,
            "slug": SLUG,
            "content": content,
            "excerpt": EXCERPT,
            "status": "draft",
            "author": metadata["author"],
            "featured_media": metadata["featured_media"],
            "categories": metadata["categories"],
        }
        post, _ = request("POST", "/wp-json/wp/v2/posts", payload)
        action = "CREATE_DRAFT"

    post_id = int(post.get("id") or 0)
    query = urllib.parse.urlencode({
        "context": "edit",
        "_fields": "id,slug,status,title,content,author,featured_media,categories,excerpt",
    })
    check, _ = request("GET", f"/wp-json/wp/v2/posts/{post_id}?{query}")

    if int(check.get("id") or 0) != post_id:
        raise RuntimeError("final id mismatch")
    if check.get("slug") != SLUG or check.get("status") != "draft":
        raise RuntimeError("final identity/status mismatch")
    if html.unescape(raw(check, "title")) != TITLE:
        raise RuntimeError("final title mismatch")
    if raw(check, "content").strip() != content.strip():
        raise RuntimeError("final content mismatch")
    if norm_excerpt(raw(check, "excerpt")) != EXCERPT:
        raise RuntimeError("final excerpt mismatch")
    if int(check.get("author") or 0) != metadata["author"]:
        raise RuntimeError("final author mismatch")
    if int(check.get("featured_media") or 0) != metadata["featured_media"]:
        raise RuntimeError("final featured media mismatch")
    if sorted(check.get("categories") or []) != metadata["categories"]:
        raise RuntimeError("final category mismatch")

    after = public_counts()
    if after != before:
        raise RuntimeError(f"public counts changed: {before} -> {after}")

    write_report({
        "result": "SUCCESS",
        "action": action,
        "post_id": post_id,
        "status": "draft",
        "before": before,
        "after": after,
        "sha": sha256(raw(check, "content")),
    })


if __name__ == "__main__":
    main()
