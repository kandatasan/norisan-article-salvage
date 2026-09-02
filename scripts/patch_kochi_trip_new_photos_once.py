#!/usr/bin/env python3
"""Safely patch the current Kochi draft with four newly confirmed user photos."""
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

SITE_URL = "https://tsurikue.com"
POST_ID = 3384
SLUG = "kochi-1night-2days-drive"
EXPECTED_STATUS = "draft"
EXPECTED_CURRENT_SHA256 = "431895b36dd4d594f638ff95cba5b8aa428f5ca468b57255d53746f7782ad5f8"
OUT = Path("reports/kochi-photo-patch-20260903")
USER_AGENT = "tsurikue-kochi-photo-patch/1.0"
NEW_MEDIA = {
    3393: "/wp-content/uploads/2026/09/19890c96-7b96-4aa9-9b9d-ad1cfec91397.jpg",
    3394: "/wp-content/uploads/2026/09/49c84656-d80c-445f-8d6e-0871a7a9b7f6.jpg",
    3395: "/wp-content/uploads/2026/09/400b630d-20e7-408e-89b9-df6e3542e03a.jpg",
    3396: "/wp-content/uploads/2026/09/c411bbe7-9abd-49e9-8edf-7806e8fb5fa7.jpg",
}


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return "Basic " + token


def request_json(url: str, auth: str, *, method: str = "GET", payload: dict[str, Any] | None = None, timeout: int = 60):
    data = None
    headers = {"Authorization": auth, "Accept": "application/json", "User-Agent": USER_AGENT}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8")), dict(response.headers)
        except Exception as exc:
            last = exc
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(str(last))


def raw_field(row: dict[str, Any], key: str) -> str:
    value = row.get(key) or {}
    if isinstance(value, dict):
        return html.unescape(value.get("raw") or value.get("rendered") or "")
    return html.unescape(str(value))


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def count_published(auth: str) -> int:
    total = 0
    for endpoint in ("posts", "pages"):
        q = urllib.parse.urlencode({"context": "edit", "status": "publish", "per_page": 1, "_fields": "id"})
        _, headers = request_json(f"{SITE_URL}/wp-json/wp/v2/{endpoint}?{q}", auth)
        total += int(headers.get("X-WP-Total", "0"))
    return total


def validate_media(auth: str) -> None:
    for media_id, expected_path in NEW_MEDIA.items():
        q = urllib.parse.urlencode({"context": "edit", "_fields": "id,source_url,mime_type"})
        row, _ = request_json(f"{SITE_URL}/wp-json/wp/v2/media/{media_id}?{q}", auth)
        actual = urllib.parse.unquote(urllib.parse.urlparse(row.get("source_url") or "").path)
        if int(row.get("id") or 0) != media_id or actual.casefold() != expected_path.casefold():
            raise RuntimeError(f"media mismatch id={media_id}: {actual}")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")
    auth = auth_header(user, password)
    validate_media(auth)

    before_public = count_published(auth)
    q = urllib.parse.urlencode({"context": "edit", "_fields": "id,slug,status,title,content,featured_media,categories,modified"})
    row, _ = request_json(f"{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}?{q}", auth)
    if int(row.get("id") or 0) != POST_ID or row.get("status") != EXPECTED_STATUS or row.get("slug") != SLUG:
        raise RuntimeError("target metadata changed; refusing patch")
    current = raw_field(row, "content").strip()
    current_sha = sha(current)
    if current_sha != EXPECTED_CURRENT_SHA256:
        raise RuntimeError("draft changed after audit; refusing patch: " + current_sha)

    taimeshi_old = '''<!-- wp:image {"id":1704,"sizeSlug":"large"} -->
<figure class="wp-block-image size-large"><img src="https://tsurikue.com/wp-content/uploads/2026/05/img_4568.jpg" alt="宇和島鯛めし" class="wp-image-1704"/><figcaption class="wp-element-caption">愛媛で宇和島鯛めし。</figcaption></figure>
<!-- /wp:image -->

<!-- wp:paragraph -->
<p>商店街を歩いて、みかんジュースの蛇口を見つけて、昼は宇和島鯛めし。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>鯛の刺身、卵、タレ、ごはん。<br>全部を合わせていただきます。</p>
<!-- /wp:paragraph -->'''
    taimeshi_new = '''<!-- wp:image {"id":3393,"sizeSlug":"large"} -->
<figure class="wp-block-image size-large"><img src="https://tsurikue.com/wp-content/uploads/2026/09/19890c96-7b96-4aa9-9b9d-ad1cfec91397.jpg" alt="道後で見つけたみかんジュースの蛇口と3杯のジュース" class="wp-image-3393"/><figcaption class="wp-element-caption">道後で見つけた、みかんジュースの蛇口。3杯並べると色の違いも分かります。</figcaption></figure>
<!-- /wp:image -->

<!-- wp:paragraph -->
<p>商店街を歩いていると、みかんジュースの蛇口。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>愛媛に来た感をしっかり味わったところで、昼は宇和島鯛めしです。</p>
<!-- /wp:paragraph -->

<!-- wp:image {"id":3395,"sizeSlug":"large"} -->
<figure class="wp-block-image size-large"><img src="https://tsurikue.com/wp-content/uploads/2026/09/400b630d-20e7-408e-89b9-df6e3542e03a.jpg" alt="宇和島鯛めしの具材と自分で作った鯛めし丼" class="wp-image-3395"/><figcaption class="wp-element-caption">鯛の刺身や卵、薬味を自分でごはんにのせて、鯛めし丼にしました。</figcaption></figure>
<!-- /wp:image -->

<!-- wp:paragraph -->
<p>鯛の刺身、卵、薬味、タレ、ごはんが別々に出てきて、自分で好きなようにのっけます。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>そして完成したのが写真右。<br>自分で丼にしていく時間まで含めて、楽しい昼ごはんでした。</p>
<!-- /wp:paragraph -->'''
    patched = replace_once(current, taimeshi_old, taimeshi_new, "taimeshi section")

    yosakoi_anchor = '''<!-- wp:paragraph -->
<p><strong>これだけで旅行に来て良かった。</strong><br>そう感じるくらい楽しかったです。</p>
<!-- /wp:paragraph -->'''
    yosakoi_new = yosakoi_anchor + '''

<!-- wp:image {"id":3394,"sizeSlug":"large"} -->
<figure class="wp-block-image size-large"><img src="https://tsurikue.com/wp-content/uploads/2026/09/49c84656-d80c-445f-8d6e-0871a7a9b7f6.jpg" alt="OMO7高知のよさこい体験後に鳴子を持って撮った記念写真" class="wp-image-3394"/><figcaption class="wp-element-caption">よさこい体験のあとに記念写真。ここは本当に旅のハイライトでした。</figcaption></figure>
<!-- /wp:image -->'''
    patched = replace_once(patched, yosakoi_anchor, yosakoi_new, "yosakoi photo")

    izakaya_anchor = '''<!-- wp:paragraph -->
<p>そこで近くの居酒屋へ行き、地のものをいただきます。</p>
<!-- /wp:paragraph -->'''
    izakaya_new = izakaya_anchor + '''

<!-- wp:image {"id":3396,"sizeSlug":"large"} -->
<figure class="wp-block-image size-large"><img src="https://tsurikue.com/wp-content/uploads/2026/09/c411bbe7-9abd-49e9-8edf-7806e8fb5fa7.jpg" alt="高知の居酒屋で食べた料理の4枚グリッド" class="wp-image-3396"/><figcaption class="wp-element-caption">夜の居酒屋では、地のものをいろいろ。高知の夜はここからやっと本番です。</figcaption></figure>
<!-- /wp:image -->'''
    patched = replace_once(patched, izakaya_anchor, izakaya_new, "izakaya grid")

    if "editorial:kochi-1night-2days-drive:photo-patch:v1" not in patched:
        patched = patched.replace("<!-- wp:paragraph -->\n<p>高知へ1泊2日でドライブしてきました。</p>", "<!-- editorial:kochi-1night-2days-drive:photo-patch:v1 -->\n<!-- wp:paragraph -->\n<p>高知へ1泊2日でドライブしてきました。</p>", 1)

    for media_id, path in NEW_MEDIA.items():
        if f"wp-image-{media_id}" not in patched or path not in patched:
            raise RuntimeError(f"new media missing from patched content: {media_id}")
    if "自分で好きなようにのっけます" not in patched:
        raise RuntimeError("taimeshi clarification missing")

    updated, _ = request_json(
        f"{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}", auth, method="POST",
        payload={"content": patched, "status": "draft"}, timeout=90,
    )
    if int(updated.get("id") or 0) != POST_ID or updated.get("status") != "draft":
        raise RuntimeError("unexpected update response")

    after, _ = request_json(f"{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}?{q}", auth)
    after_content = raw_field(after, "content").strip()
    if after_content != patched:
        raise RuntimeError("content mismatch after patch: " + sha(after_content))
    after_public = count_published(auth)
    if after_public != before_public:
        raise RuntimeError(f"published count changed: {before_public} -> {after_public}")

    report = {
        "action": "PATCH_DRAFT",
        "post_id": POST_ID,
        "status": after.get("status"),
        "old_content_sha256": current_sha,
        "new_content_sha256": sha(patched),
        "new_media_ids": sorted(NEW_MEDIA),
        "wordpress_write_count": 1,
        "published_before": before_public,
        "published_after": after_public,
        "publish_count": 0,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "summary.md").write_text(
        "# Kochi new-photo patch\n\n"
        f"- action: **{report['action']}**\n- post_id: **{POST_ID}**\n- status: **draft**\n"
        f"- new_media_ids: **{', '.join(map(str, report['new_media_ids']))}**\n"
        f"- old_content_sha256: `{current_sha}`\n- new_content_sha256: `{report['new_content_sha256']}`\n"
        f"- wordpress_write_count: **1**\n- published_before: **{before_public}**\n- published_after: **{after_public}**\n- publish_count: **0**\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
