#!/usr/bin/env python3
from __future__ import annotations

import base64
import html
import json
import os
import re
import urllib.parse
import urllib.request

SITE = "https://tsurikue.com"
UA = "tsurikue-trim-gourmet-repetition-20260924/1.0"

TARGETS = {
    "ask": {
        "id": 3463,
        "slug": "ask-the-meat",
        "title": "アスクザミートを実食レビュー｜広島で熟成肉コースを6人で食べた。過去最強クラスかも",
        "featured_media": 3291,
    },
    "yakiniku": {
        "id": 2662,
        "slug": "yakinikucenter",
        "title": "可部焼肉センターを実食レビュー｜東広島から通うほど好き！和牛カルビが旨い",
        "featured_media": 1293,
    },
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
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode()), dict(response.headers)

def raw(row, key):
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)

def get_post(pid):
    q = urllib.parse.urlencode({
        "context":"edit",
        "_fields":"id,slug,status,title,content,featured_media,date,date_gmt,modified_gmt,categories,tags",
    })
    row, _ = req(f"{SITE}/wp-json/wp/v2/posts/{pid}?{q}")
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

def replace_once(text, old, new, label):
    if text.count(old) != 1:
        raise RuntimeError(f"{label}: expected exactly 1 old block, got {text.count(old)}")
    return text.replace(old, new, 1)

def remove_once(text, old, label):
    return replace_once(text, old, "", label)

def verify_identity(row, target):
    if row.get("id") != target["id"]: raise RuntimeError("id mismatch")
    if row.get("slug") != target["slug"]: raise RuntimeError("slug mismatch")
    if row.get("status") != "publish": raise RuntimeError("status mismatch")
    if html.unescape(raw(row, "title")) != target["title"]: raise RuntimeError("title mismatch")
    if int(row.get("featured_media") or 0) != target["featured_media"]: raise RuntimeError("featured_media mismatch")

def edit_ask(content):
    if content.count("肉の名前は分からん") != 1:
        raise RuntimeError("ask name-unknown keeper missing or duplicated before edit")

    content = replace_once(
        content,
        '<figcaption class="wp-element-caption">部位の名前は分かりません。でも、見た瞬間に「これは旨いやつ」と分かる肉でした。</figcaption>',
        '<figcaption class="wp-element-caption">霜降りの見た目から、食べる前から期待が上がる肉でした。</figcaption>',
        "ask first caption",
    )
    content = replace_once(
        content,
        '<p>肉の部位はほとんど覚えていません。<br>でも、写真を見返すと「これ旨かったなあ」と味の記憶はしっかり残っています。</p>',
        '<p>写真を見返すと「これ旨かったなあ」と、味の記憶はしっかり残っています。</p>',
        "ask first body repeat",
    )
    content = replace_once(
        content,
        '<figcaption class="wp-element-caption">部位を説明できなくても、旨かった記憶はしっかり残っています。</figcaption>',
        '<figcaption class="wp-element-caption">赤身の旨さもしっかり印象に残っています。</figcaption>',
        "ask second caption",
    )
    content = replace_once(
        content,
        '<p>部位名まで詳しく説明できる記事ではありません。<br>それでも、<strong>「また食べたい」と思えるくらい旨かった</strong>ことは間違いありません。</p>',
        '<p><strong>「また食べたい」と思えるくらい旨かった</strong>ことは間違いありません。</p>',
        "ask closing repeat",
    )

    if content.count("肉の名前は分からん") != 1:
        raise RuntimeError("ask name-unknown idea should remain exactly once")
    if "部位" in content:
        raise RuntimeError("ask still contains duplicate 部位 wording")
    return content

def edit_yakiniku(content):
    content = replace_once(
        content,
        '<p>昔ながらの焼肉屋さんなのですが、旨い。<br>私はこの店のためだけに東広島から可部まで通っています。</p>',
        '<p>昔ながらの焼肉屋さんなのですが、旨い。</p>',
        "yakiniku intro distance repeat",
    )
    content = replace_once(
        content,
        '<h2 class="wp-block-heading">可部焼肉センターを実食レビュー｜わざわざ食べに行きたくなる店</h2>',
        '<h2 class="wp-block-heading">可部焼肉センターを実食レビュー｜赤い牛の看板が目印</h2>',
        "yakiniku distance heading",
    )
    content = remove_once(
        content,
        '<!-- wp:paragraph -->\n<p>私も東広島から可部まで距離はあります。<br>それでも焼肉センターを食べたくなると、ここまで行きます。</p>\n<!-- /wp:paragraph -->\n\n',
        "yakiniku distance paragraph 1",
    )
    content = remove_once(
        content,
        '<!-- wp:paragraph -->\n<p><strong>近いから行くんじゃなく、ここで食べたいから行く。</strong><br>私の中では、そんな店です。</p>\n<!-- /wp:paragraph -->\n\n',
        "yakiniku distance paragraph 2",
    )
    content = replace_once(
        content,
        '<p>焼肉センターは何を食べても美味しいのですが、私のイチオシは<strong>和牛カルビ</strong>。</p>',
        '<p>焼肉センターは何を食べても美味しいのですが、私が一番楽しみにしているのがこの一皿です。</p>',
        "yakiniku kalbi repeat 1",
    )
    content = replace_once(
        content,
        '<p>1人前でもしっかり量があって、白ごはんと一緒に食べると止まりません。</p>',
        '<p>1人前でもしっかり量があります。</p>',
        "yakiniku rice repeat 1",
    )
    content = replace_once(
        content,
        '<p>焼いて、タレにつけて、ごはん。</p>',
        '<p>焼いて、タレにつけて、白ごはん。<br><strong>ほんと、いくらでもご飯が食えるやつ。</strong></p>',
        "yakiniku kalbi-rice keeper",
    )
    content = remove_once(
        content,
        '<!-- wp:paragraph -->\n<p><strong>ほんと、いくらでもご飯が食えるやつ。</strong></p>\n<!-- /wp:paragraph -->\n\n',
        "yakiniku duplicate rice punchline",
    )
    content = replace_once(
        content,
        '<p>とはいえ、私が焼肉センターへ行く理由はやっぱり肉。<br>和牛カルビを焼いて、ごはんを食べる。これが好きです。</p>',
        '<p>とはいえ、私が焼肉センターへ行く理由はやっぱり肉です。</p>',
        "yakiniku kalbi-rice repeat 2",
    )
    content = replace_once(
        content,
        '<p>私は東広島から、焼肉センターのためだけに可部まで通っています。</p>',
        '<p>国道54号線を走ると、今でもあの赤い牛の看板が目に入ります。</p>',
        "yakiniku closing distance repeat",
    )
    content = replace_once(
        content,
        '<p>年季の入った外観。<br>旨い肉。<br>そして和牛カルビで白ごはん。</p>',
        '<p>年季の入った外観。<br>旨い肉。<br>昔ながらの焼肉屋さんらしい雰囲気。</p>',
        "yakiniku closing kalbi-rice repeat",
    )

    if content.count("東広島") != 1:
        raise RuntimeError(f"yakiniku 東広島 should appear once in body, got {content.count('東広島')}")
    if content.count("通いたくなる") != 1:
        raise RuntimeError("yakiniku distance idea keeper missing or duplicated")
    if "わざわざ食べに行きたくなる" in content or "ここで食べたいから行く" in content or "通っています" in content:
        raise RuntimeError("yakiniku distance duplicate wording remains")
    if content.count("和牛カルビ") != 1:
        raise RuntimeError(f"yakiniku 和牛カルビ should appear once in body, got {content.count('和牛カルビ')}")
    if content.count("白ごはん") != 1:
        raise RuntimeError(f"yakiniku 白ごはん should appear once in body, got {content.count('白ごはん')}")
    return content

def main():
    before_total = pub_count()
    prepared = []

    for key, target in TARGETS.items():
        row = get_post(target["id"])
        verify_identity(row, target)
        before = raw(row, "content")
        if block_problems(before):
            raise RuntimeError(f"broken Gutenberg before: {key}")
        fixed = edit_ask(before) if key == "ask" else edit_yakiniku(before)
        if fixed == before:
            raise RuntimeError(f"no changes produced: {key}")
        if len(re.findall(r"<!-- wp:image\b", fixed)) != len(re.findall(r"<!-- wp:image\b", before)):
            raise RuntimeError(f"image count changed locally: {key}")
        if len(re.findall(r"\[blog_parts\s+id=", fixed)) != len(re.findall(r"\[blog_parts\s+id=", before)):
            raise RuntimeError(f"blog_parts count changed locally: {key}")
        if block_problems(fixed):
            raise RuntimeError(f"broken Gutenberg after local edit: {key}")
        prepared.append({
            "key": key,
            "target": target,
            "before_row": row,
            "before_content": before,
            "fixed_content": fixed,
        })

    changed = []
    try:
        for item in prepared:
            target = item["target"]
            req(
                f"{SITE}/wp-json/wp/v2/posts/{target['id']}",
                method="POST",
                payload={"content": item["fixed_content"]},
            )
            changed.append(item)
            after = get_post(target["id"])
            verify_identity(after, target)

            if after.get("date") != item["before_row"].get("date") or after.get("date_gmt") != item["before_row"].get("date_gmt"):
                raise RuntimeError(f"publication date changed: {item['key']}")
            actual = raw(after, "content")
            if actual.strip() != item["fixed_content"].strip():
                raise RuntimeError(f"content mismatch after write: {item['key']}")
            if len(re.findall(r"<!-- wp:image\b", actual)) != len(re.findall(r"<!-- wp:image\b", item["before_content"])):
                raise RuntimeError(f"image count changed after write: {item['key']}")
            if len(re.findall(r"\[blog_parts\s+id=", actual)) != len(re.findall(r"\[blog_parts\s+id=", item["before_content"])):
                raise RuntimeError(f"blog_parts count changed after write: {item['key']}")
            if block_problems(actual):
                raise RuntimeError(f"Gutenberg broken after write: {item['key']}")
            if after.get("modified_gmt") == item["before_row"].get("modified_gmt"):
                raise RuntimeError(f"modified date did not advance: {item['key']}")

            if item["key"] == "ask":
                if actual.count("肉の名前は分からん") != 1 or "部位" in actual:
                    raise RuntimeError("ask duplicate idea verification failed")
            else:
                if actual.count("東広島") != 1 or actual.count("通いたくなる") != 1:
                    raise RuntimeError("yakiniku distance verification failed")
                if actual.count("和牛カルビ") != 1 or actual.count("白ごはん") != 1:
                    raise RuntimeError("yakiniku kalbi-rice verification failed")

    except Exception:
        for item in reversed(changed):
            try:
                target = item["target"]
                req(
                    f"{SITE}/wp-json/wp/v2/posts/{target['id']}",
                    method="POST",
                    payload={"content": item["before_content"]},
                )
            except Exception:
                pass
        raise

    after_total = pub_count()
    if after_total != before_total:
        raise RuntimeError(f"published post count changed: {before_total} -> {after_total}")

    print("# Gourmet repetition trim 2026-09-24")
    print("- result: **SUCCESS**")
    print(f"- public posts: **{before_total} → {after_total}**")
    print("- ask-the-meat: **肉名称わからん系 = 1回**")
    print("- yakinikucenter: **遠くても通う系 = 1回**")
    print("- yakinikucenter: **和牛カルビ＋白ごはん系 = 1回**")
    print("- titles / slugs / status / featured media: **unchanged**")
    print("- original publication dates: **unchanged**")
    print("- image counts / blog_parts counts: **unchanged**")
    print("- Gutenberg problems after: **0**")

if __name__ == "__main__":
    main()
