#!/usr/bin/env python3
from __future__ import annotations

import base64, hashlib, html, json, os, urllib.parse, urllib.request

SITE = "https://tsurikue.com"
UA = "tsurikue-gourmet-featured-category-20260924/1.0"
GOURMET_CATEGORY_ID = 9

TARGETS = [
    {
        "id": 2638,
        "slug": "karaagekariju",
        "title": "東広島・からあげやカリッジュ西条寺家店を実食｜紅ショウガ唐揚げがうまい",
        "featured_media": 343,
        "media_path": "/wp-content/uploads/2026/05/img_0747.jpg",
        "marker": "<!-- tsurikue-editorial:karaagekariju:v2 -->",
    },
    {
        "id": 2663,
        "slug": "yakitori-riku",
        "title": "東広島・西条「炭火焼鳥 陸」を実食｜白肝ととり丼がうまい",
        "featured_media": 177,
        "media_path": "/wp-content/uploads/2026/05/img_0243.jpg",
        "marker": "<!-- tsurikue-editorial:yakitori-riku:v2 -->",
    },
]

def auth_header():
    raw = f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()
    return "Basic " + base64.b64encode(raw).decode()

def req(url, method="GET", payload=None):
    headers = {
        "Accept": "application/json",
        "Authorization": auth_header(),
        "User-Agent": UA,
    }
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode()
        headers["Content-Type"] = "application/json; charset=utf-8"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode()), dict(response.headers)

def raw(row, key):
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)

def get_post(pid):
    q = urllib.parse.urlencode({
        "context": "edit",
        "_fields": "id,slug,status,title,content,featured_media,categories,modified_gmt",
    })
    row, _ = req(f"{SITE}/wp-json/wp/v2/posts/{pid}?{q}")
    return row

def count_published(endpoint):
    q = urllib.parse.urlencode({"status": "publish", "per_page": 1, "_fields": "id"})
    _, headers = req(f"{SITE}/wp-json/wp/v2/{endpoint}?{q}")
    return int(headers.get("X-WP-Total", 0))

def public_counts():
    return {"posts": count_published("posts"), "pages": count_published("pages")}

def validate_category():
    q = urllib.parse.urlencode({"context": "edit", "_fields": "id,slug,name"})
    row, _ = req(f"{SITE}/wp-json/wp/v2/categories/{GOURMET_CATEGORY_ID}?{q}")
    if row.get("id") != GOURMET_CATEGORY_ID:
        raise RuntimeError("gourmet category id mismatch")
    if row.get("slug") != "gourmet":
        raise RuntimeError(f"category 9 slug is not gourmet: {row.get('slug')}")
    if html.unescape(row.get("name") or "") != "グルメ":
        raise RuntimeError(f"category 9 name is not グルメ: {row.get('name')}")

def validate_media(target):
    q = urllib.parse.urlencode({"context": "edit", "_fields": "id,status,source_url"})
    row, _ = req(f"{SITE}/wp-json/wp/v2/media/{target['featured_media']}?{q}")
    if row.get("id") != target["featured_media"]:
        raise RuntimeError(f"media id mismatch: {target['slug']}")
    actual = urllib.parse.unquote(
        urllib.parse.urlparse(row.get("source_url") or "").path
    ).casefold()
    if actual != target["media_path"].casefold():
        raise RuntimeError(
            f"media path mismatch {target['slug']}: {actual} != {target['media_path']}"
        )

def main():
    before_public = public_counts()
    validate_category()

    prepared = []
    for target in TARGETS:
        row = get_post(target["id"])
        if row.get("id") != target["id"]:
            raise RuntimeError(f"id mismatch: {target['slug']}")
        if row.get("slug") != target["slug"]:
            raise RuntimeError(f"slug mismatch: {target['slug']}")
        if row.get("status") != "draft":
            raise RuntimeError(f"target is not draft: {target['slug']}")
        if html.unescape(raw(row, "title")) != target["title"]:
            raise RuntimeError(f"title mismatch: {target['slug']}")
        content = raw(row, "content")
        if target["marker"] not in content:
            raise RuntimeError(f"salvaged editorial marker missing: {target['slug']}")
        validate_media(target)
        prepared.append({
            "target": target,
            "before": row,
            "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
        })

    for item in prepared:
        target = item["target"]
        before = item["before"]
        already = (
            int(before.get("featured_media") or 0) == target["featured_media"]
            and list(before.get("categories") or []) == [GOURMET_CATEGORY_ID]
        )
        if not already:
            req(
                f"{SITE}/wp-json/wp/v2/posts/{target['id']}",
                method="POST",
                payload={
                    "featured_media": target["featured_media"],
                    "categories": [GOURMET_CATEGORY_ID],
                    "status": "draft",
                },
            )

        after = get_post(target["id"])
        if after.get("slug") != target["slug"] or after.get("status") != "draft":
            raise RuntimeError(f"post identity/status changed: {target['slug']}")
        if html.unescape(raw(after, "title")) != target["title"]:
            raise RuntimeError(f"title changed unexpectedly: {target['slug']}")
        if hashlib.sha256(raw(after, "content").encode()).hexdigest() != item["content_sha256"]:
            raise RuntimeError(f"content changed unexpectedly: {target['slug']}")
        if int(after.get("featured_media") or 0) != target["featured_media"]:
            raise RuntimeError(f"featured image not applied: {target['slug']}")
        if list(after.get("categories") or []) != [GOURMET_CATEGORY_ID]:
            raise RuntimeError(
                f"category not exactly gourmet: {target['slug']} -> {after.get('categories')}"
            )
        item["action"] = "ALREADY_UP_TO_DATE" if already else "UPDATE"

    after_public = public_counts()
    if before_public != after_public:
        raise RuntimeError(f"published counts changed: {before_public} -> {after_public}")

    print("# Gourmet draft featured image + category 2026-09-24")
    print("- result: **SUCCESS**")
    print(f"- public posts: **{before_public['posts']} → {after_public['posts']}**")
    print(f"- public pages: **{before_public['pages']} → {after_public['pages']}**")
    print("- category: **グルメ (ID 9)**")
    for item in prepared:
        target = item["target"]
        print(
            f"- {target['slug']}: **{item['action']}** / draft / "
            f"featured_media **{target['featured_media']}** / category **9**"
        )
    print("- titles/content: **unchanged**")
    print("- draft statuses: **preserved**")

if __name__ == "__main__":
    main()
