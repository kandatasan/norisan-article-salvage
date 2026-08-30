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
EXPECTED_OLD_TITLE = "湯来町ドライブ｜牧場・川遊び・釣り堀をめぐる子連れ日帰りコース"
NEW_TITLE = "湯来町で子どもと遊ぶなら？牧場・川遊び・釣り堀をめぐる日帰りドライブ"
EXPECTED_FEATURED_MEDIA = 2023
USER_AGENT = "tsurikue-yuki-town-drive-reader-first/1.0"
REPORT_DIR = Path("reports/yuki-town-drive-reader-first")
MARKER = "<!-- tsurikue-editorial:yuki-town-drive:reader-first-v1 -->"


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def request_json(url: str, auth: str, *, method: str = "GET", payload: dict[str, Any] | None = None):
    data = None
    headers = {
        "Accept": "application/json",
        "Authorization": auth,
        "User-Agent": USER_AGENT,
    }
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


def count_published(endpoint: str, auth: str) -> int:
    query = urllib.parse.urlencode({
        "context": "edit",
        "status": "publish",
        "per_page": "1",
        "_fields": "id",
    })
    _, headers = request_json(f"{SITE_URL}/wp-json/wp/v2/{endpoint}?{query}", auth)
    return int(headers.get("X-WP-Total", "0"))


def public_counts(auth: str) -> dict[str, int]:
    posts = count_published("posts", auth)
    pages = count_published("pages", auth)
    return {"published_posts": posts, "published_pages": pages, "published_total": posts + pages}


def fetch_target(auth: str) -> dict[str, Any]:
    query = urllib.parse.urlencode({
        "context": "edit",
        "_fields": "id,slug,status,title,content,featured_media,categories,modified,link",
    })
    row, _ = request_json(f"{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}?{query}", auth)
    return row


def media_blocks(content: str) -> list[str]:
    pattern = re.compile(r"<!-- wp:(image|video)\b.*?<!-- /wp:\1 -->", flags=re.S)
    return [m.group(0) for m in pattern.finditer(content)]


def wp_p(text: str) -> str:
    return f'<!-- wp:paragraph -->\n<p>{text}</p>\n<!-- /wp:paragraph -->'


def wp_h2(text: str) -> str:
    return f'<!-- wp:heading -->\n<h2 class="wp-block-heading">{text}</h2>\n<!-- /wp:heading -->'


def wp_h3(text: str) -> str:
    return f'<!-- wp:heading {{"level":3}} -->\n<h3 class="wp-block-heading">{text}</h3>\n<!-- /wp:heading -->'


def wp_list(items: list[str]) -> str:
    lis = "".join(f'<!-- wp:list-item --><li>{item}</li><!-- /wp:list-item -->' for item in items)
    return f'<!-- wp:list -->\n<ul class="wp-block-list">{lis}</ul>\n<!-- /wp:list -->'


def build_content(media: list[str]) -> str:
    if len(media) < 9:
        raise RuntimeError(f"too few existing media blocks to preserve: {len(media)}")

    def m(index: int) -> str:
        return media[index] if index < len(media) else ""

    parts: list[str] = [MARKER]
    parts += [
        wp_p("広島市内から日帰りで自然遊びをするなら、湯来町はかなり使いやすい場所です。"),
        wp_p("牧場で動物を見る。<br>ジェラートを食べる。<br>川で遊ぶ。<br>サワガニを探す。<br>釣り堀で魚を釣る。"),
        wp_p("全部を詰め込まなくても大丈夫。<strong>「今日はどこまで遊ぶ？」と、その日の天気や子どもの体力に合わせて組みやすい</strong>のが湯来町のいいところです。"),
        wp_p("特に夏は、街中の公園とはまったく違う一日になります。川へ入るなら着替えと濡れてもいい靴だけは忘れずに。"),
        wp_h2("湯来町で子どもと遊ぶなら、この流れが組みやすい"),
        '''<!-- wp:table -->\n<figure class="wp-block-table"><table><thead><tr><th>順番</th><th>遊び方</th><th>こんな楽しみ</th></tr></thead><tbody><tr><td>1</td><td>久保アグリファーム</td><td>動物・ジェラート・芝生でゆっくり</td></tr><tr><td>2</td><td>川遊び</td><td>水遊び・サワガニ探し</td></tr><tr><td>3</td><td>湯来つり堀</td><td>手軽に魚釣り・釣った魚を味わう</td></tr><tr><td>4</td><td>温泉</td><td>遊んだあとに湯来ロッジなどでひと休み</td></tr></tbody></table></figure>\n<!-- /wp:table -->''',
        wp_p("季節が合えば、夕方からホタル観賞を足すこともできます。全部制覇するより、<strong>牧場＋川、川＋釣り堀</strong>くらいに絞っても十分楽しめます。"),
        wp_h2("久保アグリファーム｜最初は牧場でゆるく遊ぶ"),
        m(0),
        wp_p("最初に寄りやすいのが、サゴタニ牧場・久保アグリファーム。広い牧場の景色を見ながら、牛やヤギを見たり、芝生でのんびりしたりできます。"),
        wp_p("いきなり川へ飛び込むより、まず牧場で遊ぶと一日のスタートがゆるい。小さい子ども連れでも動きやすいです。"),
        wp_p('<a href="https://www.sagotani.net/" target="_blank" rel="noopener">砂谷牛乳・サゴタニ牧農公式サイト</a>'),
        wp_h3("牧場へ来たらジェラート"),
        m(1),
        wp_p("ここで食べたジェラートは、サラッとした口どけで、甘さがしつこくないのにミルク感はしっかり。牧場で食べると、景色まで込みでうまいです。"),
        wp_p('広島の牧場ジェラートを食べ比べたい人は、<a href="https://tsurikue.com/hiroshima-bokujyou/">広島の遊べる牧場5選</a>にもまとめています。'),
        wp_h3("ランチもできると一日の予定が組みやすい"),
        m(2),
        wp_p("訪れた時はバーガーなどの食事も楽しめました。牧場で遊んで、そのまま食事まで済ませられると、子ども連れのドライブではかなり助かります。"),
        wp_h3("芝生でのんびりするだけでも気持ちいい"),
        m(3),
        wp_p("広場ではテントを出して過ごす人もいました。動物を見て、ジェラートを食べて、芝生で休憩。予定を詰め込まず、ここで長めに過ごすのもありです。"),
        wp_h2("湯来町の川遊び｜暑い日はここが本番"),
        m(4),
        wp_p("湯来町の魅力は、やっぱり山の中を流れる川。水がきれいで、暑い日は足を入れるだけでも気持ちいいです。"),
        wp_p("ただし、川は遊具のある公園とは違います。前日に雨が降っていたり、水量が多かったりする日は無理をしない。見た目が穏やかでも急に深くなる場所や滑る石があります。"),
        wp_p("子どもと入るなら、<strong>大人が先に深さと流れを確認すること</strong>。アクアシューズなど脱げにくい履き物も用意しておきたいです。"),
        wp_h3("サワガニ探しは、ちょっとした宝探し"),
        m(5),
        wp_p("川へ入ったら、サワガニ探しも面白いです。石をそっとめくって、下流側に網を構える。サワガニが出てきたらすくう。"),
        wp_p("子どもにとっては、ほぼ宝探し。<strong>そして大人も、なぜか本気になります。</strong>"),
        wp_p("湯来町は、子どもの頃に祖父と川釣りや沢遊びをしていた場所でもあります。今は子どもとサワガニを探す。こういう遊びは、世代が変わっても面白いですね。"),
        wp_p("なお、子どもの<strong>「少しだけ水に入る」</strong>は、あまり信用しない方がいいです。だいたい想像以上に濡れます。"),
        wp_h2("湯来つり堀｜初めての魚釣りにも使いやすい"),
        m(6),
        wp_p("川遊びのあとにもう一つ体験を足すなら、湯来つり堀も候補です。"),
        wp_p("公式サイトでは、マスやヤマメの釣りを手ぶらで楽しめ、夏にはアユのひっかけ釣りも案内されています。釣った魚をその場で調理して食べられるのも大きな楽しみです。"),
        wp_p('<a href="https://morishitakashi.wixsite.com/mysite-3" target="_blank" rel="noopener">湯来つり堀公式サイト</a>'),
        wp_p("魚が見える池で、自分で竿を持って待つ。魚がかかった瞬間は、釣りをしたことがない子どもでも一気にテンションが上がります。"),
        m(7),
        wp_p("実際に釣れた魚を手にすると、嬉しさは写真でもよく分かります。自然の川釣りより成功しやすいので、<strong>子どもの最初の釣り</strong>にも向いています。"),
        wp_p("営業日や対象魚、調理内容は季節で変わることがあるので、釣り堀を目的に行く日は公式サイトを確認してから出発するのがおすすめです。"),
        wp_h2("遊んだあとは温泉へ｜季節が合えばホタルも"),
        m(8),
        wp_p("牧場、川、釣り堀まで遊んだら、帰りに温泉を入れると一日の締めがかなり楽になります。"),
        wp_p("湯来ロッジでは現在も日帰り入浴が案内されているので、川遊びで濡れたり、外でたっぷり遊んだ日の帰り道にも使いやすいです。"),
        wp_p('<a href="https://yuki-lodge.jp/" target="_blank" rel="noopener">湯来ロッジ公式サイト</a>'),
        wp_p('さらに初夏ならホタルも候補。実際に見に行った様子は、<a href="https://tsurikue.com/yuki-hotaru/">湯来町のホタル観賞体験</a>で紹介しています。'),
        wp_h2("湯来町の自然遊びで持って行きたいもの"),
        wp_list([
            "アクアシューズなど濡れてもいい履き物",
            "子どもの着替え",
            "タオル",
            "サワガニを探すなら手網",
            "虫よけ",
            "暑い時期は帽子・飲み物などの熱中症対策",
        ]),
        wp_p("特に大事なのは、<strong>着替えと足元</strong>。川へ行く予定が少しでもあるなら、最初から濡れる前提で準備しておく方が帰り道まで平和です。"),
        wp_h2("湯来町はどんな家族におすすめ？"),
        '''<!-- wp:table -->\n<figure class="wp-block-table"><table><thead><tr><th>こんな人</th><th>おすすめの遊び方</th></tr></thead><tbody><tr><td>小さい子どもとゆっくり遊びたい</td><td>久保アグリファーム中心</td></tr><tr><td>夏に思い切り自然遊びしたい</td><td>川遊び＋サワガニ探し</td></tr><tr><td>初めて魚釣りをさせたい</td><td>湯来つり堀</td></tr><tr><td>一日たっぷり遊びたい</td><td>牧場→川→釣り堀→温泉</td></tr><tr><td>初夏の夕方まで遊べる</td><td>日中の自然遊び＋ホタル</td></tr></tbody></table></figure>\n<!-- /wp:table -->''',
        wp_p("湯来町のいいところは、<strong>全員が同じ遊び方をしなくていいこと</strong>。子どもの年齢や天気に合わせて、牧場だけ、川だけ、釣り堀だけでも成立します。"),
        wp_h2("まとめ｜湯来町は『今日は自然で遊ぼう』の日にちょうどいい"),
        wp_p("湯来町には、牧場、川遊び、サワガニ探し、釣り堀、温泉があります。季節が合えばホタルも楽しめます。"),
        wp_p("全部回らなくても大丈夫。<strong>久保アグリファームでジェラートを食べて、川へ行く。</strong>それだけでも街中とはかなり違う休日になります。"),
        wp_p("もう少し遊べそうなら釣り堀へ。帰りに温泉へ寄る。そんなふうに、その日の様子を見ながら予定を足せるのが湯来町ドライブの使いやすさです。"),
        wp_p('広島の日帰り候補をもっと探すなら、<a href="https://tsurikue.com/hiroshima-sightseeing/">広島観光・レジャーまとめ</a>もどうぞ。'),
        wp_p("※営業時間・定休日・販売商品・体験内容・河川状況などは変わることがあります。目的の施設や体験がある場合は、出発前に公式情報をご確認ください。"),
    ]

    used = min(9, len(media))
    if len(media) > used:
        parts.append(wp_h2("写真で見る湯来町の自然遊び"))
        parts.extend(media[used:])
    return "\n\n".join(part for part in parts if part).strip() + "\n"


def write_report(report: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Yuki town drive reader-first rewrite",
        "",
        f"- result: **{report.get('result')}**",
        f"- post_id: **{report.get('post_id', 0)}**",
        f"- slug: **{SLUG}**",
        f"- status_before: **{report.get('status_before')}**",
        f"- status_after: **{report.get('status_after')}**",
        f"- old_title: {report.get('old_title', '')}",
        f"- new_title: {report.get('new_title', '')}",
        f"- featured_media_before: **{report.get('featured_media_before', 0)}**",
        f"- featured_media_after: **{report.get('featured_media_after', 0)}**",
        f"- media_blocks_preserved: **{report.get('media_blocks_preserved', 0)}**",
        f"- categories_preserved: **{report.get('categories_preserved', False)}**",
        f"- public_before: **{report.get('public_before', {}).get('published_total', 'unknown')}**",
        f"- public_after: **{report.get('public_after', {}).get('published_total', 'unknown')}**",
        f"- wordpress_write_count: **{report.get('wordpress_write_count', 0)}**",
        f"- source_sha256: `{report.get('source_sha256', '')}`",
        f"- content_sha256: `{report.get('content_sha256', '')}`",
        "- publish_count: **0** (existing published post updated in place)",
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
        current_content = raw_field(before, "content")
        current_title = html.unescape(raw_field(before, "title"))
        current_media = media_blocks(current_content)
        current_sha = sha256(current_content)
        featured_media = int(before.get("featured_media") or 0)
        categories = [int(x) for x in (before.get("categories") or [])]

        report.update({
            "post_id": int(before.get("id") or 0),
            "status_before": before.get("status"),
            "old_title": current_title,
            "new_title": NEW_TITLE,
            "featured_media_before": featured_media,
            "public_before": before_counts,
            "source_sha256": current_sha,
            "media_blocks_preserved": len(current_media),
        })

        if int(before.get("id") or 0) != POST_ID or before.get("slug") != SLUG:
            raise RuntimeError("target identity mismatch")
        if before.get("status") != "publish":
            raise RuntimeError("target is not published")
        if current_title not in {EXPECTED_OLD_TITLE, NEW_TITLE}:
            raise RuntimeError(f"unexpected current title: {current_title!r}")
        if featured_media != EXPECTED_FEATURED_MEDIA:
            raise RuntimeError(f"featured media mismatch: {featured_media}")
        if not categories:
            raise RuntimeError("categories missing")
        if len(current_media) < 9:
            raise RuntimeError(f"unexpectedly low media block count: {len(current_media)}")

        desired = build_content(current_media)
        if "<h1" in desired.casefold():
            raise RuntimeError("body contains H1")
        if any(emoji in desired for emoji in ("😏", "🔥", "🤣")):
            raise RuntimeError("emoji found in article body")
        if "普通に" in desired:
            raise RuntimeError("disallowed expression '普通に' found")

        # Re-fetch immediately before write. Any manual/concurrent edit blocks the run.
        latest = fetch_target(auth)
        latest_content = raw_field(latest, "content")
        if sha256(latest_content) != current_sha:
            raise RuntimeError("content changed after snapshot; refusing overwrite")
        if int(latest.get("featured_media") or 0) != featured_media:
            raise RuntimeError("featured media changed after snapshot")
        if [int(x) for x in (latest.get("categories") or [])] != categories:
            raise RuntimeError("categories changed after snapshot")

        response, _ = request_json(
            f"{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}",
            auth,
            method="POST",
            payload={"title": NEW_TITLE, "content": desired, "status": "publish"},
        )
        if int(response.get("id") or 0) != POST_ID or response.get("status") != "publish":
            raise RuntimeError("WordPress update response validation failed")

        after = fetch_target(auth)
        after_counts = public_counts(auth)
        after_content = raw_field(after, "content")
        after_media = media_blocks(after_content)
        after_title = html.unescape(raw_field(after, "title"))

        if before_counts != after_counts:
            raise RuntimeError(f"published counts changed: {before_counts} -> {after_counts}")
        if after.get("status") != "publish" or after.get("slug") != SLUG:
            raise RuntimeError("post-update identity/status mismatch")
        if after_title != NEW_TITLE:
            raise RuntimeError("post-update title mismatch")
        if int(after.get("featured_media") or 0) != featured_media:
            raise RuntimeError("featured media changed")
        if [int(x) for x in (after.get("categories") or [])] != categories:
            raise RuntimeError("categories changed")
        if after_media != current_media:
            raise RuntimeError("existing media blocks were not preserved exactly")
        if after_content.strip() != desired.strip():
            raise RuntimeError("post-update content mismatch")

        report.update({
            "result": "SUCCESS",
            "status_after": after.get("status"),
            "featured_media_after": int(after.get("featured_media") or 0),
            "categories_preserved": True,
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
