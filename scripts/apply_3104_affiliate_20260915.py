#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

SITE = "https://tsurikue.com"
UA = "tsurikue-apply-3104-affiliate-20260915/1.0"
REPORT = Path("reports/3104-affiliate-apply-20260915")

SOURCE_PART_ID = 2184
SOURCE_PART_TITLE = "CTNボタン"
SOURCE_PART_SHA256 = "d9c97b68cf2d080598c9edea932217a6070531bf9b199d947be25bb5bb2203e9"
SOURCE_CLICK_URL = "https://px.a8.net/svt/ejp?a8mat=3Z8YF4+7VECQA+5I4S+5YJRM"
SOURCE_PIXEL_URL = "https://www12.a8.net/0.gif?a8mat=3Z8YF4+7VECQA+5I4S+5YJRM"
TRACK_VALUE = "3104"
TARGET_PART_TITLE = "CTNボタン 3104"
TARGET_PART_SLUG = "ctn-button-3104"

POST_SPECS = [
    {"id": 3774, "slug": "landcruiser-fj-review", "status": "publish", "sha256": "55ee793708b5317f60e6344c3c76f821df998b47557c2f181d7329b9831905bd"},
    {"id": 3767, "slug": "landcruiser-fj-price", "status": "publish", "sha256": "290dc2905360f3198621d72a1adff6d71903c6eff903b4df9e4c55c29d6f6ceb"},
    {"id": 3777, "slug": "landcruiser-fj-rear-seat", "status": "draft", "sha256": "4908dfd4d8931d58e6d36d7c88297fb62ec9e5c014f9b6dc6d07151c01a72ef9"},
    {"id": 3778, "slug": "landcruiser-fj-drawbacks", "status": "publish", "sha256": "58ae28f85d94ee01a483c5d1d485c60b11b2fe4f1a39ba0be049343d82fca970"},
]
OLD_SHORTCODE = '[blog_parts id="2184"]'

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

def get_part(part_id: int) -> dict:
    row, _ = request("GET", f"/wp-json/wp/v2/blog_parts/{part_id}?context=edit")
    return row

def find_target_part():
    q = urllib.parse.urlencode({
        "context": "edit",
        "slug": TARGET_PART_SLUG,
        "per_page": 10,
        "_fields": "id,slug,status,title,content,type,author,modified",
    })
    rows, _ = request("GET", f"/wp-json/wp/v2/blog_parts?{q}")
    return rows

def get_post(post_id: int) -> dict:
    q = urllib.parse.urlencode({
        "context": "edit",
        "_fields": "id,slug,status,title,content,author,modified,featured_media,categories,excerpt",
    })
    row, _ = request("GET", f"/wp-json/wp/v2/posts/{post_id}?{q}")
    return row

def target_part_content(source: str) -> str:
    if sha256(source) != SOURCE_PART_SHA256:
        raise RuntimeError("source blog part hash mismatch")
    if source.count(SOURCE_CLICK_URL) != 1:
        raise RuntimeError("source click URL count mismatch")
    if source.count(SOURCE_PIXEL_URL) != 1:
        raise RuntimeError("source pixel URL count mismatch")
    if re.search(r"[?&]id1=", source):
        raise RuntimeError("source blog part already has id1")
    target = source.replace(SOURCE_CLICK_URL, SOURCE_CLICK_URL + "&id1=" + TRACK_VALUE, 1)
    if target.count(SOURCE_CLICK_URL + "&id1=" + TRACK_VALUE) != 1:
        raise RuntimeError("failed to add id1 to click URL")
    if target.count(SOURCE_PIXEL_URL) != 1:
        raise RuntimeError("tracking pixel was unexpectedly changed")
    if target.replace(SOURCE_CLICK_URL + "&id1=" + TRACK_VALUE, SOURCE_CLICK_URL, 1) != source:
        raise RuntimeError("target blog part differs by more than id1")
    return target

def validate_source_part():
    part = get_part(SOURCE_PART_ID)
    title = html.unescape(raw_field(part, "title"))
    content = raw_field(part, "content")
    if int(part.get("id") or 0) != SOURCE_PART_ID:
        raise RuntimeError("source blog part ID mismatch")
    if part.get("status") != "publish":
        raise RuntimeError(f"source blog part status changed: {part.get('status')}")
    if title != SOURCE_PART_TITLE:
        raise RuntimeError(f"source blog part title changed: {title}")
    if sha256(content) != SOURCE_PART_SHA256:
        raise RuntimeError(f"source blog part content changed: {sha256(content)}")
    return part, content, target_part_content(content)

def validate_posts():
    rows = []
    for spec in POST_SPECS:
        row = get_post(spec["id"])
        content = raw_field(row, "content")
        if int(row.get("id") or 0) != spec["id"]:
            raise RuntimeError(f"post ID mismatch for {spec['slug']}")
        if row.get("slug") != spec["slug"]:
            raise RuntimeError(f"post {spec['id']} slug changed: {row.get('slug')}")
        if row.get("status") != spec["status"]:
            raise RuntimeError(f"post {spec['id']} status changed: {row.get('status')}")
        actual_sha = sha256(content)
        if actual_sha != spec["sha256"]:
            raise RuntimeError(f"post {spec['id']} content changed since audit: {actual_sha}")
        if content.count(OLD_SHORTCODE) != 1:
            raise RuntimeError(f"post {spec['id']} old shortcode count is {content.count(OLD_SHORTCODE)}")
        rows.append((spec, row, content))
    return rows

def validate_existing_target(rows, expected_content):
    if not rows:
        return None
    if len(rows) != 1:
        raise RuntimeError(f"target blog part slug collision: {len(rows)} rows")
    row = rows[0]
    if row.get("slug") != TARGET_PART_SLUG:
        raise RuntimeError("target blog part slug mismatch")
    if row.get("status") != "publish":
        raise RuntimeError(f"target blog part status is {row.get('status')}")
    if html.unescape(raw_field(row, "title")) != TARGET_PART_TITLE:
        raise RuntimeError("target blog part title mismatch")
    if raw_field(row, "content") != expected_content:
        raise RuntimeError("target blog part content mismatch")
    return row

def write_report(data: dict):
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / "result.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# 3104 affiliate apply 2026-09-15",
        "",
        f"- result: **{data['result']}**",
        f"- mode: **{data['mode']}**",
        f"- source blog part: **{SOURCE_PART_ID} / {SOURCE_PART_TITLE}**",
        f"- target blog part ID: **{data.get('target_part_id', 'not-created')}**",
        f"- target blog part title: **{TARGET_PART_TITLE}**",
        f"- A8 parameter: **id1={TRACK_VALUE}**",
        f"- updated post IDs: **{data.get('updated_ids', [])}**",
        f"- public posts before/after: **{data.get('public_before',{}).get('posts','-')} / {data.get('public_after',{}).get('posts','-')}**",
        f"- public pages before/after: **{data.get('public_before',{}).get('pages','-')} / {data.get('public_after',{}).get('pages','-')}**",
    ]
    if data.get("errors"):
        lines += ["", "## Errors"] + [f"- {x}" for x in data["errors"]]
    lines += ["", "## Posts", "", "|ID|slug|status|old shortcode|new shortcode|", "|---:|---|---|---:|---:|"]
    for r in data.get("posts", []):
        lines.append(f"|{r['id']}|{r['slug']}|{r['status']}|{r['old_count']}|{r['new_count']}|")
    (REPORT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["preflight", "apply"], default="preflight")
    args = parser.parse_args()

    public_before = public_counts()
    source_part, source_content, target_content = validate_source_part()
    originals = validate_posts()
    existing_target = validate_existing_target(find_target_part(), target_content)

    if args.mode == "preflight":
        data = {
            "result": "PREFLIGHT_OK_NO_WRITES",
            "mode": args.mode,
            "target_part_id": int(existing_target["id"]) if existing_target else None,
            "updated_ids": [],
            "public_before": public_before,
            "public_after": public_before,
            "posts": [
                {"id": spec["id"], "slug": spec["slug"], "status": spec["status"], "old_count": content.count(OLD_SHORTCODE), "new_count": 0}
                for spec, row, content in originals
            ],
            "errors": [],
        }
        write_report(data)
        return 0

    created_target = False
    if existing_target is None:
        target_part, _ = request("POST", "/wp-json/wp/v2/blog_parts", {
            "title": TARGET_PART_TITLE,
            "slug": TARGET_PART_SLUG,
            "content": target_content,
            "status": "publish",
        })
        created_target = True
    else:
        target_part = existing_target

    target_id = int(target_part.get("id") or 0)
    if target_id <= 0:
        raise RuntimeError("invalid target blog part ID")
    target_check = get_part(target_id)
    if target_check.get("status") != "publish" or target_check.get("slug") != TARGET_PART_SLUG:
        raise RuntimeError("target blog part post-write identity check failed")
    if html.unescape(raw_field(target_check, "title")) != TARGET_PART_TITLE:
        raise RuntimeError("target blog part post-write title check failed")
    if raw_field(target_check, "content") != target_content:
        raise RuntimeError("target blog part post-write content check failed")

    new_shortcode = f'[blog_parts id="{target_id}"]'
    updated = []
    errors = []
    try:
        for spec, row, original in originals:
            revised = original.replace(OLD_SHORTCODE, new_shortcode, 1)
            if revised == original or revised.count(OLD_SHORTCODE) != 0 or revised.count(new_shortcode) != 1:
                raise RuntimeError(f"post {spec['id']} shortcode replacement failed locally")
            request("POST", f"/wp-json/wp/v2/posts/{spec['id']}", {"content": revised})
            check = get_post(spec["id"])
            saved = raw_field(check, "content")
            if check.get("slug") != spec["slug"] or check.get("status") != spec["status"]:
                raise RuntimeError(f"post {spec['id']} identity changed after write")
            if saved != revised:
                raise RuntimeError(f"post {spec['id']} saved content mismatch")
            updated.append(spec["id"])
    except Exception as exc:
        errors.append(str(exc))
        for spec, row, original in reversed(originals):
            if spec["id"] not in updated:
                continue
            try:
                request("POST", f"/wp-json/wp/v2/posts/{spec['id']}", {"content": original})
                check = get_post(spec["id"])
                if sha256(raw_field(check, "content")) != spec["sha256"]:
                    errors.append(f"rollback hash mismatch for post {spec['id']}")
            except Exception as rb:
                errors.append(f"rollback failed for post {spec['id']}: {rb}")
        if created_target:
            try:
                request("POST", f"/wp-json/wp/v2/blog_parts/{target_id}", {"status": "draft"})
            except Exception as rb:
                errors.append(f"target blog part rollback-to-draft failed: {rb}")
        data = {
            "result": "APPLY_FAILED_ROLLBACK_ATTEMPTED",
            "mode": args.mode,
            "target_part_id": target_id,
            "updated_ids": updated,
            "public_before": public_before,
            "public_after": public_counts(),
            "posts": [],
            "errors": errors,
        }
        write_report(data)
        return 3

    public_after = public_counts()
    if public_after != public_before:
        errors.append(f"public post/page counts changed: {public_before} -> {public_after}")

    post_rows = []
    for spec in POST_SPECS:
        row = get_post(spec["id"])
        content = raw_field(row, "content")
        old_count = content.count(OLD_SHORTCODE)
        new_count = content.count(new_shortcode)
        if row.get("slug") != spec["slug"] or row.get("status") != spec["status"]:
            errors.append(f"final identity mismatch for post {spec['id']}")
        if old_count != 0 or new_count != 1:
            errors.append(f"final shortcode mismatch for post {spec['id']}: old={old_count} new={new_count}")
        post_rows.append({
            "id": spec["id"],
            "slug": spec["slug"],
            "status": row.get("status"),
            "old_count": old_count,
            "new_count": new_count,
        })

    final_part = get_part(target_id)
    final_content = raw_field(final_part, "content")
    if final_part.get("status") != "publish" or final_part.get("slug") != TARGET_PART_SLUG:
        errors.append("final target blog part identity mismatch")
    if final_content != target_content:
        errors.append("final target blog part content mismatch")
    if final_content.count(SOURCE_CLICK_URL + "&id1=" + TRACK_VALUE) != 1:
        errors.append("final id1 parameter missing from click URL")
    if final_content.count(SOURCE_PIXEL_URL) != 1:
        errors.append("final tracking pixel mismatch")

    data = {
        "result": "APPLIED_OK" if not errors else "APPLIED_BUT_FINAL_VERIFY_FAILED",
        "mode": args.mode,
        "target_part_id": target_id,
        "updated_ids": updated,
        "public_before": public_before,
        "public_after": public_after,
        "posts": post_rows,
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
            "target_part_id": None,
            "updated_ids": [],
            "public_before": {},
            "public_after": {},
            "posts": [],
            "errors": [f"{type(exc).__name__}: {exc}"],
        }
        write_report(data)
        raise
