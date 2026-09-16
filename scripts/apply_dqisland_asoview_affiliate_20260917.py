#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

SITE = "https://tsurikue.com"
UA = "tsurikue-dqisland-asoview-affiliate-20260917/1.0"
REPORT = Path("reports/dqisland-asoview-affiliate-20260917")

POST_ID = 2927
SLUG = "dqisland"
STATUS = "publish"
TITLE = "ニジゲンノモリのドラゴンクエスト アイランドをレビュー！大人4人で冒険した感想・所要時間"
EXPECTED_SHA256 = "303e41a30d6ae2e5bff802076e5dc863b62b0e35a3568619719bccbbaa785a73"
TARGET_SHA256 = "0f54254f703afdae152244f02937a5217f607ac0a3e5ee89cb9c18a4c6c9d884"

AFFILIATE_URL = "https://px.a8.net/svt/ejp?a8mat=3T8PZU+5HNXMA+455G+BW0YB&amp;a8ejpredirect=https%3A%2F%2Fwww.asoview.com%2Fchannel%2Ftickets%2FEDmZ9rpZk5%2F"

TICKET_ANCHOR = """<!-- wp:paragraph -->
<p>当日券や空き状況は日によって変わる可能性があるので、行く日が決まったら<a href="https://www.nijigennomori.com/dragonquestisland/" target="_blank" rel="noopener noreferrer">公式ページ</a>を確認しておくのが安心です。</p>
<!-- /wp:paragraph -->"""

TICKET_REPLACEMENT = TICKET_ANCHOR + f"""

<!-- wp:paragraph -->
<p>チケットをWebで買うなら、<strong>アソビューにもドラゴンクエスト アイランドの専用ページ</strong>があります。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>アソビュー経由ならチケット購入でポイントが貯まるので、どうせ事前に買うなら<strong>ちょっとお得</strong>です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><a href="{AFFILIATE_URL}" rel="nofollow sponsored noreferrer noopener" target="_blank">アソビューでドラゴンクエスト アイランドのチケットを見る</a></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>※チケット内容、料金、ポイントの付与条件は変わることがあります。購入前にリンク先の最新情報を確認してください。</p>
<!-- /wp:paragraph -->"""

END_ANCHOR = """<!-- wp:paragraph -->
<p>……どうやら冒険は、まだ完全には終わっていないようです。</p>
<!-- /wp:paragraph -->"""

END_INSERTION = f"""<!-- wp:paragraph -->
<p>これから行くなら、行く日が決まった時点でチケットを見ておくと安心です。<br>アソビューならポイントも貯まります。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><a href="{AFFILIATE_URL}" rel="nofollow sponsored noreferrer noopener" target="_blank">アソビューでドラクエアイランドのチケットを確認する</a></p>
<!-- /wp:paragraph -->"""


def sha256(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()


def auth_header() -> str:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise RuntimeError("missing WordPress secrets")
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()


AUTH = None


def request(method: str, path: str, payload=None):
    global AUTH
    if AUTH is None:
        AUTH = auth_header()
    headers = {
        "Authorization": AUTH,
        "Accept": "application/json",
        "User-Agent": UA,
    }
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


def public_count(endpoint: str) -> int:
    q = urllib.parse.urlencode({"status": "publish", "per_page": 1, "_fields": "id"})
    _, headers = request("GET", f"/wp-json/wp/v2/{endpoint}?{q}")
    for key, value in headers.items():
        if key.lower() == "x-wp-total":
            return int(value)
    raise RuntimeError(f"X-WP-Total missing for {endpoint}")


def public_counts() -> dict:
    return {"posts": public_count("posts"), "pages": public_count("pages")}


def get_post() -> dict:
    q = urllib.parse.urlencode({
        "context": "edit",
        "_fields": "id,slug,status,title,content,author,featured_media,categories",
    })
    row, _ = request("GET", f"/wp-json/wp/v2/posts/{POST_ID}?{q}")
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


def validate_identity(row: dict) -> dict:
    ident = identity_snapshot(row)
    if ident["id"] != POST_ID:
        raise RuntimeError(f"post ID mismatch: {ident['id']}")
    if ident["slug"] != SLUG:
        raise RuntimeError(f"slug changed: {ident['slug']}")
    if ident["status"] != STATUS:
        raise RuntimeError(f"status changed: {ident['status']}")
    if ident["title"] != TITLE:
        raise RuntimeError(f"title changed: {ident['title']}")
    return ident


def build_target(current: str):
    current_sha = sha256(current)
    if current_sha == TARGET_SHA256:
        if current.count(AFFILIATE_URL) != 2:
            raise RuntimeError("target hash matched but affiliate link count is not 2")
        return current, False

    if current_sha != EXPECTED_SHA256:
        raise RuntimeError(f"content changed since source audit: {current_sha}")
    if current.count(TICKET_ANCHOR) != 1:
        raise RuntimeError(f"ticket anchor count is {current.count(TICKET_ANCHOR)}")
    if current.count(END_ANCHOR) != 1:
        raise RuntimeError(f"end anchor count is {current.count(END_ANCHOR)}")
    if "3T8PZU+5HNXMA+455G+BW0YB" in current:
        raise RuntimeError("Asoview A8 link already present in current article")

    target = current.replace(TICKET_ANCHOR, TICKET_REPLACEMENT, 1)
    target = target.replace(END_ANCHOR, END_ANCHOR + "\n\n" + END_INSERTION, 1)

    if target.count(AFFILIATE_URL) != 2:
        raise RuntimeError("target affiliate link count mismatch")
    if target.count("アソビューならポイントも貯まります") != 1:
        raise RuntimeError("end benefit copy missing")
    if target.count("どうせ事前に買うなら<strong>ちょっとお得</strong>") != 1:
        raise RuntimeError("ticket benefit copy missing")
    if "<h1" in target.lower():
        raise RuntimeError("target must not contain H1")
    if sha256(target) != TARGET_SHA256:
        raise RuntimeError(f"reviewed target hash drift: {sha256(target)}")
    return target, True


def write_report(data: dict):
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / "result.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        "# DQ Island Asoview affiliate update — 2026-09-17",
        "",
        f"- result: **{data['result']}**",
        f"- mode: **{data['mode']}**",
        f"- post: **{POST_ID} / {SLUG}**",
        f"- status: **{data.get('status','-')}**",
        f"- before sha256: **{data.get('before_sha256','-')}**",
        f"- target/final sha256: **{data.get('after_sha256','-')}**",
        f"- affiliate link count: **{data.get('affiliate_count','-')}**",
        f"- public posts before/after: **{data.get('public_before',{}).get('posts','-')} / {data.get('public_after',{}).get('posts','-')}**",
        f"- public pages before/after: **{data.get('public_before',{}).get('pages','-')} / {data.get('public_after',{}).get('pages','-')}**",
    ]
    if data.get("errors"):
        lines.extend(["", "## Errors"])
        lines.extend([f"- {x}" for x in data["errors"]])
    (REPORT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["preflight", "apply"], default="preflight")
    args = parser.parse_args()

    public_before = public_counts()
    row = get_post()
    original_identity = validate_identity(row)
    original = raw_field(row, "content")
    target, needs_write = build_target(original)

    if args.mode == "preflight":
        data = {
            "result": "PREFLIGHT_OK_NO_WRITES",
            "mode": args.mode,
            "status": original_identity["status"],
            "before_sha256": sha256(original),
            "after_sha256": sha256(target),
            "affiliate_count": target.count(AFFILIATE_URL),
            "public_before": public_before,
            "public_after": public_before,
            "errors": [],
        }
        write_report(data)
        return 0

    errors = []
    attempted = False
    try:
        if needs_write:
            attempted = True
            request("POST", f"/wp-json/wp/v2/posts/{POST_ID}", {"content": target})
            saved = get_post()
            saved_identity = validate_identity(saved)
            if saved_identity != original_identity:
                raise RuntimeError(f"identity/metadata changed: {original_identity} -> {saved_identity}")
            if raw_field(saved, "content") != target:
                raise RuntimeError("saved content mismatch")

        public_after = public_counts()
        if public_after != public_before:
            raise RuntimeError(f"public counts changed: {public_before} -> {public_after}")
    except Exception as exc:
        errors.append(str(exc))
        if attempted:
            try:
                request("POST", f"/wp-json/wp/v2/posts/{POST_ID}", {"content": original})
                rolled = get_post()
                if raw_field(rolled, "content") != original:
                    errors.append("rollback content mismatch")
                if identity_snapshot(rolled) != original_identity:
                    errors.append("rollback identity mismatch")
            except Exception as rb:
                errors.append(f"rollback failed: {rb}")
        data = {
            "result": "APPLY_FAILED_ROLLBACK_ATTEMPTED",
            "mode": args.mode,
            "status": original_identity["status"],
            "before_sha256": sha256(original),
            "after_sha256": "",
            "affiliate_count": 0,
            "public_before": public_before,
            "public_after": public_counts(),
            "errors": errors,
        }
        write_report(data)
        return 3

    final = get_post()
    final_identity = validate_identity(final)
    final_content = raw_field(final, "content")
    public_after = public_counts()
    if final_identity != original_identity:
        errors.append("final identity mismatch")
    if final_content != target:
        errors.append("final content mismatch")
    if final_content.count(AFFILIATE_URL) != 2:
        errors.append("final affiliate link count mismatch")
    if public_after != public_before:
        errors.append(f"final public counts changed: {public_before} -> {public_after}")

    data = {
        "result": "APPLIED_OK" if not errors else "APPLIED_BUT_FINAL_VERIFY_FAILED",
        "mode": args.mode,
        "status": final_identity["status"],
        "before_sha256": sha256(original),
        "after_sha256": sha256(final_content),
        "affiliate_count": final_content.count(AFFILIATE_URL),
        "public_before": public_before,
        "public_after": public_after,
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
            "status": "-",
            "before_sha256": "-",
            "after_sha256": "-",
            "affiliate_count": "-",
            "public_before": {},
            "public_after": {},
            "errors": [f"{type(exc).__name__}: {exc}"],
        }
        write_report(data)
        raise
