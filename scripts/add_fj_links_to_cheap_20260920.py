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
UA = "tsurikue-fj-links-to-cheap-20260920/1.0"
CHEAP_URL = "https://tsurikue.com/landcruiser-fj-cheap/"

POSTS = {
    3767: {
        "slug": "landcruiser-fj-price",
        "status": "publish",
        "title": "ランドクルーザーFJの乗り出し価格はいくら？実際の見積り総額は550万516円",
        "sha": "8cd3d9973a6d42ed2cec7fe3d96a21c99519e9f703e073a3a15061ba2377a566",
        "anchor": """<!-- wp:shortcode -->
[blog_parts id="3788"]
<!-- /wp:shortcode -->

<!-- wp:paragraph -->
<p></p>
<!-- /wp:paragraph -->""",
        "replacement": """<!-- wp:shortcode -->
[blog_parts id="3788"]
<!-- /wp:shortcode -->

<!-- wp:paragraph -->
<p>550万円を見て「高っ」となった人は、オプションを削る前にこっちも見てみてください。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><a href="https://tsurikue.com/landcruiser-fj-cheap/">ランドクルーザーFJを安く買う方法｜欲しいオプションを諦めず負担を減らす5つのコツ</a></p>
<!-- /wp:paragraph -->""",
        "phrase": "550万円を見て「高っ」となった人は",
    },
    3774: {
        "slug": "landcruiser-fj-review",
        "status": "publish",
        "title": "ランドクルーザーFJ実車レビュー｜実際に乗って分かった良い点・残念な点",
        "sha": "a37b41cc6663b214fc1f946c62de6f219024d15affb0d4a67143b95e4197982a",
        "anchor": """<!-- wp:shortcode -->
[blog_parts id="3788"]
<!-- /wp:shortcode -->""",
        "replacement": """<!-- wp:shortcode -->
[blog_parts id="3788"]
<!-- /wp:shortcode -->

<!-- wp:paragraph -->
<p>「乗ってみたい」が「欲しい」に変わってきたら、次に気になるのはやっぱり予算です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><a href="https://tsurikue.com/landcruiser-fj-cheap/">欲しい装備をなるべく残してFJの負担を減らす方法はこちら</a></p>
<!-- /wp:paragraph -->""",
        "phrase": "「乗ってみたい」が「欲しい」に変わってきたら",
    },
    3778: {
        "slug": "landcruiser-fj-drawbacks",
        "status": "publish",
        "title": "ランドクルーザーFJは後悔する？実際に買って気づいた残念なところ4選",
        "sha": "ecd779d275fc4c4291b65b7f1c20ee2a5c169d85e977b7f984fa89290fd3dcf0",
        "anchor": """<!-- wp:paragraph -->
<p>気になるところがあるなら、納車後に「知らなかった」となる前に一度見ておくと安心です。</p>
<!-- /wp:paragraph -->""",
        "replacement": """<!-- wp:paragraph -->
<p>気になるところがあるなら、納車後に「知らなかった」となる前に一度見ておくと安心です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>この4つを見ても「やっぱりFJが欲しい」なら、次は予算の話です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><a href="https://tsurikue.com/landcruiser-fj-cheap/">ランドクルーザーFJを安く買う方法｜欲しい装備を諦めず負担を減らす5つのコツ</a></p>
<!-- /wp:paragraph -->""",
        "phrase": "この4つを見ても「やっぱりFJが欲しい」なら",
    },
    3777: {
        "slug": "landcruiser-fj-rear-seat",
        "status": "draft",
        "title": "ランドクルーザーFJの後部座席は狭い？実車写真で広さを確認",
        "sha": "e639dc7c389cf2b78dfc9570904b17e1bee90862b3a78b9fd4d02fdc8a7e6457",
        "anchor": """<!-- wp:shortcode -->
[blog_parts id="3788"]
<!-- /wp:shortcode -->""",
        "replacement": """<!-- wp:shortcode -->
[blog_parts id="3788"]
<!-- /wp:shortcode -->

<!-- wp:paragraph -->
<p>後席もこれなら使えそう、と思ったら次に気になるのは値段です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><a href="https://tsurikue.com/landcruiser-fj-cheap/">欲しい装備をなるべく残してFJの負担を減らす方法はこちら</a></p>
<!-- /wp:paragraph -->""",
        "phrase": "後席もこれなら使えそう、と思ったら",
    },
}


def auth_header() -> str:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise RuntimeError("missing WordPress secrets")
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()


def request(method: str, path: str, payload=None):
    headers = {
        "Authorization": auth_header(),
        "Accept": "application/json",
        "User-Agent": UA,
    }
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


def get_post(post_id: int) -> dict:
    q = urllib.parse.urlencode({
        "context": "edit",
        "_fields": "id,slug,status,title,content,author,featured_media,categories",
    })
    row, _ = request("GET", f"/wp-json/wp/v2/posts/{post_id}?{q}")
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


def public_count(endpoint: str) -> int:
    q = urllib.parse.urlencode({"status": "publish", "per_page": 1, "_fields": "id"})
    _, headers = request("GET", f"/wp-json/wp/v2/{endpoint}?{q}")
    for key, value in headers.items():
        if key.lower() == "x-wp-total":
            return int(value)
    raise RuntimeError(f"missing X-WP-Total for {endpoint}")


def validate_before(post_id: int, cfg: dict, row: dict) -> tuple[dict, str, str]:
    ident = identity(row)
    if ident["id"] != post_id:
        raise RuntimeError(f"{post_id}: id mismatch")
    if ident["slug"] != cfg["slug"]:
        raise RuntimeError(f"{post_id}: slug mismatch: {ident['slug']}")
    if ident["status"] != cfg["status"]:
        raise RuntimeError(f"{post_id}: status mismatch: {ident['status']}")
    if ident["title"] != cfg["title"]:
        raise RuntimeError(f"{post_id}: title mismatch: {ident['title']}")

    current = raw(row, "content")
    current_sha = sha256(current)

    if cfg["phrase"] in current and CHEAP_URL in current:
        return ident, current, "ALREADY_LINKED"

    if current_sha != cfg["sha"]:
        raise RuntimeError(
            f"{post_id}: content sha mismatch: {current_sha} != {cfg['sha']}"
        )
    if current.count(cfg["anchor"]) != 1:
        raise RuntimeError(
            f"{post_id}: anchor count {current.count(cfg['anchor'])}, expected 1"
        )
    return ident, current, "UPDATE"


def main() -> None:
    posts_before = public_count("posts")
    pages_before = public_count("pages")

    snapshots = {}
    targets = {}
    actions = {}

    # Preflight every post before the first write.
    for post_id, cfg in POSTS.items():
        row = get_post(post_id)
        ident, current, action = validate_before(post_id, cfg, row)
        snapshots[post_id] = {"identity": ident, "content": current}
        actions[post_id] = action
        if action == "UPDATE":
            target = current.replace(cfg["anchor"], cfg["replacement"], 1)
            if target.count(CHEAP_URL) != current.count(CHEAP_URL) + 1:
                raise RuntimeError(f"{post_id}: cheap URL count did not increase by 1")
            if cfg["phrase"] not in target:
                raise RuntimeError(f"{post_id}: inserted phrase missing")
            targets[post_id] = target

    updated = []
    try:
        for post_id, target in targets.items():
            request("POST", f"/wp-json/wp/v2/posts/{post_id}", {"content": target})
            updated.append(post_id)

            check = get_post(post_id)
            if identity(check) != snapshots[post_id]["identity"]:
                raise RuntimeError(f"{post_id}: identity changed after update")
            final_content = raw(check, "content")
            if final_content != target:
                raise RuntimeError(f"{post_id}: final content mismatch")
            if POSTS[post_id]["phrase"] not in final_content:
                raise RuntimeError(f"{post_id}: final phrase missing")
            if CHEAP_URL not in final_content:
                raise RuntimeError(f"{post_id}: cheap URL missing after update")

        # Re-check posts that were already linked too.
        for post_id, cfg in POSTS.items():
            check = get_post(post_id)
            if identity(check) != snapshots[post_id]["identity"]:
                raise RuntimeError(f"{post_id}: identity changed in final verification")
            final_content = raw(check, "content")
            if cfg["phrase"] not in final_content:
                raise RuntimeError(f"{post_id}: expected transition phrase missing")
            if CHEAP_URL not in final_content:
                raise RuntimeError(f"{post_id}: cheap URL missing in final verification")

        posts_after = public_count("posts")
        pages_after = public_count("pages")
        if posts_after != posts_before:
            raise RuntimeError(f"published posts changed: {posts_before} -> {posts_after}")
        if pages_after != pages_before:
            raise RuntimeError(f"published pages changed: {pages_before} -> {pages_after}")

    except Exception:
        # Best-effort rollback for posts changed by this run.
        for post_id in reversed(updated):
            try:
                request(
                    "POST",
                    f"/wp-json/wp/v2/posts/{post_id}",
                    {"content": snapshots[post_id]["content"]},
                )
            except Exception as rollback_exc:
                print(f"ROLLBACK_FAILED {post_id}: {rollback_exc}")
        raise

    print("# FJ articles -> cheap article links 2026-09-20")
    print("- result: **SUCCESS**")
    print(f"- published posts before/after: **{posts_before} / {posts_after}**")
    print(f"- published pages before/after: **{pages_before} / {pages_after}**")
    for post_id in sorted(POSTS):
        cfg = POSTS[post_id]
        print(
            f"- {post_id} {cfg['slug']}: **{actions[post_id]}** -> "
            f"{cfg['status']} / {cfg['phrase']}"
        )


if __name__ == "__main__":
    main()
