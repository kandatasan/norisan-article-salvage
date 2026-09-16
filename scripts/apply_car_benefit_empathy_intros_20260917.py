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
UA = "tsurikue-car-benefit-empathy-intros-20260917/1.0"
REPORT = Path("reports/car-benefit-empathy-intros-20260917")

POSTS = [
    {
        "id": 2329,
        "slug": "ux300h",
        "status": "publish",
        "title": "レクサスUX300hを試乗｜UX250hオーナーが比較して感じた3つの違い",
        "expected_sha256": "01c0132f3e0270733d33f5f56a2112d19bc59103fd4f47ab70a6730ba1742527",
        "mode": "prepend",
        "insertion": """<!-- wp:paragraph -->
<p>UX300hと中古のUX250hで迷っているなら、違いを知ってから選べば<strong>「新しい方だから」という理由だけで予算を上げる失敗も、あとから「300hにすればよかった」と後悔するのも避けやすくなります。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>毎日見るメーターやシフト、燃費まで含めて300hの進化に魅力を感じるなら、そこへお金を使う理由も見えてきます。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>ただ、カタログを見ただけでは<strong>「実際の走りまでそんなに違うの？」</strong>が分かりにくいんですよね。</p>
<!-- /wp:paragraph -->

""",
        "required": ["UX300h、超良くなってるじゃん！", "UX250hを所有していた私が"],
    },
    {
        "id": 2517,
        "slug": "ux-koukai",
        "status": "publish",
        "title": "レクサスUXはひどい？616万円で買って後悔した欠点と満足している理由",
        "expected_sha256": "5145559e3f7baca6e22582ca45f1c16f5f62b4ca82023d90d138ee0f0abb95fc",
        "mode": "prepend",
        "insertion": """<!-- wp:paragraph -->
<p>レクサスUXを買って、街中も旅行も気軽に走れて、駐車場でも扱いやすい。<br>そんな毎日を想像しているなら、UXはかなり魅力的なクルマです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>でも、500〜600万円台を出したあとで<strong>「後席、こんなに狭いの？」「荷物、思ったより積めないな」</strong>となるのは避けたいですよね。</p>
<!-- /wp:paragraph -->

""",
        "required": ["レクサスUX、私はかなり好きでした。", "最後は427万円で売った私が"],
    },
    {
        "id": 3611,
        "slug": "lexus-lbx-options",
        "status": "publish",
        "title": "レクサスLBXのおすすめオプションは？ディーラー見積もりから必要・不要を本音で整理",
        "expected_sha256": "9a57cf13db0a26a5dc3aacdce15427acce94589b4ed55064de549cd1e6167ef0",
        "mode": "prepend",
        "insertion": """<!-- wp:paragraph -->
<p>LBXに毎日使う装備はしっかり付ける。<br>でも、使わないオプションに何十万円も払わず、その分を旅行や次の車の予算に残す。オプション選びは、そのくらい現実的に考えていいと思います。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>ただ、見積もりを作り始めると<strong>「人気なら付けるべき？」「あとで付ければよかったと後悔しない？」</strong>と迷いやすいんですよね。</p>
<!-- /wp:paragraph -->

""",
        "required": ["レクサスLBX、どのオプションを付ければいい？", "合計：256,300円"],
    },
    {
        "id": 3767,
        "slug": "landcruiser-fj-price",
        "status": "publish",
        "title": "ランドクルーザーFJの乗り出し価格はいくら？実際の見積り総額は550万516円",
        "expected_sha256": "58529ceb2f377d570f19660bdabca0ba12080c3a4f005d72ce3b77549ba1da6a",
        "mode": "after_anchor",
        "anchor": """<p><!-- tsurikue-original:v1 slug=landcruiser-fj-price source=user-provided-20260913 --><br />
<!-- tsurikue-editorial:v1 slug=landcruiser-fj-price --></p>

""",
        "insertion": """<!-- wp:paragraph -->
<p>ランドクルーザーFJを買うなら、欲しい装備は付けたい。<br>でも、納車してから<strong>「思っていたより100万円高かった」</strong>となるのは避けたいところです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>車両本体だけでなく、MODELLISTAやコーティング、諸費用まで含めた総額が分かれば、<strong>欲しい仕様と予算のバランスを先に決められます。</strong></p>
<!-- /wp:paragraph -->

""",
        "required": ["現金販売時の支払総額は", "差額は100万416円"],
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


def build_target(spec: dict, current: str) -> str:
    current_sha = sha256(current)
    if current_sha != spec["expected_sha256"]:
        raise RuntimeError(
            f"{spec['slug']}: content changed since source audit: {current_sha}"
        )
    for needle in spec["required"]:
        if needle not in current:
            raise RuntimeError(f"{spec['slug']}: current content missing marker: {needle}")
    if spec["insertion"].strip() in current:
        raise RuntimeError(f"{spec['slug']}: insertion already present")
    if spec["mode"] == "prepend":
        target = spec["insertion"] + current
    elif spec["mode"] == "after_anchor":
        anchor = spec["anchor"]
        if not current.startswith(anchor):
            raise RuntimeError(f"{spec['slug']}: expected opening anchor changed")
        target = anchor + spec["insertion"] + current[len(anchor):]
    else:
        raise RuntimeError(f"{spec['slug']}: unsupported mode")
    if "<h1" in target.lower():
        raise RuntimeError(f"{spec['slug']}: target must not contain H1")
    for needle in spec["required"]:
        if needle not in target:
            raise RuntimeError(f"{spec['slug']}: target lost required marker: {needle}")
    return target


def validate_identity(spec: dict, row: dict) -> dict:
    ident = identity_snapshot(row)
    if ident["id"] != spec["id"]:
        raise RuntimeError(f"{spec['slug']}: post ID mismatch: {ident['id']}")
    if ident["slug"] != spec["slug"]:
        raise RuntimeError(f"{spec['slug']}: slug changed: {ident['slug']}")
    if ident["status"] != spec["status"]:
        raise RuntimeError(f"{spec['slug']}: status changed: {ident['status']}")
    if ident["title"] != spec["title"]:
        raise RuntimeError(f"{spec['slug']}: title changed: {ident['title']}")
    return ident


def write_report(data: dict):
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / "result.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        "# Car benefit/empathy intro update — 2026-09-17",
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
            f"- {item['slug']} (post {item['id']}): **{item['status']}**",
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

    public_before = public_counts()
    states = []
    for spec in POSTS:
        row = get_post(spec["id"])
        ident = validate_identity(spec, row)
        current = raw_field(row, "content")
        target = build_target(spec, current)
        states.append({
            "spec": spec,
            "identity": ident,
            "original": current,
            "target": target,
        })

    if args.mode == "preflight":
        data = {
            "result": "PREFLIGHT_OK_NO_WRITES",
            "mode": args.mode,
            "public_before": public_before,
            "public_after": public_before,
            "posts": [
                {
                    "id": s["spec"]["id"],
                    "slug": s["spec"]["slug"],
                    "status": s["identity"]["status"],
                    "before_sha256": sha256(s["original"]),
                    "after_sha256": sha256(s["target"]),
                }
                for s in states
            ],
            "errors": [],
        }
        write_report(data)
        return 0

    changed = []
    errors = []
    try:
        for state in states:
            spec = state["spec"]
            request("POST", f"/wp-json/wp/v2/posts/{spec['id']}", {"content": state["target"]})
            saved = get_post(spec["id"])
            saved_identity = validate_identity(spec, saved)
            if saved_identity != state["identity"]:
                raise RuntimeError(
                    f"{spec['slug']}: identity/metadata changed: {state['identity']} -> {saved_identity}"
                )
            saved_content = raw_field(saved, "content")
            if saved_content != state["target"]:
                raise RuntimeError(f"{spec['slug']}: saved content mismatch")
            changed.append(state)

        public_after = public_counts()
        if public_after != public_before:
            raise RuntimeError(
                f"public post/page counts changed: {public_before} -> {public_after}"
            )
    except Exception as exc:
        errors.append(str(exc))
        for state in reversed(changed):
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
                if identity_snapshot(rolled) != state["identity"]:
                    errors.append(f"{spec['slug']}: rollback identity mismatch")
            except Exception as rb:
                errors.append(f"{spec['slug']}: rollback failed: {rb}")
        data = {
            "result": "APPLY_FAILED_ROLLBACK_ATTEMPTED",
            "mode": args.mode,
            "public_before": public_before,
            "public_after": public_counts(),
            "posts": [
                {
                    "id": s["spec"]["id"],
                    "slug": s["spec"]["slug"],
                    "status": s["identity"]["status"],
                    "before_sha256": sha256(s["original"]),
                    "after_sha256": "",
                }
                for s in states
            ],
            "errors": errors,
        }
        write_report(data)
        return 3

    final_posts = []
    for state in states:
        spec = state["spec"]
        final = get_post(spec["id"])
        final_identity = validate_identity(spec, final)
        final_content = raw_field(final, "content")
        if final_identity != state["identity"]:
            errors.append(f"{spec['slug']}: final identity mismatch")
        if final_content != state["target"]:
            errors.append(f"{spec['slug']}: final content mismatch")
        final_posts.append({
            "id": spec["id"],
            "slug": spec["slug"],
            "status": final_identity["status"],
            "before_sha256": sha256(state["original"]),
            "after_sha256": sha256(final_content),
        })

    public_after = public_counts()
    if public_after != public_before:
        errors.append(f"final public counts changed: {public_before} -> {public_after}")

    data = {
        "result": "APPLIED_OK" if not errors else "APPLIED_BUT_FINAL_VERIFY_FAILED",
        "mode": args.mode,
        "public_before": public_before,
        "public_after": public_after,
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
