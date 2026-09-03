#!/usr/bin/env python3
"""Create the Matsue Vogel Park experience article as a guarded WordPress draft."""
from __future__ import annotations

import base64, hashlib, html, json, os, time, urllib.parse, urllib.request
from pathlib import Path
from typing import Any

SITE_URL = "https://tsurikue.com"
USER_AGENT = "tsurikue-matsue-vogel-park-create/1.1"
TITLE = "松江フォーゲルパークへ行ってきた！鳥との距離が近すぎる園内を5時間満喫"
SLUG = "matsue-vogel-park"
CATEGORY_ID = 7
TAG_IDS = [26, 40, 31]
FEATURED_MEDIA_ID = 3425
EXCERPT = "松江フォーゲルパークを鳥好き一家が約5時間満喫。オオハシの餌やり、ペンギンのお散歩、ハシビロコウ、バードショー、園内ランチまで実体験で紹介。現在の料金・営業時間・アクセスもまとめました。"
CONTENT_PATH = Path("editorial/matsue-vogel-park/content.html")
OUT = Path("reports/matsue-vogel-park-create")
MARKER = "<!-- editorial:matsue-vogel-park:create:v1 -->"
EXPECTED_MEDIA = {
    3430: "/wp-content/uploads/2026/09/img_5120.jpg",
    3435: "/wp-content/uploads/2026/09/img_5129.jpg",
    3429: "/wp-content/uploads/2026/09/img_8010.jpg",
    1849: "/wp-content/uploads/2026/05/img_5136.jpg",
    3431: "/wp-content/uploads/2026/09/img_8011.jpg",
    3425: "/wp-content/uploads/2026/09/img_5160.jpg",
    3433: "/wp-content/uploads/2026/09/img_5158.jpg",
    3428: "/wp-content/uploads/2026/09/img_5153.jpg",
    3427: "/wp-content/uploads/2026/09/img_5144.jpg",
}
EXPECTED_TAXONOMY = {
    "category": {CATEGORY_ID: ("おでかけ", "sightseeing-leisure")},
    "tag": {
        26: ("山陰", "sanin"),
        40: ("体験スポット", "experience-spot"),
        31: ("子どもと遊ぶ", "family-outing"),
    },
}

def auth_header(user: str, password: str) -> str:
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()

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
        return value.get("raw") or value.get("rendered") or ""
    return str(value)

def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def count_published(endpoint: str, auth: str) -> int:
    q = urllib.parse.urlencode({"context":"edit","status":"publish","per_page":1,"_fields":"id"})
    _, headers = request_json(f"{SITE_URL}/wp-json/wp/v2/{endpoint}?{q}", auth)
    return int(headers.get("X-WP-Total", "0"))

def public_counts(auth: str) -> dict[str, int]:
    posts = count_published("posts", auth); pages = count_published("pages", auth)
    return {"published_posts": posts, "published_pages": pages, "published_total": posts + pages}

def validate_media(auth: str) -> None:
    for media_id, expected_path in EXPECTED_MEDIA.items():
        q = urllib.parse.urlencode({"context":"edit","_fields":"id,source_url,mime_type"})
        row, _ = request_json(f"{SITE_URL}/wp-json/wp/v2/media/{media_id}?{q}", auth)
        actual = urllib.parse.unquote(urllib.parse.urlparse(row.get("source_url") or "").path)
        if int(row.get("id") or 0) != media_id or actual.casefold() != expected_path.casefold():
            raise RuntimeError(f"media mismatch id={media_id}: {actual}")
        if not str(row.get("mime_type") or "").startswith("image/"):
            raise RuntimeError(f"non-image media id={media_id}")

def validate_taxonomy(auth: str) -> None:
    for kind, endpoint in (("category", "categories"), ("tag", "tags")):
        for term_id, (expected_name, expected_slug) in EXPECTED_TAXONOMY[kind].items():
            q = urllib.parse.urlencode({"context":"edit","_fields":"id,name,slug"})
            row, _ = request_json(f"{SITE_URL}/wp-json/wp/v2/{endpoint}/{term_id}?{q}", auth)
            if int(row.get("id") or 0) != term_id or row.get("name") != expected_name or row.get("slug") != expected_slug:
                raise RuntimeError(f"taxonomy mismatch {kind} id={term_id}: {row}")

def build_content() -> str:
    body = CONTENT_PATH.read_text(encoding="utf-8").strip()
    if "<h1" in body.casefold(): raise RuntimeError("body must not contain H1")
    for media_id, path in EXPECTED_MEDIA.items():
        if f"wp-image-{media_id}" not in body or path not in body:
            raise RuntimeError(f"expected media missing from body: {media_id}")
    if any(x in body for x in ("😀", "🔥", "🚀")):
        raise RuntimeError("article body contains emoji")
    return MARKER + "\n" + body

def fetch_exact_slug_any_status(auth: str):
    q = urllib.parse.urlencode({"context":"edit","status":"any","slug":SLUG,"per_page":100,"_fields":"id,slug,status,title,content,excerpt,featured_media,categories,tags,link"})
    rows, _ = request_json(f"{SITE_URL}/wp-json/wp/v2/posts?{q}", auth)
    return list(rows)

def fetch_title_search(auth: str):
    q = urllib.parse.urlencode({"context":"edit","status":"any","search":"松江フォーゲルパーク","per_page":100,"_fields":"id,slug,status,title"})
    rows, _ = request_json(f"{SITE_URL}/wp-json/wp/v2/posts?{q}", auth)
    return list(rows)

def validate_draft(row: dict[str, Any], expected: str) -> None:
    if row.get("status") != "draft" or row.get("slug") != SLUG: raise RuntimeError("draft metadata mismatch")
    if html.unescape(raw_field(row, "title")) != TITLE: raise RuntimeError("draft title mismatch")
    if int(row.get("featured_media") or 0) != FEATURED_MEDIA_ID: raise RuntimeError("featured mismatch")
    if [int(x) for x in (row.get("categories") or [])] != [CATEGORY_ID]: raise RuntimeError("category mismatch")
    if sorted(int(x) for x in (row.get("tags") or [])) != sorted(TAG_IDS): raise RuntimeError("tags mismatch")
    if raw_field(row, "content").strip() != expected.strip(): raise RuntimeError("content mismatch")

def write_report(report: dict[str, Any]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/"result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    lines = [
        "# Matsue Vogel Park draft creation", "",
        f"- action: **{report['action']}**", f"- post_id: **{report['post_id']}**", f"- status: **draft**",
        f"- title: {TITLE}", f"- slug: `{SLUG}`", f"- category_id: **{CATEGORY_ID}**",
        f"- tag_ids: **{', '.join(map(str, TAG_IDS))}**", f"- featured_media: **{FEATURED_MEDIA_ID}**",
        f"- confirmed_media_checked: **{len(EXPECTED_MEDIA)}**", f"- wordpress_write_count: **{report['wordpress_write_count']}**",
        f"- published_before: **{report['public_before']['published_total']}**", f"- published_after: **{report['public_after']['published_total']}**",
        f"- content_sha256: `{report['content_sha256']}`", "- publish_count: **0**", "- media_upload_count: **0**",
    ]
    (OUT/"summary.md").write_text("\n".join(lines)+"\n", encoding="utf-8")

def main() -> int:
    user=os.environ.get("TSURIKUE_WP_USER"); password=os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password: raise SystemExit("BLOCKED_MISSING_SECRETS")
    auth=auth_header(user,password)
    before=public_counts(auth)
    validate_media(auth); validate_taxonomy(auth)
    content=build_content()

    exact=fetch_exact_slug_any_status(auth)
    if len(exact)>1: raise RuntimeError("multiple exact-slug posts found")
    if exact:
        if exact[0].get("status") != "draft":
            raise RuntimeError(f"/{SLUG}/ already exists with status={exact[0].get('status')}; refusing create")
        validate_draft(exact[0], content)
        post_id=int(exact[0]["id"]); action="ALREADY_UP_TO_DATE"; write_count=0
    else:
        title_matches=fetch_title_search(auth)
        if title_matches:
            raise RuntimeError("possible duplicate title/search matches found: "+json.dumps(title_matches,ensure_ascii=False))
        payload={"title":TITLE,"slug":SLUG,"status":"draft","content":content,"excerpt":EXCERPT,"featured_media":FEATURED_MEDIA_ID,"categories":[CATEGORY_ID],"tags":TAG_IDS}
        created,_=request_json(f"{SITE_URL}/wp-json/wp/v2/posts",auth,method="POST",payload=payload,timeout=90)
        post_id=int(created.get("id") or 0)
        if not post_id or created.get("status")!="draft": raise RuntimeError("unexpected create response")
        action="CREATE_DRAFT"; write_count=1

    q=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,content,excerpt,featured_media,categories,tags,link"})
    after_row,_=request_json(f"{SITE_URL}/wp-json/wp/v2/posts/{post_id}?{q}",auth)
    validate_draft(after_row,content)
    after=public_counts(auth)
    if after!=before: raise RuntimeError(f"published counts changed: {before} -> {after}")
    report={"action":action,"post_id":post_id,"wordpress_write_count":write_count,"public_before":before,"public_after":after,"content_sha256":sha(content.strip())}
    write_report(report); print(json.dumps(report,ensure_ascii=False,indent=2)); return 0

if __name__=="__main__": raise SystemExit(main())
