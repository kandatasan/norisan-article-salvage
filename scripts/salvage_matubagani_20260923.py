#!/usr/bin/env python3
from __future__ import annotations

import base64, json, os, re, urllib.request

SITE = "https://tsurikue.com"
UA = "tsurikue-salvage-matubagani-20260923/1.0"

TARGET = {
    "id": 2644,
    "slug": "matubagani",
    "old_title": "境港で松葉ガニを買って食べてみた｜美味しすぎて本当に泣いた実食記",
    "new_title": "境港で松葉ガニを買って食べた｜水産物直売センターで2杯購入、美味しすぎて泣いた",
    "featured_media": 2692,
}

TOKEN = re.compile(r"<!--\s+/?wp:[\s\S]*?-->")
OPEN = re.compile(r"<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->")
CLOSE = re.compile(r"<!--\s+/wp:([\w\-/]+)\s+-->")

def auth():
    raw = f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()
    return "Basic " + base64.b64encode(raw).decode()

def req(url, method="GET", payload=None):
    headers = {"Accept":"application/json","Authorization":auth(),"User-Agent":UA}
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode()
        headers["Content-Type"] = "application/json; charset=utf-8"
    rq = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(rq, timeout=60) as res:
        return json.loads(res.read().decode()), dict(res.headers)

def raw(row, key):
    v = row.get(key) or {}
    if isinstance(v, dict):
        return v.get("raw") or v.get("rendered") or ""
    return str(v)

def get_post(pid):
    row, _ = req(f"{SITE}/wp-json/wp/v2/posts/{pid}?context=edit")
    return row

def pub_count():
    _, h = req(f"{SITE}/wp-json/wp/v2/posts?status=publish&per_page=1&_fields=id")
    return int(h.get("X-WP-Total", 0))

def block_problems(text):
    stack = []
    for m in TOKEN.finditer(text):
        t = m.group(0)
        op = OPEN.fullmatch(t)
        cl = CLOSE.fullmatch(t)
        if op:
            if op.group(2):
                continue
            stack.append(op.group(1))
        elif cl:
            name = cl.group(1)
            if not stack or stack[-1] != name:
                return [("mismatch", stack[-1] if stack else None, name)]
            stack.pop()
    return [("unclosed", stack)] if stack else []

def h2(title):
    return f'<!-- wp:heading -->\n<h2 class="wp-block-heading">{title}</h2>\n<!-- /wp:heading -->'

NEW_PREFIX = """<!-- old-tsurikue-salvage:v1 slug=matubagani -->
<!-- tsurikue-editorial:matubagani:v2 -->

<!-- wp:paragraph -->
<p>ども。ノリの妻、<strong>とも</strong>です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>あの鳥取旅行、私の目的はかなりシンプルでした。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>「蟹を買うまでは帰れない!!」</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>ということで境港へ。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>ところが、この日の本命だったベニズワイガニが見つからない。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>色んな市場を見て回って、行ったり来たりして、気づけば同じところを3往復。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>もう完全に蟹を買う人です。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>そして最後に選んだのが、<strong>境港水産物直売センターの松葉ガニ。</strong><br>お店の方に身入りを見てもらって、生きた松葉ガニを2杯購入しました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>これがもう、本当に美味しかった。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>「美味しい！」で終わらず、なぜか涙まで出たくらいです。</p>
<!-- /wp:paragraph -->"""

NEW_INFO = """<!-- wp:heading -->
<h2 class="wp-block-heading">境港で松葉ガニを買った場所｜境港水産物直売センター</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>私が松葉ガニを買ったのは、<strong>境港水産物直売センター</strong>です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>住所は鳥取県境港市昭和町9-5。現在の公式案内では<strong>8:00〜16:00頃・火曜定休</strong>となっています。営業時間は変わる場合があるので、出発前に公式サイトを確認しておくと安心です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><a href="https://sanmaki-direct.jp/" target="_blank" rel="noreferrer noopener">境港水産物直売センター公式サイトを見る</a></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>私たちは何軒も見て回ったあと、最後はここでお店の方に身入りを見てもらって2杯を購入しました。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">松葉ガニのシーズンは11月〜3月｜漁期は11月6日〜3月20日</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>鳥取県では、ズワイガニのうち<strong>成長した雄を「松葉がに」</strong>と呼びます。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>鳥取県が案内する旬は<strong>11月〜3月</strong>。雄の松葉がにの漁期は<strong>11月6日〜3月20日</strong>です。境漁港は、鳥取港・網代漁港と並ぶ主な水揚港のひとつです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><a href="https://www.pref.tottori.lg.jp/178131.htm" target="_blank" rel="noreferrer noopener">鳥取県公式「松葉がに」を見る</a></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>この旅行では最初から松葉ガニ狙いだったわけではありません。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>でも結果的には、こっちを買って大正解でした。</p>
<!-- /wp:paragraph -->"""

def make_fixed(content):
    old_anchor = h2("境港で蟹探し｜市場を3往復してようやく決めた")
    if content.count(old_anchor) != 1:
        raise RuntimeError("anchor heading not found exactly once")
    pos = content.index(old_anchor)
    fixed = NEW_PREFIX + "\n\n" + NEW_INFO + "\n\n" + content[pos:]
    fixed = fixed.replace(
        "色んな市場を回りましたが、当時は本命のベニズワイガニがなかなか見つかりませんでした。",
        "色んな市場を回りましたが、この日は本命のベニズワイガニがなかなか見つかりませんでした。",
        1
    )
    fixed = fixed.replace(
        "そんなことを繰り返して、結局3往復しました🤣",
        "そんなことを繰り返して、結局3往復しました。",
        1
    )
    fixed = fixed.replace(
        "そのくらい美味しかったです🤣",
        "そのくらい美味しかったです。",
        1
    )
    fixed = fixed.replace(
        '<!-- wp:paragraph -->\n<p></p>\n<!-- /wp:paragraph -->',
        "",
        1
    )
    return fixed.strip() + "\n"

def verify_identity(row):
    assert row.get("id") == TARGET["id"]
    assert row.get("slug") == TARGET["slug"]
    assert row.get("status") == "publish"
    assert raw(row, "title") == TARGET["old_title"]
    assert int(row.get("featured_media") or 0) == TARGET["featured_media"]

def main():
    before_total = pub_count()
    row = get_post(TARGET["id"])
    verify_identity(row)
    before = raw(row, "content")

    assert "tsurikue-editorial:matubagani:v2" not in before
    assert "11月26日〜3月20日" in before
    assert not block_problems(before)

    fixed = make_fixed(before)

    assert "tsurikue-editorial:matubagani:v2" in fixed
    assert "11月26日〜3月20日" not in fixed
    assert "11月6日〜3月20日" in fixed
    assert "境港水産物直売センター" in fixed
    assert "美味しーーい!!" in fixed
    assert "ここで世界が滅亡してもいい" in fixed
    assert "🤣" not in fixed
    assert len(re.findall(r"<!-- wp:image\b", fixed)) == len(re.findall(r"<!-- wp:image\b", before))
    assert len(re.findall(r"\[blog_parts\s+id=", fixed)) == len(re.findall(r"\[blog_parts\s+id=", before))
    assert not block_problems(fixed)

    before_modified = row.get("modified_gmt")
    req(
        f"{SITE}/wp-json/wp/v2/posts/{TARGET['id']}",
        method="POST",
        payload={"title": TARGET["new_title"], "content": fixed},
    )
    after = get_post(TARGET["id"])

    assert after.get("id") == TARGET["id"]
    assert after.get("slug") == TARGET["slug"]
    assert after.get("status") == "publish"
    assert int(after.get("featured_media") or 0) == TARGET["featured_media"]
    assert raw(after, "title") == TARGET["new_title"]
    actual = raw(after, "content")
    assert "tsurikue-editorial:matubagani:v2" in actual
    assert "11月26日〜3月20日" not in actual
    assert "11月6日〜3月20日" in actual
    assert "🤣" not in actual
    assert len(re.findall(r"<!-- wp:image\b", actual)) == len(re.findall(r"<!-- wp:image\b", before))
    assert len(re.findall(r"\[blog_parts\s+id=", actual)) == len(re.findall(r"\[blog_parts\s+id=", before))
    assert not block_problems(actual)
    assert after.get("modified_gmt") != before_modified

    after_total = pub_count()
    assert after_total == before_total

    print("# Matsubagani full salvage 2026-09-23")
    print("- result: **SUCCESS**")
    print(f"- public posts: **{before_total} → {after_total}**")
    print("- post: **2644 / matubagani / publish → publish**")
    print("- title: **updated**")
    print("- slug / featured_media: **unchanged**")
    print("- incorrect season note: **11/26 → 11/6 corrected**")
    print("- current purchase-place block: **added**")
    print("- firsthand story: **preserved**")
    print("- article-body emoji: **removed**")
    print("- image counts / blog_parts counts: **unchanged**")
    print("- Gutenberg problems after: **0**")
    print("- modified date: **updated**")

if __name__ == "__main__":
    main()
