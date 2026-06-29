#!/usr/bin/env python3
"""Analyze and optionally clean known dead internal links on tsurikue.com.

Default operation remains a public GET-only dry-run for local inspection. The
GitHub Actions workflow uses authenticated-dry-run/apply modes, which fetch
``content.raw`` with ``context=edit`` and restrict work to the known 10 posts.
"""
from __future__ import annotations

import argparse
import base64
import csv
import difflib
import html
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

TARGET_PATHS = {
    "/fishingpage", "/managed-fishing-area", "/aoriika-fishing",
    "/drive-gourmet", "/higashihiroshima-gourmet", "/hiroshima-gourmet",
    "/iroha-sushi-akitsu-menu", "/konomiseoishii", "/sanin-sightseeing",
    "/tottori-drive", "/tougorouiwashi", "/trout-cooking", "/hanabiramenn",
}
TARGET_POST_IDS = (2358, 2350, 2180, 2135, 2157, 2152, 2096, 1939, 1892, 1883)
EXPECTED_COUNTS = {
    "documents": 10,
    "links": 23,
    "delete_blocks": 22,
    "unwrap_anchors": 1,
    "remaining": 0,
}
APPLY_CONFIRMATION = "APPLY-23-LINKS"
HOSTS = {"tsurikue.com", "www.tsurikue.com"}
CUES = ("詳しく", "こちら", "個別記事", "関連記事", "まとめへ", "記事へ", "紹介しています", "で紹介", "感想は")
ANCHOR_RE = re.compile(r"<a\b[^>]*?href\s*=\s*(?P<q>[\"'])(?P<href>.*?)(?P=q)[^>]*>(?P<body>.*?)</a\s*>", re.I | re.S)
WP_P_RE = re.compile(r"(?P<whole><!--\s*wp:paragraph(?:\s+\{.*?\})?\s*-->\s*(?P<html><p\b.*?</p>)\s*<!--\s*/wp:paragraph\s*-->)", re.I | re.S)
WP_LI_RE = re.compile(r"(?P<whole><!--\s*wp:list-item(?:\s+\{.*?\})?\s*-->\s*(?P<html><li\b.*?</li>)\s*<!--\s*/wp:list-item\s*-->)", re.I | re.S)
P_RE = re.compile(r"<p\b[^>]*>.*?</p>", re.I | re.S)
LI_RE = re.compile(r"<li\b[^>]*>.*?</li>", re.I | re.S)
EMPTY_LIST_RE = re.compile(r"<!--\s*wp:list(?:\s+\{.*?\})?\s*-->\s*<ul\b[^>]*>\s*</ul>\s*<!--\s*/wp:list\s*-->", re.I | re.S)
TAG_RE = re.compile(r"<!--.*?-->|<[^>]+>", re.S)
IMG_RE = re.compile(r"<img\b", re.I)


@dataclass
class Action:
    kind: str
    hrefs: list[str]
    before: str
    after: str
    reason: str


@dataclass
class Result:
    original: str
    updated: str
    actions: list[Action] = field(default_factory=list)
    remaining: list[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return sum(len(action.hrefs) for action in self.actions) + len(self.remaining)


@dataclass
class Document:
    post_id: int
    post_type: str
    title: str
    link: str
    content: str


@dataclass
class RunSummary:
    affected_documents: int
    target_links: int
    delete_blocks: int
    unwrap_anchors: int
    remaining: int


def text(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", fragment))).strip()


def path_for(href: str) -> Optional[str]:
    value = html.unescape(href).strip()
    if not value or value.startswith(("#", "mailto:", "tel:", "javascript:")):
        return None
    if value.startswith("//"):
        value = "https:" + value
    parsed = urllib.parse.urlsplit(value)
    if (parsed.scheme or parsed.netloc) and (parsed.hostname or "").lower() not in HOSTS:
        return None
    path = urllib.parse.unquote(parsed.path or "/")
    if not path.startswith("/"):
        path = "/" + path
    path = re.sub(r"/{2,}", "/", path)
    return path.rstrip("/").lower() or "/"


def is_target(href: str) -> bool:
    return path_for(href) in TARGET_PATHS


def anchors(fragment: str):
    return [match for match in ANCHOR_RE.finditer(fragment) if is_target(match.group("href"))]


def unwrap(fragment: str) -> str:
    return ANCHOR_RE.sub(lambda match: match.group("body") if is_target(match.group("href")) else match.group(0), fragment)


def classify(fragment: str, label: str):
    if IMG_RE.search(fragment):
        return "unwrap_anchor", f"{label} contains an image that must be preserved"
    outside = ANCHOR_RE.sub(lambda match: "" if is_target(match.group("href")) else match.group(0), fragment)
    outside_text = text(outside)
    full_text = text(fragment)
    if not outside_text:
        return "delete_block", f"{label} is only a target link"
    if any(cue in outside_text or cue in full_text for cue in CUES):
        return "delete_block", f"{label} is link-navigation copy"
    return "unwrap_anchor", f"{label} contains substantive body text"


def process(content: str, pattern, label: str, actions: list[Action]) -> str:
    def replace(match):
        whole = match.groupdict().get("whole") or match.group(0)
        inner = match.groupdict().get("html") or whole
        found = anchors(inner)
        if not found:
            return whole
        kind, reason = classify(inner, label)
        after = "" if kind == "delete_block" else unwrap(whole)
        actions.append(Action(kind, [item.group("href") for item in found], whole, after, reason))
        return after
    return pattern.sub(replace, content)


def transform(content: str) -> Result:
    actions: list[Action] = []
    updated = process(content, WP_P_RE, "paragraph", actions)
    updated = process(updated, WP_LI_RE, "list item", actions)
    updated = process(updated, P_RE, "paragraph", actions)
    updated = process(updated, LI_RE, "list item", actions)

    def loose(match):
        if not is_target(match.group("href")):
            return match.group(0)
        after = match.group("body")
        actions.append(Action("unwrap_anchor", [match.group("href")], match.group(0), after, "anchor outside a recognized text block"))
        return after

    updated = ANCHOR_RE.sub(loose, updated)
    updated = EMPTY_LIST_RE.sub("", updated)
    updated = re.sub(r"\n{4,}", "\n\n\n", updated)
    return Result(content, updated, actions, [item.group("href") for item in anchors(updated)])


def fetch_xml(path: Path) -> list[Document]:
    ns = {"wp": "http://wordpress.org/export/1.2/", "content": "http://purl.org/rss/1.0/modules/content/"}
    tree = ET.parse(path)
    documents = []
    for item in tree.findall("./channel/item"):
        status = item.findtext("wp:status", namespaces=ns)
        kind = item.findtext("wp:post_type", namespaces=ns)
        if status != "publish" or kind not in {"post", "page"}:
            continue
        documents.append(Document(
            int(item.findtext("wp:post_id", default="0", namespaces=ns)), kind,
            item.findtext("title", default=""), item.findtext("link", default=""),
            item.findtext("content:encoded", default="", namespaces=ns),
        ))
    return documents


def request_json(url: str, *, method: str = "GET", auth_header: str | None = None, payload: dict | None = None) -> dict:
    headers = {"Accept": "application/json", "User-Agent": "tsurikue-dead-link-cleanup/1.0"}
    data = None
    if auth_header:
        headers["Authorization"] = auth_header
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def auth_header(user: str, app_password: str) -> str:
    token = base64.b64encode(f"{user}:{app_password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def endpoint_for(site_url: str, post_id: int) -> str:
    return f"{site_url.rstrip('/')}/wp-json/wp/v2/posts/{post_id}"


def document_from_edit_row(row: dict) -> Document:
    if row.get("status") != "publish":
        raise ValueError(f"Post {row.get('id')} is not published")
    content = (row.get("content") or {}).get("raw")
    if content is None:
        raise ValueError(f"Post {row.get('id')} response did not include content.raw")
    return Document(
        int(row["id"]),
        "post",
        html.unescape((row.get("title") or {}).get("raw") or (row.get("title") or {}).get("rendered", "")),
        row.get("link", ""),
        content,
    )


def fetch_authenticated_posts(site_url: str, user: str, app_password: str) -> list[Document]:
    header = auth_header(user, app_password)
    documents = []
    fields = "id,status,link,title,content"
    for post_id in TARGET_POST_IDS:
        query = urllib.parse.urlencode({"context": "edit", "_fields": fields})
        row = request_json(f"{endpoint_for(site_url, post_id)}?{query}", auth_header=header)
        documents.append(document_from_edit_row(row))
    return documents


def fetch_rest(site_url: str) -> list[Document]:
    documents = []
    for endpoint_name, kind in (("posts", "post"), ("pages", "page")):
        page = 1
        while True:
            query = urllib.parse.urlencode({"status": "publish", "per_page": 100, "page": page, "_fields": "id,link,title,content"})
            request = urllib.request.Request(f"{site_url.rstrip('/')}/wp-json/wp/v2/{endpoint_name}?{query}", headers={"Accept": "application/json", "User-Agent": "tsurikue-dry-run/1.0"}, method="GET")
            with urllib.request.urlopen(request, timeout=30) as response:
                rows = json.loads(response.read().decode("utf-8"))
                total_pages = int(response.headers.get("X-WP-TotalPages", "1"))
            for row in rows:
                documents.append(Document(int(row["id"]), kind, html.unescape((row.get("title") or {}).get("rendered", "")), row.get("link", ""), (row.get("content") or {}).get("rendered", "")))
            if page >= total_pages:
                break
            page += 1
    return documents


def summarize(rows) -> RunSummary:
    affected = [(doc, result) for doc, result in rows if result.actions or result.remaining]
    return RunSummary(
        affected_documents=len(affected),
        target_links=sum(result.count for _, result in affected),
        delete_blocks=sum(a.kind == "delete_block" for _, result in affected for a in result.actions),
        unwrap_anchors=sum(a.kind == "unwrap_anchor" for _, result in affected for a in result.actions),
        remaining=sum(len(result.remaining) for _, result in affected),
    )


def validate_expected(summary: RunSummary) -> None:
    actual = {
        "documents": summary.affected_documents,
        "links": summary.target_links,
        "delete_blocks": summary.delete_blocks,
        "unwrap_anchors": summary.unwrap_anchors,
        "remaining": summary.remaining,
    }
    if actual != EXPECTED_COUNTS:
        raise SystemExit(f"Preflight counts did not match expected values. expected={EXPECTED_COUNTS} actual={actual}")


def write_report(output: Path, rows, source: str, mode: str, apply_status: dict[int, str] | None = None) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "backups").mkdir(exist_ok=True)
    (output / "diffs").mkdir(exist_ok=True)
    affected = [(doc, result) for doc, result in rows if result.actions or result.remaining]
    summary = summarize(rows)
    with (output / "cleanup-summary.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["post_id", "type", "title", "url", "occurrences", "delete_blocks", "unwrap_anchors", "remaining", "apply_status"])
        for doc, result in affected:
            writer.writerow([doc.post_id, doc.post_type, doc.title, doc.link, result.count, sum(a.kind == "delete_block" for a in result.actions), sum(a.kind == "unwrap_anchor" for a in result.actions), len(result.remaining), (apply_status or {}).get(doc.post_id, "not-run")])

    lines = [
        "# つりくえ！不通内部リンク cleanup", "", f"- モード: {mode}", f"- 取得元: {source}",
        f"- 対象記事数: **{summary.affected_documents}**",
        f"- 対象リンク出現数: **{summary.target_links}**",
        f"- 段落・リスト項目ごと削除: **{summary.delete_blocks}**",
        f"- aタグだけ解除: **{summary.unwrap_anchors}**",
        f"- 要確認・残存リンク: **{summary.remaining}**", "",
    ]
    if apply_status:
        lines += ["## apply結果", ""]
        for post_id in TARGET_POST_IDS:
            lines.append(f"- {post_id}: {apply_status.get(post_id, 'not-run')}")
        lines.append("")
    for doc, result in affected:
        name = f"{doc.post_type}-{doc.post_id}"
        (output / "backups" / f"{name}.html").write_text(doc.content, encoding="utf-8")
        diff = "".join(difflib.unified_diff(doc.content.splitlines(keepends=True), result.updated.splitlines(keepends=True), fromfile=f"before/{name}.html", tofile=f"after/{name}.html"))
        (output / "diffs" / f"{name}.diff").write_text(diff, encoding="utf-8")
        lines += [f"## {doc.title}", "", f"- ID: `{doc.post_id}`", f"- URL: {doc.link}", f"- 対象リンク数: {result.count}", ""]
        for index, action in enumerate(result.actions, 1):
            label = "段落・リスト項目ごと削除" if action.kind == "delete_block" else "aタグだけ解除"
            lines += [f"### {index}. {label}", "", f"- 理由: {action.reason}", f"- href: {', '.join(f'`{href}`' for href in action.hrefs)}", "", "変更前:", "```html", action.before.strip(), "```", "", "変更後:", "```html", action.after.strip() or "（削除）", "```", ""]
        if result.remaining:
            lines += ["### 要確認・残存リンク", ""] + [f"- `{href}`" for href in result.remaining] + [""]
    (output / "cleanup-report.md").write_text("\n".join(lines), encoding="utf-8")


def apply_updates(site_url: str, user: str, app_password: str, rows) -> dict[int, str]:
    header = auth_header(user, app_password)
    statuses: dict[int, str] = {}
    for doc, result in rows:
        if not result.actions and not result.remaining:
            statuses[doc.post_id] = "skipped-no-target-links"
            continue
        try:
            request_json(endpoint_for(site_url, doc.post_id), method="POST", auth_header=header, payload={"content": result.updated})
            statuses[doc.post_id] = "updated"
        except Exception as error:
            statuses[doc.post_id] = f"failed: {type(error).__name__}"
    return statuses


def verify_after_apply(site_url: str, user: str, app_password: str) -> RunSummary:
    rows = [(doc, transform(doc.content)) for doc in fetch_authenticated_posts(site_url, user, app_password)]
    summary = summarize(rows)
    if summary.target_links != 0 or summary.remaining != 0:
        raise SystemExit(f"Post-apply verification failed: target_links={summary.target_links} remaining={summary.remaining}")
    return summary


def credentials_from_args(args) -> tuple[str, str]:
    user = args.wp_user or os.environ.get("TSURIKUE_WP_USER")
    app_password = args.wp_app_password or os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not app_password:
        raise SystemExit("WordPress credentials are required for authenticated modes")
    return user, app_password


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--xml", type=Path)
    parser.add_argument("--site-url", default="https://tsurikue.com")
    parser.add_argument("--output-dir", type=Path, default=Path("reports/tsurikue-link-dry-run"))
    parser.add_argument("--mode", choices=("public-dry-run", "authenticated-dry-run", "apply"), default="public-dry-run")
    parser.add_argument("--wp-user")
    parser.add_argument("--wp-app-password")
    parser.add_argument("--apply-confirmation", default="")
    args = parser.parse_args()

    try:
        if args.mode == "apply" and args.apply_confirmation != APPLY_CONFIRMATION:
            raise SystemExit(f"apply mode requires confirmation string {APPLY_CONFIRMATION}")
        if args.xml:
            documents = fetch_xml(args.xml)
            source = f"WordPress XML: {args.xml}"
        elif args.mode in {"authenticated-dry-run", "apply"}:
            user, app_password = credentials_from_args(args)
            documents = fetch_authenticated_posts(args.site_url, user, app_password)
            source = "WordPress REST API authenticated context=edit content.raw"
        else:
            documents = fetch_rest(args.site_url)
            source = "WordPress REST API public rendered HTML"
    except urllib.error.HTTPError as error:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "connection-error.txt").write_text(f"HTTP {error.code}", encoding="utf-8")
        raise
    except Exception as error:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "connection-error.txt").write_text(type(error).__name__, encoding="utf-8")
        raise

    rows = [(doc, transform(doc.content)) for doc in documents]
    summary = summarize(rows)
    apply_status = None
    if args.mode in {"authenticated-dry-run", "apply"}:
        validate_expected(summary)
    if args.mode == "apply":
        user, app_password = credentials_from_args(args)
        apply_status = apply_updates(args.site_url, user, app_password, rows)
        verify_after_apply(args.site_url, user, app_password)
    write_report(args.output_dir, rows, source, args.mode, apply_status)
    print(f"Affected documents: {summary.affected_documents}")
    print(f"Target link occurrences: {summary.target_links}")
    print(f"Delete blocks: {summary.delete_blocks}")
    print(f"Unwrap anchors: {summary.unwrap_anchors}")
    print(f"Remaining target links: {summary.remaining}")
    print(f"Report: {args.output_dir / 'cleanup-report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
