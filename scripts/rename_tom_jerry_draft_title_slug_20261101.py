#!/usr/bin/env python3
"""Safely rename title and slug of an already published Tom and Jerry review #4282.

The article was published by its owner between requests. PR is read-only; main
updates only metadata, verifies publication, then checks old URL 301 to new URL.
No article body, photo, category, or publication-state changes are permitted.
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
    fields = "id,slug,status,title,content,categories,featured_media,author,link"
    query = urllib.parse.urlencode({"context": "edit", "_fields": fields})
    return request_json("/wp-json/wp/v2/posts/" + str(PID) + "?" + query, token)

def current_body(post):
    return (post.get("content") or {}).get("raw") or ""

def live_title(post):
    return html.unescape((post.get("title") or {}).get("raw") or "")

def validate_base(post, slug, title):
    if (post.get("id"), post.get("slug"), post.get("status")) != (PID, slug, "publish"):
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

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, msg, headers, newurl):
        return None

def probe_public(url):
    # Test the live URL without silently following redirects.
    if urllib.parse.urlsplit(url).hostname != "tsurikue.com":
        raise RuntimeError("STOP: unsafe external public URL")
    opener = urllib.request.build_opener(NoRedirect)
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 (compatible; TsurikueAudit/1.0)"})
    try:
        with opener.open(req, timeout=35) as resp:
            resp.read(64)
            return {"status":resp.status,"location":resp.headers.get("Location","")}
    except urllib.error.HTTPError as err:
        return {"status":err.code,"location":err.headers.get("Location","")}

def assert_redirect(old_url, new_url):
    old_probe=probe_public(old_url)
    new_probe=probe_public(new_url)
    redirect_target=urllib.parse.urljoin(old_url,old_probe["location"])
    if old_probe["status"] not in (301,308) or redirect_target.rstrip("/") != new_url.rstrip("/") or new_probe["status"]!=200:
        raise RuntimeError("STOP: 301 redirect verification failed: old="+str(old_probe)+" new="+str(new_probe))
    print("PUBLIC_OLD_URL_REDIRECT_OK",json.dumps({"old":old_url,"new":new_url,"code":old_probe["status"]},ensure_ascii=False),flush=True)

def main(mode):
    if mode not in ("check", "apply"):
        raise RuntimeError("Use check or apply")
    token = auth_header()
    before = live_post(token)
    print("CURRENT_POST_METADATA", json.dumps({
        "id": before.get("id"), "slug": before.get("slug"), "status": before.get("status"),
        "title": live_title(before), "category_ids": before.get("categories"),
        "featured_media": before.get("featured_media"),
        "content_sha256": sha(current_body(before))
    }, ensure_ascii=False), flush=True)
    old = validate_base(before, OLD_SLUG, OLD_TITLE)
    duplicate_slug_check(token)
    original_public_link = before.get("link") or ""
    if urllib.parse.urlsplit(original_public_link).hostname != "tsurikue.com":
        raise RuntimeError("STOP: no trusted current public permalink")
    original_frontend = probe_public(original_public_link)
    if original_frontend["status"] != 200:
        raise RuntimeError("STOP: current public article is not HTTP 200: " + str(original_frontend))
    print("ORIGINAL_PUBLIC_URL_OK",original_public_link,flush=True)
    print("RENAME_PREFLIGHT_OK", json.dumps({
        "post_id": PID, "old_title": OLD_TITLE, "new_title": NEW_TITLE,
        "old_slug": OLD_SLUG, "new_slug": NEW_SLUG, "status": "publish",
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
    new_public_link = after.get("link") or ""
    if urllib.parse.urlsplit(new_public_link).hostname != "tsurikue.com":
        raise RuntimeError("STOP: changed post permalink has unexpected domain")
    try:
        assert_redirect(original_public_link,new_public_link)
    except Exception as redirect_error:
        # Restore the working public URL rather than leave broken inbound links.
        print("REDIRECT_FAILED_ROLLING_BACK",repr(redirect_error),flush=True)
        try:
            request_json("/wp-json/wp/v2/posts/"+str(PID),token,{"title":OLD_TITLE,"slug":OLD_SLUG})
            restored=live_post(token)
            validate_base(restored,OLD_SLUG,OLD_TITLE)
            print("PUBLIC_URL_ROLLBACK_VERIFIED",OLD_SLUG,flush=True)
        except Exception as rollback_error:
            raise RuntimeError("CRITICAL: redirect and rollback failed: "+str(redirect_error)+" ; "+str(rollback_error))
        raise RuntimeError("STOP: new URL did not 301 redirect; old title and URL restored")
    report = {
        "action":"RENAME_EXISTING_PUBLISHED_POST_WITH_REDIRECT_CHECK",
        "post_id": PID, "status":"publish", "old_title": OLD_TITLE, "new_title": NEW_TITLE,
        "old_slug": OLD_SLUG, "new_slug": NEW_SLUG,
        "body_sha256": BODY_SHA, "photo_count":15, "featured_media":COVER,
        "photo_uploads":0, "body_writes":0, "wordpress_metadata_writes":1,
        "published_before":counts_before, "published_after":counts_after,
        "public_old_url":original_public_link,"public_new_url":new_public_link,
        "old_url_301_verified":True,
        "result":"SAVED_AND_VERIFIED"
    }
    output = Path("reports/tom-jerry-title-slug")
    output.mkdir(parents=True, exist_ok=True)
    (output / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("TITLE_AND_SLUG_UPDATED_VERIFIED", json.dumps(report, ensure_ascii=False), flush=True)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "check")
