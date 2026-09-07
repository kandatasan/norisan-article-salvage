#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import re
import urllib.request

SITE = "https://tsurikue.com"
POST_ID = 2948
SLUG = "lexus-ux-used"
TITLE = "レクサスUXの中古は狙い目？新車と比べて中古をおすすめしたい理由"
UA = "tsurikue-audit-lexus-ux-used-funnel-20260907/1.0"

CTN_BANNER = '[blog_parts id="2846"]'
CTN_BUTTON = '[blog_parts id="2184"]'
GULLIVER_BANNER = '[blog_parts id="2843"]'
GULLIVER_A8 = 'a8mat=4B65SD+8DUSHE+9QU+NVHCY'

TOKEN = re.compile(r"<!--\s+/?wp:[\s\S]*?-->")
OPEN = re.compile(r"<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->")
CLOSE = re.compile(r"<!--\s+/wp:([\w\-/]+)\s+-->")
BLOCK = re.compile(r"<!--\s+wp:(paragraph|heading|shortcode)(?:\s+\{.*?\})?\s*-->([\s\S]*?)<!--\s+/wp:\1\s+-->")
TAG = re.compile(r"<[^>]+>")


def auth_header() -> str:
    raw = f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()
    return "Basic " + base64.b64encode(raw).decode()


def get_post():
    req = urllib.request.Request(
        f"{SITE}/wp-json/wp/v2/posts/{POST_ID}?context=edit",
        headers={"Authorization": auth_header(), "Accept": "application/json", "User-Agent": UA},
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def raw_field(row, key: str) -> str:
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)


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


def clean_text(s: str) -> str:
    s = s.replace("<br>", " / ").replace("<br/>", " / ").replace("<br />", " / ")
    s = TAG.sub("", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def blocks(content: str):
    out = []
    for m in BLOCK.finditer(content):
        kind = m.group(1)
        body = m.group(2).strip()
        if kind == "shortcode":
            text = body
            label = "SHORT"
        else:
            text = clean_text(body)
            label = "H" if kind == "heading" else "P"
        if text:
            out.append((label, text))
    return out


def main():
    row = get_post()
    assert row.get("id") == POST_ID
    assert row.get("slug") == SLUG
    assert row.get("status") == "publish"
    assert raw_field(row, "title") == TITLE

    content = raw_field(row, "content")
    parsed = blocks(content)
    problems = block_problems(content)
    sha = hashlib.sha256(content.encode("utf-8")).hexdigest()

    print("# lexus-ux-used funnel audit (GET only)")
    print("- wordpress_write_count: **0**")
    print(f"- post_id: **{POST_ID}**")
    print(f"- status: **{row.get('status')}**")
    print(f"- title: {raw_field(row, 'title')}")
    print(f"- featured_media: **{row.get('featured_media')}**")
    print(f"- content_sha256: `{sha}`")
    print(f"- content_chars: **{len(content)}**")
    print(f"- Gutenberg problems: **{len(problems)}**")
    print(f"- image blocks: **{len(re.findall(r'<!--\\s+wp:image\\b', content))}**")
    print(f"- Gulliver banner 2843: **{content.count(GULLIVER_BANNER)}**")
    print(f"- Gulliver A8 free-text link: **{content.count(GULLIVER_A8)}**")
    print(f"- CTN banner 2846: **{content.count(CTN_BANNER)}**")
    print(f"- CTN button 2184: **{content.count(CTN_BUTTON)}**")
    print(f"- CTN text occurrences: **{content.count('CTN')}**")
    print()

    needles = ("CTN", "2846", "2184", "2843", "ガリバー", "下取り", "買取", "高く売", "25万円")
    hit_indexes = [i for i, (_, text) in enumerate(parsed) if any(n in text for n in needles)]
    print("## CTA / trade-in vicinity")
    if not hit_indexes:
        print("- no matching blocks")
    else:
        shown = set()
        for hit in hit_indexes:
            start = max(0, hit - 3)
            end = min(len(parsed), hit + 4)
            for i in range(start, end):
                if i in shown:
                    continue
                shown.add(i)
                label, text = parsed[i]
                print(f"- **{label}** {text}")
            print("-")

    print("## Last 32 readable blocks")
    for label, text in parsed[-32:]:
        print(f"- **{label}** {text}")


if __name__ == "__main__":
    main()
