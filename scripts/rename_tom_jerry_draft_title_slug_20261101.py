#!/usr/bin/env python3
"""Safely rename only title and slug of existing unpublished Tom and Jerry draft #4282.

Pull request: read-only preflight. On main: exact-state guarded metadata update.
No changes to article body, any of the 15 photos, featured photo, categories, or publication.
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
BODY_SHA = "4e91ed9241e30faae4d220ca2552f84e5ddef3acf4aa3f66e2acbce1f88b69d9"
COVER = 4301
MANIFEST = Path("editorial/tom-and-jerry-hiroshima-2026/photo-plan.json")
IMAGE = re.compile(r'<!-- wp:image\b.*?<!-- /wp:image -->', re.S)

def sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def auth_header():
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise RuntimeError("STOP: missing WordPress credentials")
    token = base64.b64encode((user + ":" + password).encode()).decode()
    return "Basic " + token

def request_json(endpoint, token, data=None, return_headers=False):
    is_write = data is not None
    method = "POST" if is_write else "GET"
    headers = {
        "Authorization": token,
        "Accept": "application/json",
        "User-Agent": "tsurikue-tom-jerry-draft-title-slug/1.0"
    }
    if is_write:
        headers["Content-Type"] = "application/json; charset=utf-8"
    body = json.dumps(data, ensure_ascii=False).encode() if is_write else None
    req = urllib.request.Request(SITE + endpoint, data=body, headers=headers, method=method)
    for attempt in range(1 if is_write else 3):
        try:
            with urllib.request.urlopen(req, timeout=55) as response:
                result = json.loads(response.read().decode("utf-8"))
                if return_headers:
                    return result, dict(response.headers)
                return result
        except (urllib.error.URLError, TimeoutError) as err:
            if is_write or attempt == 2:
                raise
            print("GET_RETRY", attempt + 1, type(err).__name__, flush=True)
            time.sleep(2 * (attempt + 1))

def live_post(token):
    fields = "id,slug,status,title,content,categories,featured_media,author"
    query = urllib.parse.urlencode({"context": "edit", "_fields": fields})
    return request_json("/wp-json/wp/v2/posts/" + str(PID) + "?" + query, token)

def current_body(post):
    return (post.get("content") or {}).get("raw") or ""

def live_title(post):
    return html.unescape((post.get("title") or {}).get("raw") or "")

def validate_base(post, slug, title):
    if (post.get("id"), post.get("slug"), post.get("status")) != (PID, slug, "draft"):
        raise RuntimeError("STOP: wrong post ID, slug, or unpublished state")
    if live_title(post) != title:
        raise RuntimeError("STOP: expected post title changed")
    if post.get("categories") != [7] or int(post.get("featured_media") or 0) != COVER:
        raise RuntimeError("STOP: post category or featured media changed")
    body = current_body(post)
    if sha(body) != BODY_SHA:
        raise RuntimeError("STOP: live article content differs from last verified body")
    manifest = json.loads(MANIFEST.read_text("utf-8"))
    mapping = manifest["media_mapping"]
    expected = [int(x["wp_media_id"]) for x in mapping]
    blocks = IMAGE.findall(body)
    actual = []
    for block in blocks:
        found = re.search(r'wp-image-(\d+)', block)
        if not found:
            raise RuntimeError("STOP: image Gutenberg block missing media ID")
        actual.append(int(found.group(1)))
    if len(blocks) != 15 or len(set(actual)) != 15 or sorted(actual) != sorted(expected):
        raise RuntimeError("STOP: missing or changed image IDs")
    if body.count("<!-- wp:table -->") != 1 or body.count("<!-- wp:paragraph -->") != 45:
        raise RuntimeError("STOP: pricing table or paragraph structure drift")
    return body

def duplicate_slug_check(token):
    for endpoint in ("posts", "pages"):
        q = urllib.parse.urlencode({
            "context": "edit", "slug": NEW_SLUG, "status": "any",
            "per_page": "100", "_fields": "id,slug,status"
        })
        matches = request_json("/wp-json/wp/v2/" + endpoint + "?" + q, token)
        if not isinstance(matches, list):
            raise RuntimeError("STOP: unexpected slug lookup")
        collisions = [x for x in matches if int(x.get("id") or 0) != PID]
        if collisions:
            raise RuntimeError("STOP: target slug already used by another " + endpoint + ": " + str(collisions))

def publication_counts(token):
    counts = {}
    for endpoint in ("posts", "pages"):
        q = urllib.parse.urlencode({"context":"edit", "status":"publish", "per_page":"1", "_fields":"id"})
        _, headers = request_json("/wp-json/wp/v2/" + endpoint + "?" + q, token, return_headers=True)
        counts[endpoint] = int(headers.get("X-WP-Total", 0))
    return counts

def main(mode):
    if mode not in ("check", "apply"):
        raise RuntimeError("Use check or apply")
    token = auth_header()
    before = live_post(token)
    old = validate_base(before, OLD_SLUG, OLD_TITLE)
    duplicate_slug_check(token)
    print("RENAME_PREFLIGHT_OK", json.dumps({
        "post_id": PID, "old_title": OLD_TITLE, "new_title": NEW_TITLE,
        "old_slug": OLD_SLUG, "new_slug": NEW_SLUG, "status": "draft",
        "body_sha256": BODY_SHA, "photo_count": 15, "featured_media": COVER
    }, ensure_ascii=False), flush=True)
    if mode == "check":
        return
    counts_before = publication_counts(token)
    second = live_post(token)
    validate_base(second, OLD_SLUG, OLD_TITLE)
    if any(second.get(key) != before.get(key) for key in
        ("id", "slug", "title", "status", "categories", "featured_media", "content", "author")):
        raise RuntimeError("STOP: concurrent editor change")
    # Never blindly retry uncertain WordPress metadata POSTs.
    try:
        response = request_json("/wp-json/wp/v2/posts/" + str(PID), token,
                                {"title": NEW_TITLE, "slug": NEW_SLUG})
        if response.get("id") != PID:
            raise RuntimeError("STOP: unexpected WordPress update target")
    except (urllib.error.URLError, TimeoutError) as err:
        print("POST_UNCERTAIN_VERIFY_WITH_GET_NO_RETRY", type(err).__name__, flush=True)
    after = live_post(token)
    validate_base(after, NEW_SLUG, NEW_TITLE)
    for field in ("id", "status", "categories", "featured_media", "author", "content"):
        if after.get(field) != before.get(field):
            raise RuntimeError("STOP: protected field was changed: " + field)
    counts_after = publication_counts(token)
    if counts_after != counts_before:
        raise RuntimeError("STOP: published post/page counts changed")
    report = {
        "action":"RENAME_EXISTING_UNPUBLISHED_DRAFT",
        "post_id": PID, "status":"draft", "old_title": OLD_TITLE, "new_title": NEW_TITLE,
        "old_slug": OLD_SLUG, "new_slug": NEW_SLUG,
        "body_sha256": BODY_SHA, "photo_count":15, "featured_media":COVER,
        "photo_uploads":0, "body_writes":0, "wordpress_metadata_writes":1,
        "published_before":counts_before, "published_after":counts_after,
        "result":"SAVED_AND_VERIFIED"
    }
    output = Path("reports/tom-jerry-title-slug")
    output.mkdir(parents=True, exist_ok=True)
    (output / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("TITLE_AND_SLUG_UPDATED_VERIFIED", json.dumps(report, ensure_ascii=False), flush=True)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "check")
