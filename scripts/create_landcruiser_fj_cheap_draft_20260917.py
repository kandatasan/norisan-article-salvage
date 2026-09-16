#!/usr/bin/env python3
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

SITE = "https://tsurikue.com"
UA = "tsurikue-create-landcruiser-fj-cheap-20260917/1.0"
TITLE = "ランドクルーザーFJを安く買う方法｜欲しいオプションを諦めず負担を減らす5つのコツ"
SLUG = "landcruiser-fj-cheap"
CONTENT_PATH = Path("packages/landcruiser-fj-cheap/content.html")
EXCERPT = "ランドクルーザーFJを安く買うには、オプションを削るだけではありません。実際の550万516円の見積もりをもとに、今の車を高く売る、自動車保険を比較する、中古相場やローン総額を確認するなど、欲しい装備を残しながら実質負担を減らす方法を整理します。"
FEATURED = 3757
CATEGORY_SLUGS = ["car", "landcruiser-fj"]
SOURCE_FJ_POST_ID = 3767
EXPECTED_MEDIA = {
    3757: "/wp-content/uploads/2026/09/img_8130.jpg",
    3756: "/wp-content/uploads/2026/09/img_8129.jpg",
    3765: "/wp-content/uploads/2026/09/img_8318.jpg",
}
BODY_MEDIA = {3756, 3765}
SOURCE_MARKER = "<!-- tsurikue-original:v1 slug=landcruiser-fj-cheap source=user-direction-20260917 -->"
EDITORIAL_MARKER = "<!-- tsurikue-editorial:v1 slug=landcruiser-fj-cheap -->"
CTN_PART_ID = 3788
CTN_PART_TITLE = "CTNボタン 3104"
CTN_PART_SLUG = "ctn-button-3104"
CTN_TRACK = "id1=3104"
INSWEB_TITLE = "インズウェブ 3104"
INSWEB_SLUG = "insweb-3104"
OLD_INSWEB_CLICK_BASE = "https://px.a8.net/svt/ejp?a8mat=3Z0TXU+5GH69M+2PS+15RK36"
OLD_INSWEB_PIXEL = "https://www15.a8.net/0.gif?a8mat=3Z0TXU+5GH69M+2PS+15RK36"
INSWEB_CLICK_BASE = "https://px.a8.net/svt/ejp?a8mat=3Z0TXU+5GH2EQ+2PS+15RK36"
INSWEB_PIXEL = "https://www10.a8.net/0.gif?a8mat=3Z0TXU+5GH2EQ+2PS+15RK36"
INSWEB_TRACK_VALUE = "3104"
OLD_INSWEB_PART_CONTENT = f'''<!-- wp:html -->
<a href="{OLD_INSWEB_CLICK_BASE}&id1={INSWEB_TRACK_VALUE}" rel="nofollow">一番安い自動車保険がわかる！</a>
<img border="0" width="1" height="1" src="{OLD_INSWEB_PIXEL}" alt="">
<!-- /wp:html -->'''
INSWEB_PART_CONTENT = f'''<!-- wp:html -->
<a href="{INSWEB_CLICK_BASE}&id1={INSWEB_TRACK_VALUE}" rel="nofollow">一番安い自動車保険がわかる！</a>
<img border="0" width="1" height="1" src="{INSWEB_PIXEL}" alt="">
<!-- /wp:html -->'''
REPORT = Path("reports/landcruiser-fj-cheap-create-20260917")

TOKEN = re.compile(r"<!--\s+/?wp:[\s\S]*?-->")
OPEN = re.compile(r"<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->")
CLOSE = re.compile(r"<!--\s+/wp:([\w\-/]+)\s+-->")
IMAGE_ID = re.compile(r"wp-image-(\d+)")
H2_RE = re.compile(r"<h2[^>]*>(.*?)</h2>", re.I | re.S)
PLACEHOLDER = "{{INSWEB_3104_SHORTCODE}}"
EXPECTED_H2 = [
    "結論｜FJはオプションを削る前に「使えるお金を増やす」",
    "僕のFJは支払総額550万516円だった",
    "方法1｜今の車を高く売って購入資金を増やす",
    "方法2｜自動車保険を比較して毎年の負担を見直す",
    "方法3｜値引きだけに期待しすぎない",
    "方法4｜中古車は「新車より安い」と決めつけない",
    "ローンは月額より総支払額まで見る",
    "どこを削る？ではなく「何を残したい？」から決める",
    "まとめ｜納得できるFJを買うために、先に使えるお金を増やす",
]


def auth_header() -> str:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise RuntimeError("missing WordPress secrets")
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()


def request(method: str, path: str, payload=None):
    headers = {"Authorization": auth_header(), "Accept": "application/json", "User-Agent": UA}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(SITE + path, data=data, headers=headers, method=method)
    last = None
    for n in range(3):
        try:
            with urllib.request.urlopen(req, timeout=75) as resp:
                body = resp.read().decode("utf-8")
                return (json.loads(body) if body else None), dict(resp.headers.items())
        except Exception as exc:
            last = exc
            if n < 2:
                time.sleep(2 * (n + 1))
    raise last


def raw(row: dict, key: str) -> str:
    v = row.get(key) or {}
    if isinstance(v, dict):
        return v.get("raw") or v.get("rendered") or ""
    return str(v)


def sha256(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def public_count(endpoint: str) -> int:
    q = urllib.parse.urlencode({"status": "publish", "per_page": 1, "_fields": "id"})
    _, headers = request("GET", f"/wp-json/wp/v2/{endpoint}?{q}")
    for k, v in headers.items():
        if k.lower() == "x-wp-total":
            return int(v)
    raise RuntimeError(f"X-WP-Total missing for {endpoint}")


def public_counts() -> dict:
    return {"posts": public_count("posts"), "pages": public_count("pages")}


def resolve_category(slug: str) -> int:
    q = urllib.parse.urlencode({"context": "edit", "slug": slug, "per_page": 10, "_fields": "id,slug,name"})
    rows, _ = request("GET", f"/wp-json/wp/v2/categories?{q}")
    if len(rows) != 1 or rows[0].get("slug") != slug:
        raise RuntimeError(f"category resolution failed for {slug}: {rows}")
    return int(rows[0]["id"])


def validate_media() -> None:
    for mid, expected_path in EXPECTED_MEDIA.items():
        q = urllib.parse.urlencode({"context": "edit", "_fields": "id,status,source_url"})
        row, _ = request("GET", f"/wp-json/wp/v2/media/{mid}?{q}")
        path = urllib.parse.unquote(urllib.parse.urlparse(row.get("source_url") or "").path)
        if int(row.get("id") or 0) != mid or path.casefold() != expected_path.casefold():
            raise RuntimeError(f"media mismatch {mid}: {path} != {expected_path}")


def source_author() -> int:
    q = urllib.parse.urlencode({"context": "edit", "_fields": "id,slug,status,author"})
    row, _ = request("GET", f"/wp-json/wp/v2/posts/{SOURCE_FJ_POST_ID}?{q}")
    if int(row.get("id") or 0) != SOURCE_FJ_POST_ID or row.get("slug") != "landcruiser-fj-price":
        raise RuntimeError("source FJ post identity mismatch")
    author = int(row.get("author") or 0)
    if author <= 0:
        raise RuntimeError("source FJ author missing")
    return author


def validate_ctn_part() -> None:
    q = urllib.parse.urlencode({"context": "edit", "_fields": "id,slug,status,title,content"})
    row, _ = request("GET", f"/wp-json/wp/v2/blog_parts/{CTN_PART_ID}?{q}")
    if int(row.get("id") or 0) != CTN_PART_ID:
        raise RuntimeError("CTN 3104 part ID mismatch")
    if row.get("slug") != CTN_PART_SLUG or row.get("status") != "publish":
        raise RuntimeError("CTN 3104 part identity mismatch")
    if html.unescape(raw(row, "title")) != CTN_PART_TITLE:
        raise RuntimeError("CTN 3104 part title mismatch")
    if CTN_TRACK not in raw(row, "content"):
        raise RuntimeError("CTN 3104 tracking parameter missing")


def find_blog_part(slug: str):
    q = urllib.parse.urlencode({"context": "edit", "slug": slug, "per_page": 10, "_fields": "id,slug,status,title,content"})
    rows, _ = request("GET", f"/wp-json/wp/v2/blog_parts?{q}")
    return rows


def ensure_insweb_part() -> tuple[int, str]:
    rows = find_blog_part(INSWEB_SLUG)
    if rows:
        if len(rows) != 1:
            raise RuntimeError(f"InsWeb part slug collision: {len(rows)}")
        row = rows[0]
        if row.get("status") != "publish" or html.unescape(raw(row, "title")) != INSWEB_TITLE:
            raise RuntimeError("existing InsWeb part identity mismatch")
        current = raw(row, "content").strip()
        part_id = int(row["id"])
        if current == INSWEB_PART_CONTENT.strip():
            return part_id, "REUSE"
        if current != OLD_INSWEB_PART_CONTENT.strip():
            raise RuntimeError("existing InsWeb part content mismatch")
        request("POST", f"/wp-json/wp/v2/blog_parts/{part_id}", {"content": INSWEB_PART_CONTENT})
        check, _ = request("GET", f"/wp-json/wp/v2/blog_parts/{part_id}?context=edit")
        if check.get("slug") != INSWEB_SLUG or check.get("status") != "publish":
            raise RuntimeError("InsWeb part identity changed after correction")
        if raw(check, "content").strip() != INSWEB_PART_CONTENT.strip():
            raise RuntimeError("InsWeb part correction failed")
        return part_id, "CORRECT_CODE"
    row, _ = request("POST", "/wp-json/wp/v2/blog_parts", {
        "title": INSWEB_TITLE,
        "slug": INSWEB_SLUG,
        "content": INSWEB_PART_CONTENT,
        "status": "publish",
    })
    part_id = int(row.get("id") or 0)
    if part_id <= 0:
        raise RuntimeError("invalid InsWeb part ID after create")
    check, _ = request("GET", f"/wp-json/wp/v2/blog_parts/{part_id}?context=edit")
    if check.get("slug") != INSWEB_SLUG or check.get("status") != "publish":
        raise RuntimeError("InsWeb part post-create identity mismatch")
    if raw(check, "content").strip() != INSWEB_PART_CONTENT.strip():
        raise RuntimeError("InsWeb part post-create content mismatch")
    return part_id, "CREATE"


def gutenberg_problems(text: str) -> int:
    stack = []
    for m in TOKEN.finditer(text):
        token = m.group(0)
        opened = OPEN.fullmatch(token)
        closed = CLOSE.fullmatch(token)
        if opened:
            if not opened.group(2):
                stack.append(opened.group(1))
        elif closed:
            if not stack or stack[-1] != closed.group(1):
                return 1
            stack.pop()
    return len(stack)


def validate_template(template: str) -> None:
    if "<h1" in template.casefold() or '"level":1' in template:
        raise RuntimeError("body h1 forbidden")
    if template.count(SOURCE_MARKER) != 1 or template.count(EDITORIAL_MARKER) != 1:
        raise RuntimeError("marker mismatch")
    if template.count(PLACEHOLDER) != 1:
        raise RuntimeError("InsWeb shortcode placeholder mismatch")
    if template.count(f'[blog_parts id="{CTN_PART_ID}"]') != 1:
        raise RuntimeError("CTN 3104 shortcode count mismatch")
    if any(x in template for x in ["普通に", "もちろん", "🔥", "🤣", "😁", "😏", "😂", "😊"]):
        raise RuntimeError("banned wording/emoji present")
    if template.count("かなり") > 1 or template.count("めちゃくちゃ") > 1:
        raise RuntimeError("intensifier overuse")
    h2 = [re.sub(r"<[^>]+>", "", x).strip() for x in H2_RE.findall(template)]
    if h2 != EXPECTED_H2:
        raise RuntimeError(f"H2 structure mismatch: {h2}")
    used = {int(x) for x in IMAGE_ID.findall(template)}
    if used != BODY_MEDIA:
        raise RuntimeError(f"body media mismatch: {used}")
    required = [
        "550万516円", "欲しいFJを削って安くするより", "車を楽に高く売る方法",
        "SBIの保険比較インズウェブ", "納車前の車や、乗り換え予定の車でも見積もりできます",
        "月刊自家用車", "車両本体値引き目標は<strong>5万円</strong>",
        "平均価格が約598万円", "最終回の支払額は256万5,050円", "実質年率は4.9％",
        "https://toyota.jp/landcruiserfj/", "https://www.insweb.co.jp/car/insweb", "https://www.insweb.co.jp/car/faq",
        "https://jikayosha.jp/2026/09/10/330992/", "https://www.carsensor.net/usedcar/souba/TO_S272/F001/",
    ]
    for x in required:
        if x not in template:
            raise RuntimeError(f"required phrase missing: {x}")


def find_post():
    q = urllib.parse.urlencode({"context": "edit", "slug": SLUG, "status": "any", "per_page": 10, "_fields": "id,slug,status,title,content,author,featured_media,categories,excerpt"})
    rows, _ = request("GET", f"/wp-json/wp/v2/posts?{q}")
    return rows


def normalized_excerpt(value: str) -> str:
    return re.sub(r"<[^>]+>", "", html.unescape(value or "")).strip()


def write_report(data: dict) -> None:
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / "result.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Land Cruiser FJ cheap draft create 2026-09-17", "",
        f"- result: **{data['result']}**",
        f"- article_action: **{data['article_action']}**",
        f"- post_id: **{data['post_id']}**",
        f"- status: **{data['status']}**",
        f"- slug: **{data['slug']}**",
        f"- InsWeb part action: **{data['insweb_part_action']}**",
        f"- InsWeb part ID: **{data['insweb_part_id']}**",
        f"- InsWeb tracking: **id1={INSWEB_TRACK_VALUE}**",
        f"- CTN part ID: **{CTN_PART_ID}**",
        f"- published posts before/after: **{data['public_before']['posts']} / {data['public_after']['posts']}**",
        f"- published pages before/after: **{data['public_before']['pages']} / {data['public_after']['pages']}**",
        f"- content sha256: **{data['content_sha256']}**",
    ]
    (REPORT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def main() -> None:
    template = CONTENT_PATH.read_text(encoding="utf-8").strip() + "\n"
    validate_template(template)
    validate_media()
    validate_ctn_part()
    author = source_author()
    categories = [resolve_category(x) for x in CATEGORY_SLUGS]
    public_before = public_counts()

    insweb_id, insweb_action = ensure_insweb_part()
    final_content = template.replace(PLACEHOLDER, f'[blog_parts id="{insweb_id}"]')
    if PLACEHOLDER in final_content or gutenberg_problems(final_content) != 0:
        raise RuntimeError("final Gutenberg content validation failed")
    if final_content.count(f'[blog_parts id="{insweb_id}"]') != 1:
        raise RuntimeError("final InsWeb shortcode mismatch")

    rows = find_post()
    if rows:
        if len(rows) != 1:
            raise RuntimeError(f"post slug collision: {len(rows)}")
        row = rows[0]
        if row.get("status") != "draft":
            raise RuntimeError(f"existing {SLUG} is not a draft; refusing update")
        if html.unescape(raw(row, "title")) != TITLE:
            raise RuntimeError("existing draft title mismatch")
        if raw(row, "content").strip() != final_content.strip():
            raise RuntimeError("existing draft content differs; refusing overwrite")
        if int(row.get("author") or 0) != author or int(row.get("featured_media") or 0) != FEATURED:
            raise RuntimeError("existing draft identity metadata mismatch")
        if sorted(row.get("categories") or []) != sorted(categories):
            raise RuntimeError("existing draft categories mismatch")
        post = row
        article_action = "REUSE_EXACT_DRAFT"
    else:
        post, _ = request("POST", "/wp-json/wp/v2/posts", {
            "title": TITLE,
            "slug": SLUG,
            "content": final_content,
            "excerpt": EXCERPT,
            "status": "draft",
            "author": author,
            "featured_media": FEATURED,
            "categories": categories,
        })
        article_action = "CREATE_DRAFT"

    post_id = int(post.get("id") or 0)
    q = urllib.parse.urlencode({"context": "edit", "_fields": "id,slug,status,title,content,author,featured_media,categories,excerpt"})
    check, _ = request("GET", f"/wp-json/wp/v2/posts/{post_id}?{q}")
    public_after = public_counts()
    if public_after != public_before:
        raise RuntimeError(f"public counts changed: {public_before} -> {public_after}")
    if check.get("status") != "draft" or check.get("slug") != SLUG:
        raise RuntimeError("final draft identity mismatch")
    if html.unescape(raw(check, "title")) != TITLE or raw(check, "content").strip() != final_content.strip():
        raise RuntimeError("final draft content/title mismatch")
    if int(check.get("author") or 0) != author or int(check.get("featured_media") or 0) != FEATURED:
        raise RuntimeError("final draft metadata mismatch")
    if sorted(check.get("categories") or []) != sorted(categories):
        raise RuntimeError("final draft categories mismatch")
    if normalized_excerpt(raw(check, "excerpt")) != EXCERPT:
        raise RuntimeError("final excerpt mismatch")

    ip, _ = request("GET", f"/wp-json/wp/v2/blog_parts/{insweb_id}?context=edit")
    ic = raw(ip, "content")
    if ic.count(INSWEB_CLICK_BASE + "&id1=" + INSWEB_TRACK_VALUE) != 1 or ic.count(INSWEB_PIXEL) != 1:
        raise RuntimeError("final InsWeb affiliate verification failed")
    validate_ctn_part()

    data = {
        "result": "SUCCESS",
        "article_action": article_action,
        "post_id": post_id,
        "status": check.get("status"),
        "slug": check.get("slug"),
        "insweb_part_action": insweb_action,
        "insweb_part_id": insweb_id,
        "public_before": public_before,
        "public_after": public_after,
        "content_sha256": sha256(raw(check, "content")),
    }
    write_report(data)


if __name__ == "__main__":
    main()
