#!/usr/bin/env python3
"""Finish the Okunoshima draft: remove intro/H2 duplication and insert uploaded media."""
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
USER_AGENT = "tsurikue-okunoshima-media-finish/1.0"
POST_ID = 3730
SLUG = "okunoshima-rabbit-island"
EXPECTED_TITLE = "大久野島へ行ってきた！うさぎはどこにいる？紅葉・廃墟・釣りまで島を一周"
OUT = Path("reports/okunoshima-rabbit-island-finish")

PHOTO_SPECS = {
    "IMG_8243": {
        "alt": "大久野島で出会った茶色いうさぎ",
        "caption": "島を歩いていると、木陰からこちらを見るうさぎ。",
    },
    "IMG_5547": {
        "alt": "大久野島を時計回りに歩き始めた道の風景",
        "caption": "フェリーを降りて、島を時計回りに歩き始めました。",
    },
    "IMG_8250": {
        "alt": "大久野島の木の下で休む黒いうさぎ",
        "caption": "歩いていくと、木陰や道の脇にうさぎが増えてきます。",
    },
    "IMG_5543": {
        "alt": "大久野島で見た黒いうさぎのアップ",
        "caption": "近くで見ると表情までよく分かります。",
    },
    "IMG_8252": {
        "alt": "大久野島に残る古いコンクリートの戦争遺構",
        "caption": "島内には戦争の歴史を伝える遺構が残っています。",
    },
    "IMG_8248": {
        "alt": "大久野島の青い海と赤く色づいた木",
        "caption": "11月は青い海と紅葉の組み合わせがきれいでした。",
    },
    "IMG_8247": {
        "alt": "大久野島で赤やオレンジに色づいた紅葉",
        "caption": "島内では赤やオレンジに色づいた葉も楽しめました。",
    },
    "IMG_8246": {
        "alt": "大久野島の紅葉した木々",
        "caption": "うさぎだけでなく、秋の島歩きそのものが気持ちいい。",
    },
    "IMG_5542": {
        "alt": "大久野島の休暇村バスと海沿いの紅葉",
        "caption": "海沿いへ出ると、遺構周辺とはまた違う明るい景色になります。",
    },
}

PLACEHOLDERS = {
    "IMG_5547": "<!-- photo-slot: IMG_5547.jpeg 島を時計回りに歩き始めた道の風景 -->",
    "IMG_8250": "<!-- photo-slot: IMG_8250.jpeg 木の下で休む黒いうさぎ -->",
    "IMG_5543": "<!-- photo-slot: IMG_5543.jpeg 黒いうさぎのアップ -->",
    "IMG_8252": "<!-- photo-slot: IMG_8252.jpeg 島内で見た古いコンクリートの遺構 -->",
    "IMG_8248": "<!-- photo-slot: IMG_8248.jpeg 青い海と赤く色づいた木 -->",
    "IMG_8247": "<!-- photo-slot: IMG_8247.jpeg 赤やオレンジに色づいた葉のアップ -->",
    "IMG_8246": "<!-- photo-slot: IMG_8246.jpeg 島内の紅葉した木々 -->",
    "IMG_5542": "<!-- photo-slot: IMG_5542.jpeg 休暇村のバスと海沿いの紅葉 -->",
}

OLD_FIRST_SECTION = """<!-- wp:heading -->
<h2 class="wp-block-heading">大久野島を知ったきっかけは忠海港の大行列</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>最初に大久野島の存在を知ったのは、たまたま忠海港の近くを車で通ったときです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>港のあたりに、ものすごい人数の行列。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>観光地の入口でもない場所にこれだけ人が並んでいると、さすがに気になります。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>調べてみると、ここから船で渡れる大久野島が<strong>「うさぎ島」</strong>として人気らしい。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>それで妻と「今度行ってみよう」となりました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>実際に行った日も忠海港はかなりの人。<br>フェリー乗り場の写真を撮ろうと思う余裕もないくらい混んでいました。</p>
<!-- /wp:paragraph -->"""

NEW_FIRST_SECTION = """<!-- wp:heading -->
<h2 class="wp-block-heading">忠海港は行った日も大混雑｜船で約15分</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>そして実際に大久野島へ向かった日。<br>忠海港へ着くと、あのとき見たのと同じように人がいっぱい。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>フェリー乗り場の写真を撮ろうと思う余裕もないくらい混んでいました。</p>
<!-- /wp:paragraph -->"""

RABBIT_INSERT_AFTER = """<!-- wp:paragraph -->
<p><strong>いる。ちゃんといる。</strong></p>
<!-- /wp:paragraph -->"""


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def request_json(
    url: str,
    authorization: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: int = 60,
) -> tuple[Any, dict[str, str]]:
    data = None
    headers = {
        "Accept": "application/json",
        "Authorization": authorization,
        "User-Agent": USER_AGENT,
    }
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"

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
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(str(last))


def raw_field(row: dict[str, Any], key: str) -> str:
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def count_published(endpoint: str, auth: str) -> int:
    q = urllib.parse.urlencode({
        "context": "edit",
        "status": "publish",
        "per_page": "1",
        "_fields": "id",
    })
    _, headers = request_json(f"{SITE_URL}/wp-json/wp/v2/{endpoint}?{q}", auth)
    return int(headers.get("X-WP-Total", "0"))


def public_counts(auth: str) -> dict[str, int]:
    posts = count_published("posts", auth)
    pages = count_published("pages", auth)
    return {
        "published_posts": posts,
        "published_pages": pages,
        "published_total": posts + pages,
    }


def canonical_stem(url: str) -> str:
    filename = Path(urllib.parse.urlparse(url).path).name
    stem = Path(urllib.parse.unquote(filename)).stem
    stem = re.sub(r"-\d+x\d+$", "", stem)
    stem = re.sub(r"-scaled$", "", stem)
    stem = re.sub(r"-\d+$", "", stem)
    return stem.casefold()


def find_media(auth: str, stem: str) -> dict[str, Any]:
    found: dict[int, dict[str, Any]] = {}
    for query in (stem, stem.lower()):
        params = {
            "context": "edit",
            "search": query,
            "per_page": "100",
            "_fields": "id,slug,source_url,mime_type,media_details",
        }
        rows, _ = request_json(
            f"{SITE_URL}/wp-json/wp/v2/media?{urllib.parse.urlencode(params)}",
            auth,
        )
        for row in rows:
            if canonical_stem(row.get("source_url") or "") == stem.casefold():
                found[int(row["id"])] = row

    if not found:
        params = {
            "context": "edit",
            "slug": stem.lower().replace("_", "-"),
            "per_page": "100",
            "_fields": "id,slug,source_url,mime_type,media_details",
        }
        rows, _ = request_json(
            f"{SITE_URL}/wp-json/wp/v2/media?{urllib.parse.urlencode(params)}",
            auth,
        )
        for row in rows:
            if canonical_stem(row.get("source_url") or "") == stem.casefold():
                found[int(row["id"])] = row

    if not found:
        raise RuntimeError(f"media lookup for {stem} found 0 matches")
    # 同名画像が既に残っている場合は、今回ユーザーがアップした新しい方を採用する。
    # WordPressのattachment IDは後から追加したものほど大きくなるため、最大IDを選ぶ。
    row = found[max(found)]
    if not str(row.get("mime_type") or "").startswith("image/"):
        raise RuntimeError(f"{stem} is not an image")
    return row


def image_block(row: dict[str, Any], spec: dict[str, str]) -> str:
    media_id = int(row["id"])
    src = row.get("source_url") or ""
    return (
        f'<!-- wp:image {{"id":{media_id},"sizeSlug":"large","linkDestination":"none"}} -->\n'
        f'<figure class="wp-block-image size-large"><img src="{src}" alt="{html.escape(spec["alt"], quote=True)}" '
        f'class="wp-image-{media_id}"/><figcaption class="wp-element-caption">'
        f'{html.escape(spec["caption"])}</figcaption></figure>\n'
        '<!-- /wp:image -->'
    )


def fetch_target(auth: str) -> dict[str, Any]:
    q = urllib.parse.urlencode({
        "context": "edit",
        "_fields": "id,slug,status,title,content,featured_media,categories,link,modified",
    })
    row, _ = request_json(f"{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}?{q}", auth)
    if int(row.get("id") or 0) != POST_ID:
        raise RuntimeError("post id mismatch")
    if row.get("slug") != SLUG or row.get("status") != "draft":
        raise RuntimeError(f"unexpected target metadata: slug={row.get('slug')} status={row.get('status')}")
    if html.unescape(raw_field(row, "title")) != EXPECTED_TITLE:
        raise RuntimeError("title mismatch")
    content = raw_field(row, "content")
    if "<!-- editorial:okunoshima-rabbit-island:create-guard:v1 -->" not in content:
        raise RuntimeError("create guard marker missing")
    return row


def transform(content: str, media: dict[str, dict[str, Any]]) -> str:
    if OLD_FIRST_SECTION not in content and NEW_FIRST_SECTION not in content:
        raise RuntimeError("first-section baseline not found")
    if OLD_FIRST_SECTION in content:
        content = content.replace(OLD_FIRST_SECTION, NEW_FIRST_SECTION, 1)

    for stem, placeholder in PLACEHOLDERS.items():
        block = image_block(media[stem], PHOTO_SPECS[stem])
        if placeholder in content:
            content = content.replace(placeholder, block, 1)
        elif f"wp-image-{int(media[stem]['id'])}" not in content:
            raise RuntimeError(f"missing placeholder and image for {stem}")

    rabbit = media["IMG_8243"]
    rabbit_class = f"wp-image-{int(rabbit['id'])}"
    if rabbit_class not in content:
        if RABBIT_INSERT_AFTER not in content:
            raise RuntimeError("rabbit insertion anchor missing")
        content = content.replace(
            RABBIT_INSERT_AFTER,
            RABBIT_INSERT_AFTER + "\n\n" + image_block(rabbit, PHOTO_SPECS["IMG_8243"]),
            1,
        )

    if "<!-- photo-slot:" in content:
        raise RuntimeError("photo slots remain after transform")
    if content.count("忠海港は行った日も大混雑｜船で約15分") != 1:
        raise RuntimeError("revised first H2 missing or duplicated")
    for stem, row in media.items():
        if f"wp-image-{int(row['id'])}" not in content:
            raise RuntimeError(f"image not present after transform: {stem}")
    return content


def write_report(report: dict[str, Any]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "result.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    media = report["media"]
    lines = [
        "# Okunoshima draft finish",
        "",
        f"- action: **{report['action']}**",
        f"- post_id: **{POST_ID}**",
        "- status: **draft**",
        f"- slug: {SLUG}",
        f"- featured_media: **{report['featured_media']}** (IMG_8243)",
        f"- inserted_images: **{len(media)}**",
        "- remaining_photo_slots: **0**",
        "- first_h2: **忠海港は行った日も大混雑｜船で約15分**",
        f"- wordpress_write_count: **{report['wordpress_write_count']}**",
        f"- published_before: **{report['public_before']['published_total']}**",
        f"- published_after: **{report['public_after']['published_total']}**",
        f"- content_sha256: {report['content_sha256']}",
        "",
        "## Media",
    ]
    for stem in PHOTO_SPECS:
        row = media[stem]
        lines.append(f"- {stem}: media **#{row['id']}** — {row['source_url']}")
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")
    auth = auth_header(user, password)

    before = public_counts(auth)
    row = fetch_target(auth)
    original = raw_field(row, "content").strip()

    media: dict[str, dict[str, Any]] = {}
    for stem in PHOTO_SPECS:
        media[stem] = find_media(auth, stem)

    expected = transform(original, media).strip()
    featured_media = int(media["IMG_8243"]["id"])

    current_featured = int(row.get("featured_media") or 0)
    if original == expected and current_featured == featured_media:
        action = "ALREADY_UP_TO_DATE"
        write_count = 0
    else:
        payload = {
            "content": expected,
            "featured_media": featured_media,
        }
        updated, _ = request_json(
            f"{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}",
            auth,
            method="POST",
            payload=payload,
            timeout=90,
        )
        if updated.get("status") != "draft":
            raise RuntimeError(f"unexpected status after update: {updated.get('status')}")
        action = "UPDATE_DRAFT"
        write_count = 1

    after_row = fetch_target(auth)
    after_content = raw_field(after_row, "content").strip()
    if after_content != expected:
        raise RuntimeError("post content verification mismatch")
    if int(after_row.get("featured_media") or 0) != featured_media:
        raise RuntimeError("featured media verification mismatch")

    after = public_counts(auth)
    if before != after:
        raise RuntimeError(f"published counts changed: {before} -> {after}")

    report_media = {
        stem: {
            "id": int(m["id"]),
            "source_url": m.get("source_url") or "",
            "width": (m.get("media_details") or {}).get("width"),
            "height": (m.get("media_details") or {}).get("height"),
        }
        for stem, m in media.items()
    }
    report = {
        "action": action,
        "wordpress_write_count": write_count,
        "featured_media": featured_media,
        "public_before": before,
        "public_after": after,
        "content_sha256": sha256_text(after_content),
        "media": report_media,
    }
    write_report(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
