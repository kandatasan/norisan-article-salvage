#!/usr/bin/env python3
"""Title+slug only for existing unpublished WordPress post 4282.

PR = read-only, main push = guarded update. Preserve article body, media,
category, author, date, status, SEO fields and everything else. Never publish.
"""
from __future__ import annotations
import base64
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SITE = "https://tsurikue.com"
PID = 4282
OLD_SLUG = "tom-and-jerry-exhibition-hiroshima-2026"
NEW_SLUG = "tom-and-jerry-exhibition-review"
OLD_TITLE = "【広島】そごうのトムとジェリー展に行ってきた！見どころと限定グッズを現地レポ"
NEW_TITLE = "トムとジェリー展に行ってきた！見どころ・所要時間・限定グッズを写真で紹介【広島そごう会場】"
CONTENT_SHA = "4e91ed9241e30faae4d220ca2552f84e5ddef3acf4aa3f66e2acbce1f88b69d9"
FEATURED = 4301
IMG_IDS = [4301,4317,4315,4313,4314,4308,4309,4305,4304,4303,4306,4300,4295,4286,4287]
OUT = Path("reports/tom-jerry-title-slug-20261101")

def digest(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def creds():
    username = os.getenv("TSURIKUE_WP_USER")
    password = os.getenv("TSURIKUE_WP_APP_PASSWORD")
    if not username or not password:
        raise RuntimeError("STOP: WordPress credentials missing")
    return "Basic " + base64.b64encode((username + ":" + password).encode()).decode()

def call(path, auth, payload=None, retries=None):
    method = "POST" if payload is not None else "GET"
    if retries is None: retries = 1 if method == "POST" else 3
    headers = {
        "Authorization": auth,
        "Accept": "application/json",
        "User-Agent": "tsurikue-tom-jerry-title-slug-guard/1.0",
    }
    if payload is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(SITE + path, data=data, method=method, headers=headers)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=65) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError) as ex:
            if attempt == retries - 1:
                raise
            print("RETRY_READ", attempt + 1, type(ex).__name__, flush=True)
            time.sleep(2 * (attempt + 1))

def get_post(auth):
    query = urllib.parse.urlencode({
        "context": "edit",
        "_fields": "id,slug,status,title,categories,author,featured_media,content,date,date_gmt,modified",
    })
    return call("/wp-json/wp/v2/posts/" + str(PID) + "?" + query, auth)

def raw_content(post):
    return (post.get("content") or {}).get("raw") or ""

def raw_title(post):
    return html.unescape((post.get("title") or {}).get("raw") or "")

def guard(post):
    if post.get("id") != PID:
        raise RuntimeError("STOP: wrong WordPress post ID")
    if post.get("status") != "draft":
        raise RuntimeError("STOP: the user asked for the existing draft; status is NOT draft")
    if post.get("categories") != [7] or int(post.get("featured_media") or 0) != FEATURED:
        raise RuntimeError("STOP: category or featured image unexpectedly changed")
    body = raw_content(post)
    if digest(body) != CONTENT_SHA:
        raise RuntimeError("STOP: WordPress body differs from latest audited original. Never overwrite.")
    imgs = [int(i) for i in re.findall(r'class="wp-image-(\d+)"', body)]
    if imgs != IMG_IDS:
        raise RuntimeError("STOP: uploaded photo sequence changed")
    if body.count("<!-- wp:image ") != 15 or body.count("<!-- wp:paragraph -->") != 45:
        raise RuntimeError("STOP: expected original article blocks are absent")
    if body.count("<br>") != 45 or body.count("<!-- wp:table -->") != 1:
        raise RuntimeError("STOP: article formatting/pricing unexpectedly changed")
    if not body.startswith("<!-- tsurikue-salvage:v1 -->\n<!-- tsurikue-editorial:tom-and-jerry-hiroshima-2026:v1 -->\n"):
        raise RuntimeError("STOP: article identity marker missing")
    if raw_title(post) == NEW_TITLE and post.get("slug") == NEW_SLUG:
        return "ALREADY_CORRECT"
    if raw_title(post) == OLD_TITLE and post.get("slug") == OLD_SLUG:
        return "REQUIRES_CHANGE"
    raise RuntimeError("STOP: current post title or slug differs from both approved states")

def new_slug_available(auth):
    for endpoint in ("posts", "pages"):
        query = urllib.parse.urlencode({
            "context": "edit",
            "status": "any",
            "slug": NEW_SLUG,
            "per_page": 100,
            "_fields": "id,slug,status",
        })
        rows = call("/wp-json/wp/v2/" + endpoint + "?" + query, auth)
        if not isinstance(rows, list):
            raise RuntimeError("STOP: cannot validate slug uniqueness")
        foreign = [row for row in rows if int(row.get("id") or 0) != PID]
        if foreign:
            raise RuntimeError("STOP: new slug already used by another post/page")

def ensure_metadata_same(before, after):
    for field in ("id", "status", "categories", "author", "featured_media", "date", "date_gmt", "content"):
        if before.get(field) != after.get(field):
            raise RuntimeError("STOP: protected WordPress field changed: " + field)

def main(mode):
    if mode not in ("check", "apply"):
        raise RuntimeError("Usage: check or apply")
    auth = creds()
    before = get_post(auth)
    state = guard(before)
    new_slug_available(auth)
    report = {
        "post_id": PID, "status": before["status"],
        "old_title": OLD_TITLE, "new_title": NEW_TITLE,
        "old_slug": OLD_SLUG, "new_slug": NEW_SLUG,
        "article_sha256": CONTENT_SHA, "featured_media": FEATURED,
        "photo_count": 15, "change_state": state,
        "public_action": "NONE; DRAFT ONLY",
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "preflight.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("READ_ONLY_METADATA_PREFLIGHT_OK", json.dumps(report, ensure_ascii=False), flush=True)
    if mode == "check":
        return
    if state == "ALREADY_CORRECT":
        report["result"] = "ALREADY_CORRECT_NO_WRITE"
        report["wordpress_write_count"] = 0
    else:
        second = get_post(auth)
        if guard(second) != "REQUIRES_CHANGE":
            raise RuntimeError("STOP: WordPress title/slug changed during operation")
        for field in ("id", "slug", "status", "title", "categories", "author", "featured_media", "date", "date_gmt", "content"):
            if before.get(field) != second.get(field):
                raise RuntimeError("STOP: concurrent edit, not overwriting")
        try:
            response = call("/wp-json/wp/v2/posts/" + str(PID), auth,
                            {"title": NEW_TITLE, "slug": NEW_SLUG}, retries=1)
            if response.get("id") != PID or response.get("status") != "draft":
                raise RuntimeError("STOP: unexpected update response")
        except (urllib.error.URLError, TimeoutError) as err:
            print("POST_OUTCOME_UNCERTAIN_VERIFY_WITHOUT_RETRY", type(err).__name__, flush=True)
        report["wordpress_write_count"] = 1

    after = get_post(auth)
    if guard(after) != "ALREADY_CORRECT":
        raise RuntimeError("STOP: desired title/slug not saved correctly")
    ensure_metadata_same(before, after)
    if raw_title(after) != NEW_TITLE or after.get("slug") != NEW_SLUG:
        raise RuntimeError("STOP: WordPress metadata changed unexpectedly")
    report["result"] = "TITLE_SLUG_UPDATED_AND_VERIFIED"
    report["verified_slug"] = after["slug"]
    report["verified_title"] = raw_title(after)
    report["verified_status"] = after["status"]
    report["verified_content_sha256"] = digest(raw_content(after))
    report["draft_edit_url"] = SITE + "/wp-admin/post.php?post=" + str(PID) + "&action=edit"
    (OUT / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("WP_TITLE_SLUG_DRAFT_VERIFIED", json.dumps(report, ensure_ascii=False), flush=True)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "check")
