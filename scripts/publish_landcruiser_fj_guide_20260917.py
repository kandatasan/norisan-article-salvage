#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request

SITE = "https://tsurikue.com"
UA = "tsurikue-publish-fj-guide-20260917/1.0"
POST_ID = 3827
SLUG = "landcruiser-fj-guide"
TITLE = "ランドクルーザーFJとは？価格・サイズ・燃費・特徴を実車オーナーがまとめて解説"
EXPECTED_CONTENT_SHA256 = "f029c5b3b16d9c71d3dd79c08dfbecd53c59f9378da0fe95756d9c50feff178c"


def auth_header() -> str:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise RuntimeError("missing WordPress secrets")
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()


def request(method: str, path: str, payload=None):
    headers = {"Authorization": auth_header(), "Accept": "application/json", "User-Agent": UA}
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


def get_post() -> dict:
    q = urllib.parse.urlencode({
        "context": "edit",
        "_fields": "id,slug,status,title,content,author,featured_media,categories",
    })
    row, _ = request("GET", f"/wp-json/wp/v2/posts/{POST_ID}?{q}")
    return row


def public_count(endpoint: str) -> int:
    q = urllib.parse.urlencode({"status": "publish", "per_page": 1, "_fields": "id"})
    _, headers = request("GET", f"/wp-json/wp/v2/{endpoint}?{q}")
    for key, value in headers.items():
        if key.lower() == "x-wp-total":
            return int(value)
    raise RuntimeError(f"missing X-WP-Total for {endpoint}")


def identity(row: dict) -> dict:
    return {
        "id": int(row.get("id") or 0),
        "slug": row.get("slug"),
        "title": html.unescape(raw(row, "title")),
        "author": int(row.get("author") or 0),
        "featured_media": int(row.get("featured_media") or 0),
        "categories": sorted(row.get("categories") or []),
    }


def validate(row: dict, expected_status: str) -> dict:
    ident = identity(row)
    if ident["id"] != POST_ID:
        raise RuntimeError(f"id mismatch: {ident['id']}")
    if ident["slug"] != SLUG:
        raise RuntimeError(f"slug mismatch: {ident['slug']}")
    if ident["title"] != TITLE:
        raise RuntimeError(f"title mismatch: {ident['title']}")
    if row.get("status") != expected_status:
        raise RuntimeError(f"status mismatch: {row.get('status')} != {expected_status}")
    content_sha = sha256(raw(row, "content"))
    if content_sha != EXPECTED_CONTENT_SHA256:
        raise RuntimeError(f"content sha mismatch: {content_sha}")
    return ident


def main() -> None:
    posts_before = public_count("posts")
    pages_before = public_count("pages")
    before = get_post()

    if before.get("status") == "publish":
        ident_before = validate(before, "publish")
        action = "ALREADY_PUBLISHED"
    else:
        ident_before = validate(before, "draft")
        request("POST", f"/wp-json/wp/v2/posts/{POST_ID}", {"status": "publish"})
        action = "PUBLISH"

    after = get_post()
    ident_after = validate(after, "publish")
    if ident_after != ident_before:
        raise RuntimeError(f"identity changed: {ident_before} -> {ident_after}")

    posts_after = public_count("posts")
    pages_after = public_count("pages")

    if action == "PUBLISH" and posts_after != posts_before + 1:
        raise RuntimeError(f"published post count mismatch: {posts_before} -> {posts_after}")
    if action == "ALREADY_PUBLISHED" and posts_after != posts_before:
        raise RuntimeError(f"published post count changed unexpectedly: {posts_before} -> {posts_after}")
    if pages_after != pages_before:
        raise RuntimeError(f"published page count changed: {pages_before} -> {pages_after}")

    print("# FJ guide publish 2026-09-17")
    print("- result: **SUCCESS**")
    print(f"- action: **{action}**")
    print(f"- post_id: **{POST_ID}**")
    print("- status: **publish**")
    print(f"- slug: **{SLUG}**")
    print(f"- published posts before/after: **{posts_before} / {posts_after}**")
    print(f"- published pages before/after: **{pages_before} / {pages_after}**")
    print(f"- content sha256: **{EXPECTED_CONTENT_SHA256}**")


if __name__ == "__main__":
    main()
