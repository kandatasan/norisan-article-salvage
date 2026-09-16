#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import os
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

SITE = "https://tsurikue.com"
UA = "tsurikue-ux-traffic-affiliate-cleanup-20260917/1.0"
REPORT = Path("reports/ux-traffic-affiliate-cleanup-20260917")

GULLIVER = "a8mat=4B65SD+8DUSHE+9QU+NVHCY"
CTN = "a8mat=3Z8YF4+7VEGL6+5I4S+5YRHE"

USED_INTERNAL = """<!-- wp:paragraph -->
<p>中古で探すなら、相場や前期・後期の違いは<a href="https://tsurikue.com/lexus-ux-used/">レクサスUXの中古は狙い目？</a>で整理しています。</p>
<!-- /wp:paragraph -->"""

SELL_INTERNAL = """<!-- wp:paragraph -->
<p>査定先でどれくらい差が出たのか、一括査定の電話ラッシュを避ける方法まで含めて、<a href="https://tsurikue.com/car-sell-high/">車を楽に高く売る方法</a>にまとめています。</p>
<!-- /wp:paragraph -->"""

SHORTCODES = [
    """<!-- wp:shortcode -->
[blog_parts id="2184"]
<!-- /wp:shortcode -->""",
    """<!-- wp:shortcode -->
[blog_parts id="2843"]
<!-- /wp:shortcode -->""",
    """<!-- wp:shortcode -->
[blog_parts id="2846"]
<!-- /wp:shortcode -->""",
]

POSTS = [
    {
        "id": 2870,
        "slug": "lexus-ux-review",
        "status": "publish",
        "title": "レクサスUXの評価・感想は？1万km以上乗った元オーナーが本音レビュー",
        "expected_sha256": "e7661ab7b8f6a13984ca40d4b166200048858a8a42009f5bc9f1b7f71a08f29d",
        "target_sha256": "8ac5f337df36438ef952c430496c6a602c0769c00f6c20f6448360755ca75f44",
        "add_used_link": False,
    },
    {
        "id": 2874,
        "slug": "lexus-ux-poor",
        "status": "publish",
        "title": "レクサスUXは貧乏・見栄っ張りに見える？実際に所有して感じたこと",
        "expected_sha256": "4856dcf5fcf3395ee4b7ca410f54b44a0030780b9768b85f9a0e5071180f0afa",
        "target_sha256": "3e3af3bda7722106cdd62e6bb090e45ad19f35cbb9c8090e6709d4cd1f95c9d5",
        "add_used_link": False,
    },
    {
        "id": 2881,
        "slug": "lexus-ux-buyer",
        "status": "publish",
        "title": "レクサスUXを買う人はどんな人？年齢層・年収・向いている使い方を考える",
        "expected_sha256": "24eb69109815a2c9a2cdef2c3f161cfc309ba4dc3a3a1891d5e1ff350ae30ad3",
        "target_sha256": "e9df907d6d39fd285baf36ce397e5422128f1b0760c24d389044a5efc1582545",
        "add_used_link": False,
    },
    {
        "id": 2886,
        "slug": "lexus-ux-size",
        "status": "publish",
        "title": "レクサスUXのサイズは大きい？車幅・全長・取り回しを元オーナー目線で解説",
        "expected_sha256": "25101e30ebfd3b9b8fbb5a24951ccb54ba5d0e8fd3ca185fbe24b621203d5e9e",
        "target_sha256": "7982835427c73b0bb5c1a35299a4a5c5f54c3ed8235eb6865f77aab5e1fa545c",
        "add_used_link": True,
    },
    {
        "id": 2897,
        "slug": "lexus-ux-interior",
        "status": "publish",
        "title": "レクサスUXの内装はしょぼい？実際に触って感じた高級感と気になる部分",
        "expected_sha256": "1f9aebf1c5ad33154cf24a88e1b7873f0830b66dd100500d680b388f43e83391",
        "target_sha256": "f856be6fa117c00c4b259c64d39c1fb6d792a6eb2b7667a12f9a5a61a7a7cb00",
        "add_used_link": False,
    },
    {
        "id": 2902,
        "slug": "lexus-ux-rear-seat",
        "status": "publish",
        "title": "レクサスUXの後部座席は狭い？大人4人で乗った感想と使い勝手を確認",
        "expected_sha256": "d54cb816b2312b85b2b7af39e9bd8daf0c0661831fb9c5a0bc42688593360df7",
        "target_sha256": "8a15b024270e1483923afea5f61b046a449241db568d612cacf41d9cf321cb28",
        "add_used_link": True,
    },
    {
        "id": 2907,
        "slug": "lexus-ux-cargo",
        "status": "publish",
        "title": "レクサスUXの荷室は狭い？ゴルフバッグ・買い物で使えるかをチェック",
        "expected_sha256": "76e55ba3210ffeaf127539d3efd4e67b507becc47d33e129b6c3c591c78ca9b6",
        "target_sha256": "c8b906c6811b31227bfbf728956e2c2c591c1e614f09bd13ba0b5d03b132a91d",
        "add_used_link": True,
    },
    {
        "id": 2975,
        "slug": "lexus-ux-model-change",
        "status": "publish",
        "title": "レクサスUXのモデルチェンジはいつ？次期型は出る？生産終了の噂も整理",
        "expected_sha256": "d2913737c6a2973b0dc855836a4d99869d40086637318c73ab6f9027a417bb73",
        "target_sha256": "9e5521a806ac9ea6ae180ffec6b3927427271a8a5ffce6b88312229dd546ea73",
        "add_used_link": False,
    },
]


def sha256(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()


def auth_header() -> str:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise RuntimeError("missing WordPress secrets")
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return "Basic " + token


AUTH = None


def request(method: str, path: str, payload=None):
    global AUTH
    if AUTH is None:
        AUTH = auth_header()
    headers = {"Authorization": AUTH, "Accept": "application/json", "User-Agent": UA}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(SITE + path, data=data, headers=headers, method=method)
    last = None
    for n in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read().decode("utf-8")
                return (json.loads(body) if body else None), dict(resp.headers.items())
        except Exception as exc:
            last = exc
            if n < 2:
                time.sleep(2 * (n + 1))
    raise last


def raw_field(row: dict, key: str) -> str:
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)


def get_post(post_id: int) -> dict:
    q = urllib.parse.urlencode({
        "context": "edit",
        "_fields": "id,slug,status,title,content,author,featured_media,categories",
    })
    row, _ = request("GET", f"/wp-json/wp/v2/posts/{post_id}?{q}")
    return row


def identity_snapshot(row: dict) -> dict:
    return {
        "id": int(row.get("id") or 0),
        "slug": row.get("slug"),
        "status": row.get("status"),
        "title": html.unescape(raw_field(row, "title")),
        "author": int(row.get("author") or 0),
        "featured_media": int(row.get("featured_media") or 0),
        "categories": list(row.get("categories") or []),
    }


def validate_identity(spec: dict, row: dict) -> dict:
    ident = identity_snapshot(row)
    for key in ("id", "slug", "status", "title"):
        if ident[key] != spec[key]:
            raise RuntimeError(
                f"{spec['slug']}: {key} mismatch: expected={spec[key]!r} actual={ident[key]!r}"
            )
    return ident


def public_count(endpoint: str) -> int:
    q = urllib.parse.urlencode({"status": "publish", "per_page": 1, "_fields": "id"})
    _, headers = request("GET", f"/wp-json/wp/v2/{endpoint}?{q}")
    for key, value in headers.items():
        if key.lower() == "x-wp-total":
            return int(value)
    raise RuntimeError(f"X-WP-Total missing for {endpoint}")


def public_counts() -> dict:
    return {"posts": public_count("posts"), "pages": public_count("pages")}


def affiliate_paragraph_pattern(token: str):
    return re.compile(
        r'<!-- wp:paragraph -->\s*<p>(?:(?!<!-- /wp:paragraph -->).)*?'
        + re.escape(token)
        + r'(?:(?!<!-- /wp:paragraph -->).)*?</p>\s*<!-- /wp:paragraph -->',
        re.S,
    )


def build_target(spec: dict, current: str):
    current_sha = sha256(current)
    if current_sha == spec["target_sha256"]:
        return current, False

    if current_sha != spec["expected_sha256"]:
        raise RuntimeError(
            f"{spec['slug']}: content changed since export audit: {current_sha}"
        )

    gpat = affiliate_paragraph_pattern(GULLIVER)
    cpat = affiliate_paragraph_pattern(CTN)

    if len(gpat.findall(current)) != 1:
        raise RuntimeError(f"{spec['slug']}: expected exactly one Gulliver affiliate paragraph")
    if len(cpat.findall(current)) != 1:
        raise RuntimeError(f"{spec['slug']}: expected exactly one CTN affiliate paragraph")
    for block in SHORTCODES:
        if current.count(block) != 1:
            raise RuntimeError(f"{spec['slug']}: expected exactly one affiliate shortcode block")

    target = gpat.sub(USED_INTERNAL if spec["add_used_link"] else "", current, count=1)
    target = cpat.sub(SELL_INTERNAL, target, count=1)
    for block in SHORTCODES:
        target = target.replace(block, "")
    target = re.sub(r"\n{4,}", "\n\n\n", target)

    if GULLIVER in target or CTN in target:
        raise RuntimeError(f"{spec['slug']}: direct affiliate URL remained")
    if any(block in target for block in SHORTCODES):
        raise RuntimeError(f"{spec['slug']}: affiliate shortcode remained")
    if "https://tsurikue.com/car-sell-high/" not in target:
        raise RuntimeError(f"{spec['slug']}: sell-side revenue-core link missing")
    if "https://tsurikue.com/lexus-ux-used/" not in target:
        raise RuntimeError(f"{spec['slug']}: used-UX revenue-core link missing")
    if "<h1" in target.lower():
        raise RuntimeError(f"{spec['slug']}: target unexpectedly contains H1")
    if sha256(target) != spec["target_sha256"]:
        raise RuntimeError(
            f"{spec['slug']}: target hash drift: {sha256(target)}"
        )
    return target, True


def write_report(data: dict):
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / "result.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        "# UX traffic affiliate cleanup — 2026-09-17",
        "",
        f"- result: **{data['result']}**",
        f"- mode: **{data['mode']}**",
        f"- targets: **{len(data.get('posts', []))}**",
        f"- public posts before/after: **{data.get('public_before',{}).get('posts','-')} / {data.get('public_after',{}).get('posts','-')}**",
        f"- public pages before/after: **{data.get('public_before',{}).get('pages','-')} / {data.get('public_after',{}).get('pages','-')}**",
        "",
        "## Posts",
    ]
    for item in data.get("posts", []):
        lines.extend([
            f"- {item['slug']} (post {item['id']}): **{item['status']}** / {item['action']}",
            f"  - before: {item['before_sha256']}",
            f"  - target/final: {item['after_sha256']}",
        ])
    if data.get("errors"):
        lines.extend(["", "## Errors"])
        lines.extend([f"- {x}" for x in data["errors"]])
    (REPORT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["preflight", "apply"], default="preflight")
    args = parser.parse_args()

    before_counts = public_counts()
    states = []
    for spec in POSTS:
        row = get_post(spec["id"])
        ident = validate_identity(spec, row)
        current = raw_field(row, "content")
        target, needs_write = build_target(spec, current)
        states.append({
            "spec": spec,
            "identity": ident,
            "original": current,
            "target": target,
            "needs_write": needs_write,
        })

    if args.mode == "preflight":
        data = {
            "result": "PREFLIGHT_OK_NO_WRITES",
            "mode": args.mode,
            "public_before": before_counts,
            "public_after": before_counts,
            "posts": [
                {
                    "id": s["spec"]["id"],
                    "slug": s["spec"]["slug"],
                    "status": s["identity"]["status"],
                    "action": "WOULD_APPLY" if s["needs_write"] else "ALREADY_APPLIED",
                    "before_sha256": sha256(s["original"]),
                    "after_sha256": sha256(s["target"]),
                }
                for s in states
            ],
            "errors": [],
        }
        write_report(data)
        return 0

    attempted = []
    errors = []
    try:
        for state in states:
            if not state["needs_write"]:
                continue
            spec = state["spec"]
            attempted.append(state)
            request("POST", f"/wp-json/wp/v2/posts/{spec['id']}", {"content": state["target"]})
            saved = get_post(spec["id"])
            if validate_identity(spec, saved) != state["identity"]:
                raise RuntimeError(f"{spec['slug']}: identity/metadata changed after write")
            if raw_field(saved, "content") != state["target"]:
                raise RuntimeError(f"{spec['slug']}: saved content mismatch")

        after_counts = public_counts()
        if after_counts != before_counts:
            raise RuntimeError(f"public counts changed: {before_counts} -> {after_counts}")
    except Exception as exc:
        errors.append(str(exc))
        for state in reversed(attempted):
            spec = state["spec"]
            try:
                request(
                    "POST",
                    f"/wp-json/wp/v2/posts/{spec['id']}",
                    {"content": state["original"]},
                )
                rolled = get_post(spec["id"])
                if raw_field(rolled, "content") != state["original"]:
                    errors.append(f"{spec['slug']}: rollback content mismatch")
                if validate_identity(spec, rolled) != state["identity"]:
                    errors.append(f"{spec['slug']}: rollback identity mismatch")
            except Exception as rb:
                errors.append(f"{spec['slug']}: rollback failed: {rb}")
        data = {
            "result": "APPLY_FAILED_ROLLBACK_ATTEMPTED",
            "mode": args.mode,
            "public_before": before_counts,
            "public_after": public_counts(),
            "posts": [],
            "errors": errors,
        }
        write_report(data)
        return 3

    final_posts = []
    for state in states:
        spec = state["spec"]
        final = get_post(spec["id"])
        final_ident = validate_identity(spec, final)
        final_content = raw_field(final, "content")
        if final_ident != state["identity"]:
            errors.append(f"{spec['slug']}: final identity mismatch")
        if final_content != state["target"]:
            errors.append(f"{spec['slug']}: final content mismatch")
        if GULLIVER in final_content or CTN in final_content:
            errors.append(f"{spec['slug']}: final direct affiliate URL remained")
        if any(block in final_content for block in SHORTCODES):
            errors.append(f"{spec['slug']}: final affiliate shortcode remained")
        final_posts.append({
            "id": spec["id"],
            "slug": spec["slug"],
            "status": final_ident["status"],
            "action": "APPLIED" if state["needs_write"] else "ALREADY_APPLIED",
            "before_sha256": sha256(state["original"]),
            "after_sha256": sha256(final_content),
        })

    after_counts = public_counts()
    if after_counts != before_counts:
        errors.append(f"final public counts changed: {before_counts} -> {after_counts}")

    data = {
        "result": "APPLIED_OK" if not errors else "APPLIED_BUT_FINAL_VERIFY_FAILED",
        "mode": args.mode,
        "public_before": before_counts,
        "public_after": after_counts,
        "posts": final_posts,
        "errors": errors,
    }
    write_report(data)
    return 0 if not errors else 4


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        REPORT.mkdir(parents=True, exist_ok=True)
        data = {
            "result": "BLOCKED_BEFORE_WRITE",
            "mode": "unknown",
            "public_before": {},
            "public_after": {},
            "posts": [],
            "errors": [f"{type(exc).__name__}: {exc}"],
        }
        write_report(data)
        raise
