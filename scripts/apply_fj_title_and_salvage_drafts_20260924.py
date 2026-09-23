#!/usr/bin/env python3
from __future__ import annotations

import base64, hashlib, html, json, os, re, urllib.parse, urllib.request
from pathlib import Path

SITE = "https://tsurikue.com"
UA = "tsurikue-fj-title-salvage-drafts-reconcile-20260924/1.1"

FJ = {
    "id": 3816,
    "slug": "landcruiser-fj-cheap",
    "status": "publish",
    "old_title": "ランドクルーザーFJを安く買う方法｜欲しいオプションを諦めず負担を減らす5つのコツ",
    "new_title": "ランドクルーザーFJを安く買う方法｜値引きだけに頼らず負担を減らす5つのコツ",
    "featured_media": 3757,
    "content_sha256_stripped": "0748a8dc9431106297aa9ce36226d96beddc722ba5128045f4222ed3f0416aa3",
}

DRAFTS = [
    {
        "id": 2638,
        "slug": "karaagekariju",
        "status": "draft",
        "old_title": "東広島『からあげやカリッジュ西条寺家店』激旨テイクアウト弁当！",
        "new_title": "東広島・からあげやカリッジュ西条寺家店を実食｜紅ショウガ唐揚げがうまい",
        "featured_media": 0,
        "old_content_sha256_stripped": "aab8a207df8bfbda31b3ce2aafda46866f7603b471726e4210fc40fb11585b2e",
        "salvage_marker": "<!-- old-tsurikue-salvage:v1 slug=karaagekariju -->",
        "editorial_marker": "<!-- tsurikue-editorial:karaagekariju:v2 -->",
        "content_file": "salvage-batch/20260924/karaagekariju.html",
        "expected_images": 2,
        "media": {
            343: "/wp-content/uploads/2026/05/img_0747.jpg",
            341: "/wp-content/uploads/2026/05/img_0745.jpg",
        },
    },
    {
        "id": 2663,
        "slug": "yakitori-riku",
        "status": "draft",
        "old_title": "東広島西条『炭火焼鳥　陸』極上のひと串と、広島のソウルドリンクで乾杯！",
        "new_title": "東広島・西条「炭火焼鳥 陸」を実食｜白肝ととり丼がうまい",
        "featured_media": 0,
        "old_content_sha256_stripped": "c895bdd5f508f56af93842da2160def2ae57a3545b7b4b44e17f04b7c8d647f4",
        "salvage_marker": "<!-- old-tsurikue-salvage:v1 slug=yakitori-riku -->",
        "editorial_marker": "<!-- tsurikue-editorial:yakitori-riku:v2 -->",
        "content_file": "salvage-batch/20260924/yakitori-riku.html",
        "expected_images": 5,
        "media": {
            185: "/wp-content/uploads/2026/05/img_0239.jpg",
            168: "/wp-content/uploads/2026/05/img_0238.jpg",
            177: "/wp-content/uploads/2026/05/img_0243.jpg",
            192: "/wp-content/uploads/2026/05/img_0244.jpg",
            155: "/wp-content/uploads/2026/05/img_0248.jpg",
        },
    },
]

TOKEN = re.compile(r"<!--\s+/?wp:[\s\S]*?-->")
OPEN = re.compile(r"<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->")
CLOSE = re.compile(r"<!--\s+/wp:([\w\-/]+)\s+-->")

def auth_header():
    raw = f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()
    return "Basic " + base64.b64encode(raw).decode()

def req(url, method="GET", payload=None):
    headers = {"Accept": "application/json", "Authorization": auth_header(), "User-Agent": UA}
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
        "_fields": "id,slug,status,title,content,featured_media,date,date_gmt,modified_gmt",
    })
    row, _ = req(f"{SITE}/wp-json/wp/v2/posts/{pid}?{q}")
    return row

def count_published(endpoint):
    q = urllib.parse.urlencode({"status": "publish", "per_page": 1, "_fields": "id"})
    _, headers = req(f"{SITE}/wp-json/wp/v2/{endpoint}?{q}")
    return int(headers.get("X-WP-Total", 0))

def public_counts():
    return {"posts": count_published("posts"), "pages": count_published("pages")}

def sha_stripped(text):
    return hashlib.sha256(text.strip().encode()).hexdigest()

def count_images(text):
    return len(re.findall(r"<!--\s+wp:image\b", text))

def count_blog_parts(text):
    return len(re.findall(r"\[blog_parts\s+id=", text))

def has_h1(text):
    return bool(re.search(r"<h1\b", text, flags=re.I))

def block_problems(text):
    stack = []
    for match in TOKEN.finditer(text):
        token = match.group(0)
        opened = OPEN.fullmatch(token)
        closed = CLOSE.fullmatch(token)
        if opened:
            if opened.group(2):
                continue
            stack.append(opened.group(1))
        elif closed:
            name = closed.group(1)
            if not stack or stack[-1] != name:
                return [("mismatch", stack[-1] if stack else None, name)]
            stack.pop()
    return [("unclosed", stack)] if stack else []

def static_identity(row, target):
    if row.get("id") != target["id"]: raise RuntimeError(f"id mismatch: {target['slug']}")
    if row.get("slug") != target["slug"]: raise RuntimeError(f"slug mismatch: {target['slug']}")
    if row.get("status") != target["status"]: raise RuntimeError(f"status mismatch: {target['slug']}")
    if int(row.get("featured_media") or 0) != target["featured_media"]:
        raise RuntimeError(f"featured_media mismatch: {target['slug']}")

def validate_media(media):
    for media_id, expected_path in media.items():
        q = urllib.parse.urlencode({"context": "edit", "_fields": "id,status,source_url"})
        row, _ = req(f"{SITE}/wp-json/wp/v2/media/{media_id}?{q}")
        actual = urllib.parse.unquote(urllib.parse.urlparse(row.get("source_url") or "").path).casefold()
        if actual != expected_path.casefold():
            raise RuntimeError(f"media mismatch id={media_id}: {actual} != {expected_path}")

def load_and_validate_package(target, current):
    new_content = Path(target["content_file"]).read_text(encoding="utf-8").strip() + "\n"
    if target["salvage_marker"] not in new_content:
        raise RuntimeError(f"salvage marker missing from package: {target['slug']}")
    if target["editorial_marker"] not in new_content:
        raise RuntimeError(f"editorial marker missing from package: {target['slug']}")
    if has_h1(new_content):
        raise RuntimeError(f"H1 forbidden in body: {target['slug']}")
    if block_problems(new_content):
        raise RuntimeError(f"Gutenberg invalid in package: {target['slug']}")
    if count_images(new_content) != target["expected_images"]:
        raise RuntimeError(f"package image count mismatch: {target['slug']}")
    if count_blog_parts(new_content) != count_blog_parts(current):
        raise RuntimeError(f"blog_parts count mismatch: {target['slug']}")
    return new_content

def main():
    before_public = public_counts()
    prepared = []

    # FJ may be old-title state (normal / rolled back) or already-complete state.
    fj_row = get_post(FJ["id"])
    static_identity(fj_row, FJ)
    fj_title = html.unescape(raw(fj_row, "title"))
    fj_content = raw(fj_row, "content")
    if fj_title not in {FJ["old_title"], FJ["new_title"]}:
        raise RuntimeError("FJ title is neither expected old nor expected new value")
    if sha_stripped(fj_content) != FJ["content_sha256_stripped"]:
        raise RuntimeError("FJ body changed since inspection; refusing")
    if block_problems(fj_content):
        raise RuntimeError("FJ Gutenberg invalid")
    prepared.append({
        "target": FJ,
        "kind": "published-title-only",
        "action": "UPDATE" if fj_title == FJ["old_title"] else "ALREADY_UP_TO_DATE",
        "before_row": fj_row,
        "before_content": fj_content,
        "new_content": fj_content,
    })

    # Drafts may be untouched old state OR exact completed package state from a prior partial run.
    for target in DRAFTS:
        row = get_post(target["id"])
        static_identity(row, target)
        current = raw(row, "content")
        current_title = html.unescape(raw(row, "title"))
        new_content = load_and_validate_package(target, current)
        validate_media(target["media"])

        old_state = (
            current_title == target["old_title"]
            and sha_stripped(current) == target["old_content_sha256_stripped"]
            and target["salvage_marker"] in current
            and target["editorial_marker"] not in current
        )
        new_state = (
            current_title == target["new_title"]
            and current.strip() == new_content.strip()
            and target["editorial_marker"] in current
        )
        if not old_state and not new_state:
            raise RuntimeError(
                f"{target['slug']} is neither inspected old state nor exact completed state; refusing overwrite"
            )
        if block_problems(current):
            raise RuntimeError(f"Gutenberg invalid before: {target['slug']}")
        if count_images(current) != target["expected_images"]:
            raise RuntimeError(f"unexpected current image count: {target['slug']}")

        prepared.append({
            "target": target,
            "kind": "draft-salvage",
            "action": "UPDATE" if old_state else "ALREADY_UP_TO_DATE",
            "before_row": row,
            "before_content": current,
            "new_content": new_content,
        })

    changed = []
    try:
        for item in prepared:
            target = item["target"]
            if item["action"] == "UPDATE":
                if item["kind"] == "published-title-only":
                    payload = {"title": target["new_title"]}
                else:
                    payload = {"title": target["new_title"], "content": item["new_content"], "status": "draft"}
                req(f"{SITE}/wp-json/wp/v2/posts/{target['id']}", method="POST", payload=payload)
                # Register immediately so any verification failure also rolls this write back.
                changed.append(item)

            after = get_post(target["id"])
            static_identity(after, target)
            if html.unescape(raw(after, "title")) != target["new_title"]:
                raise RuntimeError(f"final title mismatch: {target['slug']}")

            actual = raw(after, "content")
            if item["kind"] == "published-title-only":
                if sha_stripped(actual) != target["content_sha256_stripped"]:
                    raise RuntimeError("FJ content changed during title-only operation")
                # Publication timestamp guard applies to the published post.
                if after.get("date") != item["before_row"].get("date"):
                    raise RuntimeError("FJ original publication date changed")
                if after.get("date_gmt") != item["before_row"].get("date_gmt"):
                    raise RuntimeError("FJ original publication GMT date changed")
            else:
                if actual.strip() != item["new_content"].strip():
                    raise RuntimeError(f"final content mismatch: {target['slug']}")
                if count_images(actual) != target["expected_images"]:
                    raise RuntimeError(f"final image count mismatch: {target['slug']}")
                if count_blog_parts(actual) != count_blog_parts(item["before_content"]):
                    raise RuntimeError(f"final blog_parts mismatch: {target['slug']}")
                if has_h1(actual):
                    raise RuntimeError(f"H1 found after write: {target['slug']}")
                if block_problems(actual):
                    raise RuntimeError(f"Gutenberg invalid after write: {target['slug']}")

            if item["action"] == "UPDATE" and after.get("modified_gmt") == item["before_row"].get("modified_gmt"):
                raise RuntimeError(f"modified_gmt did not advance: {target['slug']}")

    except Exception:
        for item in reversed(changed):
            target = item["target"]
            try:
                req(
                    f"{SITE}/wp-json/wp/v2/posts/{target['id']}",
                    method="POST",
                    payload={
                        "title": html.unescape(raw(item["before_row"], "title")),
                        "content": item["before_content"],
                        "status": item["before_row"].get("status"),
                        "featured_media": int(item["before_row"].get("featured_media") or 0),
                    },
                )
            except Exception:
                pass
        raise

    after_public = public_counts()
    if before_public != after_public:
        raise RuntimeError(f"published counts changed: {before_public} -> {after_public}")

    print("# FJ title micro-rewrite + two draft salvages reconciliation 2026-09-24")
    print("- result: **SUCCESS**")
    print(f"- public posts: **{before_public['posts']} → {after_public['posts']}**")
    print(f"- public pages: **{before_public['pages']} → {after_public['pages']}**")
    for item in prepared:
        print(f"- {item['target']['slug']}: **{item['action']}** / status **{item['target']['status']}**")
    print("- FJ body: **unchanged**")
    print("- FJ original publication date: **unchanged**")
    print("- draft statuses: **draft preserved**")
    print("- featured media: **unchanged on all 3**")
    print("- draft image counts: **2 / 5 preserved**")
    print("- Gutenberg problems after: **0**")

if __name__ == "__main__":
    main()
