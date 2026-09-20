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
UA = "tsurikue-update-lexus-goodbuy-benefit-20260920/1.0"
POST_ID = 3835
SLUG = "goodbuy"
STATUS = "draft"
TITLE = "レクサスを安く買う方法5選｜値引きなしでも購入負担を減らすコツ"
EXPECTED_OLD_SHA = "ac0ef1a5f09adcd76bd1b5df2adeee18eb978be01799f7e0201bfc8ee307dcd6"
CONTENT_PATH = Path("packages/lexus-goodbuy/content.html")

TOKEN = re.compile(r"<!--\s+/?wp:[\s\S]*?-->")
OPEN = re.compile(r"<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->")
CLOSE = re.compile(r"<!--\s+/wp:([\w\-/]+)\s+-->")


def auth_header():
    u = os.environ.get("TSURIKUE_WP_USER")
    p = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not u or not p:
        raise RuntimeError("missing WordPress secrets")
    return "Basic " + base64.b64encode(f"{u}:{p}".encode()).decode()


def request(method, path, payload=None):
    headers = {"Authorization": auth_header(), "Accept": "application/json", "User-Agent": UA}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    last = None
    for n in range(8):
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
        if n < 7:
            time.sleep(min(3 + n, 10))
    raise last


def raw(row, key):
    v = row.get(key) or {}
    return (v.get("raw") or v.get("rendered") or "") if isinstance(v, dict) else str(v)


def sha256(text):
    return hashlib.sha256((text or "").encode()).hexdigest()


def gutenberg_ok(text):
    stack = []
    for m in TOKEN.finditer(text):
        tok = m.group(0)
        op = OPEN.fullmatch(tok)
        cl = CLOSE.fullmatch(tok)
        if op and not op.group(2):
            stack.append(op.group(1))
        elif cl:
            if not stack or stack[-1] != cl.group(1):
                return False
            stack.pop()
    return not stack


def public_count(endpoint):
    q = urllib.parse.urlencode({"status":"publish","per_page":1,"_fields":"id"})
    _, headers = request("GET", f"/wp-json/wp/v2/{endpoint}?{q}")
    for k,v in headers.items():
        if k.lower() == "x-wp-total":
            return int(v)
    raise RuntimeError(f"missing X-WP-Total {endpoint}")


def get_post():
    q = urllib.parse.urlencode({
        "context":"edit",
        "_fields":"id,slug,status,title,content,author,featured_media,categories,excerpt"
    })
    row,_ = request("GET", f"/wp-json/wp/v2/posts/{POST_ID}?{q}")
    return row


def identity(row):
    return {
        "id": int(row.get("id") or 0),
        "slug": row.get("slug"),
        "status": row.get("status"),
        "title": html.unescape(raw(row, "title")),
        "author": int(row.get("author") or 0),
        "featured_media": int(row.get("featured_media") or 0),
        "categories": sorted(row.get("categories") or []),
        "excerpt": raw(row, "excerpt"),
    }


def main():
    target = CONTENT_PATH.read_text(encoding="utf-8").strip() + "\n"
    if "<h1" in target.casefold() or not gutenberg_ok(target):
        raise RuntimeError("target content structure invalid")
    required = [
        "納車日に「これが欲しかった」",
        "「これ、残せるじゃん」",
        "レクサスで出かける旅行やメンテナンス、次のタイヤ代",
        "「安い方にした」じゃなく「これが欲しかった」",
        "※クラウドローンは未利用。サービス内容は公式サイトで確認しています。",
        "https://crowdloan.jp/",
        '[blog_parts id="2184"]',
    ]
    for phrase in required:
        if phrase not in target:
            raise RuntimeError(f"required benefit phrase missing: {phrase}")
    if "全国すべてのレクサス販売店は絶対に値引きしない" in target:
        raise RuntimeError("defensive intro disclaimer still present")

    before_posts = public_count("posts")
    before_pages = public_count("pages")
    row = get_post()
    old_ident = identity(row)

    if old_ident["id"] != POST_ID or old_ident["slug"] != SLUG or old_ident["status"] != STATUS:
        raise RuntimeError(f"identity mismatch: {old_ident}")
    if old_ident["title"] != TITLE:
        raise RuntimeError(f"title mismatch: {old_ident['title']}")

    current = raw(row, "content")
    current_sha = sha256(current)
    target_sha = sha256(target)

    if current_sha == target_sha:
        action = "ALREADY_APPLIED"
    else:
        if current_sha != EXPECTED_OLD_SHA:
            raise RuntimeError(f"unexpected current sha: {current_sha}")
        request("POST", f"/wp-json/wp/v2/posts/{POST_ID}", {"content": target})
        action = "UPDATE_CONTENT_ONLY"

    check = get_post()
    if identity(check) != old_ident:
        raise RuntimeError("post identity/metadata changed")
    final_content = raw(check, "content")
    if sha256(final_content) != target_sha or final_content.strip() != target.strip():
        raise RuntimeError("final content mismatch")

    after_posts = public_count("posts")
    after_pages = public_count("pages")
    if (before_posts, before_pages) != (after_posts, after_pages):
        raise RuntimeError(
            f"public counts changed: posts {before_posts}->{after_posts}, pages {before_pages}->{after_pages}"
        )

    print("# Lexus goodbuy benefit polish 2026-09-20")
    print("- result: **SUCCESS**")
    print(f"- action: **{action}**")
    print(f"- post_id: **{POST_ID}**")
    print(f"- status: **{STATUS}**")
    print(f"- published posts before/after: **{before_posts} / {after_posts}**")
    print(f"- published pages before/after: **{before_pages} / {after_pages}**")
    print(f"- final content sha256: **{target_sha}**")
    print("- benefit direction: **欲しい装備を残す → 納車日・所有後の楽しみへ**")
    print("- defensive wording: **compressed**")


if __name__ == "__main__":
    main()
