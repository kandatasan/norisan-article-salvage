#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

SITE_URL = "https://tsurikue.com"
POST_ID = 2517
EXPECTED_SLUG = "ux-koukai"
EXPECTED_STATUS = "publish"
EXPECTED_TITLE = "レクサスUXはひどい？616万円で買って後悔した欠点と満足している理由"
EXPECTED_FEATURED_MEDIA = 2208
EXPECTED_CONTENT_SHA = "8efe8f41690580fe44b24a7af2ef4d2018dd16038d5f60072e591732870566b1"
REPORT_DIR = Path("reports/fix-ux-koukai-gutenberg-20260907")
USER_AGENT = "tsurikue-fix-ux-koukai-gutenberg-20260907/1.0"

OPEN_RE = re.compile(r"<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->")
CLOSE_RE = re.compile(r"<!--\s+/wp:([\w\-/]+)\s+-->")
ANY_BLOCK_COMMENT_RE = re.compile(r"<!--\s+/?wp:[\s\S]*?-->")
LEAF = {"paragraph", "heading"}


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def request_json(url: str, auth: str, method: str = "GET", payload=None):
    data = None
    headers = {"Accept": "application/json", "Authorization": auth, "User-Agent": USER_AGENT}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as response:
        body = response.read().decode("utf-8")
        return json.loads(body), dict(response.headers)


def raw_field(row, key: str) -> str:
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def strip_block_comments(text: str) -> str:
    return ANY_BLOCK_COMMENT_RE.sub("", text)


def analyze_leaf_structure(text: str):
    stack = []
    problems = []
    pos = 0
    token_re = re.compile(r"<!--\s+/?wp:[\s\S]*?-->")
    for m in token_re.finditer(text):
        token = m.group(0)
        om = OPEN_RE.fullmatch(token)
        cm = CLOSE_RE.fullmatch(token)
        if om:
            name = om.group(1)
            selfclosing = bool(om.group(2))
            if selfclosing:
                continue
            if stack and stack[-1] in LEAF:
                problems.append({"type": "nested_inside_leaf", "open_leaf": stack[-1], "next_open": name, "at": m.start()})
            stack.append(name)
        elif cm:
            name = cm.group(1)
            if not stack:
                problems.append({"type": "orphan_close", "name": name, "at": m.start()})
                continue
            if stack[-1] == name:
                stack.pop()
            else:
                problems.append({"type": "mismatched_close", "expected": stack[-1], "actual": name, "at": m.start()})
                if name in stack:
                    while stack and stack[-1] != name:
                        stack.pop()
                    if stack and stack[-1] == name:
                        stack.pop()
        pos = m.end()
    if stack:
        problems.append({"type": "unclosed", "stack": stack[:]})
    return problems


def repair_leaf_comments(text: str):
    token_re = re.compile(r"<!--\s+/?wp:[\s\S]*?-->")
    out = []
    stack = []
    last = 0
    changes = []

    for m in token_re.finditer(text):
        between = text[last:m.start()]
        out.append(between)
        token = m.group(0)
        om = OPEN_RE.fullmatch(token)
        cm = CLOSE_RE.fullmatch(token)

        if om:
            name = om.group(1)
            selfclosing = bool(om.group(2))
            if selfclosing:
                out.append(token)
            else:
                if stack and stack[-1] in LEAF:
                    leaf = stack[-1]
                    # If the previous leaf marker was immediately followed only by whitespace,
                    # the previous opener is the duplicate. Drop it rather than creating an empty block.
                    previous_text = out[-1] if out else ""
                    if previous_text.strip() == "":
                        # Find and remove the most recent opener for that same leaf from output.
                        removed = False
                        for i in range(len(out) - 2, -1, -1):
                            if re.fullmatch(rf"<!--\s+wp:{re.escape(leaf)}(?:\s+\{{.*?\}})?\s*-->", out[i] or ""):
                                out.pop(i)
                                removed = True
                                changes.append({"action": "remove_duplicate_open", "block": leaf, "at": m.start()})
                                stack.pop()
                                break
                        if not removed:
                            out.append(f"<!-- /wp:{leaf} -->")
                            changes.append({"action": "insert_leaf_close", "block": leaf, "at": m.start()})
                            stack.pop()
                    else:
                        out.append(f"<!-- /wp:{leaf} -->")
                        changes.append({"action": "insert_leaf_close", "block": leaf, "at": m.start()})
                        stack.pop()
                out.append(token)
                stack.append(name)

        elif cm:
            name = cm.group(1)
            if stack and stack[-1] == name:
                out.append(token)
                stack.pop()
            elif name in LEAF:
                # This is the stale closer for a leaf we already closed before a nested block.
                changes.append({"action": "remove_orphan_leaf_close", "block": name, "at": m.start()})
            else:
                out.append(token)
                if name in stack:
                    while stack and stack[-1] != name:
                        stack.pop()
                    if stack and stack[-1] == name:
                        stack.pop()
        else:
            out.append(token)
        last = m.end()

    out.append(text[last:])
    fixed = "".join(out)
    return fixed, changes


def get_post(auth: str):
    params = urllib.parse.urlencode({"context": "edit"})
    row, _ = request_json(f"{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}?{params}", auth)
    return row


def get_published_count(auth: str) -> int:
    params = urllib.parse.urlencode({"status": "publish", "per_page": 1, "_fields": "id"})
    _, headers = request_json(f"{SITE_URL}/wp-json/wp/v2/posts?{params}", auth)
    return int(headers.get("X-WP-Total", 0))


def assert_identity(row, content: str):
    assert row.get("id") == POST_ID, row.get("id")
    assert row.get("slug") == EXPECTED_SLUG, row.get("slug")
    assert row.get("status") == EXPECTED_STATUS, row.get("status")
    assert raw_field(row, "title") == EXPECTED_TITLE, raw_field(row, "title")
    assert row.get("featured_media") == EXPECTED_FEATURED_MEDIA, row.get("featured_media")
    assert sha(content) == EXPECTED_CONTENT_SHA, sha(content)


def main():
    user = os.environ["TSURIKUE_WP_USER"]
    password = os.environ["TSURIKUE_WP_APP_PASSWORD"]
    auth = auth_header(user, password)

    before = get_post(auth)
    before_content = raw_field(before, "content")
    assert_identity(before, before_content)
    public_before = get_published_count(auth)
    problems_before = analyze_leaf_structure(before_content)
    assert problems_before, "Expected broken Gutenberg leaf structure, but none was found"

    fixed, changes = repair_leaf_comments(before_content)
    assert fixed != before_content, "No repair was produced"
    assert strip_block_comments(fixed) == strip_block_comments(before_content), "Visible HTML changed; aborting"

    problems_after_local = analyze_leaf_structure(fixed)
    remaining_leaf = [p for p in problems_after_local if p.get("type") in {"nested_inside_leaf", "orphan_close", "mismatched_close", "unclosed"}]
    assert not remaining_leaf, remaining_leaf

    # Content-only update. Do not send status/title/slug/featured_media.
    updated, _ = request_json(
        f"{SITE_URL}/wp-json/wp/v2/posts/{POST_ID}",
        auth,
        method="POST",
        payload={"content": fixed},
    )

    after = get_post(auth)
    after_content = raw_field(after, "content")
    public_after = get_published_count(auth)

    assert after.get("id") == POST_ID
    assert after.get("slug") == EXPECTED_SLUG
    assert after.get("status") == EXPECTED_STATUS
    assert raw_field(after, "title") == EXPECTED_TITLE
    assert after.get("featured_media") == EXPECTED_FEATURED_MEDIA
    assert public_after == public_before
    assert strip_block_comments(after_content) == strip_block_comments(before_content), "Rendered source HTML changed after WordPress save"

    problems_after = analyze_leaf_structure(after_content)
    remaining_leaf_after = [p for p in problems_after if p.get("type") in {"nested_inside_leaf", "orphan_close", "mismatched_close", "unclosed"}]
    assert not remaining_leaf_after, remaining_leaf_after

    report = {
        "result": "SUCCESS",
        "post_id": POST_ID,
        "slug": EXPECTED_SLUG,
        "status_before": before.get("status"),
        "status_after": after.get("status"),
        "title_unchanged": raw_field(after, "title") == raw_field(before, "title"),
        "featured_media_before": before.get("featured_media"),
        "featured_media_after": after.get("featured_media"),
        "public_before": public_before,
        "public_after": public_after,
        "content_sha_before": sha(before_content),
        "content_sha_after": sha(after_content),
        "visible_html_sha_before": sha(strip_block_comments(before_content)),
        "visible_html_sha_after": sha(strip_block_comments(after_content)),
        "visible_html_unchanged": strip_block_comments(before_content) == strip_block_comments(after_content),
        "problems_before": problems_before,
        "problems_after": problems_after,
        "changes": changes,
        "wordpress_write_count": 1,
        "payload_fields": ["content"],
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = [
        "# UX koukai Gutenberg repair",
        "",
        "- result: **SUCCESS**",
        f"- post_id: **{POST_ID}**",
        f"- slug: `{EXPECTED_SLUG}`",
        f"- status: **{before.get('status')} → {after.get('status')}**",
        f"- featured_media: **{before.get('featured_media')} → {after.get('featured_media')}**",
        f"- public_before: **{public_before}**",
        f"- public_after: **{public_after}**",
        f"- visible_html_unchanged: **{report['visible_html_unchanged']}**",
        f"- broken_block_problems_before: **{len(problems_before)}**",
        f"- broken_block_problems_after: **{len(problems_after)}**",
        f"- block_comment_repairs: **{len(changes)}**",
        "- payload_fields: **content only**",
        "- wordpress_write_count: **1**",
        "",
        "## Repairs",
    ]
    for c in changes:
        summary.append(f"- {c['action']}: {c['block']}")
    (REPORT_DIR / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print("\n".join(summary))


if __name__ == "__main__":
    main()
