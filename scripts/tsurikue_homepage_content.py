#!/usr/bin/env python3
"""Safely strengthen the published tsurikue.com homepage body."""
from __future__ import annotations

import argparse
import base64
import csv
import difflib
import html
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

SITE_URL = "https://tsurikue.com"
PAGE_ID = 2255
EXPECTED_URL = "https://tsurikue.com/"
APPLY_CONFIRMATION = "APPLY-HOMEPAGE-CONTENT-20260711"
MARKER = "「つりくえ！」について"
EMPTY_PARAGRAPH = "<!-- wp:paragraph -->\n<p></p>\n<!-- /wp:paragraph -->"

REQUIRED_SINGLE_SNIPPETS = (
    'class="wp-image-2269"',
    'alt="釣りカテゴリー"',
    'alt="レジャー・観光カテゴリー"',
    'alt="グルメカテゴリー"',
    'alt="車カテゴリー"',
)

CATEGORY_HREF_SNIPPETS = (
    'href="https://tsurikue.com/category/fishing/"',
    'href="https://tsurikue.com/category/sightseeing-leisure/"',
    'href="https://tsurikue.com/category/gourmet/"',
    'href="https://tsurikue.com/category/car/"',
)

ADDITION = '''<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">「つりくえ！」について</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>「つりくえ！」は、広島・山口を中心に、家族で出かけた観光地やドライブ先、実際に食べたグルメ、釣りの記録、愛車レクサスUXの体験をまとめたブログです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>公式情報だけでは分かりにくい「現地でどう感じたか」「どれくらい楽しめたか」「失敗しやすいところ」まで、写真と本音を交えて紹介しています。次の休日の行き先や、釣り・食事・車選びの参考になればうれしいです。</p>
<!-- /wp:paragraph -->

<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">カテゴリーから探す</h2>
<!-- /wp:heading -->

<!-- wp:list -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li><a href="https://tsurikue.com/category/fishing/"><strong>釣り</strong></a>：釣行記、初心者向けの釣り方、管理釣り場の体験</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li><a href="https://tsurikue.com/category/sightseeing-leisure/"><strong>レジャー・観光</strong></a>：広島・山口・中国地方の日帰りドライブや旅行記</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li><a href="https://tsurikue.com/category/gourmet/"><strong>グルメ</strong></a>：実際に食べた店、海鮮、ラーメン、旅先グルメ</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li><a href="https://tsurikue.com/category/car/"><strong>車</strong></a>：レクサスUXの購入・後悔・売却、カー用品や洗車</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->

<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">まず読んでほしい記事</h2>
<!-- /wp:heading -->

<!-- wp:list -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li><a href="https://tsurikue.com/kantan-aoriika/">初めてでも簡単！秋アオリイカの釣り方｜初心者向けエギングのコツ4選</a></li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li><a href="https://tsurikue.com/hiroshima-sightseeing/">広島観光・レジャーまとめ｜車で行ける日帰りドライブ先を紹介</a></li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li><a href="https://tsurikue.com/higashihiroshima-ramen/">東広島ラーメン食べ歩き｜地元民が実際に食べたおすすめ店まとめ</a></li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li><a href="https://tsurikue.com/ux-koukai/">レクサスUXはひどい？616万円で買って後悔した欠点と満足している理由</a></li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->

<!-- wp:paragraph -->
<p>このブログを書いている人や、記事づくりで大切にしていることは、<a href="https://tsurikue.com/profile/">運営者情報</a>にまとめています。</p>
<!-- /wp:paragraph -->'''

EXPECTED_RECOMMENDED_URLS = (
    "https://tsurikue.com/kantan-aoriika/",
    "https://tsurikue.com/hiroshima-sightseeing/",
    "https://tsurikue.com/higashihiroshima-ramen/",
    "https://tsurikue.com/ux-koukai/",
)


@dataclass
class Document:
    title: str
    link: str
    content: str


@dataclass
class Result:
    original: str
    updated: str


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def request_json(url: str, *, method: str = "GET", auth: str | None = None, payload: dict | None = None) -> dict:
    headers = {"Accept": "application/json", "User-Agent": "tsurikue-homepage-content/1.0"}
    if auth:
        headers["Authorization"] = auth
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    last_error: Exception | None = None
    for attempt in range(1, 4):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as error:
            last_error = error
            if attempt < 3:
                time.sleep(attempt * 3)
    assert last_error is not None
    raise last_error


def credentials() -> tuple[str, str]:
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("WordPress credentials are required")
    return user, password


def endpoint(site_url: str) -> str:
    return f"{site_url.rstrip('/')}/wp-json/wp/v2/pages/{PAGE_ID}"


def fetch_homepage(site_url: str, user: str, password: str) -> Document:
    fields = "id,status,link,title,content"
    query = urllib.parse.urlencode({"context": "edit", "_fields": fields})
    row = request_json(f"{endpoint(site_url)}?{query}", auth=auth_header(user, password))
    if int(row.get("id", 0)) != PAGE_ID:
        raise ValueError("Homepage ID mismatch")
    if row.get("status") != "publish":
        raise ValueError("Homepage is not published")
    link = row.get("link", "")
    if link.rstrip("/") != EXPECTED_URL.rstrip("/"):
        raise ValueError(f"Homepage URL mismatch: {link}")
    raw = (row.get("content") or {}).get("raw")
    if raw is None:
        raise ValueError("Homepage content.raw missing")
    title = html.unescape((row.get("title") or {}).get("raw") or (row.get("title") or {}).get("rendered", ""))
    return Document(title, link, raw)


def transform(content: str) -> Result:
    if MARKER in content:
        raise ValueError("Homepage strengthening section already exists")
    for snippet in REQUIRED_SINGLE_SNIPPETS + CATEGORY_HREF_SNIPPETS:
        if content.count(snippet) != 1:
            raise ValueError(f"Required homepage snippet mismatch: {snippet}")
    if content.count(EMPTY_PARAGRAPH) != 1:
        raise ValueError("Expected exactly one trailing empty paragraph")
    updated = content.replace(EMPTY_PARAGRAPH, ADDITION, 1)
    if updated.count(MARKER) != 1:
        raise ValueError("Homepage marker insertion failed")
    if updated.count("<!-- wp:heading") - content.count("<!-- wp:heading") != 3:
        raise ValueError("Unexpected heading count change")
    if updated.count("<img ") != content.count("<img "):
        raise ValueError("Image count changed unexpectedly")
    for url in EXPECTED_RECOMMENDED_URLS:
        if updated.count(url) != 1:
            raise ValueError(f"Recommended URL mismatch: {url}")
    return Result(content, updated)


def verify_applied(content: str) -> None:
    if content.count(MARKER) != 1:
        raise ValueError("Homepage marker missing after apply")
    if EMPTY_PARAGRAPH in content:
        raise ValueError("Trailing empty paragraph remains after apply")
    for snippet in REQUIRED_SINGLE_SNIPPETS:
        if content.count(snippet) != 1:
            raise ValueError(f"Required homepage snippet changed after apply: {snippet}")
    for snippet in CATEGORY_HREF_SNIPPETS:
        if content.count(snippet) != 2:
            raise ValueError(f"Category href count changed unexpectedly after apply: {snippet}")
    for url in EXPECTED_RECOMMENDED_URLS:
        if content.count(url) != 1:
            raise ValueError(f"Recommended URL missing after apply: {url}")


def write_artifacts(output: Path, doc: Document, result: Result, mode: str, status: str) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "backup-homepage.html").write_text(result.original, encoding="utf-8")
    (output / "after-homepage.html").write_text(result.updated, encoding="utf-8")
    diff = "".join(difflib.unified_diff(
        result.original.splitlines(keepends=True),
        result.updated.splitlines(keepends=True),
        fromfile="before/homepage.html",
        tofile="after/homepage.html",
    ))
    (output / "homepage.diff").write_text(diff, encoding="utf-8")
    with (output / "summary.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["page_id", "title", "url", "mode", "apply_status", "added_headings", "added_category_links", "added_recommended_links"])
        writer.writerow([PAGE_ID, doc.title, doc.link, mode, status, 3, 4, 4])
    report = f"""# トップページ本文強化

- mode: {mode}
- page_id: {PAGE_ID}
- URL: {doc.link}
- apply_status: {status}
- 追加見出し: 3
- 文字カテゴリーリンク: 4
- おすすめ記事リンク: 4
- 画像変更: 0
- 既存リンク変更: 0
- タイトル・URL・公開状態の変更: 0
"""
    (output / "report.md").write_text(report, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("authenticated-dry-run", "apply"), default="authenticated-dry-run")
    parser.add_argument("--site-url", default=SITE_URL)
    parser.add_argument("--output-dir", type=Path, default=Path("reports/tsurikue-homepage-content"))
    parser.add_argument("--apply-confirmation", default="")
    args = parser.parse_args()

    if args.mode == "apply" and args.apply_confirmation != APPLY_CONFIRMATION:
        raise SystemExit(f"apply requires confirmation string {APPLY_CONFIRMATION}")

    user, password = credentials()
    doc = fetch_homepage(args.site_url, user, password)
    result = transform(doc.content)
    status = "not-run"
    write_artifacts(args.output_dir, doc, result, args.mode, status)

    if args.mode == "apply":
        auth = auth_header(user, password)
        try:
            request_json(endpoint(args.site_url), method="POST", auth=auth, payload={"content": result.updated})
            updated_doc = fetch_homepage(args.site_url, user, password)
            verify_applied(updated_doc.content)
            status = "updated"
        except Exception as error:
            try:
                request_json(endpoint(args.site_url), method="POST", auth=auth, payload={"content": result.original})
                status = "rolled-back"
            except Exception as rollback_error:
                status = "rollback-failed"
                write_artifacts(args.output_dir, doc, result, args.mode, status)
                raise RuntimeError("Homepage apply and rollback both failed") from rollback_error
            write_artifacts(args.output_dir, doc, result, args.mode, status)
            raise RuntimeError("Homepage apply failed; original content restored") from error
        write_artifacts(args.output_dir, doc, result, args.mode, status)

    print(f"Homepage: {PAGE_ID}")
    print("Added headings: 3")
    print("Added category links: 4")
    print("Added recommended links: 4")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
