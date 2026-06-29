#!/usr/bin/env python3
"""Safely clean the second batch of stale internal links on tsurikue.com.

The authenticated modes operate on eight known published documents only:
six posts and two pages. Apply mode writes preflight backups before the first
WordPress update and rolls back already-updated documents if a later update
fails.
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

DEAD_PATHS = {
    "/hiroshima-hajimarinoterasu",
    "/tanoshiiumiasobi",
    "/ginnjoura-men",
    "/matsuura",
    "/ra-tei",
    "/totoya-iiyo",
    "/matubagani",
    "/sayori",
}
OLD_CONTACT_PATH = "/contact"
CONTACT_REPLACEMENT = "https://tsurikue.com/contact-form/"
TARGET_DOCUMENTS = {
    1887: "posts",
    1892: "posts",
    1939: "posts",
    2075: "posts",
    2096: "posts",
    2115: "posts",
    1970: "pages",
    1973: "pages",
}
EXPECTED_COUNTS = {
    "documents": 8,
    "occurrences": 23,
    "delete_blocks": 18,
    "unwrap_anchors": 3,
    "replace_links": 2,
    "orphan_paragraphs": 11,
    "remaining": 0,
}
APPLY_CONFIRMATION = "APPLY-ROUND2-23-LINKS"
HOSTS = {"tsurikue.com", "www.tsurikue.com"}

SUBSTANTIVE_PARAGRAPHS = {
    "らーめんまつうらは、ガツンと濃厚な魚介が特徴のお店です。",
    "ラーメン亭・民都は、西条町下見にあるラーメン屋さんです。",
    "らー亭のラーメンは、九州熊本の味千ラーメン。",
}

ORPHAN_PARAGRAPHS = {
    1887: {
        "ハジマリノテラスの詳しい体験はこちら",
        "海遊び・貝採り系の記事はこちら",
    },
    1892: {
        "まつうらの詳しい体験はこちら",
        "民都の詳しい体験はこちら",
        "らー亭の思い出はこちら",
        "次のラーメンへ",
    },
    1939: {
        "宿の詳しい体験はこちら",
        "次の冒険へ",
    },
    2075: {
        "江田島旅の入口に寄ったハジマリノテラスの思い出はこちらです。",
    },
    2096: {
        "海辺で釣りをした時の様子はこちらです。",
    },
    2115: {
        "江田島旅の入口として立ち寄りやすいハジマリノテラスの記事はこちらです。",
    },
}

ANCHOR_RE = re.compile(
    r"<a\b[^>]*?href\s*=\s*(?P<q>[\"'])(?P<href>.*?)(?P=q)[^>]*>(?P<body>.*?)</a\s*>",
    re.I | re.S,
)
WP_P_RE = re.compile(
    r"(?P<whole><!--\s*wp:paragraph(?:\s+\{.*?\})?\s*-->\s*(?P<html><p\b.*?</p>)\s*<!--\s*/wp:paragraph\s*-->)",
    re.I | re.S,
)
WP_LI_RE = re.compile(
    r"(?P<whole><!--\s*wp:list-item(?:\s+\{.*?\})?\s*-->\s*(?P<html><li\b.*?</li>)\s*<!--\s*/wp:list-item\s*-->)",
    re.I | re.S,
)
P_RE = re.compile(r"<p\b[^>]*>.*?</p>", re.I | re.S)
LI_RE = re.compile(r"<li\b[^>]*>.*?</li>", re.I | re.S)
EMPTY_LIST_RE = re.compile(
    r"<!--\s*wp:list(?:\s+\{.*?\})?\s*-->\s*<ul\b[^>]*>\s*</ul>\s*<!--\s*/wp:list\s*-->",
    re.I | re.S,
)
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
    def occurrence_count(self) -> int:
        return sum(len(action.hrefs) for action in self.actions) + len(self.remaining)


@dataclass
class Document:
    post_id: int
    endpoint_name: str
    title: str
    link: str
    content: str


@dataclass
class RunSummary:
    affected_documents: int
    occurrences: int
    delete_blocks: int
    unwrap_anchors: int
    replace_links: int
    orphan_paragraphs: int
    remaining: int


def visible_text(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", fragment))).strip()


def normalized_path(href: str) -> Optional[str]:
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


def is_dead(href: str) -> bool:
    return normalized_path(href) in DEAD_PATHS


def is_old_contact(href: str) -> bool:
    return normalized_path(href) == OLD_CONTACT_PATH


def stale_anchors(fragment: str):
    return [
        match
        for match in ANCHOR_RE.finditer(fragment)
        if is_dead(match.group("href")) or is_old_contact(match.group("href"))
    ]


def replace_contact_anchors(fragment: str) -> str:
    def replace(match):
        if not is_old_contact(match.group("href")):
            return match.group(0)
        before = match.group(0)
        href = match.group("href")
        return before.replace(href, CONTACT_REPLACEMENT, 1)

    return ANCHOR_RE.sub(replace, fragment)


def unwrap_dead_anchors(fragment: str) -> str:
    return ANCHOR_RE.sub(
        lambda match: match.group("body") if is_dead(match.group("href")) else match.group(0),
        fragment,
    )


def process_blocks(content: str, pattern, label: str, actions: list[Action]) -> str:
    def replace(match):
        whole = match.groupdict().get("whole") or match.group(0)
        inner = match.groupdict().get("html") or whole
        found = stale_anchors(inner)
        if not found:
            return whole

        contact = [item for item in found if is_old_contact(item.group("href"))]
        dead = [item for item in found if is_dead(item.group("href"))]
        after = whole

        if contact:
            before = after
            after = replace_contact_anchors(after)
            actions.append(
                Action(
                    "replace_link",
                    [item.group("href") for item in contact],
                    before,
                    after,
                    "replace the obsolete contact URL with the published contact form",
                )
            )

        if not dead:
            return after

        if IMG_RE.search(inner):
            before = after
            after = unwrap_dead_anchors(after)
            actions.append(
                Action(
                    "unwrap_anchor",
                    [item.group("href") for item in dead],
                    before,
                    after,
                    f"{label} contains an image that must be preserved",
                )
            )
            return after

        full_text = visible_text(inner)
        compact_text = re.sub(r"\s+", "", full_text)
        if label == "paragraph" and compact_text in SUBSTANTIVE_PARAGRAPHS:
            before = after
            after = unwrap_dead_anchors(after)
            actions.append(
                Action(
                    "unwrap_anchor",
                    [item.group("href") for item in dead],
                    before,
                    after,
                    "paragraph contains substantive body text",
                )
            )
            return after

        actions.append(
            Action(
                "delete_block",
                [item.group("href") for item in dead],
                whole,
                "",
                f"{label} is navigation copy for an unpublished page",
            )
        )
        return ""

    return pattern.sub(replace, content)


def remove_orphan_paragraphs(content: str, post_id: int, actions: list[Action]) -> str:
    targets = ORPHAN_PARAGRAPHS.get(post_id, set())
    if not targets:
        return content

    def replace(match):
        whole = match.groupdict().get("whole") or match.group(0)
        inner = match.groupdict().get("html") or whole
        label = visible_text(inner)
        if label not in targets:
            return whole
        actions.append(
            Action(
                "delete_orphan_paragraph",
                [],
                whole,
                "",
                "standalone label became meaningless after its dead-link block was removed",
            )
        )
        return ""

    return WP_P_RE.sub(replace, content)


def transform(content: str, post_id: int) -> Result:
    actions: list[Action] = []
    updated = process_blocks(content, WP_P_RE, "paragraph", actions)
    updated = process_blocks(updated, WP_LI_RE, "list item", actions)
    updated = process_blocks(updated, P_RE, "paragraph", actions)
    updated = process_blocks(updated, LI_RE, "list item", actions)
    updated = EMPTY_LIST_RE.sub("", updated)
    updated = remove_orphan_paragraphs(updated, post_id, actions)
    updated = re.sub(r"\n{4,}", "\n\n\n", updated)
    remaining = [item.group("href") for item in stale_anchors(updated)]
    return Result(content, updated, actions, remaining)


def request_json(
    url: str,
    *,
    method: str = "GET",
    auth_header: str | None = None,
    payload: dict | None = None,
) -> dict:
    headers = {"Accept": "application/json", "User-Agent": "tsurikue-round2-link-cleanup/1.0"}
    data = None
    if auth_header:
        headers["Authorization"] = auth_header
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def make_auth_header(user: str, app_password: str) -> str:
    token = base64.b64encode(f"{user}:{app_password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def endpoint_for(site_url: str, endpoint_name: str, post_id: int) -> str:
    return f"{site_url.rstrip('/')}/wp-json/wp/v2/{endpoint_name}/{post_id}"


def document_from_edit_row(row: dict, endpoint_name: str) -> Document:
    if row.get("status") != "publish":
        raise ValueError(f"Document {row.get('id')} is not published")
    content = (row.get("content") or {}).get("raw")
    if content is None:
        raise ValueError(f"Document {row.get('id')} response did not include content.raw")
    return Document(
        int(row["id"]),
        endpoint_name,
        html.unescape((row.get("title") or {}).get("raw") or (row.get("title") or {}).get("rendered", "")),
        row.get("link", ""),
        content,
    )


def fetch_authenticated_documents(site_url: str, user: str, app_password: str) -> list[Document]:
    header = make_auth_header(user, app_password)
    documents = []
    fields = "id,status,link,title,content"
    for post_id, endpoint_name in TARGET_DOCUMENTS.items():
        query = urllib.parse.urlencode({"context": "edit", "_fields": fields})
        row = request_json(
            f"{endpoint_for(site_url, endpoint_name, post_id)}?{query}",
            auth_header=header,
        )
        documents.append(document_from_edit_row(row, endpoint_name))
    return documents


def fetch_xml(path: Path) -> list[Document]:
    ns = {
        "wp": "http://wordpress.org/export/1.2/",
        "content": "http://purl.org/rss/1.0/modules/content/",
    }
    tree = ET.parse(path)
    documents = []
    endpoint_for_type = {"post": "posts", "page": "pages"}
    for item in tree.findall("./channel/item"):
        post_id = int(item.findtext("wp:post_id", default="0", namespaces=ns))
        post_type = item.findtext("wp:post_type", namespaces=ns)
        status = item.findtext("wp:status", namespaces=ns)
        if post_id not in TARGET_DOCUMENTS or status != "publish" or post_type not in endpoint_for_type:
            continue
        documents.append(
            Document(
                post_id,
                endpoint_for_type[post_type],
                item.findtext("title", default=""),
                item.findtext("link", default=""),
                item.findtext("content:encoded", default="", namespaces=ns),
            )
        )
    return documents


def summarize(rows) -> RunSummary:
    affected = [(doc, result) for doc, result in rows if result.actions or result.remaining]
    return RunSummary(
        affected_documents=len(affected),
        occurrences=sum(result.occurrence_count for _, result in affected),
        delete_blocks=sum(
            action.kind == "delete_block"
            for _, result in affected
            for action in result.actions
        ),
        unwrap_anchors=sum(
            action.kind == "unwrap_anchor"
            for _, result in affected
            for action in result.actions
        ),
        replace_links=sum(
            action.kind == "replace_link"
            for _, result in affected
            for action in result.actions
        ),
        orphan_paragraphs=sum(
            action.kind == "delete_orphan_paragraph"
            for _, result in affected
            for action in result.actions
        ),
        remaining=sum(len(result.remaining) for _, result in affected),
    )


def validate_expected(summary: RunSummary) -> None:
    actual = {
        "documents": summary.affected_documents,
        "occurrences": summary.occurrences,
        "delete_blocks": summary.delete_blocks,
        "unwrap_anchors": summary.unwrap_anchors,
        "replace_links": summary.replace_links,
        "orphan_paragraphs": summary.orphan_paragraphs,
        "remaining": summary.remaining,
    }
    if actual != EXPECTED_COUNTS:
        raise SystemExit(
            f"Preflight counts did not match expected values. expected={EXPECTED_COUNTS} actual={actual}"
        )


def write_report(
    output: Path,
    rows,
    source: str,
    mode: str,
    apply_status: dict[int, str] | None = None,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "backups").mkdir(exist_ok=True)
    (output / "diffs").mkdir(exist_ok=True)
    affected = [(doc, result) for doc, result in rows if result.actions or result.remaining]
    summary = summarize(rows)

    with (output / "cleanup-summary.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "post_id",
                "endpoint",
                "title",
                "url",
                "occurrences",
                "delete_blocks",
                "unwrap_anchors",
                "replace_links",
                "orphan_paragraphs",
                "remaining",
                "apply_status",
            ]
        )
        for doc, result in affected:
            writer.writerow(
                [
                    doc.post_id,
                    doc.endpoint_name,
                    doc.title,
                    doc.link,
                    result.occurrence_count,
                    sum(a.kind == "delete_block" for a in result.actions),
                    sum(a.kind == "unwrap_anchor" for a in result.actions),
                    sum(a.kind == "replace_link" for a in result.actions),
                    sum(a.kind == "delete_orphan_paragraph" for a in result.actions),
                    len(result.remaining),
                    (apply_status or {}).get(doc.post_id, "not-run"),
                ]
            )

    lines = [
        "# つりくえ！第2回 不通内部リンク cleanup",
        "",
        f"- モード: {mode}",
        f"- 取得元: {source}",
        f"- 対象文書数: **{summary.affected_documents}**",
        f"- 対象リンク出現数: **{summary.occurrences}**",
        f"- 段落・リスト項目ごと削除: **{summary.delete_blocks}**",
        f"- aタグだけ解除: **{summary.unwrap_anchors}**",
        f"- お問い合わせURL差し替え: **{summary.replace_links}**",
        f"- 孤立した案内段落を削除: **{summary.orphan_paragraphs}**",
        f"- 要確認・残存リンク: **{summary.remaining}**",
        "",
    ]
    if apply_status:
        lines += ["## apply結果", ""]
        for post_id in TARGET_DOCUMENTS:
            lines.append(f"- {post_id}: {apply_status.get(post_id, 'not-run')}")
        lines.append("")

    for doc, result in affected:
        name = f"{doc.endpoint_name[:-1]}-{doc.post_id}"
        (output / "backups" / f"{name}.html").write_text(doc.content, encoding="utf-8")
        diff = "".join(
            difflib.unified_diff(
                doc.content.splitlines(keepends=True),
                result.updated.splitlines(keepends=True),
                fromfile=f"before/{name}.html",
                tofile=f"after/{name}.html",
            )
        )
        (output / "diffs" / f"{name}.diff").write_text(diff, encoding="utf-8")
        lines += [
            f"## {doc.title}",
            "",
            f"- ID: `{doc.post_id}`",
            f"- REST endpoint: `{doc.endpoint_name}`",
            f"- URL: {doc.link}",
            f"- 対象リンク数: {result.occurrence_count}",
            "",
        ]
        for index, action in enumerate(result.actions, 1):
            labels = {
                "delete_block": "段落・リスト項目ごと削除",
                "unwrap_anchor": "aタグだけ解除",
                "replace_link": "リンク先を差し替え",
                "delete_orphan_paragraph": "孤立した案内段落を削除",
            }
            lines += [
                f"### {index}. {labels[action.kind]}",
                "",
                f"- 理由: {action.reason}",
                f"- href: {', '.join(f'`{href}`' for href in action.hrefs) if action.hrefs else 'なし'}",
                "",
                "変更前:",
                "```html",
                action.before.strip(),
                "```",
                "",
                "変更後:",
                "```html",
                action.after.strip() or "（削除）",
                "```",
                "",
            ]
        if result.remaining:
            lines += ["### 要確認・残存リンク", ""]
            lines += [f"- `{href}`" for href in result.remaining]
            lines.append("")

    (output / "cleanup-report.md").write_text("\n".join(lines), encoding="utf-8")


def apply_updates_with_rollback(
    site_url: str,
    user: str,
    app_password: str,
    rows,
) -> dict[int, str]:
    header = make_auth_header(user, app_password)
    statuses: dict[int, str] = {}
    updated_docs: list[Document] = []

    try:
        for doc, result in rows:
            if not result.actions and not result.remaining:
                statuses[doc.post_id] = "skipped-no-target-links"
                continue
            request_json(
                endpoint_for(site_url, doc.endpoint_name, doc.post_id),
                method="POST",
                auth_header=header,
                payload={"content": result.updated},
            )
            statuses[doc.post_id] = "updated"
            updated_docs.append(doc)
    except Exception as error:
        statuses[doc.post_id] = f"failed: {type(error).__name__}"
        rollback_errors = []
        for old_doc in reversed(updated_docs):
            try:
                request_json(
                    endpoint_for(site_url, old_doc.endpoint_name, old_doc.post_id),
                    method="POST",
                    auth_header=header,
                    payload={"content": old_doc.content},
                )
                statuses[old_doc.post_id] = "rolled-back"
            except Exception as rollback_error:
                statuses[old_doc.post_id] = f"rollback-failed: {type(rollback_error).__name__}"
                rollback_errors.append(old_doc.post_id)
        if rollback_errors:
            raise RuntimeError(
                f"Update failed and rollback also failed for IDs {rollback_errors}"
            ) from error
        raise RuntimeError("Update failed; all earlier updates were rolled back") from error

    return statuses


def verify_after_apply(site_url: str, user: str, app_password: str) -> None:
    documents = fetch_authenticated_documents(site_url, user, app_password)
    rows = [(doc, transform(doc.content, doc.post_id)) for doc in documents]
    summary = summarize(rows)
    if (
        summary.occurrences != 0
        or summary.orphan_paragraphs != 0
        or summary.remaining != 0
    ):
        raise SystemExit(
            "Post-apply verification failed: "
            f"occurrences={summary.occurrences} "
            f"orphan_paragraphs={summary.orphan_paragraphs} "
            f"remaining={summary.remaining}"
        )


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
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/tsurikue-round2-link-cleanup"),
    )
    parser.add_argument(
        "--mode",
        choices=("xml-dry-run", "authenticated-dry-run", "apply"),
        default="xml-dry-run",
    )
    parser.add_argument("--wp-user")
    parser.add_argument("--wp-app-password")
    parser.add_argument("--apply-confirmation", default="")
    args = parser.parse_args()

    try:
        if args.mode == "apply" and args.apply_confirmation != APPLY_CONFIRMATION:
            raise SystemExit(
                f"apply mode requires confirmation string {APPLY_CONFIRMATION}"
            )
        if args.xml:
            documents = fetch_xml(args.xml)
            source = f"WordPress XML: {args.xml}"
        elif args.mode in {"authenticated-dry-run", "apply"}:
            user, app_password = credentials_from_args(args)
            documents = fetch_authenticated_documents(args.site_url, user, app_password)
            source = "WordPress REST API authenticated context=edit content.raw"
        else:
            raise SystemExit("xml-dry-run requires --xml")
    except urllib.error.HTTPError as error:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "connection-error.txt").write_text(
            f"HTTP {error.code}", encoding="utf-8"
        )
        raise
    except Exception as error:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "connection-error.txt").write_text(
            type(error).__name__, encoding="utf-8"
        )
        raise

    rows = [(doc, transform(doc.content, doc.post_id)) for doc in documents]
    summary = summarize(rows)
    if args.mode in {"authenticated-dry-run", "apply"} or args.xml:
        validate_expected(summary)

    apply_status = None
    if args.mode == "apply":
        # Critical safety property: write all original raw-content backups before
        # making the first WordPress POST.
        write_report(args.output_dir, rows, source, "apply-preflight")
        user, app_password = credentials_from_args(args)
        apply_status = apply_updates_with_rollback(
            args.site_url, user, app_password, rows
        )
        verify_after_apply(args.site_url, user, app_password)

    write_report(args.output_dir, rows, source, args.mode, apply_status)
    print(f"Affected documents: {summary.affected_documents}")
    print(f"Target link occurrences: {summary.occurrences}")
    print(f"Delete blocks: {summary.delete_blocks}")
    print(f"Unwrap anchors: {summary.unwrap_anchors}")
    print(f"Replace links: {summary.replace_links}")
    print(f"Delete orphan paragraphs: {summary.orphan_paragraphs}")
    print(f"Remaining stale links: {summary.remaining}")
    print(f"Report: {args.output_dir / 'cleanup-report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
