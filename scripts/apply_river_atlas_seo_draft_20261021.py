#!/usr/bin/env python3
"""Fail-closed WordPress DRAFT-only river atlas SEO article apply."""
from __future__ import annotations
import base64, hashlib, html, json, os, re, sys, urllib.parse, urllib.request
from pathlib import Path

SITE = "https://tsurikue.com"
TITLE = "日本の河川図鑑｜全国の河川名・水系・生き物を都道府県から探す"
SLUG = "japan-river-atlas"
SOURCE = Path("content/drafts/river-atlas-seo-20261021.html")
MARKER = "tsurikue-river-atlas-card"
BANNER = "9f5b9818-927a-40f1-838b-8d17735ffd7a.jpg"
DATA_ROOT = "/river-fish-atlas/data/"
UA = "tsurikue-river-atlas-seo-draft-20261021/1.0"

def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def auth():
    user, password = os.environ.get("TSURIKUE_WP_USER"), os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise RuntimeError("BLOCKED_MISSING_WP_SECRETS")
    return "Basic " + base64.b64encode((user + ":" + password).encode()).decode()

def req(path, method="GET", payload=None):
    headers = {"Authorization": auth(), "Accept": "application/json", "User-Agent": UA}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(SITE + path, data=data, method=method, headers=headers)
    with urllib.request.urlopen(request, timeout=85) as response:
        return json.loads(response.read().decode("utf-8")), dict(response.headers)

def query(endpoint, **kwargs):
    return req("/wp-json/wp/v2/" + endpoint + "?" + urllib.parse.urlencode(kwargs))[0]

def raw(row, key):
    value = row.get(key, "")
    return (value.get("raw") or value.get("rendered") or "") if isinstance(value, dict) else str(value)

def check_source():
    body = SOURCE.read_text(encoding="utf-8").strip()
    for token in (MARKER, BANNER, DATA_ROOT, "atlas.json", "fish_master.json",
                  "都道府県", "水系", "河川", "魚", "川名"):
        if token not in body:
            raise RuntimeError("Source missing expected token: " + token)
    if re.search(r"<h1\\b", body, re.I):
        raise RuntimeError("Do not duplicate WordPress title as H1")
    if body.count("<!-- wp:html -->") != body.count("<!-- /wp:html -->"):
        raise RuntimeError("Gutenberg HTML blocks unbalanced")
    if body.count("<script") != body.count("</script>"):
        raise RuntimeError("Script tags unbalanced")
    if len(body) < 35000:
        raise RuntimeError("Article unexpectedly truncated")
    return body

def candidates():
    fields = "id,slug,status,title,content,modified_gmt,featured_media,categories,link"
    all_rows = {}
    for term in ("河川図鑑", "日本の河川", "river-atlas"):
        for endpoint in ("posts", "pages"):
            rows = query(endpoint, context="edit", status="any", search=term,
                         per_page=100, _fields=fields)
            for row in rows:
                all_rows[(endpoint, row["id"])] = row
    for endpoint in ("posts", "pages"):
        for row in query(endpoint, context="edit", status="any", slug=SLUG,
                         per_page=100, _fields=fields):
            all_rows[(endpoint, row["id"])] = row
    return all_rows

def find_target(rows):
    related = []
    for (endpoint, pid), row in rows.items():
        title = re.sub(r"<[^>]+>", "", html.unescape(raw(row, "title")))
        content = raw(row, "content")
        if MARKER in content or title == TITLE or row["slug"] == SLUG or "日本の河川図鑑" in title:
            related.append((endpoint, row, title))
    if len(related) > 1:
        raise RuntimeError("BLOCKED_MULTIPLE_SIMILAR_WP_ITEMS: " +
                           json.dumps([(e, r["id"], r["slug"], r["status"]) for e,r,_ in related], ensure_ascii=False))
    if not related:
        return None
    endpoint, row, title = related[0]
    if endpoint != "posts" or row["status"] != "draft":
        raise RuntimeError(f"BLOCKED_EXISTING_NON_DRAFT_OR_PAGE: {endpoint} {row['id']} {row['status']}")
    if MARKER not in raw(row, "content"):
        raise RuntimeError(f"BLOCKED_EXISTING_ARTICLE_NOT_OUR_WIDGET: {row['id']} {title}")
    return row

def public_count():
    total = 0
    for endpoint in ("posts", "pages"):
        _, headers = req("/wp-json/wp/v2/" + endpoint + "?status=publish&per_page=1&_fields=id")
        total += int(headers.get("X-WP-Total", 0))
    return total

def main():
    body = check_source()
    rows = candidates()
    target = find_target(rows)
    # This editorial revision may ONLY update the already verified river atlas draft.
    # Never create a duplicate or overwrite a human's intervening edit.
    if target is None or int(target["id"]) != 4240 or target["slug"] != "" or target["status"] != "draft":
        raise RuntimeError("BLOCKED_EXPECTED_EXISTING_DRAFT_4240_NOT_FOUND")
    prior_hash = sha(raw(target, "content").strip())
    if prior_hash not in ("ad68e5b46f66bac2f0d08c1f4f752ebb39ac4dbf8f8c04dada41c715d832b64c", sha(body)):
        raise RuntimeError("BLOCKED_WP_DRAFT_EDITED_SINCE_LAST_VERIFIED_UPDATE")
    print("PRECHECK", json.dumps({
        "matching_article": None if target is None else {"id": target["id"], "slug": target["slug"], "status": target["status"]},
        "source_chars": len(body), "sha256": sha(body),
        "candidate_count": len(rows), "desired_status": "draft"
    }, ensure_ascii=False))
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        return
    before = public_count()
    if target is None:
        # Double-check immediately before creation to avoid duplicate posts.
        if find_target(candidates()) is not None:
            raise RuntimeError("BLOCKED_CONCURRENT_DUPLICATE")
        created, _ = req("/wp-json/wp/v2/posts", "POST",
                         {"title": TITLE, "slug": SLUG, "status": "draft", "content": body,
                          "excerpt": "全国の河川名・水系・支流・魚の調査記録を都道府県から検索。川名や魚名からも探せる日本の河川図鑑です。"})
        post_id, action = created["id"], "CREATED_DRAFT"
        expected_slug = SLUG
        expected_featured = 0
    else:
        post_id, expected_slug = target["id"], target["slug"]
        expected_featured = int(target.get("featured_media") or 0)
        current = query(f"posts/{post_id}", context="edit",
                        _fields="id,slug,status,title,content,modified_gmt,featured_media")
        if (current["slug"], current["status"], current["modified_gmt"]) != (
                target["slug"], target["status"], target["modified_gmt"]):
            raise RuntimeError("BLOCKED_CONCURRENT_WP_EDIT")
        if raw(current, "content") != raw(target, "content"):
            raise RuntimeError("BLOCKED_CONCURRENT_WP_BODY_EDIT")
        if sha(raw(current, "content").strip()) == sha(body):
            action = "ALREADY_CURRENT"
        else:
            req(f"/wp-json/wp/v2/posts/{post_id}", "POST",
                {"title": TITLE, "content": body, "status": "draft"})
            action = "UPDATED_EXISTING_DRAFT"
    saved = query(f"posts/{post_id}", context="edit",
                  _fields="id,slug,status,title,content,featured_media,link")
    if (saved["id"], saved["slug"], saved["status"]) != (post_id, expected_slug, "draft"):
        raise RuntimeError("BLOCKED_SAVED_ID_SLUG_STATUS_MISMATCH")
    if html.unescape(raw(saved, "title")) != TITLE:
        raise RuntimeError("BLOCKED_SAVED_TITLE_MISMATCH")
    if raw(saved, "content").strip() != body:
        raise RuntimeError("BLOCKED_SAVED_CONTENT_MISMATCH")
    if int(saved.get("featured_media") or 0) != expected_featured:
        raise RuntimeError("BLOCKED_FEATURED_MEDIA_CHANGED")
    after = public_count()
    if before != after:
        raise RuntimeError("BLOCKED_PUBLISHED_POST_COUNT_CHANGED")
    print("WORDPRESS_DRAFT_VERIFIED", json.dumps({
        "action": action, "post_id": post_id, "slug": expected_slug,
        "status": saved["status"], "title": TITLE, "featured_media": expected_featured,
        "content_sha256": sha(raw(saved, "content").strip()), "published_count_unchanged": True,
        "editor_url": SITE + "/wp-admin/post.php?post=" + str(post_id) + "&action=edit"
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
