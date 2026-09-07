#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import urllib.request

SITE = "https://tsurikue.com"
POST_ID = 2948
SLUG = "lexus-ux-used"
TITLE = "レクサスUXの中古は狙い目？新車と比べて中古をおすすめしたい理由"
FEATURED_MEDIA = 1001
EXPECTED_SHA = "265c4eed099996d6f7936a0db646f7af5293bb18c4e4eeb556abeb42cf4d5876"
UA = "tsurikue-optimize-lexus-ux-used-funnel-20260907/1.0"

GULLIVER_BANNER = '[blog_parts id="2843"]'
CTN_BANNER = '[blog_parts id="2846"]'
CTN_BUTTON = '[blog_parts id="2184"]'
MARKER = "<!-- tsurikue-ctn-used-funnel:20260907 -->"

INSERT = '''<!-- tsurikue-ctn-used-funnel:20260907 -->
<!-- wp:paragraph -->
<p>中古UXを少しでも安く探すのは、もちろん効果があります。<br>でも乗り換え全体で見ると、<strong>今の車を高く売る方が金額が大きく動くこともあります。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>実際に私がUXを売るときはCTNを使いました。<br>最大15社で査定し、やり取りするのは高額査定の上位3社だけ。<br><strong>私のときは2社から連絡が来て、電話が少なくて快適でした。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>まずは「今の車、いくらになる？」から。</strong></p>
<!-- /wp:paragraph -->'''

TOKEN = re.compile(r"<!--\s+/?wp:[\s\S]*?-->")
OPEN = re.compile(r"<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->")
CLOSE = re.compile(r"<!--\s+/wp:([\w\-/]+)\s+-->")


def auth_header() -> str:
    raw = f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()
    return "Basic " + base64.b64encode(raw).decode()


def req(url: str, method: str = "GET", payload=None):
    headers = {"Authorization": auth_header(), "Accept": "application/json", "User-Agent": UA}
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8")), dict(response.headers)


def raw_field(row, key: str) -> str:
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)


def get_post():
    row, _ = req(f"{SITE}/wp-json/wp/v2/posts/{POST_ID}?context=edit")
    return row


def published_count() -> int:
    _, headers = req(f"{SITE}/wp-json/wp/v2/posts?status=publish&per_page=1&_fields=id")
    return int(headers.get("X-WP-Total", 0))


def verify_identity(row):
    assert row.get("id") == POST_ID
    assert row.get("slug") == SLUG
    assert row.get("status") == "publish"
    assert raw_field(row, "title") == TITLE
    assert row.get("featured_media") == FEATURED_MEDIA


def block_problems(text: str):
    stack = []
    problems = []
    for match in TOKEN.finditer(text):
        token = match.group(0)
        om = OPEN.fullmatch(token)
        cm = CLOSE.fullmatch(token)
        if om:
            if om.group(2):
                continue
            stack.append(om.group(1))
        elif cm:
            name = cm.group(1)
            if not stack or stack[-1] != name:
                problems.append(("mismatch", stack[-1] if stack else None, name))
                return problems
            stack.pop()
    if stack:
        problems.append(("unclosed", tuple(stack)))
    return problems


def insert_before_ctn_button(content: str) -> str:
    assert content.count(CTN_BUTTON) == 1
    pos = content.index(CTN_BUTTON)
    start = content.rfind("<!-- wp:shortcode -->", 0, pos)
    end = content.find("<!-- /wp:shortcode -->", pos)
    assert start >= 0 and end >= 0
    return content[:start] + INSERT + "\n\n" + content[start:]


def main():
    public_before = published_count()
    row = get_post()
    verify_identity(row)
    content = raw_field(row, "content")

    assert hashlib.sha256(content.encode("utf-8")).hexdigest() == EXPECTED_SHA
    assert MARKER not in content
    assert not block_problems(content)
    assert content.count(GULLIVER_BANNER) == 1
    assert content.count(CTN_BANNER) == 0
    assert content.count(CTN_BUTTON) == 1
    assert content.count("CTN") == 0
    assert "ディーラー下取りが50万円、買取サービスでは75万円でした" in content

    fixed = insert_before_ctn_button(content)
    assert fixed.count(GULLIVER_BANNER) == 1
    assert fixed.count(CTN_BANNER) == 0
    assert fixed.count(CTN_BUTTON) == 1
    assert fixed.count(MARKER) == 1
    assert "お試しOK" not in fixed and "お試しＯＫ" not in fixed
    assert not block_problems(fixed)

    req(f"{SITE}/wp-json/wp/v2/posts/{POST_ID}", method="POST", payload={"content": fixed})

    after = get_post()
    verify_identity(after)
    after_content = raw_field(after, "content")
    assert after_content == fixed
    assert not block_problems(after_content)
    public_after = published_count()
    assert public_after == public_before

    print("# lexus-ux-used funnel optimization")
    print("- result: **SUCCESS**")
    print(f"- public posts: **{public_before} → {public_after}**")
    print("- WordPress payload: **content only**")
    print("- status: **publish → publish**")
    print("- featured_media: **1001 → 1001**")
    print("- Gulliver banner: **1 → 1**")
    print("- CTN banner: **0 → 0**")
    print("- CTN button: **1 → 1**")
    print("- Gutenberg problems after: **0**")
    print("- added: **安く買う + 高く売る** comparison / CTN top-3 explanation / firsthand 2-call note / curiosity microcopy")


if __name__ == "__main__":
    main()
