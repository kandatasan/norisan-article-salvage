#!/usr/bin/env python3
from __future__ import annotations

import base64
import html
import json
import os
import re
import urllib.request

SITE = "https://tsurikue.com"
UA = "tsurikue-audit-ux-ctn-funnels-20260907/1.0"
TARGETS = [
    (2517, "ux-koukai", 2208),
    (2222, "ux-resale", 2223),
]
CTN_BANNER = '[blog_parts id="2846"]'
CTN_BUTTON = '[blog_parts id="2184"]'

TOKEN = re.compile(r"<!--\s+/?wp:[\s\S]*?-->")
OPEN = re.compile(r"<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->")
CLOSE = re.compile(r"<!--\s+/wp:([\w\-/]+)\s+-->")
TAG = re.compile(r"<[^>]+>")


def auth_header() -> str:
    raw = f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()
    return "Basic " + base64.b64encode(raw).decode()


def get_json(url: str):
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "Authorization": auth_header(),
        "User-Agent": UA,
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def raw(row, key: str) -> str:
    v = row.get(key) or {}
    if isinstance(v, dict):
        return v.get("raw") or v.get("rendered") or ""
    return str(v)


def clean_text(s: str) -> str:
    s = re.sub(r"<br\s*/?>", " / ", s, flags=re.I)
    s = TAG.sub("", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def block_problems(text: str):
    stack = []
    probs = []
    for m in TOKEN.finditer(text):
        tok = m.group(0)
        om = OPEN.fullmatch(tok)
        cm = CLOSE.fullmatch(tok)
        if om:
            if om.group(2):
                continue
            stack.append(om.group(1))
        elif cm:
            name = cm.group(1)
            if not stack or stack[-1] != name:
                probs.append(("mismatch", stack[-1] if stack else None, name))
                break
            stack.pop()
    if stack:
        probs.append(("unclosed", stack.copy()))
    return probs


def timeline(content: str):
    items = []
    patterns = [
        ("H", re.compile(r"<h([2-6])\b[^>]*>(.*?)</h\1>", re.I | re.S)),
        ("P", re.compile(r"<p\b[^>]*>(.*?)</p>", re.I | re.S)),
        ("SHORT", re.compile(r"\[blog_parts\s+id=\"?(2846|2184)\"?\]", re.I)),
    ]
    for kind, pat in patterns:
        for m in pat.finditer(content):
            if kind == "H":
                text = clean_text(m.group(2))
                label = f"H{m.group(1)}"
            elif kind == "P":
                text = clean_text(m.group(1))
                label = "P"
            else:
                bid = m.group(1)
                text = "CTN_BANNER" if bid == "2846" else "CTN_BUTTON"
                label = "SHORT"
            if text:
                items.append((m.start(), label, text))
    items.sort(key=lambda x: x[0])
    return items


def windows(items):
    hits = []
    for i, (_, label, text) in enumerate(items):
        if "CTN" in text or "電話" in text or "上位3社" in text or label == "SHORT":
            hits.append(i)
    ranges = []
    for i in hits:
        a, b = max(0, i - 3), min(len(items), i + 4)
        if ranges and a <= ranges[-1][1]:
            ranges[-1] = (ranges[-1][0], max(ranges[-1][1], b))
        else:
            ranges.append((a, b))
    return ranges


def main():
    print("# Current UX CTN funnel audit (GET only)")
    print("- wordpress_write_count: **0**")
    for pid, expected_slug, expected_media in TARGETS:
        row = get_json(f"{SITE}/wp-json/wp/v2/posts/{pid}?context=edit")
        content = raw(row, "content")
        title = raw(row, "title")
        probs = block_problems(content)
        print()
        print(f"## {expected_slug}")
        print(f"- post_id: **{row.get('id')}**")
        print(f"- status: **{row.get('status')}**")
        print(f"- title: {title}")
        print(f"- featured_media: **{row.get('featured_media')}** (expected {expected_media})")
        print(f"- content_chars: **{len(content)}**")
        print(f"- CTN banner count: **{content.count(CTN_BANNER)}**")
        print(f"- CTN button count: **{content.count(CTN_BUTTON)}**")
        print(f"- CTN text occurrences: **{content.count('CTN')}**")
        print(f"- phone-note present: **{'電話が少なくて快適でした' in content or '電話が少なかったこと' in content}**")
        print(f"- Gutenberg problems: **{len(probs)}**")
        print("### CTN vicinity")
        items = timeline(content)
        rr = windows(items)
        if not rr:
            print("- no CTN vicinity found")
        for n, (a, b) in enumerate(rr, 1):
            print(f"\n#### Window {n}")
            for _, label, text in items[a:b]:
                print(f"- **{label}** {text}")


if __name__ == "__main__":
    main()
