#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import re
import urllib.request

SITE = "https://tsurikue.com"
UA = "tsurikue-gsc-mini-round2-20260923/1.0"

TARGETS = [
    {
        "id": 3730,
        "slug": "okunoshima-rabbit-island",
        "old_title": "大久野島へ行ってきた！うさぎはどこにいる？紅葉・廃墟・釣りまで島を一周",
        "new_title": None,
        "featured_media": 3735,
        "kind": "okunoshima",
        "mark": "大久野島にうさぎはいない？フェリーを降りても見つからなかった",
    },
    {
        "id": 3463,
        "slug": "ask-the-meat",
        "old_title": "アスクザミートの熟成肉コースを6人で食べてきた｜肉の味が濃い。過去最強クラスかも",
        "new_title": "アスクザミートを実食レビュー｜広島で熟成肉コースを6人で食べた。過去最強クラスかも",
        "featured_media": 3291,
        "kind": "ask",
        "mark": "アスクザミートを実食レビュー｜肉の名前は分からん。でも、とにかく旨い",
    },
    {
        "id": 2662,
        "slug": "yakinikucenter",
        "old_title": "可部焼肉センターを実食｜東広島から通うほど好き！和牛カルビが旨い",
        "new_title": "可部焼肉センターを実食レビュー｜東広島から通うほど好き！和牛カルビが旨い",
        "featured_media": 1293,
        "kind": "yakiniku",
        "mark": "可部焼肉センターを実食レビュー｜わざわざ食べに行きたくなる店",
    },
    {
        "id": 2456,
        "slug": "kulabotaisyoukan",
        "old_title": "KULABO大正館に宿泊した口コミ｜素泊まりの部屋・無料駐車場・館内を紹介",
        "new_title": "KULABO大正館の宿泊レビュー｜素泊まりの部屋・無料駐車場・館内を紹介",
        "featured_media": 2461,
        "kind": "kulabo",
        "mark": "KULABO大正館の宿泊レビュー｜泊まった感想",
    },
]

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

def replace_h2(content, old, new):
    a, b = h2(old), h2(new)
    if content.count(a) != 1:
        raise RuntimeError(f"heading guard failed: {old}")
    return content.replace(a, b, 1)

def make_fixed(content, kind):
    if kind == "okunoshima":
        return replace_h2(
            content,
            "フェリーを降りても、うさぎがいない",
            "大久野島にうさぎはいない？フェリーを降りても見つからなかった",
        )
    if kind == "ask":
        return replace_h2(
            content,
            "肉の名前は分からん。でも、とにかく旨い",
            "アスクザミートを実食レビュー｜肉の名前は分からん。でも、とにかく旨い",
        )
    if kind == "yakiniku":
        return replace_h2(
            content,
            "可部焼肉センターは、わざわざ食べに行きたくなる店",
            "可部焼肉センターを実食レビュー｜わざわざ食べに行きたくなる店",
        )
    if kind == "kulabo":
        return replace_h2(
            content,
            "KULABO大正館に泊まった感想",
            "KULABO大正館の宿泊レビュー｜泊まった感想",
        )
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

    print("# GSC mini rewrite round 2 2026-09-23")
    print("- result: **SUCCESS**")
    print(f"- public posts: **{before_total} → {after_total}**")
    print("- posts updated: **4**")
    print("- status / slug / featured_media: **unchanged**")
    print("- image counts / blog_parts counts: **unchanged**")
    print("- Gutenberg problems after: **0**")
    print("- modified date: **updated on all 4 posts**")
    print("- title changes: **3** (ask-the-meat / yakinikucenter / kulabotaisyoukan)")
    for item in changed:
        target = item["target"]
        print(f"- {target['slug']} (post {target['id']}): **publish → publish** / mini rewrite applied")

if __name__ == "__main__":
    main()
