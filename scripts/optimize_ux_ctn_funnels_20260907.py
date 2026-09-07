#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import re
import urllib.request

SITE = "https://tsurikue.com"
UA = "tsurikue-optimize-ux-ctn-funnels-20260907/1.0"
CTN_BANNER = '[blog_parts id="2846"]'
CTN_BUTTON = '[blog_parts id="2184"]'
BANNER_BLOCK_RE = re.compile(r'\n?<!-- wp:shortcode -->\s*\n\[blog_parts id="2846"\]\s*\n<!-- /wp:shortcode -->\n?')
TOKEN = re.compile(r"<!--\s+/?wp:[\s\S]*?-->")
OPEN = re.compile(r"<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->")
CLOSE = re.compile(r"<!--\s+/wp:([\w\-/]+)\s+-->")

TARGETS = {
    2517: {
        "slug": "ux-koukai",
        "title": "レクサスUXはひどい？616万円で買って後悔した欠点と満足している理由",
        "featured_media": 2208,
    },
    2222: {
        "slug": "ux-resale",
        "title": "レクサスUXのリセールは？616万円で購入し427万円で売却した記録",
        "featured_media": 2223,
    },
}

KOUKAI_TIMELINE_REPLACEMENTS = [
    (
        "さらに、納車から約5か月、走行距離約5,000kmの時点でディーラー査定を受けたところ、提示額は350万円でした。",
        "さらに、納車から約3か月ごろ、走行距離約5,000kmの時点でディーラー査定を受けたところ、提示額は350万円でした。",
    ),
    (
        "査定時点：納車約5か月後・走行距離約5,000km",
        "査定時点：納車約3か月ごろ・走行距離約5,000km",
    ),
    (
        "納車から約5か月、走行距離約5,000kmでディーラー査定を受けたところ、提示額は350万円。",
        "納車から約3か月ごろ、走行距離約5,000kmでディーラー査定を受けたところ、提示額は350万円。",
    ),
    (
        "まだ半年も乗ってないのに？",
        "まだ3か月くらいなのに？",
    ),
]

KOUKAI_CTN_OLD = (
    '<p>そこで候補になるのがCTNです。<br>最大15社で査定し、連絡が来るのは高額査定の上位3社だけ。<br>'
    '「高く売りたい。でも電話ラッシュはいらない」という人に合いやすい仕組みです。</p>'
)
KOUKAI_CTN_NEW = (
    '<p>そこで候補になるのがCTNです。<br>最大15社で査定し、連絡が来るのは高額査定の上位3社だけ。<br>'
    '<strong>私が使ったときに連絡が来たのは2社だけで、電話が少なくて快適でした。</strong></p>'
)

RESALE_PHONE_OLD = (
    '<p>CTNは最大15社で査定し、やり取りするのは高額査定の上位3社。<br>'
    '私が利用したときに連絡が来たのは、カーセブンとネクステージの2社でした。</p>'
)
RESALE_PHONE_NEW = (
    '<p>CTNは最大15社で査定し、やり取りするのは高額査定の上位3社。<br>'
    '私が利用したときに連絡が来たのは、カーセブンとネクステージの2社でした。<br>'
    '<strong>電話が少なくて、私はかなり快適でした。</strong></p>'
)
RESALE_EARLY_ANCHOR = (
    "最初の好奇心査定で「査定先によって、ここまで金額が違うのか」と知っていたので、実際の売却でも1社だけでは決めませんでした。"
)


def auth_header() -> str:
    raw = f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()
    return "Basic " + base64.b64encode(raw).decode()


def req(url: str, method: str = "GET", payload=None):
    headers = {"Accept": "application/json", "Authorization": auth_header(), "User-Agent": UA}
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


def get_post(pid: int):
    row, _ = req(f"{SITE}/wp-json/wp/v2/posts/{pid}?context=edit")
    return row


def published_count() -> int:
    _, headers = req(f"{SITE}/wp-json/wp/v2/posts?status=publish&per_page=1&_fields=id")
    return int(headers.get("X-WP-Total", 0))


def verify_identity(row, pid: int):
    exp = TARGETS[pid]
    assert row.get("id") == pid
    assert row.get("slug") == exp["slug"]
    assert row.get("status") == "publish"
    assert raw_field(row, "title") == exp["title"]
    assert row.get("featured_media") == exp["featured_media"]


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


def replace_exact_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    assert count == 1, f"{label}: expected 1 occurrence, found {count}"
    return text.replace(old, new, 1)


def remove_first_banner_after(text: str, anchor: str) -> str:
    anchor_pos = text.find(anchor)
    assert anchor_pos >= 0, "resale early anchor not found"
    match = BANNER_BLOCK_RE.search(text, anchor_pos)
    assert match is not None, "first CTN banner after early anchor not found"
    return text[:match.start()] + "\n" + text[match.end():]


def prepare_koukai(content: str) -> str:
    assert content.count(CTN_BANNER) == 1
    assert content.count(CTN_BUTTON) == 2
    assert "電話が少なくて快適でした" not in content
    fixed = content
    for idx, (old, new) in enumerate(KOUKAI_TIMELINE_REPLACEMENTS, 1):
        fixed = replace_exact_once(fixed, old, new, f"koukai timeline {idx}")
    fixed = replace_exact_once(fixed, KOUKAI_CTN_OLD, KOUKAI_CTN_NEW, "koukai CTN paragraph")
    assert "約5か月" not in fixed
    assert "約3か月ごろ" in fixed
    assert "電話が少なくて快適でした" in fixed
    assert fixed.count(CTN_BANNER) == 1
    assert fixed.count(CTN_BUTTON) == 2
    return fixed


def prepare_resale(content: str) -> str:
    assert content.count(CTN_BANNER) == 3
    assert content.count(CTN_BUTTON) == 1
    assert "電話が少なくて、私はかなり快適でした" not in content
    fixed = replace_exact_once(content, RESALE_PHONE_OLD, RESALE_PHONE_NEW, "resale phone paragraph")
    fixed = remove_first_banner_after(fixed, RESALE_EARLY_ANCHOR)
    assert fixed.count(CTN_BANNER) == 2
    assert fixed.count(CTN_BUTTON) == 1
    assert "電話が少なくて、私はかなり快適でした" in fixed
    return fixed


def main():
    public_before = published_count()
    prepared = {}
    before_meta = {}

    # Preflight both posts before any write.
    for pid in (2517, 2222):
        row = get_post(pid)
        verify_identity(row, pid)
        content = raw_field(row, "content")
        assert not block_problems(content), f"Gutenberg already broken before update: {pid}"
        before_meta[pid] = {
            "banner": content.count(CTN_BANNER),
            "button": content.count(CTN_BUTTON),
            "images": len(re.findall(r"<!-- wp:image\\b", content)),
        }
        fixed = prepare_koukai(content) if pid == 2517 else prepare_resale(content)
        assert not block_problems(fixed), f"local edit breaks Gutenberg: {pid}"
        assert len(re.findall(r"<!-- wp:image\\b", fixed)) == before_meta[pid]["images"]
        prepared[pid] = fixed

    results = []
    for pid in (2517, 2222):
        req(f"{SITE}/wp-json/wp/v2/posts/{pid}", method="POST", payload={"content": prepared[pid]})
        row = get_post(pid)
        verify_identity(row, pid)
        content = raw_field(row, "content")
        assert content == prepared[pid], f"WordPress content mismatch after update: {pid}"
        assert not block_problems(content), f"Gutenberg broken after update: {pid}"
        results.append(
            {
                "pid": pid,
                "slug": TARGETS[pid]["slug"],
                "banner": content.count(CTN_BANNER),
                "button": content.count(CTN_BUTTON),
            }
        )

    public_after = published_count()
    assert public_after == public_before

    print("# UX CTN funnel optimization")
    print("- result: **SUCCESS**")
    print(f"- public posts: **{public_before} → {public_after}**")
    print("- WordPress payload: **content only**")
    print("- Gutenberg problems after: **0**")
    print("- ux-koukai: appraisal timing unified to **約3か月ごろ**")
    print("- ux-koukai: firsthand phone note: **2社 / 電話が少なくて快適**")
    print("- ux-resale: firsthand phone note: **2社 / 電話が少なくてかなり快適**")
    print("- ux-resale: CTN banners: **3 → 2**")
    for r in results:
        print(f"- {r['slug']}: status **publish** / CTN banners **{r['banner']}** / CTN buttons **{r['button']}**")


if __name__ == "__main__":
    main()
