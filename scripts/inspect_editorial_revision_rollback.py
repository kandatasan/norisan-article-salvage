#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

SITE_URL = "https://tsurikue.com"
USER_AGENT = "tsurikue-editorial-rollback-inspector/2.0"
REPORT_ROOT = Path("reports/editorial-rollback-inspect")


def auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def get_json(url: str, authorization: str):
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": authorization,
            "User-Agent": USER_AGENT,
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode("utf-8")), dict(r.headers)


def raw_field(row, key):
    value = row.get(key) or {}
    if isinstance(value, dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)


def media_ids(content: str) -> list[int]:
    result: list[int] = []
    for match in re.finditer(r"wp-image-(\d+)|\"id\"\s*:\s*(\d+)", content):
        media_id = int(match.group(1) or match.group(2))
        if media_id not in result:
            result.append(media_id)
    return result


def text_preview(content: str, limit: int = 220) -> str:
    text = re.sub(r"<!--.*?-->", " ", content, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def inspect(config_path: Path):
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")
    authorization = auth_header(user, password)

    query = urllib.parse.urlencode(
        {"context": "edit", "_fields": "id,slug,status,title,content,featured_media"}
    )
    post, _headers = get_json(
        f"{SITE_URL}/wp-json/wp/v2/posts/{cfg['post_id']}?{query}", authorization
    )
    current_content = raw_field(post, "content")
    current_title = html.unescape(raw_field(post, "title"))
    current_sha = hashlib.sha256(current_content.encode()).hexdigest()

    if post.get("id") != cfg["post_id"] or post.get("slug") != cfg["slug"]:
        raise RuntimeError("target id/slug mismatch")
    if post.get("status") != "draft":
        raise RuntimeError("target is not draft")
    if current_title != cfg["current_title"]:
        raise RuntimeError(f"current title mismatch: {current_title!r}")
    if current_sha != cfg["current_content_sha256"]:
        raise RuntimeError(f"current content sha mismatch: {current_sha}")

    revision_query = urllib.parse.urlencode(
        {"context": "edit", "per_page": "100", "_fields": "id,parent,date,title,content"}
    )
    revisions, _headers = get_json(
        f"{SITE_URL}/wp-json/wp/v2/posts/{cfg['post_id']}/revisions?{revision_query}",
        authorization,
    )

    snippets = list(cfg.get("inspect_snippets") or [])
    rows = []
    for revision in revisions:
        content = raw_field(revision, "content")
        title = html.unescape(raw_field(revision, "title"))
        snippet_matches = {snippet: (snippet in content) for snippet in snippets}
        rows.append(
            {
                "revision_id": revision.get("id"),
                "date": revision.get("date") or "",
                "title": title,
                "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
                "content_length": len(content),
                "media_ids": media_ids(content),
                "has_salvage_marker": cfg["salvage_marker"] in content,
                "has_editorial_marker": cfg["editorial_marker"] in content,
                "is_restore_title": title == cfg["restore_title"],
                "snippet_matches": snippet_matches,
                "matched_snippet_count": sum(snippet_matches.values()),
                "preview": text_preview(content),
            }
        )

    rows.sort(key=lambda item: (item["date"], int(item["revision_id"] or 0)), reverse=True)
    report = {
        "mode": "READ_ONLY",
        "wordpress_write_count": 0,
        "post_id": post.get("id"),
        "slug": post.get("slug"),
        "status": post.get("status"),
        "current_title": current_title,
        "current_featured_media": int(post.get("featured_media") or 0),
        "current_content_sha256": current_sha,
        "revision_count": len(rows),
        "revisions": rows,
    }

    out = REPORT_ROOT / cfg["slug"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    lines = [
        f"# {cfg['slug']} rollback revision inspection v2",
        "",
        "- mode: **READ ONLY**",
        "- wordpress_write_count: **0**",
        f"- post_id: **{report['post_id']}**",
        f"- status: **{report['status']}**",
        f"- current_title: {report['current_title']}",
        f"- current_featured_media: **{report['current_featured_media']}**",
        f"- current_content_sha256: `{current_sha}`",
        f"- revision_count: **{len(rows)}**",
        "",
        "## Revisions (newest first)",
    ]
    if not rows:
        lines.extend(["(none)", ""])
    for index, row in enumerate(rows, 1):
        ids = ", ".join(map(str, row["media_ids"])) or "none"
        matched = [key for key, value in row["snippet_matches"].items() if value]
        lines.extend(
            [
                f"### {index}. revision #{row['revision_id']}",
                f"- date: {row['date']}",
                f"- title: {row['title']}",
                f"- content_length: **{row['content_length']}**",
                f"- content_sha256: `{row['content_sha256']}`",
                f"- media_ids: **{ids}**",
                f"- has_salvage_marker: **{row['has_salvage_marker']}**",
                f"- has_editorial_marker: **{row['has_editorial_marker']}**",
                f"- is_restore_title: **{row['is_restore_title']}**",
                f"- matched_snippet_count: **{row['matched_snippet_count']}/{len(snippets)}**",
                f"- matched_snippets: {' | '.join(matched) if matched else '(none)'}",
                f"- preview: {row['preview'] or '(empty)'}",
                "",
            ]
        )

    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    inspect(Path(args.config))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
