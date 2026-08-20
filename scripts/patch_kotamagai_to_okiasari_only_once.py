#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

SITE_URL = "https://tsurikue.com"
POST_ID = 2640
SLUG = "kotamagai-seafood-gathering"
OLD_TITLE = "米子でコタマガイ・オキアサリ採りをした体験記｜足で探した昔の海遊び"
NEW_TITLE = "オキアサリの採り方｜米子の海で足を使って探した体験記"
EXPECTED_CURRENT_SHA256 = "7b27e23f0303617c1c2ab649523f8649bb05e62f4e7e0f2d504ebe1cb478dd75"
SALVAGE_MARKER = "<!-- old-tsurikue-salvage:v1 slug=kotamagai-seafood-gathering -->"
EDITORIAL_MARKER = "<!-- tsurikue-editorial:kotamagai-seafood-gathering:v1 -->"
USER_AGENT = "tsurikue-okiasari-only-fix/1.0"
RIGHTS_URL = "https://www.pref.tottori.lg.jp/305753.htm"
GEAR_URL = "https://www.pref.tottori.lg.jp/305750.htm"


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def get_json(url: str, authorization: str):
    req = urllib.request.Request(url, headers={"Accept": "application/json", "Authorization": authorization, "User-Agent": USER_AGENT}, method="GET")
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.loads(response.read().decode()), dict(response.headers)


def post_json(url: str, authorization: str, payload: dict):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers={"Accept": "application/json", "Content-Type": "application/json; charset=utf-8", "Authorization": authorization, "User-Agent": USER_AGENT},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode())


def raw_field(row: dict, key: str) -> str:
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)


def fetch_post(authorization: str):
    query = urllib.parse.urlencode({"context": "edit", "_fields": "id,slug,status,title,content,featured_media"})
    row, _ = get_json(f"{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}?{query}", authorization)
    return row


def count_published(endpoint: str, authorization: str) -> int:
    query = urllib.parse.urlencode({"context": "edit", "status": "publish", "per_page": "1", "_fields": "id"})
    _, headers = get_json(f"{SITE_URL}/wp-json/wp/v2/{endpoint}?{query}", authorization)
    return int(headers.get("X-WP-Total", "0"))


def public_counts(authorization: str) -> dict:
    posts = count_published("posts", authorization)
    pages = count_published("pages", authorization)
    return {"published_posts": posts, "published_pages": pages, "published_total": posts + pages}


def replace_once(content: str, old: str, new: str, label: str) -> str:
    count = content.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return content.replace(old, new, 1)


def build_content(current: str) -> str:
    content = current

    content = replace_once(
        content,
        '<p><strong>コタマガイ・オキアサリ。</strong></p>',
        '<p><strong>オキアサリ。</strong></p>',
        "opening species",
    )

    old_location = '<p>ちなみに、この記事の体験場所は<strong>鳥取県の米子</strong>です。昔、米子の海で実際にコタマガイ・オキアサリを探して遊んだ時の記録を、今のルールに合わせて整理し直しています。</p>'
    new_location = '''<p>ちなみに、この記事の体験場所は<strong>鳥取県の米子</strong>です。昔、米子の海で実際にオキアサリを探して遊んだ時の記録です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>実は当時、最初はコタマガイだと思っていました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>ところが後から調べ直して、<strong>私が米子で採っていたのはオキアサリだった</strong>と分かりました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>なので、この記事もオキアサリの体験記として書き直しています。</p>'''
    content = replace_once(content, old_location, new_location, "Yonago/identification paragraph")

    old_note = '<!-- wp:paragraph -->\n<p><small>※現在の鳥取県ではコタマガイは漁業権対象の魚介類として案内されています。この記事は当時の体験記です。今採りに行く場合は、場所ごとの漁業権設定と対象種を必ず確認してください。</small></p>\n<!-- /wp:paragraph -->\n\n'
    content = replace_once(content, old_note, "", "old kotamagai legal note")

    section_start = '<!-- wp:heading -->\n<h2 class="wp-block-heading">今の鳥取県では、コタマガイは漁業権対象。採る前に必ず確認</h2>\n<!-- /wp:heading -->'
    section_end = '<!-- wp:heading -->\n<h2 class="wp-block-heading">採ったあとは食べる。ここまでが楽しい</h2>\n<!-- /wp:heading -->'
    if content.count(section_start) != 1 or content.count(section_end) != 1:
        raise RuntimeError("current rules section markers did not match exactly")
    before, rest = content.split(section_start, 1)
    _old_section, after = rest.split(section_end, 1)
    new_section = '''<!-- wp:heading -->
<h2 class="wp-block-heading">今採りに行くなら、場所のルールだけは確認</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>ここは昔の記事のままにはできません。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>海の採取ルールは、場所と対象となる魚介類によって変わります。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>鳥取県公式の漁業権対象一覧には「こたまがい」の記載があります。オキアサリや似た貝は呼び名・見分け方もややこしいので、<strong>この記事だけで採っていいと判断せず、今行くなら地元の漁協か鳥取県へ確認してから</strong>にしましょう。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>昔の私は足でゴソゴソ探していましたが、今はルール確認までセットです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><small>鳥取県公式：<a href="https://www.pref.tottori.lg.jp/305753.htm" target="_blank" rel="noopener noreferrer">漁業権対象の魚介類</a> ／ <a href="https://www.pref.tottori.lg.jp/305750.htm" target="_blank" rel="noopener noreferrer">遊漁に使用できる漁具・漁法の制限</a></small></p>
<!-- /wp:paragraph -->

'''
    content = before + new_section + section_end + after

    content = replace_once(
        content,
        '<p><a href="https://tsurikue.com/kotamagairyouri/"><strong>コタマガイ・オキアサリをバター焼きで食べた記事はこちら</strong></a></p>',
        '<p><a href="https://tsurikue.com/kotamagairyouri/"><strong>オキアサリをバター焼きで食べた記事はこちら</strong></a></p>',
        "cooking link anchor",
    )

    if "コタマガイ・オキアサリ" in content:
        raise RuntimeError("combined species wording remains")
    if content.count("コタマガイ") != 1:
        raise RuntimeError(f"expected one explanatory コタマガイ mention, found {content.count('コタマガイ')}")
    if content.count("オキアサリ") < 5:
        raise RuntimeError("too few オキアサリ mentions after rewrite")
    if "pref.hiroshima.lg.jp" in content:
        raise RuntimeError("Hiroshima rule link remains")
    if RIGHTS_URL not in content or GEAR_URL not in content:
        raise RuntimeError("Tottori official links missing")
    if SALVAGE_MARKER not in content or EDITORIAL_MARKER not in content:
        raise RuntimeError("required markers missing after patch")
    return content


def main() -> int:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")
    auth = auth_header(user, password)

    before_counts = public_counts(auth)
    before = fetch_post(auth)
    if before.get("id") != POST_ID or before.get("slug") != SLUG:
        raise RuntimeError("post id/slug mismatch")
    if before.get("status") != "draft":
        raise RuntimeError("target is not draft")
    if int(before.get("featured_media") or 0) != 0:
        raise RuntimeError("featured media changed; refusing patch")
    current_title = html.unescape(raw_field(before, "title"))
    if current_title != OLD_TITLE:
        raise RuntimeError(f"title changed; refusing patch: {current_title}")
    current = raw_field(before, "content")
    current_sha = hashlib.sha256(current.encode()).hexdigest()
    if current_sha != EXPECTED_CURRENT_SHA256:
        raise RuntimeError(f"content changed; refusing patch: {current_sha}")
    if SALVAGE_MARKER not in current or EDITORIAL_MARKER not in current:
        raise RuntimeError("required markers missing")

    updated = build_content(current)
    payload = {"title": NEW_TITLE, "slug": SLUG, "content": updated, "status": "draft", "featured_media": 0}
    response = post_json(f"{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}", auth, payload)
    if response.get("id") != POST_ID or response.get("status") != "draft" or response.get("slug") != SLUG:
        raise RuntimeError("update response validation failed")

    after = fetch_post(auth)
    after_counts = public_counts(auth)
    if after_counts != before_counts:
        raise RuntimeError("published counts changed")
    after_content = raw_field(after, "content")
    if html.unescape(raw_field(after, "title")) != NEW_TITLE:
        raise RuntimeError("title verification failed")
    if after_content.strip() != updated.strip():
        raise RuntimeError("content verification failed")
    if after.get("status") != "draft" or int(after.get("featured_media") or 0) != 0:
        raise RuntimeError("draft/featured state changed")

    report = {
        "action": "PATCH_OKIASARI_ONLY",
        "post_id": POST_ID,
        "slug": SLUG,
        "status": "draft",
        "title": NEW_TITLE,
        "featured_media": 0,
        "public_before": before_counts,
        "public_after": after_counts,
        "content_sha256": hashlib.sha256(after_content.encode()).hexdigest(),
        "wordpress_write_count": 1,
        "publish_count": 0,
        "media_upload_count": 0,
        "experience_location": "鳥取県米子",
        "article_subject": "オキアサリ",
    }
    out = Path("reports/kotamagai-to-okiasari-only")
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "summary.md").write_text(
        "# kotamagai → okiasari-only patch\n\n"
        "- action: **PATCH_OKIASARI_ONLY**\n"
        f"- post_id: **{POST_ID}**\n"
        "- status: **draft**\n"
        f"- title: {NEW_TITLE}\n"
        "- experience_location: **鳥取県米子**\n"
        "- article_subject: **オキアサリ**\n"
        "- slug_preserved: **kotamagai-seafood-gathering**\n"
        "- featured_media: **0**\n"
        f"- public_before: **{before_counts['published_total']}**\n"
        f"- public_after: **{after_counts['published_total']}**\n"
        f"- content_sha256: `{report['content_sha256']}`\n"
        "- wordpress_write_count: **1**\n"
        "- publish_count: **0**\n"
        "- media_upload_count: **0**\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
