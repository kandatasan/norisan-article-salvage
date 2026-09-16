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
UA = "tsurikue-adsense-cleanup-20260917/1.0"
REPORT = Path("reports/adsense-cleanup-20260917")

TOTOYA = {
    "endpoint": "posts",
    "id": 2657,
    "slug": "totoya-iiyo",
    "status": "publish",
    "title": "浜村温泉「魚と屋」に泊まってきた｜料理の量にびっくり！温泉・部屋も本音レビュー",
    "old_sha": "5d79bd02a4eab91a93cf8261affc19388016677892d4d2bdfcc029f41285315b",
    "target_sha": "fb5a6831f549350835b3deb156e07795f5753583a001ab901dd3f4943a975ec3",
}

PRIVACY = {
    "endpoint": "pages",
    "id": 1970,
    "slug": "privacy-policy",
    "status": "publish",
    "title": "プライバシーポリシー",
    "old_sha": "86928580ff5945d55e1119698e97aa593665ce9693bfae41c547650589122000",
    "target_sha": "2d63c9fd547126b21bca61f47e8663204dcdb41f14e5bafe5aaa27ecab37b8ca",
}

TOTOYA_REMOVE = """<!-- wp:paragraph -->
<p>※悲しいことに、画像データが無くなっちゃいました。見つかり次第復旧していきます…</p>
<!-- /wp:paragraph -->

"""

PRIVACY_OLD = """<!-- wp:heading -->
<h2 class="wp-block-heading">広告について</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>当サイトでは、第三者配信の広告サービスやアフィリエイトプログラムを利用する場合があります。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>主な利用サービスは以下の通りです。</p>
<!-- /wp:paragraph -->

<!-- wp:list -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>Googleアドセンス</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>A8.net</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>楽天アフィリエイト</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Amazonアソシエイト</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>もしもアフィリエイト</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>アクセストレード</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>バリューコマース</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>その他ASP広告サービス</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->

<!-- wp:paragraph -->
<p>当サイトで紹介している商品・サービスに関するお問い合わせは、各販売元・サービス提供元へ直接お願いいたします。当サイトでは対応いたしかねますので、あらかじめご了承ください。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>これらの広告配信事業者は、ユーザーの興味に応じた商品やサービスの広告を表示するため、Cookieを使用する場合があります。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>Cookieを使用することで、当サイトはユーザーのブラウザを識別できるようになりますが、氏名・住所・メールアドレス・電話番号など、個人を特定する情報は含まれません。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>Cookieの使用を望まない場合は、ブラウザの設定からCookieを無効にすることができます。</p>
<!-- /wp:paragraph -->"""

PRIVACY_NEW = """<!-- wp:heading -->
<h2 class="wp-block-heading">広告について</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>当サイトでは、第三者配信の広告サービスやアフィリエイトプログラムを利用する場合があります。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>主な利用サービスは以下の通りです。</p>
<!-- /wp:paragraph -->

<!-- wp:list -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>Googleアドセンス</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>A8.net</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>楽天アフィリエイト</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Amazonアソシエイト</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>もしもアフィリエイト</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>アクセストレード</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>バリューコマース</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>その他ASP広告サービス</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->

<!-- wp:paragraph -->
<p>当サイトで紹介している商品・サービスに関するお問い合わせは、各販売元・サービス提供元へ直接お願いいたします。当サイトでは対応いたしかねますので、あらかじめご了承ください。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>Googleなどの第三者配信事業者は、Cookieを使用して、ユーザーが当サイトや他のウェブサイトに過去にアクセスした際の情報に基づいて広告を配信する場合があります。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>Googleが広告Cookieを使用することにより、Googleおよびそのパートナーは、ユーザーが当サイトや他のウェブサイトにアクセスした際の情報に基づいて、ユーザーに適した広告を表示できます。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>ユーザーは、<a href="https://adssettings.google.com/" target="_blank" rel="noopener noreferrer">Googleの広告設定</a>からパーソナライズ広告を無効にできます。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>また、当サイトに広告を掲載することにより、第三者配信事業者や広告ネットワークがユーザーのブラウザにCookieを保存したり、ウェブビーコン、IPアドレスその他の識別子を使用して情報を収集したりする場合があります。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>Cookie自体には、氏名・住所・メールアドレス・電話番号など、ユーザー個人を直接特定する情報は含まれません。Cookieの利用を望まない場合は、ブラウザの設定からCookieを無効にすることもできます。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>GoogleがGoogleのサービスを使用するサイトやアプリから収集した情報をどのように利用するかについては、<a href="https://policies.google.com/technologies/partner-sites?hl=ja" target="_blank" rel="noopener noreferrer">Googleのポリシーと規約</a>をご確認ください。</p>
<!-- /wp:paragraph -->"""

OLD_DATE = "<p>最終更新日：2026年5月21日</p>"
NEW_DATE = "<p>最終更新日：2026年9月17日</p>"


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
    for n in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read().decode("utf-8")
                return (json.loads(body) if body else None), dict(resp.headers.items())
        except Exception as exc:
            last = exc
            if n < 3:
                time.sleep(2 * (n + 1))
    raise last


def raw(row: dict, key: str) -> str:
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)


def public_count(endpoint: str) -> int:
    q = urllib.parse.urlencode({"status": "publish", "per_page": 1, "_fields": "id"})
    _, headers = request("GET", f"/wp-json/wp/v2/{endpoint}?{q}")
    for k, v in headers.items():
        if k.lower() == "x-wp-total":
            return int(v)
    raise RuntimeError(f"X-WP-Total missing for {endpoint}")


def public_counts() -> dict:
    return {"posts": public_count("posts"), "pages": public_count("pages")}


def get_item(spec: dict) -> dict:
    q = urllib.parse.urlencode({
        "context": "edit",
        "_fields": "id,slug,status,title,content,author,featured_media,categories,parent",
    })
    row, _ = request("GET", f"/wp-json/wp/v2/{spec['endpoint']}/{spec['id']}?{q}")
    return row


def identity(row: dict, spec: dict) -> dict:
    snap = {
        "id": int(row.get("id") or 0),
        "slug": row.get("slug"),
        "status": row.get("status"),
        "title": html.unescape(raw(row, "title")),
        "author": int(row.get("author") or 0),
        "featured_media": int(row.get("featured_media") or 0),
        "categories": list(row.get("categories") or []),
        "parent": int(row.get("parent") or 0),
    }
    if snap["id"] != spec["id"]:
        raise RuntimeError(f"id mismatch for {spec['slug']}: {snap['id']}")
    if snap["slug"] != spec["slug"]:
        raise RuntimeError(f"slug mismatch for {spec['slug']}: {snap['slug']}")
    if snap["status"] != spec["status"]:
        raise RuntimeError(f"status mismatch for {spec['slug']}: {snap['status']}")
    if snap["title"] != spec["title"]:
        raise RuntimeError(f"title mismatch for {spec['slug']}: {snap['title']}")
    return snap


def build_totoya(current: str) -> str:
    current_sha = sha256(current)
    if current_sha == TOTOYA["target_sha"]:
        if "見つかり次第復旧" in current or "画像データが無くなっちゃいました" in current:
            raise RuntimeError("totoya target hash matched but restoration notice still exists")
        return current
    if current_sha != TOTOYA["old_sha"]:
        raise RuntimeError(f"totoya content changed since audit: {current_sha}")
    if current.count(TOTOYA_REMOVE) != 1:
        raise RuntimeError(f"totoya restoration block count is {current.count(TOTOYA_REMOVE)}")
    target = current.replace(TOTOYA_REMOVE, "", 1)
    if sha256(target) != TOTOYA["target_sha"]:
        raise RuntimeError(f"totoya reviewed target hash drift: {sha256(target)}")
    return target


def build_privacy(current: str) -> str:
    current_sha = sha256(current)
    if current_sha == PRIVACY["target_sha"]:
        required = [
            "Googleなどの第三者配信事業者",
            "Googleが広告Cookieを使用",
            "https://adssettings.google.com/",
            "ウェブビーコン、IPアドレスその他の識別子",
            "https://policies.google.com/technologies/partner-sites?hl=ja",
            NEW_DATE,
        ]
        for phrase in required:
            if phrase not in current:
                raise RuntimeError(f"privacy target missing required phrase: {phrase}")
        return current
    if current_sha != PRIVACY["old_sha"]:
        raise RuntimeError(f"privacy content changed since audit: {current_sha}")
    if current.count(PRIVACY_OLD) != 1:
        raise RuntimeError(f"privacy old ad block count is {current.count(PRIVACY_OLD)}")
    if current.count(OLD_DATE) != 1:
        raise RuntimeError(f"privacy old date count is {current.count(OLD_DATE)}")
    target = current.replace(PRIVACY_OLD, PRIVACY_NEW, 1).replace(OLD_DATE, NEW_DATE, 1)
    if sha256(target) != PRIVACY["target_sha"]:
        raise RuntimeError(f"privacy reviewed target hash drift: {sha256(target)}")
    return target


def write_report(data: dict) -> None:
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / "result.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        "# AdSense cleanup — 2026-09-17",
        "",
        f"- result: **{data['result']}**",
        f"- mode: **{data['mode']}**",
        f"- totoya action: **{data.get('totoya_action','-')}**",
        f"- privacy action: **{data.get('privacy_action','-')}**",
        f"- totoya before/final sha256: **{data.get('totoya_before','-')} / {data.get('totoya_final','-')}**",
        f"- privacy before/final sha256: **{data.get('privacy_before','-')} / {data.get('privacy_final','-')}**",
        f"- published posts before/after: **{data.get('public_before',{}).get('posts','-')} / {data.get('public_after',{}).get('posts','-')}**",
        f"- published pages before/after: **{data.get('public_before',{}).get('pages','-')} / {data.get('public_after',{}).get('pages','-')}**",
    ]
    if data.get("errors"):
        lines.extend(["", "## Errors"])
        lines.extend([f"- {x}" for x in data["errors"]])
    (REPORT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["preflight", "apply"], default="preflight")
    args = parser.parse_args()

    before_counts = public_counts()

    tot_row = get_item(TOTOYA)
    pri_row = get_item(PRIVACY)
    tot_identity = identity(tot_row, TOTOYA)
    pri_identity = identity(pri_row, PRIVACY)
    tot_current = raw(tot_row, "content")
    pri_current = raw(pri_row, "content")

    tot_target = build_totoya(tot_current)
    pri_target = build_privacy(pri_current)

    if args.mode == "preflight":
        data = {
            "result": "PREFLIGHT_OK_NO_WRITES",
            "mode": args.mode,
            "totoya_action": "NOOP" if tot_current == tot_target else "REMOVE_RESTORATION_NOTICE",
            "privacy_action": "NOOP" if pri_current == pri_target else "UPDATE_ADSENSE_DISCLOSURE",
            "totoya_before": sha256(tot_current),
            "totoya_final": sha256(tot_target),
            "privacy_before": sha256(pri_current),
            "privacy_final": sha256(pri_target),
            "public_before": before_counts,
            "public_after": before_counts,
            "errors": [],
        }
        write_report(data)
        return 0

    changed = []
    errors = []
    try:
        if tot_current != tot_target:
            request("POST", f"/wp-json/wp/v2/posts/{TOTOYA['id']}", {"content": tot_target})
            changed.append(("totoya", TOTOYA, tot_current))
        if pri_current != pri_target:
            request("POST", f"/wp-json/wp/v2/pages/{PRIVACY['id']}", {"content": pri_target})
            changed.append(("privacy", PRIVACY, pri_current))

        tot_final_row = get_item(TOTOYA)
        pri_final_row = get_item(PRIVACY)
        if identity(tot_final_row, TOTOYA) != tot_identity:
            raise RuntimeError("totoya metadata changed")
        if identity(pri_final_row, PRIVACY) != pri_identity:
            raise RuntimeError("privacy metadata changed")
        tot_final = raw(tot_final_row, "content")
        pri_final = raw(pri_final_row, "content")
        if tot_final != tot_target:
            raise RuntimeError("totoya final content mismatch")
        if pri_final != pri_target:
            raise RuntimeError("privacy final content mismatch")
        if "見つかり次第復旧" in tot_final or "画像データが無くなっちゃいました" in tot_final:
            raise RuntimeError("totoya restoration notice remains")
        for phrase in [
            "Googleなどの第三者配信事業者",
            "https://adssettings.google.com/",
            "ウェブビーコン、IPアドレスその他の識別子",
            "https://policies.google.com/technologies/partner-sites?hl=ja",
            NEW_DATE,
        ]:
            if phrase not in pri_final:
                raise RuntimeError(f"privacy required phrase missing after save: {phrase}")
        after_counts = public_counts()
        if after_counts != before_counts:
            raise RuntimeError(f"public counts changed: {before_counts} -> {after_counts}")
    except Exception as exc:
        errors.append(str(exc))
        for _, spec, original in reversed(changed):
            try:
                request(
                    "POST",
                    f"/wp-json/wp/v2/{spec['endpoint']}/{spec['id']}",
                    {"content": original},
                )
            except Exception as rb:
                errors.append(f"rollback failed for {spec['slug']}: {rb}")
        write_report({
            "result": "APPLY_FAILED_ROLLBACK_ATTEMPTED",
            "mode": args.mode,
            "totoya_action": "ROLLBACK_ATTEMPTED",
            "privacy_action": "ROLLBACK_ATTEMPTED",
            "totoya_before": sha256(tot_current),
            "totoya_final": "-",
            "privacy_before": sha256(pri_current),
            "privacy_final": "-",
            "public_before": before_counts,
            "public_after": public_counts(),
            "errors": errors,
        })
        return 3

    write_report({
        "result": "APPLIED_OK",
        "mode": args.mode,
        "totoya_action": "NOOP" if tot_current == tot_target else "REMOVE_RESTORATION_NOTICE",
        "privacy_action": "NOOP" if pri_current == pri_target else "UPDATE_ADSENSE_DISCLOSURE",
        "totoya_before": sha256(tot_current),
        "totoya_final": sha256(tot_target),
        "privacy_before": sha256(pri_current),
        "privacy_final": sha256(pri_target),
        "public_before": before_counts,
        "public_after": public_counts(),
        "errors": [],
    })
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        REPORT.mkdir(parents=True, exist_ok=True)
        write_report({
            "result": "BLOCKED_BEFORE_WRITE",
            "mode": "unknown",
            "totoya_action": "-",
            "privacy_action": "-",
            "totoya_before": "-",
            "totoya_final": "-",
            "privacy_before": "-",
            "privacy_final": "-",
            "public_before": {},
            "public_after": {},
            "errors": [f"{type(exc).__name__}: {exc}"],
        })
        raise
