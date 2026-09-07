#!/usr/bin/env python3
from __future__ import annotations

import base64, json, os, re, urllib.request

SITE = "https://tsurikue.com"
UA = "tsurikue-optimize-ux-ctn-funnels-20260907/1.1"
CTN_BANNER = '[blog_parts id="2846"]'
CTN_BUTTON = '[blog_parts id="2184"]'
BANNER_BLOCK_RE = re.compile(r'\n?<!-- wp:shortcode -->\s*\n\[blog_parts id="2846"\]\s*\n<!-- /wp:shortcode -->\n?')
TOKEN = re.compile(r"<!--\s+/?wp:[\s\S]*?-->")
OPEN = re.compile(r"<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->")
CLOSE = re.compile(r"<!--\s+/wp:([\w\-/]+)\s+-->")

TARGETS = {
    2517: ("ux-koukai", "レクサスUXはひどい？616万円で買って後悔した欠点と満足している理由", 2208),
    2222: ("ux-resale", "レクサスUXのリセールは？616万円で購入し427万円で売却した記録", 2223),
}

KOUKAI_REPL = [
    ("さらに、納車から約5か月、走行距離約5,000kmの時点でディーラー査定を受けたところ、提示額は350万円でした。",
     "さらに、納車から約3か月ごろ、走行距離約5,000kmの時点でディーラー査定を受けたところ、提示額は350万円でした。"),
    ("査定時点：納車約5か月後・走行距離約5,000km",
     "査定時点：納車約3か月ごろ・走行距離約5,000km"),
    ("納車から約5か月、走行距離約5,000kmでディーラー査定を受けたところ、提示額は350万円。",
     "納車から約3か月ごろ、走行距離約5,000kmでディーラー査定を受けたところ、提示額は350万円。"),
    ("まだ半年も乗ってないのに？", "まだ3か月くらいなのに？"),
]

KOUKAI_CTN_OLD = '<p>そこで候補になるのがCTNです。<br>最大15社で査定し、連絡が来るのは高額査定の上位3社だけ。<br>「高く売りたい。でも電話ラッシュはいらない」という人に合いやすい仕組みです。</p>'
KOUKAI_CTN_NEW = '<p>そこで候補になるのがCTNです。<br>最大15社で査定し、連絡が来るのは高額査定の上位3社だけ。<br><strong>私が使ったときに連絡が来たのは2社だけで、電話が少なくて快適でした。</strong></p>'

RESALE_PHONE_OLD = '<p>CTNは最大15社で査定し、やり取りするのは高額査定の上位3社。<br>私が利用したときに連絡が来たのは、カーセブンとネクステージの2社でした。</p>'
RESALE_PHONE_NEW = '<p>CTNは最大15社で査定し、やり取りするのは高額査定の上位3社。<br>私が利用したときに連絡が来たのは、カーセブンとネクステージの2社でした。<br><strong>電話が少なくて、私はかなり快適でした。</strong></p>'
RESALE_EARLY_ANCHOR = "最初の好奇心査定で「査定先によって、ここまで金額が違うのか」と知っていたので、実際の売却でも1社だけでは決めませんでした。"


def auth():
    raw = f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()
    return "Basic " + base64.b64encode(raw).decode()


def req(url, method="GET", payload=None):
    headers = {"Accept": "application/json", "Authorization": auth(), "User-Agent": UA}
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(r, timeout=60) as x:
        return json.loads(x.read().decode("utf-8")), dict(x.headers)


def raw(row, key):
    v = row.get(key) or {}
    return (v.get("raw") or v.get("rendered") or "") if isinstance(v, dict) else str(v)


def get_post(pid):
    row, _ = req(f"{SITE}/wp-json/wp/v2/posts/{pid}?context=edit")
    return row


def public_count():
    _, h = req(f"{SITE}/wp-json/wp/v2/posts?status=publish&per_page=1&_fields=id")
    return int(h.get("X-WP-Total", 0))


def verify(row, pid):
    slug, title, media = TARGETS[pid]
    assert row.get("id") == pid
    assert row.get("slug") == slug
    assert row.get("status") == "publish"
    assert raw(row, "title") == title
    assert row.get("featured_media") == media


def block_problems(text):
    stack = []
    for m in TOKEN.finditer(text):
        t = m.group(0); om = OPEN.fullmatch(t); cm = CLOSE.fullmatch(t)
        if om:
            if not om.group(2): stack.append(om.group(1))
        elif cm:
            name = cm.group(1)
            if not stack or stack[-1] != name: return [("mismatch", stack[-1] if stack else None, name)]
            stack.pop()
    return [("unclosed", tuple(stack))] if stack else []


def image_count(text):
    return len(re.findall(r"<!--\s+wp:image\b", text))


def replace_once(text, old, new, label):
    n = text.count(old)
    assert n == 1, f"{label}: expected 1, found {n}"
    return text.replace(old, new, 1)


def prepare_koukai(c):
    assert c.count(CTN_BANNER) == 1 and c.count(CTN_BUTTON) == 2
    assert "電話が少なくて快適でした" not in c
    fixed = c
    for i, (old, new) in enumerate(KOUKAI_REPL, 1):
        fixed = replace_once(fixed, old, new, f"koukai timeline {i}")
    fixed = replace_once(fixed, KOUKAI_CTN_OLD, KOUKAI_CTN_NEW, "koukai CTN")
    assert "約5か月" not in fixed
    assert "約3か月ごろ" in fixed and "電話が少なくて快適でした" in fixed
    assert fixed.count(CTN_BANNER) == 1 and fixed.count(CTN_BUTTON) == 2
    return fixed


def prepare_resale(c):
    assert c.count(CTN_BANNER) == 3 and c.count(CTN_BUTTON) == 1
    assert "電話が少なくて、私はかなり快適でした" not in c
    fixed = replace_once(c, RESALE_PHONE_OLD, RESALE_PHONE_NEW, "resale phone note")
    pos = fixed.find(RESALE_EARLY_ANCHOR)
    assert pos >= 0
    m = BANNER_BLOCK_RE.search(fixed, pos)
    assert m is not None
    fixed = fixed[:m.start()] + "\n" + fixed[m.end():]
    assert fixed.count(CTN_BANNER) == 2 and fixed.count(CTN_BUTTON) == 1
    assert "電話が少なくて、私はかなり快適でした" in fixed
    return fixed


def main():
    before_public = public_count()
    prepared = {}

    # Preflight both targets before either WordPress write.
    for pid in (2517, 2222):
        row = get_post(pid); verify(row, pid)
        c = raw(row, "content")
        assert not block_problems(c)
        before_images = image_count(c)
        fixed = prepare_koukai(c) if pid == 2517 else prepare_resale(c)
        assert image_count(fixed) == before_images
        assert not block_problems(fixed)
        prepared[pid] = fixed

    results = []
    for pid in (2517, 2222):
        req(f"{SITE}/wp-json/wp/v2/posts/{pid}", method="POST", payload={"content": prepared[pid]})
        row = get_post(pid); verify(row, pid)
        c = raw(row, "content")
        assert c == prepared[pid]
        assert not block_problems(c)
        results.append((TARGETS[pid][0], c.count(CTN_BANNER), c.count(CTN_BUTTON)))

    after_public = public_count()
    assert before_public == after_public
    print("# UX CTN funnel optimization")
    print("- result: **SUCCESS**")
    print(f"- public posts: **{before_public} → {after_public}**")
    print("- WordPress payload: **content only**")
    print("- Gutenberg problems after: **0**")
    print("- image counts: **unchanged**")
    print("- ux-koukai: appraisal timing **約5か月 → 約3か月ごろ**")
    print("- ux-koukai: firsthand note **連絡2社 / 電話が少なくて快適**")
    print("- ux-resale: firsthand note **連絡2社 / 電話が少なくてかなり快適**")
    print("- ux-resale: CTN banners **3 → 2**")
    for slug, banners, buttons in results:
        print(f"- {slug}: **publish** / banners **{banners}** / buttons **{buttons}**")


if __name__ == "__main__":
    main()
