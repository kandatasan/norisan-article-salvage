#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import re
import urllib.request

SITE = "https://tsurikue.com"
UA = "tsurikue-gsc-batch-micro-updates-20260923/1.0"

TARGETS = [
    {
        "id": 2975,
        "slug": "lexus-ux-model-change",
        "old_title": "レクサスUXのモデルチェンジはいつ？次期型は出る？生産終了の噂も整理",
        "new_title": "レクサスUXのモデルチェンジはいつ？2027年2月生産終了・次期型は出る？",
        "featured_media": 2244,
        "kind": "ux_section",
        "mark": "2027年2月をもって生産終了予定",
    },
    {
        "id": 2621,
        "slug": "agetate-tenpura-hongo",
        "old_title": "あつあつ揚立てっちゃん本郷店へ｜揚げたて天ぷらが熱々すぎて最高！",
        "new_title": "あつあつ揚立てっちゃん本郷店へ｜メニューも紹介！揚げたて天ぷらが熱々すぎて最高",
        "featured_media": 569,
        "kind": "agetate",
        "mark": "Yahoo!マップで現在のメニュー掲載を見る",
    },
    {
        "id": 2647,
        "slug": "orizuru-tower",
        "old_title": "おりづるタワーの料金は高い？実際に行って分かった楽しみ方と本音【広島観光】",
        "new_title": None,
        "featured_media": 801,
        "kind": "orizuru",
        "mark": "所要時間を90分",
    },
    {
        "id": 2622,
        "slug": "catfish",
        "old_title": "ナマズの釣り方｜釣れる時期・ポイント・ルアー・エサ釣りを初心者向けに解説",
        "new_title": None,
        "featured_media": 125,
        "kind": "catfish",
        "mark": "ナマズの餌釣り仕掛け｜ミミズや魚の切り身でブッコミ釣り",
    },
    {
        "id": 2639,
        "slug": "komugikodesakanatsureruyo",
        "old_title": "小麦粉は釣り餌になる？水で練るだけの簡単練り餌でハヤを釣ってみた",
        "new_title": None,
        "featured_media": 0,
        "kind": "komugi",
        "mark": "小麦粉と水の分量は？水を少しずつ入れて固さで調整",
    },
    {
        "id": 2659,
        "slug": "tougorouiwashi",
        "old_title": "トウゴロウイワシは美味しい？唐揚げ・塩焼き・せごし・刺身で食べてみた",
        "new_title": None,
        "featured_media": 311,
        "kind": "tougorou",
        "mark": "4種類を食べ比べると、こんな違いがありました",
    },
    {
        "id": 1887,
        "slug": "etajima-sightseeing",
        "old_title": "江田島観光に行こう｜ドライブ良し・食事良し・景色良しの休日旅",
        "new_title": None,
        "featured_media": 0,
        "kind": "etajima",
        "mark": "江田島ドライブの立ち寄り例",
    },
]

TOKEN = re.compile(r"<!--\s+/?wp:[\s\S]*?-->")
OPEN = re.compile(r"<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->")
CLOSE = re.compile(r"<!--\s+/wp:([\w\-/]+)\s+-->")

def auth():
    raw = f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()
    return "Basic " + base64.b64encode(raw).decode()

def req(url, method="GET", payload=None):
    headers = {"Accept": "application/json", "Authorization": auth(), "User-Agent": UA}
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode()
        headers["Content-Type"] = "application/json; charset=utf-8"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode()), dict(response.headers)

def raw(row, key):
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)

def get_post(pid):
    row, _ = req(f"{SITE}/wp-json/wp/v2/posts/{pid}?context=edit")
    return row

def pub_count():
    _, headers = req(f"{SITE}/wp-json/wp/v2/posts?status=publish&per_page=1&_fields=id")
    return int(headers.get("X-WP-Total", 0))

def block_problems(text):
    stack = []
    for match in TOKEN.finditer(text):
        token = match.group(0)
        opened = OPEN.fullmatch(token)
        closed = CLOSE.fullmatch(token)
        if opened:
            if opened.group(2):
                continue
            stack.append(opened.group(1))
        elif closed:
            name = closed.group(1)
            if not stack or stack[-1] != name:
                return [("mismatch", stack[-1] if stack else None, name)]
            stack.pop()
    return [("unclosed", stack)] if stack else []

def h2(title):
    return f'<!-- wp:heading -->\n<h2 class="wp-block-heading">{title}</h2>\n<!-- /wp:heading -->'

def replace_between_headings(content, start_title, end_title, replacement):
    start = h2(start_title)
    end = h2(end_title)
    if content.count(start) != 1 or content.count(end) != 1:
        raise RuntimeError(f"heading guard failed: {start_title} / {end_title}")
    a = content.index(start)
    b = content.index(end)
    if a >= b:
        raise RuntimeError("section order guard failed")
    return content[:a] + replacement + "\n\n" + content[b:]

def insert_before_heading(content, title, block):
    anchor = h2(title)
    if content.count(anchor) != 1:
        raise RuntimeError(f"heading guard failed: {title}")
    pos = content.index(anchor)
    return content[:pos] + block + "\n\n" + content[pos:]

def insert_after_heading(content, title, block):
    anchor = h2(title)
    if content.count(anchor) != 1:
        raise RuntimeError(f"heading guard failed: {title}")
    pos = content.index(anchor) + len(anchor)
    return content[:pos] + "\n\n" + block + content[pos:]

def replace_heading(content, old, new):
    a = h2(old)
    b = h2(new)
    if content.count(a) != 1:
        raise RuntimeError(f"heading guard failed: {old}")
    return content.replace(a, b, 1)

UX_SECTION = """<!-- wp:heading -->
<h2 class="wp-block-heading">レクサスUXはフルモデルチェンジせず生産終了する？</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p><strong>ここは状況が変わりました。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>レクサス公式は現在、UXについて<strong>2027年2月をもって生産終了予定</strong>と案内しています。<br>また、検討する時期によっては、生産予定台数に達したため予定より早く販売終了となる場合があるとも案内されています。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>→ <a href="https://lexus.jp/models/ux/" target="_blank" rel="noreferrer noopener">レクサス公式｜UX生産終了のお知らせ</a></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>ただし、<strong>現行UXの生産終了＝次期UXが出ない</strong>という意味ではありません。<br>2026年9月23日時点で、レクサスから次期UXやフルモデルチェンジ時期についての公式発表は確認できません。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>なので今は、「UXは2027年2月に生産終了する」は公式情報。<br>一方で「そのあと新型UXが出るか」はまだ未発表、と分けて考えるのが分かりやすいです。</p>
<!-- /wp:paragraph -->"""

AGETATE_BLOCK = """<!-- wp:heading -->
<h2 class="wp-block-heading">あつあつ揚立てっちゃん本郷店のメニューは？</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>2026年9月にオンラインのメニュー掲載を確認すると、<strong>天ぷら定食・上天ぷら定食・彩り定食・太刀魚の天重定食・えび天定食</strong>などが掲載されています。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>→ <a href="https://map.yahoo.co.jp/v3/place/Gcx-qVzZyKs/menu" target="_blank" rel="noreferrer noopener">Yahoo!マップで現在のメニュー掲載を見る</a></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>私が食べた時に一推しだったのは、上で紹介した<strong>炙り太刀天重</strong>。<br>メニュー名や価格、提供内容は変わることがあるので、行く前や店頭の券売機で最新の内容を確認してください。</p>
<!-- /wp:paragraph -->"""

ORIZURU_BLOCK = """<!-- wp:heading -->
<h2 class="wp-block-heading">おりづるタワーの所要時間は？目安は約90分</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>広島県の公式観光サイト「Dive! Hiroshima」のモデルコースでは、<strong>おりづるタワーの所要時間を90分</strong>で組んでいます。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>→ <a href="https://dive-hiroshima.com/course/course-84101/" target="_blank" rel="noreferrer noopener">Dive! Hiroshimaのモデルコースを見る</a></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>これは施設の制限時間ではなく、観光コースを組む時の目安です。<br>屋上から景色を見て、おりづるを折って、デジタルコンテンツや散歩坂を楽しみ、お土産まで見るなら、<strong>1時間半くらい空けておくと予定を組みやすい</strong>と思います。</p>
<!-- /wp:paragraph -->"""

KOMUGI_BLOCK = """<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">小麦粉と水の分量は？水を少しずつ入れて固さで調整</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>この練り餌は、きっちり「小麦粉○g・水○ml」と量らなくても作れます。<br><strong>小麦粉へ水を少しずつ加えて、耳たぶくらいの固さまでこねる</strong>。私がやっていたのはこの作り方です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>最初から水をたくさん入れるのではなく、少しずつ加えながら固さを見る方が調整しやすいです。</p>
<!-- /wp:paragraph -->"""

TOUGOROU_BLOCK = """<!-- wp:paragraph -->
<p><strong>先に結論をまとめると、私の一推しは唐揚げです。</strong><br>4種類を食べ比べると、こんな違いがありました。</p>
<!-- /wp:paragraph -->

<!-- wp:list -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li><strong>唐揚げ</strong>：一番おすすめ。頑丈なウロコまでサクサクになった</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li><strong>塩焼き</strong>：味は良い。ただしウロコは剥がした方がいい</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li><strong>せごし</strong>：手軽でサッパリ。小さい魚と相性が良かった</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li><strong>刺身</strong>：美味しい。でも3枚おろしがちょっと面倒</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->"""

ETAJIMA_BLOCK = """<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">江田島ドライブの立ち寄り例</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>この記事で紹介しているスポットをつなぐなら、こんな流れで江田島を楽しめます。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>ハジマリノテラス → 島の駅 豆ヶ島 → 江田島オリーブファクトリー → ウミノス スパ＆リゾート → ヒューマンビーチ長瀬</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>飲食店や施設の営業状況は変わることがあるので、その日の営業を確認しながら「海沿いを走って、気になる場所へ寄る」くらいの組み方が江田島には合っています。</p>
<!-- /wp:paragraph -->"""

def make_fixed(content, kind):
    if kind == "ux_section":
        return replace_between_headings(
            content,
            "レクサスUXはフルモデルチェンジせず生産終了する？",
            "2026年のShining Essenceは新型UXではない",
            UX_SECTION,
        )
    if kind == "agetate":
        return insert_before_heading(content, "あつあつ揚立てっちゃん本郷店の店舗情報", AGETATE_BLOCK)
    if kind == "orizuru":
        return insert_before_heading(content, "おりづるタワーへ初入場！思ったより遊べるぞ", ORIZURU_BLOCK)
    if kind == "catfish":
        return replace_heading(
            content,
            "エサ釣りはかなりシンプルでOK",
            "ナマズの餌釣り仕掛け｜ミミズや魚の切り身でブッコミ釣り",
        )
    if kind == "komugi":
        return insert_after_heading(content, "小麦粉練り餌の作り方｜水を入れてこねるだけ", KOMUGI_BLOCK)
    if kind == "tougorou":
        return insert_after_heading(content, "トウゴロウイワシを4種類で食べてみた", TOUGOROU_BLOCK)
    if kind == "etajima":
        return insert_before_heading(content, "江田島観光：飲食店・立ち寄りスポット", ETAJIMA_BLOCK)
    raise RuntimeError(f"unknown kind: {kind}")

def verify_identity(row, target):
    assert row.get("id") == target["id"]
    assert row.get("slug") == target["slug"]
    assert row.get("status") == "publish"
    assert raw(row, "title") == target["old_title"]
    assert int(row.get("featured_media") or 0) == target["featured_media"]

def main():
    before_total = pub_count()
    prepared = []

    # Preflight every post before any write.
    for target in TARGETS:
        row = get_post(target["id"])
        verify_identity(row, target)
        before = raw(row, "content")
        assert target["mark"] not in before, f"mark already present: {target['slug']}"
        assert not block_problems(before), f"broken Gutenberg before: {target['slug']}"

        fixed = make_fixed(before, target["kind"])
        assert target["mark"] in fixed
        assert len(re.findall(r"<!-- wp:image\b", fixed)) == len(re.findall(r"<!-- wp:image\b", before))
        assert len(re.findall(r"\[blog_parts\s+id=", fixed)) == len(re.findall(r"\[blog_parts\s+id=", before))
        assert not block_problems(fixed), f"broken Gutenberg after local edit: {target['slug']}"

        prepared.append({
            "target": target,
            "before_content": before,
            "before_title": raw(row, "title"),
            "before_modified_gmt": row.get("modified_gmt"),
            "fixed_content": fixed,
        })

    changed = []
    try:
        for item in prepared:
            target = item["target"]
            payload = {"content": item["fixed_content"]}
            if target.get("new_title"):
                payload["title"] = target["new_title"]

            req(f"{SITE}/wp-json/wp/v2/posts/{target['id']}", method="POST", payload=payload)
            after = get_post(target["id"])

            assert after.get("id") == target["id"]
            assert after.get("slug") == target["slug"]
            assert after.get("status") == "publish"
            assert int(after.get("featured_media") or 0) == target["featured_media"]
            expected_title = target.get("new_title") or target["old_title"]
            assert raw(after, "title") == expected_title

            actual = raw(after, "content")
            assert target["mark"] in actual
            assert len(re.findall(r"<!-- wp:image\b", actual)) == len(re.findall(r"<!-- wp:image\b", item["before_content"]))
            assert len(re.findall(r"\[blog_parts\s+id=", actual)) == len(re.findall(r"\[blog_parts\s+id=", item["before_content"]))
            assert not block_problems(actual)
            assert after.get("modified_gmt") != item["before_modified_gmt"]

            changed.append(item)
    except Exception:
        for item in reversed(changed):
            target = item["target"]
            try:
                req(
                    f"{SITE}/wp-json/wp/v2/posts/{target['id']}",
                    method="POST",
                    payload={"content": item["before_content"], "title": item["before_title"]},
                )
            except Exception:
                pass
        raise

    after_total = pub_count()
    assert after_total == before_total

    print("# GSC batch micro updates 2026-09-23")
    print("- result: **SUCCESS**")
    print(f"- public posts: **{before_total} → {after_total}**")
    print("- posts updated: **7**")
    print("- status / slug / featured_media: **unchanged**")
    print("- image counts / blog_parts counts: **unchanged**")
    print("- Gutenberg problems after: **0**")
    print("- modified date: **updated on all 7 posts**")
    print("- title changes: **2** (UX model-change / Agetate)")
    for item in changed:
        target = item["target"]
        print(f"- {target['slug']} (post {target['id']}): **publish → publish** / micro update applied")

if __name__ == "__main__":
    main()
