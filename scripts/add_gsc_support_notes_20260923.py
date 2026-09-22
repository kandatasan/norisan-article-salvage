#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import re
import urllib.request

SITE = "https://tsurikue.com"
UA = "tsurikue-gsc-support-notes-20260923/1.0"
AUDIT_LABEL = "gsc-support-notes-20260923"

TARGETS = [
    {
        "id": 2575,
        "slug": "ccwatergold",
        "title": "CCウォーターゴールドの評価は？プレミアを使って感じた効果・防汚・ムラの注意点",
        "featured_media": 2581,
        "anchor": "乾いたボディへ施工する場合は、一度に広い範囲へ塗らず、狭い範囲ごとに塗布と拭き取りを進めた方が安全です。",
        "mark": "50cm四方につき1回",
        "note": """<!-- wp:paragraph -->
<p>ちなみに、<a href="https://prostaff-jp.com/products/s235/" target="_blank" rel="noreferrer noopener">メーカー公式の取扱説明</a>でも、乾いたボディへの施工は可能です。<br>ただし、<strong>液が乾く前にクロスで拭き上げる</strong>こと、スプレーは<strong>50cm四方につき1回</strong>が目安。艶成分が濃いため、濃淡ムラが目立つことがあるとも案内されています。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>つまり、乾いたボディへの施工そのものがダメなわけではありません。<br>私の場合は、液剤が乾く前の拭き上げで失敗した可能性が高そうです。ラクに使うなら、私は今でも濡れたボディへ施工する方が好みです。</p>
<!-- /wp:paragraph -->""",
    },
    {
        "id": 2408,
        "slug": "muvalley",
        "title": "美川ムーバレーは怖い？大人だけで行った本音口コミ｜所要時間・服装・料金",
        "featured_media": 2409,
        "anchor": '<h2 class="wp-block-heading">美川ムーバレーの所要時間</h2>',
        "mark": "所要時間は<strong>60分</strong>",
        "mode": "after_heading",
        "note": """<!-- wp:paragraph -->
<p>2026年現在、公式サイトに掲載されている謎解きアトラクション<a href="https://muvalley.com/attraction/20260312-3/" target="_blank" rel="noreferrer noopener">「世界を救うパンドラの箱」</a>の所要時間は<strong>60分</strong>。地底王国は全長約1kmです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>ただし、この60分は謎解きアトラクションの目安。砂金探しや宝石探し、食事まで含めた滞在時間ではありません。<br>私たちが2023年に遊んだときは、洞窟探検だけで約2時間かかりました。</p>
<!-- /wp:paragraph -->""",
    },
    {
        "id": 2623,
        "slug": "chibou",
        "title": "チー坊の飲み方5選｜広島のソウルドリンク？水・炭酸・お酒で割ってみた",
        "featured_media": 261,
        "anchor": "<p><strong>飲みやすいので、飲みすぎ注意。</strong></p>",
        "mark": "チー坊サワーってどんなお酒？",
        "note": """<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">チー坊サワーってどんなお酒？</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>広島では、チー坊を使ったアルコールドリンクが<strong>「チー坊サワー」</strong>として実際に提供されています。<br>チー坊の正規販売代理店が出店した2026年のイベントでも、<a href="https://ktcc.jp/news/chiboh-hanabi-makuhari-2026/" target="_blank" rel="noreferrer noopener">チー坊サワー・チー坊レモンサワー・チー坊ハイボール</a>がメニューに並んでいました。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>ただ、お店ごとの配合までは公開されていません。<br>この記事で私が実際に作って飲んでいたのは、上で紹介した<strong>ウイスキー＋炭酸のチー坊ハイボール</strong>です。</p>
<!-- /wp:paragraph -->""",
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
    problems = []
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
                problems.append(("mismatch", stack[-1] if stack else None, name))
                return problems
            stack.pop()
    if stack:
        problems.append(("unclosed", stack))
    return problems

def insert_after_paragraph(content, anchor, note):
    if content.count(anchor) != 1:
        raise RuntimeError(f"anchor count != 1: {anchor}")
    pos = content.index(anchor)
    start = content.rfind("<!-- wp:paragraph -->", 0, pos)
    end = content.find("<!-- /wp:paragraph -->", pos)
    if start < 0 or end < 0:
        raise RuntimeError("paragraph block not found")
    end += len("<!-- /wp:paragraph -->")
    return content[:end] + "\n\n" + note + content[end:]

def insert_after_heading(content, heading_html, note):
    if content.count(heading_html) != 1:
        raise RuntimeError(f"heading count != 1: {heading_html}")
    pos = content.index(heading_html)
    end = content.find("<!-- /wp:heading -->", pos)
    if end < 0:
        raise RuntimeError("heading block close not found")
    end += len("<!-- /wp:heading -->")
    return content[:end] + "\n\n" + note + content[end:]

def verify_identity(row, target):
    assert row.get("id") == target["id"]
    assert row.get("slug") == target["slug"]
    assert row.get("status") == "publish"
    assert raw(row, "title") == target["title"]
    assert row.get("featured_media") == target["featured_media"]

def make_fixed(content, target):
    if target.get("mode") == "after_heading":
        return insert_after_heading(content, target["anchor"], target["note"])
    return insert_after_paragraph(content, target["anchor"], target["note"])

def main():
    before_total = pub_count()
    prepared = []

    for target in TARGETS:
        row = get_post(target["id"])
        verify_identity(row, target)
        content = raw(row, "content")
        assert target["mark"] not in content, f"note already present: {target['slug']}"
        assert not block_problems(content), f"broken Gutenberg before update: {target['slug']}"
        fixed = make_fixed(content, target)
        assert target["mark"] in fixed
        assert len(re.findall(r"<!-- wp:image\b", fixed)) == len(re.findall(r"<!-- wp:image\b", content))
        assert len(re.findall(r"\[blog_parts\s+id=", fixed)) == len(re.findall(r"\[blog_parts\s+id=", content))
        assert not block_problems(fixed), f"broken Gutenberg after local edit: {target['slug']}"
        prepared.append((target, content, fixed))

    changed = []
    try:
        for target, before, fixed in prepared:
            req(f"{SITE}/wp-json/wp/v2/posts/{target['id']}", method="POST", payload={"content": fixed})
            after = get_post(target["id"])
            verify_identity(after, target)
            actual = raw(after, "content")
            assert target["mark"] in actual
            assert target["anchor"] in actual
            assert len(re.findall(r"<!-- wp:image\b", actual)) == len(re.findall(r"<!-- wp:image\b", before))
            assert len(re.findall(r"\[blog_parts\s+id=", actual)) == len(re.findall(r"\[blog_parts\s+id=", before))
            assert not block_problems(actual)
            changed.append((target, before))
    except Exception:
        for target, before in reversed(changed):
            try:
                req(f"{SITE}/wp-json/wp/v2/posts/{target['id']}", method="POST", payload={"content": before})
            except Exception:
                pass
        raise

    after_total = pub_count()
    assert after_total == before_total

    print(f"# {AUDIT_LABEL}")
    print("- result: **SUCCESS**")
    print(f"- public posts: **{before_total} → {after_total}**")
    print("- WordPress payload: **content only**")
    print("- title / slug / status / featured_media: **unchanged**")
    print("- image counts / blog_parts counts: **unchanged**")
    print("- Gutenberg problems after: **0**")
    for target, _ in changed:
        print(f"- {target['slug']} (post {target['id']}): **publish → publish** / support note added")

if __name__ == "__main__":
    main()
