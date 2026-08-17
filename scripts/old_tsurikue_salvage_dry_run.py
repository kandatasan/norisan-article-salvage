#!/usr/bin/env python3
"""Authenticated, GET-only reconciliation for the 46 old Tsurikue articles."""
from __future__ import annotations

import argparse
import base64
import csv
import html
import json
import os
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

MANIFEST_PATH = Path(__file__).with_name("old_tsurikue_targets.json")
ALLOWED_SOURCE = "tsurikue.com"
EXPECTED_TARGETS = 46
USER_AGENT = "old-tsurikue-salvage-dry-run/1.0"
LEXUS_MARKERS = ("lexus", "レクサス", "ux", "nx", "lbx", "lm")


def normalize_title(value: str) -> str:
    value = html.unescape(value)
    value = unicodedata.normalize("NFKC", value).casefold()
    return "".join(character for character in value if character.isalnum())


def load_targets(path: Path = MANIFEST_PATH) -> list[dict[str, Any]]:
    targets = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(targets, list):
        raise ValueError("manifest root must be a list")
    if len(targets) != EXPECTED_TARGETS:
        raise ValueError(f"manifest must contain exactly {EXPECTED_TARGETS} targets")
    slugs = [target["slug"] for target in targets]
    if len(slugs) != len(set(slugs)):
        raise ValueError("manifest contains duplicate slugs")
    if any(target.get("source_site") != ALLOWED_SOURCE for target in targets):
        raise ValueError("manifest contains a non-tsurikue.com target")
    required = {"slug", "title", "source_site", "known_alias_slugs"}
    if any(set(target) != required for target in targets):
        raise ValueError("manifest target schema mismatch")
    if any(not isinstance(target["known_alias_slugs"], list) for target in targets):
        raise ValueError("known_alias_slugs must be a list")
    searchable = lambda target: unicodedata.normalize("NFKC", f"{target['slug']} {target['title']}").casefold()
    lexus = [target for target in targets if any(marker in searchable(target) for marker in LEXUS_MARKERS)]
    if lexus:
        raise ValueError("manifest contains Lexus targets")
    return targets


def basic_auth(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def get_json(url: str, authorization: str) -> tuple[Any, dict[str, str]]:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "Authorization": authorization, "User-Agent": USER_AGENT},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.loads(response.read().decode("utf-8")), dict(response.headers)


def fetch_collection(site_url: str, endpoint: str, authorization: str, **parameters: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        query = urllib.parse.urlencode({**parameters, "per_page": "100", "page": str(page)})
        data, headers = get_json(f"{site_url.rstrip('/')}/wp-json/wp/v2/{endpoint}?{query}", authorization)
        rows.extend(data)
        total_pages = int(headers.get("X-WP-TotalPages", "1"))
        if page >= total_pages:
            return rows
        page += 1


def fetch_live_state(site_url: str, user: str, password: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    authorization = basic_auth(user, password)
    content: list[dict[str, Any]] = []
    fields = "id,slug,status,link,title,type"
    for endpoint in ("posts", "pages"):
        rows = fetch_collection(site_url, endpoint, authorization, context="edit", status="publish,draft", _fields=fields)
        for row in rows:
            row["rest_endpoint"] = endpoint
        content.extend(rows)
    media = fetch_collection(site_url, "media", authorization, context="edit", status="inherit,private", _fields="id,slug,status,source_url,title,media_details")
    return content, media


def raw_title(row: dict[str, Any]) -> str:
    title = row.get("title") or {}
    return html.unescape(title.get("raw") or title.get("rendered") or "")


def reconcile(targets: list[dict[str, Any]], content: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_slug = {row.get("slug", ""): row for row in content}
    by_title: dict[str, list[dict[str, Any]]] = {}
    for row in content:
        normalized = normalize_title(raw_title(row))
        if normalized:
            by_title.setdefault(normalized, []).append(row)

    results = []
    for target in targets:
        match = by_slug.get(target["slug"])
        reason = "exact_slug"
        action = "SKIP_EXISTING"
        duplicate_candidate_count = 0
        if match is None:
            aliases = [by_slug[slug] for slug in target.get("known_alias_slugs", []) if slug in by_slug]
            normalized_target_title = normalize_title(target["title"])
            title_matches = by_title.get(normalized_target_title, []) if normalized_target_title else []
            duplicate_matches = aliases or title_matches
            if duplicate_matches:
                match = duplicate_matches[0]
                action, reason = "SKIP_DUPLICATE", "known_alias_slug" if aliases else "normalized_title"
                duplicate_candidate_count = len(duplicate_matches)
            else:
                action, reason = "CREATE_DRAFT", "no_live_match"
        results.append({
            "target_slug": target["slug"],
            "target_title": target["title"],
            "source_site": target["source_site"],
            "action": action,
            "match_reason": reason,
            "matched_id": match.get("id") if match else None,
            "matched_slug": match.get("slug") if match else None,
            "matched_title": raw_title(match) if match else None,
            "matched_status": match.get("status") if match else None,
            "matched_url": match.get("link") if match else None,
            "matched_endpoint": match.get("rest_endpoint") if match else None,
            "duplicate_candidate_count": duplicate_candidate_count,
        })
    return results


def build_report(targets: list[dict[str, Any]], content: list[dict[str, Any]], media: list[dict[str, Any]]) -> dict[str, Any]:
    results = reconcile(targets, content)
    actions = Counter(row["action"] for row in results)
    statuses = Counter(row.get("status", "unknown") for row in content)
    endpoints = Counter((row.get("rest_endpoint", "unknown"), row.get("status", "unknown")) for row in content)
    return {
        "mode": "authenticated-dry-run",
        "manifest_count": len(targets),
        "lexus_target_count": 0,
        "live_publish_count": statuses["publish"],
        "live_draft_count": statuses["draft"],
        "live_post_publish_count": endpoints[("posts", "publish")],
        "live_post_draft_count": endpoints[("posts", "draft")],
        "live_page_publish_count": endpoints[("pages", "publish")],
        "live_page_draft_count": endpoints[("pages", "draft")],
        "live_media_count": len(media),
        "action_counts": {name: actions[name] for name in ("CREATE_DRAFT", "SKIP_EXISTING", "SKIP_DUPLICATE")},
        "wordpress_write_count": 0,
        "photo_reconciliation": {
            "implemented": False,
            "next_step": "Match normalized legacy filenames to current media, then conservatively compare pHash/dHash, aspect ratio, and surrounding text.",
            "missing_data": "Legacy article bodies, image positions/filenames, and image binaries or hashes are not included in this manifest.",
            "fallback": "Leave 【写真差し込み】 at the original position when no confident existing-media match is available; never upload media.",
        },
        "results": results,
    }


def write_artifacts(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    columns = list(report["results"][0])
    with (output_dir / "result.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(report["results"])
    counts = report["action_counts"]
    lines = [
        "# 旧つりくえ！46記事サルベージ dry-run", "",
        "- mode: authenticated-dry-run",
        f"- manifest_count: **{report['manifest_count']}**",
        f"- lexus_target_count: **{report['lexus_target_count']}**",
        f"- live_publish_count: **{report['live_publish_count']}**",
        f"- live_draft_count: **{report['live_draft_count']}**",
        f"- live_post_publish_count: **{report['live_post_publish_count']}**",
        f"- live_post_draft_count: **{report['live_post_draft_count']}**",
        f"- live_page_publish_count: **{report['live_page_publish_count']}**",
        f"- live_page_draft_count: **{report['live_page_draft_count']}**",
        f"- live_media_count: **{report['live_media_count']}**",
        f"- CREATE_DRAFT: **{counts['CREATE_DRAFT']}**",
        f"- SKIP_EXISTING: **{counts['SKIP_EXISTING']}**",
        f"- SKIP_DUPLICATE: **{counts['SKIP_DUPLICATE']}**",
        f"- wordpress_write_count: **{report['wordpress_write_count']}**", "",
        "| target slug | title | action | match reason | current match |", "|---|---|---|---|---|",
    ]
    for row in report["results"]:
        matched = f"{row['matched_status']} #{row['matched_id']} `{row['matched_slug']}`" if row["matched_id"] else "—"
        lines.append(f"| `{row['target_slug']}` | {row['target_title'].replace('|', '｜')} | {row['action']} | {row['match_reason']} | {matched} |")
    photo = report["photo_reconciliation"]
    lines += ["", "## 写真照合の次工程", "", f"- 実装方針: {photo['next_step']}", f"- 不足データ: {photo['missing_data']}", f"- 不明時: {photo['fallback']}"]
    (output_dir / "result.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-url", default="https://tsurikue.com")
    parser.add_argument("--output-dir", type=Path, default=Path("reports/old-tsurikue-salvage"))
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    args = parser.parse_args()
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")
    targets = load_targets(args.manifest)
    content, media = fetch_live_state(args.site_url, user, password)
    report = build_report(targets, content, media)
    write_artifacts(args.output_dir, report)
    print(json.dumps({key: value for key, value in report.items() if key not in {"results", "photo_reconciliation"}}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
