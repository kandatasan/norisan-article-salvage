#!/usr/bin/env python3
from __future__ import annotations

import base64, json, os, re, urllib.request

SITE = "https://tsurikue.com"
UA = "tsurikue-ux-ctn-phone-note-20260907/1.0"
CTN_BANNER = '[blog_parts id="2846"]'
CTN_BUTTON = '[blog_parts id="2184"]'

TARGETS = [
    {
        "id": 2517,
        "slug": "ux-koukai",
        "title": "レクサスUXはひどい？616万円で買って後悔した欠点と満足している理由",
        "featured_media": 2208,
        "anchor": "最大15社で査定し、連絡が来るのは高額査定の上位3社だけ。",
        "mark": "電話が少なくて快適でした",
        "note": '<!-- wp:paragraph -->\n<p>実際に私がCTNを使ったときも、連絡が来るのは高額査定の上位3社だけ。<br><strong>電話が少なくて快適でした。</strong></p>\n<!-- /wp:paragraph -->',
    },
    {
        "id": 2222,
        "slug": "ux-resale",
        "title": "レクサスUXのリセールは？616万円で購入し427万円で売却した記録",
        "featured_media": 2223,
        "anchor": "CTNは最大15社で査定し、高額査定の上位3社とやり取りする仕組みです。",
        "mark": "私はかなり快適でした",
        "note": '<!-- wp:paragraph -->\n<p>実際に使ってみて良かったのは、電話が少なかったこと。<br>連絡が来るのは高額査定の上位3社だけだったので、<strong>私はかなり快適でした。</strong></p>\n<!-- /wp:paragraph -->',
    },
]

TOKEN = re.compile(r"<!--\s+/?wp:[\s\S]*?-->")
OPEN = re.compile(r"<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->")
CLOSE = re.compile(r"<!--\s+/wp:([\w\-/]+)\s+-->")


def auth():
    raw = f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()
    return "Basic " + base64.b64encode(raw).decode()


def req(url, method="GET", payload=None):
    headers = {"Accept":"application/json", "Authorization":auth(), "User-Agent":UA}
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode()
        headers["Content-Type"] = "application/json; charset=utf-8"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(r, timeout=60) as x:
        return json.loads(x.read().decode()), dict(x.headers)


def raw(row, key):
    v = row.get(key) or {}
    return v.get("raw") or v.get("rendered") or "" if isinstance(v, dict) else str(v)


def get_post(pid):
    row,_ = req(f"{SITE}/wp-json/wp/v2/posts/{pid}?context=edit")
    return row


def pub_count():
    _,h = req(f"{SITE}/wp-json/wp/v2/posts?status=publish&per_page=1&_fields=id")
    return int(h.get("X-WP-Total",0))


def block_problems(text):
    stack=[]; problems=[]
    for m in TOKEN.finditer(text):
        t=m.group(0); om=OPEN.fullmatch(t); cm=CLOSE.fullmatch(t)
        if om:
            if om.group(2): continue
            stack.append(om.group(1))
        elif cm:
            n=cm.group(1)
            if not stack or stack[-1] != n:
                problems.append(("mismatch", stack[-1] if stack else None, n))
                return problems
            stack.pop()
    if stack: problems.append(("unclosed", stack))
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


def verify_identity(row,t):
    assert row.get("id") == t["id"]
    assert row.get("slug") == t["slug"]
    assert row.get("status") == "publish"
    assert raw(row,"title") == t["title"]
    assert row.get("featured_media") == t["featured_media"]


def main():
    before_total = pub_count()
    prepared=[]

    # Preflight both before any write.
    for t in TARGETS:
        row=get_post(t["id"]); verify_identity(row,t)
        c=raw(row,"content")
        assert t["mark"] not in c, f"note already present in {t['slug']}"
        assert not block_problems(c), f"broken Gutenberg before update: {t['slug']}"
        fixed=insert_after_paragraph(c,t["anchor"],t["note"])
        assert fixed.count(CTN_BANNER) == c.count(CTN_BANNER)
        assert fixed.count(CTN_BUTTON) == c.count(CTN_BUTTON)
        assert len(re.findall(r"<!-- wp:image\\b", fixed)) == len(re.findall(r"<!-- wp:image\\b", c))
        assert not block_problems(fixed), f"broken Gutenberg after local edit: {t['slug']}"
        prepared.append((t,c,fixed))

    results=[]
    for t,before,fixed in prepared:
        req(f"{SITE}/wp-json/wp/v2/posts/{t['id']}", method="POST", payload={"content":fixed})
        after=get_post(t["id"]); verify_identity(after,t)
        ac=raw(after,"content")
        assert t["mark"] in ac
        assert t["anchor"] in ac
        assert ac.count(CTN_BANNER) == before.count(CTN_BANNER)
        assert ac.count(CTN_BUTTON) == before.count(CTN_BUTTON)
        assert not block_problems(ac)
        results.append({"id":t["id"],"slug":t["slug"],"status":after.get("status")})

    after_total=pub_count()
    assert after_total == before_total
    print("# UX CTN phone-volume note")
    print("- result: **SUCCESS**")
    print(f"- public posts: **{before_total} → {after_total}**")
    print("- WordPress payload: **content only**")
    print("- CTA counts: **unchanged**")
    print("- Gutenberg problems after: **0**")
    for r in results:
        print(f"- {r['slug']}: **publish → {r['status']}** / note added")

if __name__ == '__main__':
    main()
