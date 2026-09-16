#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

SITE = "https://tsurikue.com"
UA = "tsurikue-apply-car-sell-high-revenue-20260916/1.0"
REPORT = Path("reports/car-sell-high-revenue-20260916")
CONTENT_FILE = Path("review/published/car-sell-high/content.html")

POST_ID = 3614
SLUG = "car-sell-high"
STATUS = "publish"
TITLE = "車を楽に高く売る方法は？一括査定とディーラー査定を体験談つきで解説"
EXPECTED_CURRENT_SHA256 = "f2e3da17db803d62ad06b09ce1f0ae248597e2d73976bb981ee53d8530532b09"

def sha256(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()

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
    headers = {
        "Authorization": AUTH,
        "Accept": "application/json",
        "User-Agent": UA,
    }
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(SITE + path, data=data, headers=headers, method=method)
    last = None
    for n in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body) if body else None, dict(resp.headers.items())
        except Exception as exc:
            last = exc
            if n < 2:
                time.sleep(2 * (n + 1))
    raise last

def raw_field(row: dict, key: str) -> str:
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)

def public_count(endpoint: str) -> int:
    q = urllib.parse.urlencode({"status": "publish", "per_page": 1, "_fields": "id"})
    _, headers = request("GET", f"/wp-json/wp/v2/{endpoint}?{q}")
    for k, v in headers.items():
        if k.lower() == "x-wp-total":
            return int(v)
    raise RuntimeError(f"X-WP-Total missing for {endpoint}")

def public_counts():
    return {"posts": public_count("posts"), "pages": public_count("pages")}

def get_post() -> dict:
    q = urllib.parse.urlencode({
        "context": "edit",
        "_fields": "id,slug,status,title,content,author,modified,featured_media,categories,excerpt",
    })
    row, _ = request("GET", f"/wp-json/wp/v2/posts/{POST_ID}?{q}")
    return row

def identity_snapshot(row: dict) -> dict:
    return {
        "id": int(row.get("id") or 0),
        "slug": row.get("slug"),
        "status": row.get("status"),
        "title": html.unescape(raw_field(row, "title")),
        "author": int(row.get("author") or 0),
        "featured_media": int(row.get("featured_media") or 0),
        "categories": list(row.get("categories") or []),
        "excerpt": raw_field(row, "excerpt"),
    }

def validate_current(row: dict) -> str:
    ident = identity_snapshot(row)
    if ident["id"] != POST_ID:
        raise RuntimeError(f"post ID mismatch: {ident['id']}")
    if ident["slug"] != SLUG:
        raise RuntimeError(f"slug changed: {ident['slug']}")
    if ident["status"] != STATUS:
        raise RuntimeError(f"status changed: {ident['status']}")
    if ident["title"] != TITLE:
        raise RuntimeError(f"title changed: {ident['title']}")
    current = raw_field(row, "content")
    current_sha = sha256(current)
    if current_sha != EXPECTED_CURRENT_SHA256:
        raise RuntimeError(f"content changed since 2026-09-16 audit: {current_sha}")
    return current

def validate_target(content: str):
    if not content.strip():
        raise RuntimeError("target content is empty")
    required = [
        "10万円、20万円高く売れたら",
        "約150万円差",
        "UXを考えていたところからRXまで視野に入る",
        "1時間で30件ほど着信",
        '[blog_parts id="2184"]',
        '[blog_parts id="2846"]',
    ]
    for needle in required:
        if needle not in content:
            raise RuntimeError(f"target content missing required marker: {needle}")
    if "<h1" in content.lower():
        raise RuntimeError("target content must not contain H1")
    if content.count('[blog_parts id="2184"]') != 1:
        raise RuntimeError("CTN button shortcode count must be exactly 1")
    if content.count('[blog_parts id="2846"]') != 1:
        raise RuntimeError("CTN banner shortcode count must be exactly 1")

def write_report(data: dict):
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / "result.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# car-sell-high revenue rewrite — 2026-09-16",
        "",
        f"- result: **{data['result']}**",
        f"- mode: **{data['mode']}**",
        f"- post_id: **{POST_ID}**",
        f"- slug: **{SLUG}**",
        f"- status: **{data.get('status', '-')}**",
        f"- title: **{data.get('title', '-')}**",
        f"- before_sha256: **{data.get('before_sha256', '-')}**",
        f"- after_sha256: **{data.get('after_sha256', '-')}**",
        f"- public posts before/after: **{data.get('public_before',{}).get('posts','-')} / {data.get('public_after',{}).get('posts','-')}**",
        f"- public pages before/after: **{data.get('public_before',{}).get('pages','-')} / {data.get('public_after',{}).get('pages','-')}**",
    ]
    if data.get("errors"):
        lines += ["", "## Errors"] + [f"- {x}" for x in data["errors"]]
    (REPORT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["preflight", "apply"], default="preflight")
    args = parser.parse_args()

    target = CONTENT_FILE.read_text(encoding="utf-8")
    validate_target(target)

    public_before = public_counts()
    before = get_post()
    original = validate_current(before)
    before_identity = identity_snapshot(before)

    if args.mode == "preflight":
        data = {
            "result": "PREFLIGHT_OK_NO_WRITES",
            "mode": args.mode,
            "status": before_identity["status"],
            "title": before_identity["title"],
            "before_sha256": sha256(original),
            "after_sha256": sha256(target),
            "public_before": public_before,
            "public_after": public_before,
            "errors": [],
        }
        write_report(data)
        return 0

    errors = []
    wrote = False
    try:
        request("POST", f"/wp-json/wp/v2/posts/{POST_ID}", {"content": target})
        wrote = True
        after = get_post()
        saved = raw_field(after, "content")
        after_identity = identity_snapshot(after)

        if saved != target:
            raise RuntimeError("saved content mismatch")
        if after_identity != before_identity:
            raise RuntimeError(f"identity/metadata changed: {before_identity} -> {after_identity}")

        public_after = public_counts()
        if public_after != public_before:
            raise RuntimeError(f"public post/page counts changed: {public_before} -> {public_after}")

    except Exception as exc:
        errors.append(str(exc))
        if wrote:
            try:
                request("POST", f"/wp-json/wp/v2/posts/{POST_ID}", {"content": original})
                rollback = get_post()
                if sha256(raw_field(rollback, "content")) != EXPECTED_CURRENT_SHA256:
                    errors.append("rollback content hash mismatch")
                if identity_snapshot(rollback) != before_identity:
                    errors.append("rollback identity/metadata mismatch")
            except Exception as rb:
                errors.append(f"rollback failed: {rb}")
        data = {
            "result": "APPLY_FAILED_ROLLBACK_ATTEMPTED",
            "mode": args.mode,
            "status": before_identity["status"],
            "title": before_identity["title"],
            "before_sha256": sha256(original),
            "after_sha256": "",
            "public_before": public_before,
            "public_after": public_counts(),
            "errors": errors,
        }
        write_report(data)
        return 3

    final = get_post()
    final_content = raw_field(final, "content")
    final_identity = identity_snapshot(final)
    public_after = public_counts()

    if final_content != target:
        errors.append("final content mismatch")
    if final_identity != before_identity:
        errors.append("final identity/metadata mismatch")
    if public_after != public_before:
        errors.append(f"final public counts changed: {public_before} -> {public_after}")

    data = {
        "result": "APPLIED_OK" if not errors else "APPLIED_BUT_FINAL_VERIFY_FAILED",
        "mode": args.mode,
        "status": final_identity["status"],
        "title": final_identity["title"],
        "before_sha256": sha256(original),
        "after_sha256": sha256(final_content),
        "public_before": public_before,
        "public_after": public_after,
        "errors": errors,
    }
    write_report(data)
    return 0 if not errors else 4

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        REPORT.mkdir(parents=True, exist_ok=True)
        data = {
            "result": "BLOCKED_BEFORE_WRITE",
            "mode": "unknown",
            "status": "-",
            "title": "-",
            "before_sha256": "",
            "after_sha256": "",
            "public_before": {},
            "public_after": {},
            "errors": [f"{type(exc).__name__}: {exc}"],
        }
        write_report(data)
        raise
