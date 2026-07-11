#!/usr/bin/env python3
"""Safely replace reader-facing "要確認" placeholders in seven published tsurikue.com posts."""
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
APPLY_CONFIRMATION = "APPLY-YOKAKUNIN-20260711"

TARGETS = {
    1887: ("posts", "https://tsurikue.com/etajima-sightseeing/", 1),
    1892: ("posts", "https://tsurikue.com/higashihiroshima-ramen/", 4),
    1911: ("posts", "https://tsurikue.com/hiroshima-bokujyou/", 7),
    1939: ("posts", "https://tsurikue.com/hiroshima-sanin-1night-2days/", 4),
    1955: ("posts", "https://tsurikue.com/sera-sightseeing/", 4),
    2011: ("posts", "https://tsurikue.com/yuki-town-drive/", 3),
    2063: ("posts", "https://tsurikue.com/hiroshima-hajimarinoteras/", 1),
}

REPLACEMENTS = (
    (
        "<tr><th>営業状況</th><td>営業情報あり（要確認）</td></tr>",
        "<tr><th>営業状況</th><td>最新の営業情報は公式サイトや店舗SNSをご確認ください</td></tr>",
        "営業情報あり（要確認）",
    ),
    (
        "<tr><th>営業状況</th><td>閉店情報あり（要確認）</td></tr>",
        "<tr><th>営業状況</th><td>閉店情報があるため、訪問前に最新情報をご確認ください</td></tr>",
        "閉店情報あり（要確認）",
    ),
    (
        "<tr><th>営業状況</th><td>公式情報あり（要確認）</td></tr>",
        "<tr><th>営業状況</th><td>最新の営業情報は公式サイトや施設のSNSをご確認ください</td></tr>",
        "公式情報あり（要確認）",
    ),
    (
        "<tr><th>営業状況</th><td>要確認</td></tr>",
        "<tr><th>営業状況</th><td>最新の営業状況は公式情報をご確認ください</td></tr>",
        "営業状況：要確認",
    ),
    (
        "<tr><th>駐車場</th><td>要確認</td></tr>",
        "<tr><th>駐車場</th><td>駐車場の利用条件は訪問前に公式情報をご確認ください</td></tr>",
        "駐車場：要確認",
    ),
    (
        "<tr><th>駐車場</th><td>あり（要確認）</td></tr>",
        "<tr><th>駐車場</th><td>あり。最新の利用条件は公式情報をご確認ください</td></tr>",
        "駐車場：あり（要確認）",
    ),
    (
        "<tr><th>利用前確認</th><td>予約条件・釣り堀ルール・対象魚を要確認</td></tr>",
        "<tr><th>利用前確認</th><td>予約条件・釣り堀ルール・対象魚は、利用前に公式情報をご確認ください</td></tr>",
        "利用前確認",
    ),
)

EXPECTED_PATTERN_COUNTS = {
    "営業情報あり（要確認）": 3,
    "閉店情報あり（要確認）": 1,
    "公式情報あり（要確認）": 13,
    "営業状況：要確認": 2,
    "駐車場：要確認": 3,
    "駐車場：あり（要確認）": 1,
    "利用前確認": 1,
}
EXPECTED_TOTAL = 24

@dataclass
class Document:
    post_id: int
    endpoint: str
    title: str
    link: str
    content: str

@dataclass
class Change:
    label: str
    before: str
    after: str

@dataclass
class Result:
    original: str
    updated: str
    changes: list[Change]
    remaining: int

def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"

def endpoint(site_url: str, endpoint_name: str, post_id: int) -> str:
    return f"{site_url.rstrip('/')}/wp-json/wp/v2/{endpoint_name}/{post_id}"

def request_json(url: str, *, method: str = "GET", auth: str | None = None, payload: dict | None = None) -> dict:
    headers = {"Accept": "application/json", "User-Agent": "tsurikue-yokakunin-cleanup/1.0"}
    if auth:
        headers["Authorization"] = auth
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    last_error = None
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            last_error = exc
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

def fetch_documents(site_url: str, user: str, password: str) -> list[Document]:
    auth = auth_header(user, password)
    fields = "id,status,link,title,content"
    documents = []
    for post_id, (endpoint_name, expected_url, _) in TARGETS.items():
        query = urllib.parse.urlencode({"context": "edit", "_fields": fields})
        row = request_json(f"{endpoint(site_url, endpoint_name, post_id)}?{query}", auth=auth)
        if int(row.get("id", 0)) != post_id:
            raise ValueError(f"ID mismatch for {post_id}")
        if row.get("status") != "publish":
            raise ValueError(f"Document {post_id} is not published")
        link = row.get("link", "")
        if link.rstrip("/") != expected_url.rstrip("/"):
            raise ValueError(f"URL mismatch for {post_id}: {link}")
        raw = (row.get("content") or {}).get("raw")
        if raw is None:
            raise ValueError(f"content.raw missing for {post_id}")
        title = html.unescape((row.get("title") or {}).get("raw") or (row.get("title") or {}).get("rendered", ""))
        documents.append(Document(post_id, endpoint_name, title, link, raw))
    return documents

def transform(doc: Document) -> Result:
    updated = doc.content
    changes: list[Change] = []
    for before, after, label in REPLACEMENTS:
        count = updated.count(before)
        if count:
            for _ in range(count):
                changes.append(Change(label, before, after))
            updated = updated.replace(before, after)
    remaining = updated.count("要確認")
    expected = TARGETS[doc.post_id][2]
    if len(changes) != expected:
        raise ValueError(f"Document {doc.post_id} expected {expected} replacements but found {len(changes)}")
    if remaining:
        raise ValueError(f"Document {doc.post_id} still contains {remaining} 要確認 occurrences")
    return Result(doc.content, updated, changes, remaining)

def validate_global(rows: list[tuple[Document, Result]]) -> None:
    actual = {}
    for _, result in rows:
        for change in result.changes:
            actual[change.label] = actual.get(change.label, 0) + 1
    for label, expected in EXPECTED_PATTERN_COUNTS.items():
        if actual.get(label, 0) != expected:
            raise SystemExit(f"Pattern count mismatch for {label}: expected={expected} actual={actual.get(label, 0)}")
    total = sum(actual.values())
    if total != EXPECTED_TOTAL:
        raise SystemExit(f"Total replacement count mismatch: expected={EXPECTED_TOTAL} actual={total}")

def write_artifacts(output: Path, rows: list[tuple[Document, Result]], mode: str, statuses: dict[int, str] | None = None) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for name in ("backups", "after", "diffs"):
        (output / name).mkdir(exist_ok=True)
    with (output / "summary.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["post_id", "title", "url", "replacement_count", "remaining_yokakunin", "apply_status"])
        for doc, result in rows:
            writer.writerow([doc.post_id, doc.title, doc.link, len(result.changes), result.remaining, (statuses or {}).get(doc.post_id, "not-run")])
    report = [
        "# 「要確認」表記の読者向け置換",
        "",
        f"- mode: {mode}",
        f"- 対象記事: {len(rows)}",
        f"- 置換総数: {sum(len(r.changes) for _, r in rows)}",
        f"- 残存数: {sum(r.remaining for _, r in rows)}",
        "",
    ]
    for doc, result in rows:
        name = f"post-{doc.post_id}"
        (output / "backups" / f"{name}.html").write_text(doc.content, encoding="utf-8")
        (output / "after" / f"{name}.html").write_text(result.updated, encoding="utf-8")
        diff = "".join(difflib.unified_diff(
            doc.content.splitlines(keepends=True),
            result.updated.splitlines(keepends=True),
            fromfile=f"before/{name}.html",
            tofile=f"after/{name}.html",
        ))
        (output / "diffs" / f"{name}.diff").write_text(diff, encoding="utf-8")
        report += [f"## {doc.title}", "", f"- ID: {doc.post_id}", f"- URL: {doc.link}", f"- 置換数: {len(result.changes)}", ""]
        for idx, change in enumerate(result.changes, 1):
            report += [
                f"### {idx}. {change.label}",
                "",
                "変更前:",
                "```html",
                change.before,
                "```",
                "",
                "変更後:",
                "```html",
                change.after,
                "```",
                "",
            ]
    (output / "report.md").write_text("\n".join(report), encoding="utf-8")

def apply_with_rollback(site_url: str, user: str, password: str, rows: list[tuple[Document, Result]]) -> dict[int, str]:
    auth = auth_header(user, password)
    statuses: dict[int, str] = {}
    updated: list[Document] = []
    try:
        for doc, result in rows:
            request_json(endpoint(site_url, doc.endpoint, doc.post_id), method="POST", auth=auth, payload={"content": result.updated})
            statuses[doc.post_id] = "updated"
            updated.append(doc)
    except Exception as exc:
        failed_id = doc.post_id
        statuses[failed_id] = f"failed:{type(exc).__name__}"
        rollback_failures = []
        for old in reversed(updated):
            try:
                request_json(endpoint(site_url, old.endpoint, old.post_id), method="POST", auth=auth, payload={"content": old.content})
                statuses[old.post_id] = "rolled-back"
            except Exception:
                statuses[old.post_id] = "rollback-failed"
                rollback_failures.append(old.post_id)
        if rollback_failures:
            raise RuntimeError(f"Apply failed and rollback failed for {rollback_failures}") from exc
        raise RuntimeError("Apply failed; all earlier updates rolled back") from exc
    return statuses

def verify_after_apply(site_url: str, user: str, password: str) -> None:
    documents = fetch_documents(site_url, user, password)
    for doc in documents:
        if "要確認" in doc.content:
            raise SystemExit(f"Post-apply verification failed: 要確認 remains in {doc.post_id}")
        if any(before in doc.content for before, _, _ in REPLACEMENTS):
            raise SystemExit(f"Post-apply verification failed: source text remains in {doc.post_id}")

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("authenticated-dry-run", "apply"), default="authenticated-dry-run")
    parser.add_argument("--site-url", default=SITE_URL)
    parser.add_argument("--output-dir", type=Path, default=Path("reports/tsurikue-yokakunin"))
    parser.add_argument("--apply-confirmation", default="")
    args = parser.parse_args()

    if args.mode == "apply" and args.apply_confirmation != APPLY_CONFIRMATION:
        raise SystemExit(f"apply requires confirmation string {APPLY_CONFIRMATION}")

    user, password = credentials()
    documents = fetch_documents(args.site_url, user, password)
    rows = [(doc, transform(doc)) for doc in documents]
    validate_global(rows)
    write_artifacts(args.output_dir, rows, args.mode)

    statuses = None
    if args.mode == "apply":
        statuses = apply_with_rollback(args.site_url, user, password, rows)
        verify_after_apply(args.site_url, user, password)
        write_artifacts(args.output_dir, rows, args.mode, statuses)

    print(f"Documents: {len(rows)}")
    print(f"Replacements: {sum(len(r.changes) for _, r in rows)}")
    print(f"Remaining: {sum(r.remaining for _, r in rows)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
