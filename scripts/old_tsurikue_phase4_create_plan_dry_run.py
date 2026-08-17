#!/usr/bin/env python3
"""Phase 4 Step A: authenticated GET-only WordPress create-plan dry-run.

Freshly regenerates the approved Phase 3.2 reader-polished 46-article artifacts,
then reads current WordPress state and decides whether each target is safe to
create later as a draft. This script has no WordPress write path.
"""
from __future__ import annotations

import argparse
import base64
import csv
import difflib
import hashlib
import html
import json
import os
import re
import tempfile
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

import old_tsurikue_remake_publish_polish_dry_run as final_generator

EXPECTED_TARGETS = 46
EXPECTED_LEXUS = 0
EXPECTED_MATCHED_AVAILABLE = 110
EXPECTED_MATCHED_USED = 105
EXPECTED_MATCHED_REDUNDANT = 5
EXPECTED_PLACEHOLDERS = 28
EXPECTED_OMITTED = 225
EXPECTED_UNRESOLVED = 253
TARGETS_PATH = Path(__file__).with_name("old_tsurikue_targets.json")
USER_AGENT = "old-tsurikue-phase4-create-plan-dry-run/1.0"
SALVAGE_MARKER_PREFIX = "<!-- old-tsurikue-salvage:v1 slug="
TITLE_REVIEW_THRESHOLD = 0.70
COMBINED_TITLE_THRESHOLD = 0.55
COMBINED_SLUG_THRESHOLD = 0.50
CONTENT_CONTAINMENT_THRESHOLD = 0.08
CONTENT_SHINGLE_SIZE = 12


def salvage_marker(slug: str) -> str:
    return f"{SALVAGE_MARKER_PREFIX}{slug} -->"


def normalize_title(value: str) -> str:
    value = html.unescape(value or "")
    value = unicodedata.normalize("NFKC", value).casefold()
    return "".join(ch for ch in value if ch.isalnum())


def visible_text(value: str) -> str:
    value = re.sub(r"<!--.*?-->", " ", value or "", flags=re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", "", value)


def shingles(value: str, size: int = CONTENT_SHINGLE_SIZE) -> set[str]:
    text = visible_text(value)
    if len(text) < size:
        return set()
    return {text[i : i + size] for i in range(len(text) - size + 1)}


def content_containment(left: str, right: str) -> float:
    a = shingles(left)
    b = shingles(right)
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return difflib.SequenceMatcher(None, left, right).ratio()


def raw_title(row: dict[str, Any]) -> str:
    title = row.get("title") or {}
    if isinstance(title, dict):
        return html.unescape(title.get("raw") or title.get("rendered") or "")
    return html.unescape(str(title))


def raw_content(row: dict[str, Any]) -> str:
    content = row.get("content") or {}
    if isinstance(content, dict):
        return content.get("raw") or content.get("rendered") or ""
    return str(content)


def basic_auth(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def get_json(url: str, authorization: str) -> tuple[Any, dict[str, str]]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": authorization,
            "User-Agent": USER_AGENT,
        },
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.loads(response.read().decode("utf-8")), dict(response.headers)


def fetch_collection(
    site_url: str,
    endpoint: str,
    authorization: str,
    **parameters: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        query = urllib.parse.urlencode({**parameters, "per_page": "100", "page": str(page)})
        data, headers = get_json(
            f"{site_url.rstrip('/')}/wp-json/wp/v2/{endpoint}?{query}", authorization
        )
        rows.extend(data)
        total_pages = int(headers.get("X-WP-TotalPages", "1"))
        if page >= total_pages:
            return rows
        page += 1


def fetch_live_state(
    site_url: str, user: str, password: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    authorization = basic_auth(user, password)
    content: list[dict[str, Any]] = []
    fields = "id,slug,status,link,title,type,content"
    for endpoint in ("posts", "pages"):
        rows = fetch_collection(
            site_url,
            endpoint,
            authorization,
            context="edit",
            status="publish,draft",
            _fields=fields,
        )
        for row in rows:
            row["rest_endpoint"] = endpoint
        content.extend(rows)
    media = fetch_collection(
        site_url,
        "media",
        authorization,
        context="edit",
        status="inherit,private",
        _fields="id,status,source_url",
    )
    return content, media


def load_target_manifest(path: Path = TARGETS_PATH) -> list[dict[str, Any]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or len(rows) != EXPECTED_TARGETS:
        raise ValueError("target manifest must contain exactly 46 rows")
    if len({row["slug"] for row in rows}) != EXPECTED_TARGETS:
        raise ValueError("target manifest slugs must be unique")
    return rows


def validate_final_summary(summary: dict[str, Any]) -> None:
    expected = {
        "targets": EXPECTED_TARGETS,
        "lexus_targets": EXPECTED_LEXUS,
        "articles_generated": EXPECTED_TARGETS,
        "matched_images_available": EXPECTED_MATCHED_AVAILABLE,
        "matched_images_used": EXPECTED_MATCHED_USED,
        "matched_images_omitted_redundant": EXPECTED_MATCHED_REDUNDANT,
        "placeholders_retained": EXPECTED_PLACEHOLDERS,
        "unresolved_positions_omitted": EXPECTED_OMITTED,
        "wordpress_write_count": 0,
        "draft_creation_count": 0,
        "media_upload_count": 0,
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            raise ValueError(
                f"final artifact baseline mismatch: {key}={summary.get(key)!r}, expected {value!r}"
            )
    if summary["placeholders_retained"] + summary["unresolved_positions_omitted"] != EXPECTED_UNRESOLVED:
        raise ValueError("final artifact unresolved-photo disposition mismatch")


def generate_fresh_articles() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    with tempfile.TemporaryDirectory(prefix="old-tsurikue-phase4-plan-") as tmp:
        out = Path(tmp) / "final"
        report = final_generator.build(out)
        validate_final_summary(report["summary"])
        paths = sorted((out / "articles").glob("*.json"))
        if len(paths) != EXPECTED_TARGETS:
            raise ValueError("fresh final artifact must contain 46 article JSON files")
        articles = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
        if len({row["slug"] for row in articles}) != EXPECTED_TARGETS:
            raise ValueError("fresh final artifact slugs must be unique")
        return articles, report["summary"]


def canonical_media_path(url: str) -> str:
    parsed = urllib.parse.urlparse(url or "")
    return urllib.parse.unquote(parsed.path).casefold()


def validate_media_references(
    articles: list[dict[str, Any]], media: list[dict[str, Any]]
) -> dict[str, Any]:
    live = {int(row["id"]): row for row in media if row.get("id") is not None}
    errors: list[dict[str, Any]] = []
    checked = 0
    for article in articles:
        ids = list(article.get("matched_media_ids") or [])
        urls = list(article.get("matched_media_source_urls") or [])
        if len(ids) != len(urls):
            errors.append({"slug": article["slug"], "reason": "media_id_url_length_mismatch"})
            continue
        for media_id, expected_url in zip(ids, urls):
            checked += 1
            row = live.get(int(media_id))
            if row is None:
                errors.append(
                    {"slug": article["slug"], "media_id": media_id, "reason": "missing_live_media"}
                )
                continue
            actual_url = row.get("source_url") or ""
            if canonical_media_path(actual_url) != canonical_media_path(expected_url):
                errors.append(
                    {
                        "slug": article["slug"],
                        "media_id": media_id,
                        "reason": "media_url_path_mismatch",
                        "expected_url": expected_url,
                        "actual_url": actual_url,
                    }
                )
    return {
        "confirmed_media_refs_checked": checked,
        "confirmed_media_ref_errors": len(errors),
        "errors": errors,
    }


def best_duplicate_candidate(
    article: dict[str, Any], current: list[dict[str, Any]]
) -> dict[str, Any] | None:
    target_title = normalize_title(article["title"])
    target_slug = article["slug"]
    candidates = []
    for row in current:
        title_ratio = similarity(target_title, normalize_title(raw_title(row)))
        slug_ratio = similarity(target_slug, row.get("slug") or "")
        containment = content_containment(article.get("content") or "", raw_content(row))
        is_review = (
            title_ratio >= TITLE_REVIEW_THRESHOLD
            or containment >= CONTENT_CONTAINMENT_THRESHOLD
            or (
                title_ratio >= COMBINED_TITLE_THRESHOLD
                and slug_ratio >= COMBINED_SLUG_THRESHOLD
            )
        )
        if not is_review:
            continue
        score = max(title_ratio, containment, (title_ratio + slug_ratio) / 2)
        candidates.append(
            {
                "row": row,
                "score": score,
                "title_similarity": title_ratio,
                "slug_similarity": slug_ratio,
                "content_containment": containment,
            }
        )
    if not candidates:
        return None
    candidates.sort(key=lambda item: item["score"], reverse=True)
    return candidates[0]


def reconcile(
    articles: list[dict[str, Any]],
    target_manifest: list[dict[str, Any]],
    current: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    manifest_by_slug = {row["slug"]: row for row in target_manifest}
    by_slug: dict[str, list[dict[str, Any]]] = {}
    by_title: dict[str, list[dict[str, Any]]] = {}
    for row in current:
        by_slug.setdefault(row.get("slug") or "", []).append(row)
        normalized = normalize_title(raw_title(row))
        if normalized:
            by_title.setdefault(normalized, []).append(row)

    results: list[dict[str, Any]] = []
    for article in sorted(articles, key=lambda row: row["slug"]):
        slug = article["slug"]
        title = article["title"]
        marker = salvage_marker(slug)
        manifest = manifest_by_slug.get(slug)
        if manifest is None:
            raise ValueError(f"article slug is absent from target manifest: {slug}")
        if manifest["title"] != title:
            raise ValueError(f"article title differs from approved target manifest: {slug}")

        action = "CREATE_DRAFT"
        reason = "no_current_collision"
        match: dict[str, Any] | None = None
        duplicate_details: dict[str, Any] | None = None

        exact_slug = by_slug.get(slug, [])
        if exact_slug:
            action, reason, match = "SKIP_EXISTING", "exact_slug", exact_slug[0]
        else:
            alias_matches = [
                row
                for alias in manifest.get("known_alias_slugs", [])
                for row in by_slug.get(alias, [])
            ]
            if alias_matches:
                action, reason, match = "SKIP_EXISTING", "known_alias_slug", alias_matches[0]
            else:
                marker_matches = [row for row in current if marker in raw_content(row)]
                if marker_matches:
                    action, reason, match = "SKIP_EXISTING", "salvage_marker", marker_matches[0]
                else:
                    exact_titles = by_title.get(normalize_title(title), [])
                    if exact_titles:
                        action, reason, match = "SKIP_EXISTING", "normalized_title", exact_titles[0]
                    else:
                        duplicate_details = best_duplicate_candidate(article, current)
                        if duplicate_details:
                            action = "REVIEW_DUPLICATE"
                            reason = "semantic_similarity"
                            match = duplicate_details["row"]

        content = article.get("content") or ""
        planned_content = marker + "\n" + content
        result = {
            "target_slug": slug,
            "target_title": title,
            "action": action,
            "reason": reason,
            "matched_id": match.get("id") if match else None,
            "matched_slug": match.get("slug") if match else None,
            "matched_title": raw_title(match) if match else None,
            "matched_status": match.get("status") if match else None,
            "matched_endpoint": match.get("rest_endpoint") if match else None,
            "matched_url": match.get("link") if match else None,
            "title_similarity": round(duplicate_details["title_similarity"], 6)
            if duplicate_details
            else None,
            "slug_similarity": round(duplicate_details["slug_similarity"], 6)
            if duplicate_details
            else None,
            "content_containment": round(duplicate_details["content_containment"], 6)
            if duplicate_details
            else None,
            "salvage_marker": marker,
            "artifact_content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "planned_content_sha256": hashlib.sha256(planned_content.encode("utf-8")).hexdigest(),
            "matched_media_count": len(article.get("matched_media_ids") or []),
            "placeholder_count": len(article.get("placeholders") or []),
            "omitted_photo_count": len(article.get("omitted_photo_positions") or []),
        }
        results.append(result)
    return results


def build_report(
    articles: list[dict[str, Any]],
    final_summary: dict[str, Any],
    target_manifest: list[dict[str, Any]],
    current: list[dict[str, Any]],
    media: list[dict[str, Any]],
) -> dict[str, Any]:
    media_validation = validate_media_references(articles, media)
    if media_validation["confirmed_media_ref_errors"]:
        raise ValueError(
            f"live media validation failed: {media_validation['confirmed_media_ref_errors']} errors"
        )
    results = reconcile(articles, target_manifest, current)
    actions = Counter(row["action"] for row in results)
    statuses = Counter(row.get("status", "unknown") for row in current)
    endpoints = Counter(
        (row.get("rest_endpoint", "unknown"), row.get("status", "unknown")) for row in current
    )
    return {
        "mode": "authenticated-phase4-create-plan-get-only",
        "targets": EXPECTED_TARGETS,
        "lexus_targets": 0,
        "final_artifact_summary": final_summary,
        "live_publish_count": statuses["publish"],
        "live_draft_count": statuses["draft"],
        "live_post_publish_count": endpoints[("posts", "publish")],
        "live_post_draft_count": endpoints[("posts", "draft")],
        "live_page_publish_count": endpoints[("pages", "publish")],
        "live_page_draft_count": endpoints[("pages", "draft")],
        "live_media_count": len(media),
        "media_validation": media_validation,
        "action_counts": {
            "CREATE_DRAFT": actions["CREATE_DRAFT"],
            "SKIP_EXISTING": actions["SKIP_EXISTING"],
            "REVIEW_DUPLICATE": actions["REVIEW_DUPLICATE"],
        },
        "wordpress_write_count": 0,
        "draft_creation_count": 0,
        "media_upload_count": 0,
        "results": results,
    }


def write_artifacts(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "plan.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    rows = report["results"]
    with (output_dir / "plan.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    counts = report["action_counts"]
    mv = report["media_validation"]
    lines = [
        "# Phase 4 Step A：WordPress下書き作成計画 dry-run",
        "",
        f"- mode: `{report['mode']}`",
        f"- targets: **{report['targets']}**",
        f"- Lexus targets: **{report['lexus_targets']}**",
        f"- live publish / draft: **{report['live_publish_count']} / {report['live_draft_count']}**",
        f"- live posts publish / draft: **{report['live_post_publish_count']} / {report['live_post_draft_count']}**",
        f"- live pages publish / draft: **{report['live_page_publish_count']} / {report['live_page_draft_count']}**",
        f"- live media: **{report['live_media_count']}**",
        f"- confirmed media refs checked / errors: **{mv['confirmed_media_refs_checked']} / {mv['confirmed_media_ref_errors']}**",
        f"- CREATE_DRAFT: **{counts['CREATE_DRAFT']}**",
        f"- SKIP_EXISTING: **{counts['SKIP_EXISTING']}**",
        f"- REVIEW_DUPLICATE: **{counts['REVIEW_DUPLICATE']}**",
        f"- WordPress writes / drafts / media uploads: **0 / 0 / 0**",
        "",
        "| slug | title | action | reason | current match | similarity |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        matched = (
            f"{row['matched_status']} #{row['matched_id']} `{row['matched_slug']}`"
            if row["matched_id"]
            else "—"
        )
        similarity_text = "—"
        if row["action"] == "REVIEW_DUPLICATE":
            similarity_text = (
                f"title {row['title_similarity']:.3f} / slug {row['slug_similarity']:.3f} / "
                f"content {row['content_containment']:.3f}"
            )
        title = row["target_title"].replace("|", "｜")
        lines.append(
            f"| `{row['target_slug']}` | {title} | {row['action']} | {row['reason']} | {matched} | {similarity_text} |"
        )
    (output_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-url", default="https://tsurikue.com")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/old-tsurikue-phase4-create-plan-dry-run"),
    )
    args = parser.parse_args()
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")
    articles, final_summary = generate_fresh_articles()
    manifest = load_target_manifest()
    current, media = fetch_live_state(args.site_url, user, password)
    report = build_report(articles, final_summary, manifest, current, media)
    write_artifacts(args.output_dir, report)
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "results"},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
