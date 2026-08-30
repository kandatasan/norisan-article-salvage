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
from typing import Any

SITE_URL = "https://tsurikue.com"
POST_ID = 2011
SLUG = "yuki-town-drive"
TITLE = "湯来町で子どもと遊ぶなら？牧場・川遊び・釣り堀をめぐる日帰りドライブ"
EXPECTED_FEATURED_MEDIA = 2023
EXPECTED_SOURCE_SHA256 = "920e255cecb2ffbf6f8653b5eaeede52bf090704bf979603ce86826613abac67"
MARKER = "<!-- tsurikue-editorial:yuki-town-drive:reader-first-v1 -->"
USER_AGENT = "tsurikue-yuki-town-drive-linebreaks/1.0"
REPORT_DIR = Path("reports/yuki-town-drive-linebreaks")


def auth_header(user: str, password: str) -> str:
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()


def request_json(url: str, auth: str, *, method: str = "GET", payload: dict[str, Any] | None = None):
    data = None
    headers = {"Accept": "application/json", "Authorization": auth, "User-Agent": USER_AGENT}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    last: Exception | None = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=75) as response:
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


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fetch_target(auth: str) -> dict[str, Any]:
    query = urllib.parse.urlencode({"context": "edit", "_fields": "id,slug,status,title,content,featured_media,categories,modified,link"})
    row, _ = request_json(f"{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}?{query}", auth)
    return row


def count_published(endpoint: str, auth: str) -> int:
    query = urllib.parse.urlencode({"context": "edit", "status": "publish", "per_page": "1", "_fields": "id"})
    _, headers = request_json(f"{SITE_URL}/wp-json/wp/v2/{endpoint}?{query}", auth)
    return int(headers.get("X-WP-Total", "0"))


def public_counts(auth: str) -> dict[str, int]:
    posts = count_published("posts", auth)
    pages = count_published("pages", auth)
    return {"published_posts": posts, "published_pages": pages, "published_total": posts + pages}


def media_blocks(content: str) -> list[str]:
    pattern = re.compile(r"<!-- wp:(image|video)\b.*?<!-- /wp:\1 -->", flags=re.S)
    return [m.group(0) for m in pattern.finditer(content)]


def p(text: str) -> str:
    return f'<!-- wp:paragraph -->\n<p>{text}</p>\n<!-- /wp:paragraph -->'


def merge_paragraphs(content: str, paragraphs: list[str], merged_html: str) -> tuple[str, bool]:
    old = "\n\n".join(p(x) for x in paragraphs)
    new = p(merged_html)
    if old not in content:
        return content, False
    return content.replace(old, new, 1), True


def visible_text(content: str) -> str:
    text = re.sub(r"<!--.*?-->", " ", content, flags=re.S)
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def polish(content: str) -> tuple[str, int]:
    replacements = [
        (
            [
                "全部を詰め込まなくても大丈夫。<strong>「今日はどこまで遊ぶ？」と、その日の天気や子どもの体力に合わせて組みやすい</strong>のが湯来町のいいところです。",
                "特に夏は、街中の公園とはまったく違う一日になります。川へ入るなら着替えと濡れてもいい靴だけは忘れずに。",
            ],
            "全部を詰め込まなくても大丈夫。<br><strong>「今日はどこまで遊ぶ？」と、その日の天気や子どもの体力に合わせて組みやすい</strong>のが湯来町のいいところです。<br>特に夏は、街中の公園とはまったく違う一日になります。<br>川へ入るなら着替えと濡れてもいい靴だけは忘れずに。",
        ),
        (
            [
                "最初に寄りやすいのが、サゴタニ牧場・久保アグリファーム。広い牧場の景色を見ながら、牛やヤギを見たり、芝生でのんびりしたりできます。",
                "いきなり川へ飛び込むより、まず牧場で遊ぶと一日のスタートがゆるい。小さい子ども連れでも動きやすいです。",
            ],
            "最初に寄りやすいのが、サゴタニ牧場・久保アグリファーム。<br>広い牧場の景色を見ながら、牛やヤギを見たり、芝生でのんびりしたりできます。<br>いきなり川へ飛び込むより、まず牧場で遊ぶと一日のスタートがゆるい。<br>小さい子ども連れでも動きやすいです。",
        ),
        (
            [
                "湯来町の魅力は、やっぱり山の中を流れる川。水がきれいで、暑い日は足を入れるだけでも気持ちいいです。",
                "ただし、川は遊具のある公園とは違います。前日に雨が降っていたり、水量が多かったりする日は無理をしない。見た目が穏やかでも急に深くなる場所や滑る石があります。",
                "子どもと入るなら、<strong>大人が先に深さと流れを確認すること</strong>。アクアシューズなど脱げにくい履き物も用意しておきたいです。",
            ],
            "湯来町の魅力は、やっぱり山の中を流れる川。<br>水がきれいで、暑い日は足を入れるだけでも気持ちいいです。<br><br>ただし、川は遊具のある公園とは違います。<br>前日に雨が降っていたり、水量が多かったりする日は無理をしない。<br>見た目が穏やかでも急に深くなる場所や滑る石があります。<br>子どもと入るなら、<strong>大人が先に深さと流れを確認すること</strong>。<br>アクアシューズなど脱げにくい履き物も用意しておきたいです。",
        ),
        (
            [
                "川へ入ったら、サワガニ探しも面白いです。石をそっとめくって、下流側に網を構える。サワガニが出てきたらすくう。",
                "子どもにとっては、ほぼ宝探し。<strong>そして大人も、なぜか本気になります。</strong>",
            ],
            "川へ入ったら、サワガニ探しも面白いです。<br>石をそっとめくって、下流側に網を構える。<br>サワガニが出てきたらすくう。<br>子どもにとっては、ほぼ宝探し。<br><strong>そして大人も、なぜか本気になります。</strong>",
        ),
        (
            [
                "湯来町は、子どもの頃に祖父と川釣りや沢遊びをしていた場所でもあります。今は子どもとサワガニを探す。こういう遊びは、世代が変わっても面白いですね。",
                "なお、子どもの<strong>「少しだけ水に入る」</strong>は、あまり信用しない方がいいです。だいたい想像以上に濡れます。",
            ],
            "湯来町は、子どもの頃に祖父と川釣りや沢遊びをしていた場所でもあります。<br>今は子どもとサワガニを探す。<br>こういう遊びは、世代が変わっても面白いですね。<br><br>なお、子どもの<strong>「少しだけ水に入る」</strong>は、あまり信用しない方がいいです。<br>だいたい想像以上に濡れます。",
        ),
        (
            [
                "牧場、川、釣り堀まで遊んだら、帰りに温泉を入れると一日の締めがかなり楽になります。",
                "湯来ロッジでは現在も日帰り入浴が案内されているので、川遊びで濡れたり、外でたっぷり遊んだ日の帰り道にも使いやすいです。",
            ],
            "牧場、川、釣り堀まで遊んだら、帰りに温泉を入れると一日の締めがかなり楽になります。<br>湯来ロッジでは現在も日帰り入浴が案内されているので、川遊びで濡れたり、外でたっぷり遊んだ日の帰り道にも使いやすいです。",
        ),
        (
            [
                "湯来町には、牧場、川遊び、サワガニ探し、釣り堀、温泉があります。季節が合えばホタルも楽しめます。",
                "全部回らなくても大丈夫。<strong>久保アグリファームでジェラートを食べて、川へ行く。</strong>それだけでも街中とはかなり違う休日になります。",
                "もう少し遊べそうなら釣り堀へ。帰りに温泉へ寄る。そんなふうに、その日の様子を見ながら予定を足せるのが湯来町ドライブの使いやすさです。",
            ],
            "湯来町には、牧場、川遊び、サワガニ探し、釣り堀、温泉があります。<br>季節が合えばホタルも楽しめます。<br><br>全部回らなくても大丈夫。<br><strong>久保アグリファームでジェラートを食べて、川へ行く。</strong><br>それだけでも街中とはかなり違う休日になります。<br><br>もう少し遊べそうなら釣り堀へ。<br>帰りに温泉へ寄る。<br>そんなふうに、その日の様子を見ながら予定を足せるのが湯来町ドライブの使いやすさです。",
        ),
    ]

    out = content
    applied = 0
    for paras, merged in replacements:
        out, ok = merge_paragraphs(out, paras, merged)
        if not ok:
            raise RuntimeError(f"expected paragraph group not found: {paras[0][:40]}")
        applied += 1
    return out, applied


def write_report(report: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Yuki town drive line-break polish",
        "",
        f"- result: **{report.get('result')}**",
        f"- post_id: **{report.get('post_id', 0)}**",
        f"- slug: **{SLUG}**",
        f"- status_before: **{report.get('status_before')}**",
        f"- status_after: **{report.get('status_after')}**",
        f"- title_preserved: **{report.get('title_preserved', False)}**",
        f"- featured_media_preserved: **{report.get('featured_media_preserved', False)}**",
        f"- categories_preserved: **{report.get('categories_preserved', False)}**",
        f"- media_blocks_preserved: **{report.get('media_blocks_preserved', 0)}**",
        f"- paragraph_groups_polished: **{report.get('paragraph_groups_polished', 0)}**",
        f"- visible_text_preserved: **{report.get('visible_text_preserved', False)}**",
        f"- public_before: **{report.get('public_before', {}).get('published_total', 'unknown')}**",
        f"- public_after: **{report.get('public_after', {}).get('published_total', 'unknown')}**",
        f"- wordpress_write_count: **{report.get('wordpress_write_count', 0)}**",
        f"- source_sha256: `{report.get('source_sha256', '')}`",
        f"- content_sha256: `{report.get('content_sha256', '')}`",
        "- publish_count: **0** (formatting-only update to existing published post)",
    ]
    if report.get("error"):
        lines.append(f"- error: `{report['error']}`")
    (REPORT_DIR / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    report: dict[str, Any] = {"result": "BLOCKED", "wordpress_write_count": 0}
    try:
        user = os.environ.get("TSURIKUE_WP_USER")
        password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
        if not user or not password:
            raise RuntimeError("missing WordPress secrets")
        auth = auth_header(user, password)

        before_counts = public_counts(auth)
        before = fetch_target(auth)
        content = raw_field(before, "content")
        title = html.unescape(raw_field(before, "title"))
        categories = [int(x) for x in (before.get("categories") or [])]
        featured = int(before.get("featured_media") or 0)
        source_sha = sha256(content)
        media_before = media_blocks(content)

        report.update({"post_id": int(before.get("id") or 0), "status_before": before.get("status"), "public_before": before_counts, "source_sha256": source_sha})

        if int(before.get("id") or 0) != POST_ID or before.get("slug") != SLUG:
            raise RuntimeError("target identity mismatch")
        if before.get("status") != "publish":
            raise RuntimeError("target is not published")
        if title != TITLE:
            raise RuntimeError(f"unexpected title: {title!r}")
        if featured != EXPECTED_FEATURED_MEDIA:
            raise RuntimeError(f"featured media mismatch: {featured}")
        if MARKER not in content:
            raise RuntimeError("editorial marker missing")
        if source_sha != EXPECTED_SOURCE_SHA256:
            raise RuntimeError(f"source content changed since approved rewrite: {source_sha}")
        if len(media_before) != 9:
            raise RuntimeError(f"unexpected media block count: {len(media_before)}")

        desired, applied = polish(content)
        if visible_text(desired) != visible_text(content):
            raise RuntimeError("visible article text changed during formatting-only polish")
        if media_blocks(desired) != media_before:
            raise RuntimeError("media blocks changed during formatting-only polish")

        latest = fetch_target(auth)
        if sha256(raw_field(latest, "content")) != source_sha:
            raise RuntimeError("content changed after snapshot; refusing overwrite")
        if html.unescape(raw_field(latest, "title")) != title:
            raise RuntimeError("title changed after snapshot")
        if int(latest.get("featured_media") or 0) != featured:
            raise RuntimeError("featured media changed after snapshot")
        if [int(x) for x in (latest.get("categories") or [])] != categories:
            raise RuntimeError("categories changed after snapshot")

        response, _ = request_json(f"{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}", auth, method="POST", payload={"content": desired, "status": "publish"})
        if int(response.get("id") or 0) != POST_ID or response.get("status") != "publish":
            raise RuntimeError("WordPress update response validation failed")

        after = fetch_target(auth)
        after_counts = public_counts(auth)
        after_content = raw_field(after, "content")
        if before_counts != after_counts:
            raise RuntimeError(f"published counts changed: {before_counts} -> {after_counts}")
        if after.get("status") != "publish" or after.get("slug") != SLUG:
            raise RuntimeError("post identity/status changed")
        if html.unescape(raw_field(after, "title")) != title:
            raise RuntimeError("title changed")
        if int(after.get("featured_media") or 0) != featured:
            raise RuntimeError("featured media changed")
        if [int(x) for x in (after.get("categories") or [])] != categories:
            raise RuntimeError("categories changed")
        if media_blocks(after_content) != media_before:
            raise RuntimeError("media blocks changed")
        if visible_text(after_content) != visible_text(content):
            raise RuntimeError("visible text changed")
        if after_content.strip() != desired.strip():
            raise RuntimeError("post-update content mismatch")

        report.update({
            "result": "SUCCESS",
            "status_after": after.get("status"),
            "title_preserved": True,
            "featured_media_preserved": True,
            "categories_preserved": True,
            "media_blocks_preserved": len(media_before),
            "paragraph_groups_polished": applied,
            "visible_text_preserved": True,
            "public_after": after_counts,
            "wordpress_write_count": 1,
            "content_sha256": sha256(after_content),
        })
        write_report(report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        report["error"] = str(exc)
        write_report(report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
