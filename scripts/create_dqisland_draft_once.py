#!/usr/bin/env python3
"""Create the Dragon Quest Island salvage as a new WordPress draft, once and safely."""
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

SITE_URL = "https://tsurikue.com"
USER_AGENT = "tsurikue-dqisland-create/1.0"
TITLE = "ニジゲンノモリのドラゴンクエスト アイランドをレビュー！大人4人で冒険した感想・所要時間"
SLUG = "dqisland"
CATEGORY_ID = 7
FEATURED_MEDIA_ID = 1457
EXCERPT = "淡路島・ニジゲンノモリのドラゴンクエスト アイランドを大人4人で体験。冒険の書、オノコガルドの町、モンスター、ルイーダの酒場まで写真たっぷりでレビューし、現在の所要時間・料金・駐車場もまとめます。"
CONTENT_PATH = Path("editorial/dqisland/content.html")
MUG_B64_PATH = Path("editorial/dqisland/img_3122.jpg.b64")
EXPECTED_MUG_SHA256 = "e5ca43b121cd565b1783422835f35665587decc965a5917bf275f2e6a079903b"
OUT = Path("reports/dqisland-create")
SOURCE_MARKER = "<!-- salvage:source=https://lexus-diary.com/dqisland/ captured=20250624230914 old_date=2024-05-05 -->"
EDITORIAL_MARKER = "<!-- editorial:dqisland:v1 updated=2026-08-28 -->"
PLACEHOLDER = "__MUG_IMAGE_BLOCK__"

EXPECTED_MEDIA = {
    1457: "/wp-content/uploads/2026/05/img_3058.jpg",
    1464: "/wp-content/uploads/2026/05/img_3074.jpg",
    1466: "/wp-content/uploads/2026/05/img_3061.jpg",
    1447: "/wp-content/uploads/2026/05/img_3059.jpg",
    1514: "/wp-content/uploads/2026/05/img_3068.jpg",
    1469: "/wp-content/uploads/2026/05/img_3062.jpg",
    1479: "/wp-content/uploads/2026/05/img_3069.jpg",
    1480: "/wp-content/uploads/2026/05/img_3075.jpg",
    1518: "/wp-content/uploads/2026/05/img_3073.jpg",
    1470: "/wp-content/uploads/2026/05/img_3072.jpg",
    1478: "/wp-content/uploads/2026/05/img_3076.jpg",
    1474: "/wp-content/uploads/2026/05/img_3081.jpg",
    1510: "/wp-content/uploads/2026/05/img_3077.jpg",
    1511: "/wp-content/uploads/2026/05/img_3085.jpg",
}


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def request_json(
    url: str,
    authorization: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    raw_data: bytes | None = None,
    extra_headers: dict[str, str] | None = None,
    timeout: int = 60,
) -> tuple[Any, dict[str, str]]:
    if payload is not None and raw_data is not None:
        raise ValueError("payload and raw_data are mutually exclusive")
    data = None
    headers = {
        "Accept": "application/json",
        "Authorization": authorization,
        "User-Agent": USER_AGENT,
    }
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    elif raw_data is not None:
        data = raw_data
    if extra_headers:
        headers.update(extra_headers)

    last: Exception | None = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8")), dict(response.headers)
        except Exception as exc:
            last = exc
            if attempt == 2:
                raise
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(str(last))


def raw_field(row: dict[str, Any], key: str) -> str:
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def canonical_stem(url: str) -> str:
    filename = Path(urllib.parse.urlparse(url).path).name
    stem = Path(filename).stem.casefold()
    stem = re.sub(r"-\d+x\d+$", "", stem)
    stem = re.sub(r"-scaled$", "", stem)
    stem = re.sub(r"-\d+$", "", stem)
    return stem


def count_published(endpoint: str, auth: str) -> int:
    q = urllib.parse.urlencode({"context": "edit", "status": "publish", "per_page": "1", "_fields": "id"})
    _, headers = request_json(f"{SITE_URL}/wp-json/wp/v2/{endpoint}?{q}", auth)
    return int(headers.get("X-WP-Total", "0"))


def public_counts(auth: str) -> dict[str, int]:
    posts = count_published("posts", auth)
    pages = count_published("pages", auth)
    return {"published_posts": posts, "published_pages": pages, "published_total": posts + pages}


def validate_existing_media(auth: str) -> None:
    for media_id, expected_path in EXPECTED_MEDIA.items():
        q = urllib.parse.urlencode({"context": "edit", "_fields": "id,source_url"})
        row, _ = request_json(f"{SITE_URL}/wp-json/wp/v2/media/{media_id}?{q}", auth)
        if int(row.get("id") or 0) != media_id:
            raise RuntimeError(f"media id mismatch: {media_id}")
        actual = urllib.parse.unquote(urllib.parse.urlparse(row.get("source_url") or "").path).casefold()
        if actual != expected_path.casefold():
            raise RuntimeError(f"media path mismatch id={media_id}: {actual}")


def find_mug_media(auth: str) -> dict[str, Any] | None:
    params = {
        "context": "edit",
        "search": "img_3122",
        "per_page": "100",
        "_fields": "id,slug,source_url",
    }
    rows, _ = request_json(f"{SITE_URL}/wp-json/wp/v2/media?{urllib.parse.urlencode(params)}", auth)
    matches = [row for row in rows if canonical_stem(row.get("source_url") or "") == "img_3122"]
    if len(matches) > 1:
        raise RuntimeError(f"multiple img_3122 media matches: {[row.get('id') for row in matches]}")
    return matches[0] if matches else None


def upload_mug_media(auth: str) -> tuple[dict[str, Any], int]:
    existing = find_mug_media(auth)
    if existing:
        return existing, 0

    encoded = MUG_B64_PATH.read_text(encoding="utf-8").strip()
    try:
        image_bytes = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise RuntimeError(f"invalid mug base64: {exc}") from exc
    actual_sha = sha256_bytes(image_bytes)
    if actual_sha != EXPECTED_MUG_SHA256:
        raise RuntimeError(f"mug image sha256 mismatch: {actual_sha}")
    if not image_bytes.startswith(b"\xff\xd8\xff"):
        raise RuntimeError("mug payload is not a JPEG")

    row, _ = request_json(
        f"{SITE_URL}/wp-json/wp/v2/media",
        auth,
        method="POST",
        raw_data=image_bytes,
        extra_headers={
            "Content-Type": "image/jpeg",
            "Content-Disposition": 'attachment; filename="img_3122.jpg"',
        },
        timeout=90,
    )
    if not row.get("id") or canonical_stem(row.get("source_url") or "") != "img_3122":
        raise RuntimeError(f"unexpected uploaded media response: id={row.get('id')} url={row.get('source_url')}")
    return row, 1


def mug_image_block(media: dict[str, Any]) -> str:
    media_id = int(media.get("id") or 0)
    src = media.get("source_url") or ""
    if not media_id or not src:
        raise RuntimeError("mug media missing id/source_url")
    return (
        f'<!-- wp:image {{"id":{media_id},"sizeSlug":"full","linkDestination":"none"}} -->\n'
        f'<figure class="wp-block-image size-full"><img src="{src}" alt="ルイーダの酒場で購入し数年後も自宅で使っているタル型ジョッキ2個" class="wp-image-{media_id}"/>'
        '<figcaption class="wp-element-caption">数年後も我が家に残っているタル型ジョッキ。しかも2個。</figcaption></figure>\n'
        '<!-- /wp:image -->'
    )


def build_content(mug_media: dict[str, Any]) -> str:
    template = CONTENT_PATH.read_text(encoding="utf-8")
    if template.count(PLACEHOLDER) != 1:
        raise RuntimeError(f"mug placeholder expected once, found {template.count(PLACEHOLDER)}")
    if "<h1" in template.casefold():
        raise RuntimeError("body must not contain H1")
    if "lexus-diary.com" in template:
        raise RuntimeError("visible content must not hotlink old site")
    content = template.replace(PLACEHOLDER, mug_image_block(mug_media), 1)
    content = SOURCE_MARKER + "\n" + EDITORIAL_MARKER + "\n" + content
    return content


def fetch_posts_by_slug(auth: str, status: str) -> list[dict[str, Any]]:
    params = {
        "context": "edit",
        "status": status,
        "slug": SLUG,
        "per_page": "100",
        "_fields": "id,slug,status,title,content,excerpt,featured_media,categories,modified,link",
    }
    rows, _ = request_json(f"{SITE_URL}/wp-json/wp/v2/posts?{urllib.parse.urlencode(params)}", auth)
    return list(rows)


def validate_draft(row: dict[str, Any], expected_content: str) -> None:
    if row.get("status") != "draft":
        raise RuntimeError("target is not draft")
    if str(row.get("slug") or "") != SLUG:
        raise RuntimeError("slug mismatch")
    if html.unescape(raw_field(row, "title")) != TITLE:
        raise RuntimeError("title mismatch")
    if int(row.get("featured_media") or 0) != FEATURED_MEDIA_ID:
        raise RuntimeError("featured media mismatch")
    categories = [int(value) for value in (row.get("categories") or [])]
    if categories != [CATEGORY_ID]:
        raise RuntimeError(f"category mismatch: {categories}")
    actual_content = raw_field(row, "content").strip()
    if actual_content != expected_content.strip():
        raise RuntimeError(
            "existing draft content differs; refusing overwrite: " + sha256_text(actual_content)
        )


def write_report(report: dict[str, Any]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Dragon Quest Island draft creation",
        "",
        f"- action: **{report['action']}**",
        f"- post_id: **{report['post_id']}**",
        f"- status: **{report['status']}**",
        f"- slug: `{SLUG}`",
        f"- category_id: **{CATEGORY_ID}**",
        f"- featured_media: **{FEATURED_MEDIA_ID}**",
        f"- mug_media_id: **{report['mug_media_id']}**",
        f"- mug_media_url: {report['mug_media_url']}",
        f"- media_upload_count: **{report['media_upload_count']}**",
        f"- wordpress_write_count: **{report['wordpress_write_count']}**",
        f"- published_before: **{report['public_before']['published_total']}**",
        f"- published_after: **{report['public_after']['published_total']}**",
        f"- content_sha256: `{report['content_sha256']}`",
        "- publish_count: **0**",
    ]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")
    auth = auth_header(user, password)

    before_counts = public_counts(auth)
    validate_existing_media(auth)

    published = fetch_posts_by_slug(auth, "publish")
    if published:
        raise RuntimeError(f"published /{SLUG}/ already exists; refusing create")

    mug_media, media_upload_count = upload_mug_media(auth)
    expected_content = build_content(mug_media)

    drafts = fetch_posts_by_slug(auth, "draft")
    if len(drafts) > 1:
        raise RuntimeError(f"multiple /{SLUG}/ drafts found: {[row.get('id') for row in drafts]}")

    if drafts:
        row = drafts[0]
        validate_draft(row, expected_content)
        action = "ALREADY_UP_TO_DATE"
        post_id = int(row.get("id") or 0)
        post_write_count = 0
    else:
        payload = {
            "title": TITLE,
            "slug": SLUG,
            "status": "draft",
            "content": expected_content,
            "excerpt": EXCERPT,
            "featured_media": FEATURED_MEDIA_ID,
            "categories": [CATEGORY_ID],
        }
        created, _ = request_json(
            f"{SITE_URL}/wp-json/wp/v2/posts",
            auth,
            method="POST",
            payload=payload,
            timeout=90,
        )
        post_id = int(created.get("id") or 0)
        if not post_id or created.get("status") != "draft":
            raise RuntimeError(f"unexpected create response: id={post_id} status={created.get('status')}")
        action = "CREATE_DRAFT"
        post_write_count = 1

    q = urllib.parse.urlencode({
        "context": "edit",
        "_fields": "id,slug,status,title,content,excerpt,featured_media,categories,modified,link",
    })
    after_row, _ = request_json(f"{SITE_URL}/wp-json/wp/v2/posts/{post_id}?{q}", auth)
    validate_draft(after_row, expected_content)

    after_counts = public_counts(auth)
    if before_counts != after_counts:
        raise RuntimeError(f"published counts changed: {before_counts} -> {after_counts}")

    report = {
        "action": action,
        "post_id": post_id,
        "status": "draft",
        "mug_media_id": int(mug_media.get("id") or 0),
        "mug_media_url": mug_media.get("source_url") or "",
        "media_upload_count": media_upload_count,
        "wordpress_write_count": media_upload_count + post_write_count,
        "public_before": before_counts,
        "public_after": after_counts,
        "content_sha256": sha256_text(expected_content),
        "publish_count": 0,
    }
    write_report(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
