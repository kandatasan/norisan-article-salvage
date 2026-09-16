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
from pathlib import Path

SITE = "https://tsurikue.com"
UA = "tsurikue-fj-dedup-persona-20260917/1.0"
POST_ID = 3816
SLUG = "landcruiser-fj-cheap"
STATUS = "publish"
TITLE = "ランドクルーザーFJを安く買う方法｜欲しいオプションを諦めず負担を減らす5つのコツ"
EXPECTED_SHA256 = "f0bb7e825ee3de9fb946fb36102c7fc6e0918b372707fb796e4f1b64fd60fbe9"
CONTENT_PATH = Path("packages/landcruiser-fj-cheap/content.html")
INSWEB_PART_ID = 3815
CTN_PART_ID = 3788
REPORT = Path("reports/fj-dedup-persona-20260917")


def sha256(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def auth_header() -> str:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise RuntimeError("missing WordPress secrets")
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()


AUTH = None


def request(method: str, path: str, payload=None):
    global AUTH
    if AUTH is None:
        AUTH = auth_header()
    headers = {"Authorization": AUTH, "Accept": "application/json", "User-Agent": UA}
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


def get_post() -> dict:
    q = urllib.parse.urlencode({
        "context": "edit",
        "_fields": "id,slug,status,title,content,author,featured_media,categories",
    })
    row, _ = request("GET", f"/wp-json/wp/v2/posts/{POST_ID}?{q}")
    return row


def identity(row: dict) -> dict:
    return {
        "id": int(row.get("id") or 0),
        "slug": row.get("slug"),
        "status": row.get("status"),
        "title": html.unescape(raw(row, "title")),
        "author": int(row.get("author") or 0),
        "featured_media": int(row.get("featured_media") or 0),
        "categories": sorted(row.get("categories") or []),
    }


def validate_identity(row: dict) -> dict:
    ident = identity(row)
    if ident["id"] != POST_ID:
        raise RuntimeError(f"id mismatch: {ident['id']}")
    if ident["slug"] != SLUG:
        raise RuntimeError(f"slug mismatch: {ident['slug']}")
    if ident["status"] != STATUS:
        raise RuntimeError(f"status mismatch: {ident['status']}")
    if ident["title"] != TITLE:
        raise RuntimeError(f"title mismatch: {ident['title']}")
    return ident


def public_count(endpoint: str) -> int:
    q = urllib.parse.urlencode({"status": "publish", "per_page": 1, "_fields": "id"})
    _, headers = request("GET", f"/wp-json/wp/v2/{endpoint}?{q}")
    for key, value in headers.items():
        if key.lower() == "x-wp-total":
            return int(value)
    raise RuntimeError(f"missing X-WP-Total for {endpoint}")


def public_counts() -> dict:
    return {"posts": public_count("posts"), "pages": public_count("pages")}


def build_target() -> str:
    template = CONTENT_PATH.read_text(encoding="utf-8").strip() + "\n"
    if template.count("{{INSWEB_3104_SHORTCODE}}") != 1:
        raise RuntimeError("InsWeb placeholder mismatch")
    target = template.replace(
        "{{INSWEB_3104_SHORTCODE}}",
        f'[blog_parts id="{INSWEB_PART_ID}"]',
    )
    required = [
        f'[blog_parts id="{CTN_PART_ID}"]',
        f'[blog_parts id="{INSWEB_PART_ID}"]',
        'このサイトでUXの記事を書いてる「のりさん」の実例',
        "のりさんがレクサスUXを売ったとき",
        "まとめ｜僕ならこの順番で見る",
        "欲しいFJを諦める前に",
    ]
    for phrase in required:
        if phrase not in target:
            raise RuntimeError(f"target phrase missing: {phrase}")
    if target.count(f'[blog_parts id="{CTN_PART_ID}"]') != 1:
        raise RuntimeError("CTN shortcode count mismatch")
    if target.count(f'[blog_parts id="{INSWEB_PART_ID}"]') != 1:
        raise RuntimeError("InsWeb shortcode count mismatch")
    return target


def write_report(data: dict) -> None:
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / "result.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        "# FJ dedup/persona update 2026-09-17",
        "",
        f"- result: **{data['result']}**",
        f"- action: **{data['action']}**",
        f"- post: **{POST_ID} / {SLUG}**",
        f"- status: **{data['status']}**",
        f"- before sha256: **{data['before_sha256']}**",
        f"- final sha256: **{data['final_sha256']}**",
        f"- public posts before/after: **{data['public_before']['posts']} / {data['public_after']['posts']}**",
        f"- public pages before/after: **{data['public_before']['pages']} / {data['public_after']['pages']}**",
    ]
    (REPORT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def main() -> None:
    target = build_target()
    target_sha = sha256(target)

    before_counts = public_counts()
    row = get_post()
    before_ident = validate_identity(row)
    current = raw(row, "content")
    current_sha = sha256(current)

    if current_sha == target_sha:
        action = "REUSE_EXACT"
    else:
        if current_sha != EXPECTED_SHA256:
            raise RuntimeError(
                f"unexpected current content sha: {current_sha}; expected {EXPECTED_SHA256}"
            )
        request("POST", f"/wp-json/wp/v2/posts/{POST_ID}", {"content": target})
        action = "UPDATE_CONTENT_ONLY"

    final = get_post()
    final_ident = validate_identity(final)
    final_content = raw(final, "content")
    final_sha = sha256(final_content)

    if final_ident != before_ident:
        raise RuntimeError(f"identity metadata changed: {before_ident} -> {final_ident}")
    if final_content != target:
        raise RuntimeError("final content does not match reviewed target")
    if final_content.count(f'[blog_parts id="{CTN_PART_ID}"]') != 1:
        raise RuntimeError("final CTN shortcode count mismatch")
    if final_content.count(f'[blog_parts id="{INSWEB_PART_ID}"]') != 1:
        raise RuntimeError("final InsWeb shortcode count mismatch")

    after_counts = public_counts()
    if after_counts != before_counts:
        raise RuntimeError(f"public counts changed: {before_counts} -> {after_counts}")

    data = {
        "result": "APPLIED_OK",
        "action": action,
        "status": final_ident["status"],
        "before_sha256": current_sha,
        "final_sha256": final_sha,
        "public_before": before_counts,
        "public_after": after_counts,
    }
    write_report(data)


if __name__ == "__main__":
    main()
