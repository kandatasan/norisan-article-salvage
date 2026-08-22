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
USER_AGENT = "tsurikue-public-internal-links-once/1.0"
REPORT_DIR = Path("reports/public-internal-links-apply")
BATCH_MARKER = "sitewide-20260822"

PATCHES: list[dict[str, Any]] = [
    {
        "id": 2408, "slug": "muvalley",
        "title": "美川ムーバレーは怖い？大人だけで行った本音口コミ｜所要時間・服装・料金",
        "sha": "c9863f109d21fcd5e43b41b42efb20ef6c72a0483e414f1a8b9e7ea3f65fefca",
        "targets": ["yamaguchi-drive"],
        "text": '美川ムーバレーを含めて元乃隅神社・角島まで巡った旅全体は、<a href="https://tsurikue.com/yamaguchi-drive/">広島発の山口観光1泊2日モデルコース</a>にまとめています。',
    },
    {
        "id": 2437, "slug": "motonosumi",
        "title": "元乃隅神社へ行ってみた｜アクセス・滞在時間・写真スポットと賽銭箱の現在",
        "sha": "a3e839f96ea6bea565a656315dfc0c0d822d2032e2af23233b1f74c97a222229",
        "targets": ["yamaguchi-drive"],
        "text": '元乃隅神社だけでなく、美川ムーバレー・萩・角島まで車で巡った流れは、<a href="https://tsurikue.com/yamaguchi-drive/">山口観光1泊2日モデルコース</a>でまとめています。',
    },
    {
        "id": 2456, "slug": "kulabotaisyoukan",
        "title": "KULABO大正館に宿泊した口コミ｜素泊まりの部屋・無料駐車場・館内を紹介",
        "sha": "aa86c4557f34dc5674a61fbb721ec6904ba9dcfa9a16439d1ee1172ea5e920fd",
        "targets": ["yamaguchi-drive"],
        "text": 'KULABO大正館を宿にして実際に巡った1泊2日のルートは、<a href="https://tsurikue.com/yamaguchi-drive/">広島発の山口観光モデルコース</a>にまとめています。',
    },
    {
        "id": 2479, "slug": "tsunoshima",
        "title": "角島大橋と角島を観光してきた｜写真スポット・所要時間・角島灯台も紹介",
        "sha": "58650bd4e559c750d7ff807c709abf7c27307225a49d861bd07caf6a3f986a6c",
        "targets": ["yamaguchi-drive"],
        "text": '角島をゴール側にして、美川ムーバレー・萩・元乃隅神社も巡った実際のルートは、<a href="https://tsurikue.com/yamaguchi-drive/">山口観光1泊2日モデルコース</a>で紹介しています。',
    },
    {
        "id": 1939, "slug": "hiroshima-sanin-1night-2days",
        "title": "広島から山陰へ1泊2日ドライブ旅｜島根〜鳥取を車で巡る旅行記",
        "sha": "298e28b074f8eba1e8a6a4c183c39ff28b9d15963a34fdc43b05eb551aa91a73",
        "targets": ["tottori-drive", "totoya-iiyo"],
        "text": '鳥取側の立ち寄り先を詳しく見るなら<a href="https://tsurikue.com/tottori-drive/">鳥取ドライブ観光まとめ</a>へ。宿泊した浜村温泉の宿は、<a href="https://tsurikue.com/totoya-iiyo/">「魚と屋」の宿泊レビュー</a>で部屋や料理まで詳しく紹介しています。',
    },
    {
        "id": 2658, "slug": "tottori-drive",
        "title": "鳥取ドライブ観光｜境港・大山・コナン・砂の美術館へ【砂丘は雨で断念】",
        "sha": "82061467e2ec3905f3210bb8f4ea923732e0d324107ec3ab3aca4e1b7739fd2f",
        "targets": ["totoya-iiyo", "matubagani", "kotamagai-seafood-gathering"],
        "text": '鳥取で実際に泊まった宿は<a href="https://tsurikue.com/totoya-iiyo/">浜村温泉「魚と屋」</a>。境港では<a href="https://tsurikue.com/matubagani/">松葉ガニを買って実食</a>し、米子の海では<a href="https://tsurikue.com/kotamagai-seafood-gathering/">オキアサリ採り</a>まで楽しみました。',
    },
    {
        "id": 2640, "slug": "kotamagai-seafood-gathering",
        "title": "オキアサリの採り方｜米子の海で足を使って探した体験記",
        "sha": "d50462ff9fc925a26b5e0c43e1d5c7e374cb4d9dcb8a58ae17265ae86ece0a9c",
        "targets": ["tottori-drive"],
        "text": '米子だけでなく境港・大山・鳥取方面まで実際に車で巡ったスポットは、<a href="https://tsurikue.com/tottori-drive/">鳥取ドライブ観光まとめ</a>に整理しています。',
    },
    {
        "id": 1887, "slug": "etajima-sightseeing",
        "title": "江田島観光に行こう｜ドライブ良し・食事良し・景色良しの休日旅",
        "sha": "d032cd69ec3cfb1660584ebc27dee50ae9072e1e9f946b3b55f41e0612412c6c",
        "targets": ["hiroshima-hajimarinoteras", "mamegashima", "human-beach-nagase"],
        "text": '江田島をもう少し細かく見るなら、海辺で休憩した<a href="https://tsurikue.com/hiroshima-hajimarinoteras/">ハジマリノテラス</a>、鬼と豆腐が気になった<a href="https://tsurikue.com/mamegashima/">豆ヶ島</a>、ドライブ中に立ち寄った<a href="https://tsurikue.com/human-beach-nagase/">ヒューマンビーチ長瀬</a>の体験記もあります。',
    },
    {
        "id": 2041, "slug": "hiroshima-sightseeing",
        "title": "広島観光・レジャーまとめ｜車で行ける日帰りドライブ先を紹介",
        "sha": "467f260e6e1b1997e8cdacc18a004473cf7d19f74dc254fb11707108175cb29b",
        "targets": ["etajima-sightseeing", "orizuru-tower"],
        "text": '海沿いドライブまで楽しむなら<a href="https://tsurikue.com/etajima-sightseeing/">江田島観光まとめ</a>へ。広島市中心部では、実際に行って料金も含めて本音で書いた<a href="https://tsurikue.com/orizuru-tower/">おりづるタワー体験記</a>もあります。',
    },
    {
        "id": 2647, "slug": "orizuru-tower",
        "title": "おりづるタワーの料金は高い？実際に行って分かった楽しみ方と本音【広島観光】",
        "sha": "56a7078fbb930036e603648591215733f76213a026f1d1f54567b253677cc6b1",
        "targets": ["hiroshima-sightseeing"],
        "text": 'おりづるタワー以外にも実際に行った広島の休日候補は、<a href="https://tsurikue.com/hiroshima-sightseeing/">広島観光・レジャーまとめ</a>に整理しています。',
    },
    {
        "id": 2654, "slug": "sayori-taberu",
        "title": "釣ったサヨリは美味しい？刺身と塩焼きで食べてみた｜姫ひじきの塩がよく合う",
        "sha": "f66706a6bce956a0e8ff43e9111bab73f7d7b3a1036f2bd2d88821f81e07c484",
        "targets": ["sayori", "sayori-tsurikata"],
        "text": 'このサヨリを実際に釣った日の様子は<a href="https://tsurikue.com/sayori/">江田島のサヨリ釣行記</a>へ。仕掛けやエサを先に知りたい人は、<a href="https://tsurikue.com/sayori-tsurikata/">延べ竿でのサヨリの釣り方</a>にまとめています。',
    },
    {
        "id": 2655, "slug": "sayori-tsurikata",
        "title": "サヨリの釣り方｜延べ竿＋市販仕掛けなら初心者でも簡単！エサ・撒き餌も解説",
        "sha": "53397bcd40a2571731a002f1bb93971cbf9261308cfa1ba4ba82b90cd8a04b74",
        "targets": ["sayori", "sayori-taberu"],
        "text": 'この仕掛けで実際に楽しんだ様子は<a href="https://tsurikue.com/sayori/">江田島のサヨリ釣行記</a>へ。釣ったあとは、<a href="https://tsurikue.com/sayori-taberu/">刺身と塩焼きで食べた実食編</a>まで続きます。',
    },
    {
        "id": 2660, "slug": "tsureruurawaza",
        "title": "ルアー・ワームで魚が釣れない？裏技！ガルプ粉＋特撰えび粉を試してみた",
        "sha": "2f4b7bd69b48f333ded30d01dcf20c070518e306310d827637e9c98af4a60552",
        "targets": ["gulpalivepowder", "gulp-powder"],
        "text": 'ガルプ粉そのものの反応が気になるなら、<a href="https://tsurikue.com/gulpalivepowder/">ティッシュにまぶしてGoProと沈めた水中実験</a>へ。釣り餌への使い方では、<a href="https://tsurikue.com/gulp-powder/">鳥ササミをガルプ粉＋塩で漬けた実験</a>もやっています。',
    },
    {
        "id": 2629, "slug": "gulp-powder",
        "title": "ガルプはワームだけじゃない！？ガルプ！アライブパウダー＋塩で鳥ササミを漬けてみた",
        "sha": "fdf47636da1e87bbe05d33fadb323450d5275e27d77454f4b8044c067236e9d0",
        "targets": ["gulpalivepowder"],
        "text": 'そもそもガルプ！アライブパウダーに魚がどれくらい反応するのかは、<a href="https://tsurikue.com/gulpalivepowder/">ティッシュに粉をまぶして水中へ沈めた実験</a>でも確かめています。',
    },
    {
        "id": 2350, "slug": "kanritsuriba",
        "title": "フィッシングレイクたかみやで初フライ｜レンタル釣具で初心者が釣れた体験記",
        "sha": "25d0fde27d6f2db02fbf14db0feb10286fde573181ddd3f9d226db1024d1fbe3",
        "targets": ["trout-cooking"],
        "text": 'フィッシングレイクたかみやで持ち帰った魚は、家でもしっかり楽しみました。<a href="https://tsurikue.com/trout-cooking/">ギンザケを塩焼き・刺身・石狩鍋で食べた実食編</a>もあります。',
    },
    {
        "id": 2391, "slug": "trout-cooking",
        "title": "管理釣り場の魚は美味しい？ギンザケを塩焼き・刺身・石狩鍋で食べてみた",
        "sha": "75ac81ab0489b0c688490e5c22f951560dbc954192c7784f79b565d226e1b4b0",
        "targets": ["kanritsuriba"],
        "text": 'このギンザケを持ち帰った釣行は、<a href="https://tsurikue.com/kanritsuriba/">フィッシングレイクたかみやで初めてフライフィッシングに挑戦した体験記</a>で紹介しています。',
    },
    {
        "id": 2651, "slug": "sabiki-beginner",
        "title": "サビキ釣り初心者ガイド｜仕掛け・竿・エサ・釣り方のコツまでこれ1本",
        "sha": "3911263523f64bb599f491c9fc34d0b6cd1f88db55ec03b4fe29eb261c758c32",
        "targets": ["tougorouiwashi"],
        "text": '実際に江田島でコイワシ狙いのサビキをしていた時にはトウゴロウイワシも釣れました。持ち帰った魚は、<a href="https://tsurikue.com/tougorouiwashi/">唐揚げ・塩焼き・せごし・刺身で食べ比べ</a>ています。',
    },
    {
        "id": 2659, "slug": "tougorouiwashi",
        "title": "トウゴロウイワシは美味しい？唐揚げ・塩焼き・せごし・刺身で食べてみた",
        "sha": "813d648e3519e31d1f23ccb009a3ee4a750d883be678fa7bd9b005804a34e933",
        "targets": ["sabiki-beginner"],
        "text": 'このトウゴロウイワシを釣ったのはコイワシ狙いのサビキ釣りでした。初めて仕掛けを触る人向けには、<a href="https://tsurikue.com/sabiki-beginner/">サビキ釣りの道具・エサ・釣り方</a>をまとめています。',
    },
    {
        "id": 2625, "slug": "gekiyasu-metal-vibration",
        "title": "激安メタルバイブ「ゲキブルブレード」を実釣インプレ｜安くても魚は釣れる！",
        "sha": "49ff2bd96ffe4dba7139c90575d4e777c106eaa96710d335c0ef83f83b3ca4e5",
        "targets": ["kanritsuriba", "tsureruurawaza"],
        "text": 'ゲキブルブレードを実際に持ち込んだ<a href="https://tsurikue.com/kanritsuriba/">フィッシングレイクたかみやの釣行記</a>もあります。ルアーで反応がない時には、<a href="https://tsurikue.com/tsureruurawaza/">ガルプ粉＋えび粉をまぶして試した裏技</a>も実験しました。',
    },
    {
        "id": 2639, "slug": "komugikodesakanatsureruyo",
        "title": "小麦粉は釣り餌になる？水で練るだけの簡単練り餌でハヤを釣ってみた",
        "sha": "7cd85afe9ba9d1d3eb5a9efa2bbdbacd8418c47c515f2091cb86d2cb09445aa6",
        "targets": ["tsureruurawaza"],
        "text": 'こういう「いつものエサやルアーへひと工夫する遊び」が好きなら、<a href="https://tsurikue.com/tsureruurawaza/">ルアー・ワームへガルプ粉＋えび粉を使った実釣実験</a>もやっています。',
    },
    {
        "id": 2575, "slug": "ccwatergold",
        "title": "CCウォーターゴールドの評価は？プレミアを使って感じた効果・防汚・ムラの注意点",
        "sha": "edc1f6049e46e4fc8b53957b5487cb5481af8ec00c2731b8ec96bbc8a73fc1ae",
        "targets": ["ux-koukai"],
        "text": 'CCウォーターゴールド プレミアを実際に施工していた車はレクサスUXです。車そのものの良かった点と後悔した点は、<a href="https://tsurikue.com/ux-koukai/">レクサスUXを616万円で買って感じた本音レビュー</a>にまとめています。',
    },
]


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def request_json(url: str, auth: str, method: str = "GET", payload: dict[str, Any] | None = None):
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Accept": "application/json", "Authorization": auth, "User-Agent": USER_AGENT}
    if data is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=60) as response:
                return json.loads(response.read().decode("utf-8")), dict(response.headers)
        except Exception as exc:
            last_exc = exc
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
    assert last_exc is not None
    raise last_exc


def raw_field(row: dict[str, Any], key: str) -> str:
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)


def fetch_post(post_id: int, auth: str) -> dict[str, Any]:
    query = urllib.parse.urlencode({"context": "edit", "_fields": "id,slug,status,title,content,featured_media"})
    row, _ = request_json(f"{SITE_URL}/wp-json/wp/v2/posts/{post_id}?{query}", auth)
    return row


def fetch_published_slugs(auth: str) -> set[str]:
    slugs: set[str] = set()
    page = 1
    while True:
        q = urllib.parse.urlencode({"context": "edit", "status": "publish", "per_page": "100", "page": str(page), "_fields": "slug"})
        rows, headers = request_json(f"{SITE_URL}/wp-json/wp/v2/posts?{q}", auth)
        slugs.update(str(r.get("slug") or "") for r in rows)
        total_pages = int(headers.get("X-WP-TotalPages", "1"))
        if page >= total_pages:
            return slugs
        page += 1


def count_published(endpoint: str, auth: str) -> int:
    q = urllib.parse.urlencode({"context": "edit", "status": "publish", "per_page": "1", "_fields": "id"})
    _, headers = request_json(f"{SITE_URL}/wp-json/wp/v2/{endpoint}?{q}", auth)
    return int(headers.get("X-WP-Total", "0"))


def public_counts(auth: str) -> dict[str, int]:
    posts = count_published("posts", auth)
    pages = count_published("pages", auth)
    return {"posts": posts, "pages": pages, "total": posts + pages}


def media_ids(content: str) -> list[int]:
    out: list[int] = []
    for m in re.finditer(r"wp-image-(\d+)|\"id\"\s*:\s*(\d+)", content):
        mid = int(m.group(1) or m.group(2))
        if mid not in out:
            out.append(mid)
    return out


def internal_slugs(content: str) -> set[str]:
    slugs: set[str] = set()
    for href in re.findall(r"<a\b[^>]*\bhref=['\"]([^'\"]+)['\"]", content, flags=re.I):
        parsed = urllib.parse.urlsplit(html.unescape(href))
        if href.startswith("/") or (parsed.hostname or "").lower() in {"tsurikue.com", "www.tsurikue.com"}:
            path = parsed.path.strip("/")
            if path:
                slugs.add(path.split("/")[-1])
    return slugs


def patch_marker(slug: str) -> str:
    return f"<!-- tsurikue-internal-links:{BATCH_MARKER}:{slug} -->"


def desired_content(current: str, patch: dict[str, Any]) -> str:
    marker = patch_marker(patch["slug"])
    block = f'''{marker}\n\n<!-- wp:paragraph -->\n<p>{patch["text"]}</p>\n<!-- /wp:paragraph -->'''
    return current.rstrip() + "\n\n" + block + "\n"


def write_report(report: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Public internal-link optimization",
        "",
        f"- result: **{report['result']}**",
        f"- planned_articles: **{report.get('planned_articles', 0)}**",
        f"- updated_articles: **{report.get('updated_articles', 0)}**",
        f"- added_text_links: **{report.get('added_text_links', 0)}**",
        f"- blocked_articles: **{report.get('blocked_articles', 0)}**",
        f"- public_before: **{report.get('public_before', 'unknown')}**",
        f"- public_after: **{report.get('public_after', 'unknown')}**",
        f"- wordpress_write_count: **{report.get('wordpress_write_count', 0)}**",
        "",
        "## Per article",
        "",
    ]
    for row in report.get("articles", []):
        lines.append(f"- `{row['slug']}` — **{row['result']}** / links +{row.get('links_added', 0)} / sha `{row.get('after_sha', '')}`")
        if row.get("error"):
            lines.append(f"  - error: `{row['error']}`")
    if report.get("error"):
        lines += ["", f"- error: `{report['error']}`"]
    (REPORT_DIR / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    report: dict[str, Any] = {
        "result": "BLOCKED",
        "planned_articles": len(PATCHES),
        "updated_articles": 0,
        "added_text_links": 0,
        "blocked_articles": 0,
        "public_before": "unknown",
        "public_after": "unknown",
        "wordpress_write_count": 0,
        "articles": [],
    }
    try:
        user = os.environ.get("TSURIKUE_WP_USER")
        password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
        if not user or not password:
            raise RuntimeError("missing WordPress secrets")
        auth = auth_header(user, password)

        before_counts = public_counts(auth)
        published_slugs = fetch_published_slugs(auth)
        report["public_before"] = before_counts["total"]

        # Phase 1: validate every source and destination before the first write.
        preflight: list[tuple[dict[str, Any], dict[str, Any], str, list[int], int]] = []
        for patch in PATCHES:
            missing_dest = [s for s in patch["targets"] if s not in published_slugs]
            if missing_dest:
                raise RuntimeError(f"{patch['slug']}: destination not published: {missing_dest}")
            row = fetch_post(patch["id"], auth)
            current = raw_field(row, "content")
            title = html.unescape(raw_field(row, "title"))
            current_sha = hashlib.sha256(current.encode()).hexdigest()
            if int(row.get("id") or 0) != patch["id"] or row.get("slug") != patch["slug"]:
                raise RuntimeError(f"{patch['slug']}: id/slug mismatch")
            if row.get("status") != "publish":
                raise RuntimeError(f"{patch['slug']}: source is not publish")
            if title != patch["title"]:
                raise RuntimeError(f"{patch['slug']}: title changed: {title!r}")
            if current_sha != patch["sha"]:
                raise RuntimeError(f"{patch['slug']}: content hash changed: {current_sha}")
            marker = patch_marker(patch["slug"])
            if marker in current:
                raise RuntimeError(f"{patch['slug']}: patch marker already present")
            existing = internal_slugs(current)
            duplicate_targets = [s for s in patch["targets"] if s in existing]
            if duplicate_targets:
                raise RuntimeError(f"{patch['slug']}: intended target already linked: {duplicate_targets}")
            preflight.append((patch, row, current, media_ids(current), int(row.get("featured_media") or 0)))

        # Phase 2: apply additive text-link blocks only after the entire batch preflight passes.
        for patch, before, current, before_media, before_featured in preflight:
            desired = desired_content(current, patch)
            article_result: dict[str, Any] = {"slug": patch["slug"], "result": "BLOCKED", "links_added": 0, "after_sha": ""}
            try:
                try:
                    response, _ = request_json(
                        f"{SITE_URL}/wp-json/wp/v2/posts/{patch['id']}",
                        auth,
                        method="POST",
                        payload={"content": desired, "status": "publish"},
                    )
                    if int(response.get("id") or 0) != patch["id"] or response.get("status") != "publish":
                        raise RuntimeError("update response validation failed")
                except Exception:
                    # A timeout can happen after WordPress committed the write. Re-read before deciding it failed.
                    probe = fetch_post(patch["id"], auth)
                    probe_content = raw_field(probe, "content")
                    if probe.get("status") != "publish" or probe_content.strip() != desired.strip():
                        raise

                after = fetch_post(patch["id"], auth)
                after_content = raw_field(after, "content")
                after_title = html.unescape(raw_field(after, "title"))
                after_media = media_ids(after_content)
                if after.get("status") != "publish" or after.get("slug") != patch["slug"]:
                    raise RuntimeError("post-update publish/slug state mismatch")
                if after_title != patch["title"]:
                    raise RuntimeError("post-update title changed")
                if int(after.get("featured_media") or 0) != before_featured:
                    raise RuntimeError("featured_media changed")
                if after_media != before_media:
                    raise RuntimeError(f"article media ids changed: {before_media} -> {after_media}")
                if after_content.strip() != desired.strip():
                    raise RuntimeError("post-update content mismatch")
                for target in patch["targets"]:
                    if target not in internal_slugs(after_content):
                        raise RuntimeError(f"target link missing after update: {target}")
                article_result.update({
                    "result": "SUCCESS",
                    "links_added": len(patch["targets"]),
                    "after_sha": hashlib.sha256(after_content.encode()).hexdigest(),
                })
                report["updated_articles"] += 1
                report["added_text_links"] += len(patch["targets"])
                report["wordpress_write_count"] += 1
                report["articles"].append(article_result)
            except Exception as exc:
                article_result["error"] = str(exc)
                report["blocked_articles"] += 1
                report["articles"].append(article_result)
                raise RuntimeError(f"{patch['slug']}: apply failed: {exc}") from exc

        after_counts = public_counts(auth)
        report["public_after"] = after_counts["total"]
        if after_counts != before_counts:
            raise RuntimeError(f"published counts changed: {before_counts} -> {after_counts}")
        report["result"] = "SUCCESS"
        write_report(report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        report["error"] = str(exc)
        if report["public_after"] == "unknown" and report["public_before"] != "unknown":
            try:
                user = os.environ.get("TSURIKUE_WP_USER")
                password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
                if user and password:
                    report["public_after"] = public_counts(auth_header(user, password))["total"]
            except Exception:
                pass
        write_report(report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
