#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import re
import urllib.parse
import urllib.request
from typing import Any

SITE = "https://tsurikue.com"
BASE = SITE + "/wp-json/wp/v2"
UA = "tsurikue-okunoshima-related-cards-20260911/1.0"

POST_ID = 3730
SLUG = "okunoshima-rabbit-island"
SECTION_TITLE = "このあと寄りたいスポット"
MARK = "<!-- tq-outing-related-cards:v1:okunoshima-rabbit-island -->"
END_MARK = "<!-- tq-outing-related-cards:v1:end -->"

TARGETS = [
    {
        "id": 2041,
        "slug": "hiroshima-sightseeing",
        "title": "広島観光・レジャーまとめ｜車で行ける日帰りドライブ先を紹介",
        "url": "https://tsurikue.com/hiroshima-sightseeing/",
    },
    {
        "id": 3514,
        "slug": "mitakidera-autumn",
        "title": "広島・三滝寺（三瀧寺）の紅葉｜2025年11月の色づきと秋の境内を散策",
        "url": "https://tsurikue.com/mitakidera-autumn/",
    },
    {
        "id": 1887,
        "slug": "etajima-sightseeing",
        "title": "江田島観光に行こう｜ドライブ良し・食事良し・景色良しの休日旅",
        "url": "https://tsurikue.com/etajima-sightseeing/",
    },
]

TOKEN = re.compile(r"<!--\s+/?wp:[\s\S]*?-->")
OPEN = re.compile(r"<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->")
CLOSE = re.compile(r"<!--\s+/wp:([\w\-/]+)\s+-->")


def auth() -> str:
    user = os.environ.get("TSURIKUE_WP_USER")
    pw = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not pw:
        raise RuntimeError("BLOCKED_MISSING_SECRETS")
    token = base64.b64encode(f"{user}:{pw}".encode()).decode()
    return "Basic " + token


def req(url: str, method: str = "GET", payload: dict[str, Any] | None = None, timeout: int = 60):
    headers = {
        "Authorization": auth(),
        "Accept": "application/json",
        "User-Agent": UA,
    }
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
        return (json.loads(body.decode("utf-8")) if body else None), dict(response.headers)


def raw_field(row: dict, key: str) -> str:
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)


def clean_title(row: dict) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", raw_field(row, "title"))).strip()


def get_post(post_id: int) -> dict:
    q = urllib.parse.urlencode({
        "context": "edit",
        "_fields": "id,slug,status,title,content,link,categories,modified",
    })
    row, _ = req(f"{BASE}/posts/{post_id}?{q}")
    return row


def public_counts() -> dict[str, int]:
    out = {}
    for endpoint in ("posts", "pages"):
        q = urllib.parse.urlencode({"status": "publish", "per_page": 1, "_fields": "id"})
        _, headers = req(f"{BASE}/{endpoint}?{q}", timeout=45)
        out[endpoint] = int(headers.get("X-WP-Total", "0"))
    out["total"] = out["posts"] + out["pages"]
    return out


def gb_problems(text: str) -> int:
    stack: list[str] = []
    bad = 0
    for m in TOKEN.finditer(text):
        token = m.group(0)
        op = OPEN.fullmatch(token)
        cl = CLOSE.fullmatch(token)
        if op:
            if not op.group(2):
                stack.append(op.group(1))
        elif cl:
            if not stack or stack[-1] != cl.group(1):
                bad += 1
            else:
                stack.pop()
    return bad + len(stack)


def embed(url: str) -> str:
    return (
        f'<!-- wp:embed {{"url":"{url}"}} -->\n'
        f'<figure class="wp-block-embed"><div class="wp-block-embed__wrapper">\n'
        f'{url}\n'
        f'</div></figure>\n'
        f'<!-- /wp:embed -->'
    )


def section() -> str:
    cards = "\n\n".join(embed(t["url"]) for t in TARGETS)
    return (
        f"{MARK}\n"
        f'<!-- wp:heading {{"level":3}} -->\n'
        f'<h3 class="wp-block-heading">{SECTION_TITLE}</h3>\n'
        f'<!-- /wp:heading -->\n\n'
        f"{cards}\n"
        f"{END_MARK}"
    )


def validate_target(row: dict, expected: dict) -> None:
    if int(row.get("id") or 0) != expected["id"]:
        raise RuntimeError(f'target id mismatch: {expected["slug"]}')
    if row.get("slug") != expected["slug"]:
        raise RuntimeError(f'target slug mismatch: {expected["slug"]}')
    if row.get("status") != "publish":
        raise RuntimeError(f'target not published: {expected["slug"]}')
    if clean_title(row) != expected["title"]:
        raise RuntimeError(f'target title changed: {expected["slug"]}')
    if row.get("link") != expected["url"]:
        raise RuntimeError(f'target URL mismatch: {expected["slug"]}')


def main() -> None:
    before_counts = public_counts()

    source = get_post(POST_ID)
    if int(source.get("id") or 0) != POST_ID or source.get("slug") != SLUG:
        raise RuntimeError("source id/slug mismatch")
    if source.get("status") not in ("draft", "publish"):
        raise RuntimeError(f"unexpected source status={source.get('status')}")

    for target in TARGETS:
        validate_target(get_post(target["id"]), target)

    old = raw_field(source, "content")
    if not old:
        raise RuntimeError("source content empty")
    if gb_problems(old) != 0:
        raise RuntimeError(f"current Gutenberg problems={gb_problems(old)}")

    if MARK in old:
        if old.count(MARK) != 1 or END_MARK not in old:
            raise RuntimeError("existing marker invalid")
        for t in TARGETS:
            if t["url"] not in old:
                raise RuntimeError(f'existing section missing {t["url"]}')
        changed = False
        new = old
    else:
        if SECTION_TITLE in old:
            raise RuntimeError("heading already exists without marker")
        new = old.rstrip() + "\n\n" + section() + "\n"
        changed = True

    if gb_problems(new) != 0:
        raise RuntimeError(f"new Gutenberg problems={gb_problems(new)}")

    old_sha = hashlib.sha256(old.encode()).hexdigest()

    if changed:
        current = get_post(POST_ID)
        current_raw = raw_field(current, "content")
        if hashlib.sha256(current_raw.encode()).hexdigest() != old_sha:
            raise RuntimeError("source changed after preflight")
        updated, _ = req(
            f"{BASE}/posts/{POST_ID}",
            method="POST",
            payload={"content": new},
            timeout=90,
        )
        if updated.get("status") != source.get("status"):
            raise RuntimeError(
                f"status changed unexpectedly: {source.get('status')} -> {updated.get('status')}"
            )

    final = get_post(POST_ID)
    final_raw = raw_field(final, "content")
    if final_raw != new:
        raise RuntimeError("final content mismatch")
    if final_raw.count(MARK) != 1:
        raise RuntimeError("final marker count mismatch")
    if final_raw.count('<!-- wp:embed ') < 3:
        raise RuntimeError("embed count mismatch")
    for t in TARGETS:
        if t["url"] not in final_raw:
            raise RuntimeError(f'final content missing {t["url"]}')

    after_counts = public_counts()
    if after_counts != before_counts:
        raise RuntimeError(f"public counts changed: {before_counts} -> {after_counts}")

    print("# 大久野島 関連記事カード")
    print("- result: **SUCCESS**")
    print(f"- post_id: **{POST_ID}**")
    print(f"- status: **{final.get('status')}**")
    print(f"- changed: **{changed}**")
    print(f"- heading: **{SECTION_TITLE}**")
    print("- cards: **3**")
    for t in TARGETS:
        print(f'- {t["slug"]} — {t["url"]}')
    print(f"- published_before: **{before_counts}**")
    print(f"- published_after: **{after_counts}**")


if __name__ == "__main__":
    main()
