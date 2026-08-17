#!/usr/bin/env python3
"""Phase 4 Step B: create-only WordPress draft apply.

This is intentionally narrow: fresh preflight via the approved Phase 4 Step A
planner, POST only CREATE_DRAFT targets, verify each result is still draft, and
never update/delete/upload media.
"""
from __future__ import annotations

import argparse
import base64
import csv
import html
import json
import os
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

import old_tsurikue_phase4_create_plan_dry_run as planner

CONFIRMATION = "CREATE_OLD_TSURIKUE_DRAFTS"
MANUAL_EXCLUSIONS = {"aoriika-cooking"}
EXPECTED_TARGETS = 46
EXPECTED_CREATABLE_OR_EXISTING = 45
USER_AGENT = "old-tsurikue-phase4-create-drafts-apply-once/1.0"


def basic_auth(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def post_json(url: str, authorization: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": authorization,
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def get_post(site_url: str, post_id: int, authorization: str) -> dict[str, Any]:
    query = urllib.parse.urlencode(
        {"context": "edit", "_fields": "id,slug,status,link,title,content"}
    )
    data, _headers = planner.get_json(
        f"{site_url.rstrip('/')}/wp-json/wp/v2/posts/{post_id}?{query}", authorization
    )
    return data


def ensure_confirmation(value: str | None) -> None:
    if value != CONFIRMATION:
        raise ValueError("confirmation input mismatch; refusing WordPress writes")


def validate_preflight_report(report: dict[str, Any]) -> None:
    if report.get("targets") != EXPECTED_TARGETS or report.get("lexus_targets") != 0:
        raise ValueError("preflight target scope mismatch")
    if report.get("wordpress_write_count") != 0:
        raise ValueError("Step A preflight unexpectedly reports WordPress writes")
    media = report.get("media_validation") or {}
    if media.get("confirmed_media_refs_checked") != 105 or media.get("confirmed_media_ref_errors") != 0:
        raise ValueError("confirmed media validation mismatch")

    results = report.get("results") or []
    if len(results) != EXPECTED_TARGETS:
        raise ValueError("preflight must contain exactly 46 target decisions")
    reviews = {row["target_slug"] for row in results if row["action"] == "REVIEW_DUPLICATE"}
    if reviews != MANUAL_EXCLUSIONS:
        raise ValueError(f"unexpected REVIEW_DUPLICATE set: {sorted(reviews)}")
    for row in results:
        if row["target_slug"] in MANUAL_EXCLUSIONS and row["action"] != "REVIEW_DUPLICATE":
            raise ValueError("manual exclusion is no longer REVIEW_DUPLICATE; refusing apply")

    actions = Counter(row["action"] for row in results)
    allowed = {"CREATE_DRAFT", "SKIP_EXISTING", "REVIEW_DUPLICATE"}
    if set(actions) - allowed:
        raise ValueError(f"unexpected preflight action(s): {sorted(set(actions)-allowed)}")
    if actions["CREATE_DRAFT"] + actions["SKIP_EXISTING"] != EXPECTED_CREATABLE_OR_EXISTING:
        raise ValueError("45 non-excluded targets are not fully accounted for")
    if actions["REVIEW_DUPLICATE"] != 1:
        raise ValueError("expected exactly one reviewed manual exclusion")


def build_payload(article: dict[str, Any], plan_row: dict[str, Any]) -> dict[str, str]:
    slug = article["slug"]
    if slug in MANUAL_EXCLUSIONS:
        raise ValueError("manual exclusion must never be posted")
    if plan_row["action"] != "CREATE_DRAFT":
        raise ValueError("only CREATE_DRAFT targets can be posted")
    marker = plan_row["salvage_marker"]
    content = marker + "\n" + (article.get("content") or "")
    return {
        "title": article["title"],
        "slug": slug,
        "content": content,
        "status": "draft",
    }


def validate_created_post(row: dict[str, Any], slug: str) -> dict[str, Any]:
    if row.get("status") != "draft":
        raise ValueError(f"created post is not draft: {slug} status={row.get('status')!r}")
    if row.get("slug") != slug:
        raise ValueError(f"created slug mismatch: expected={slug!r} actual={row.get('slug')!r}")
    if not row.get("id"):
        raise ValueError(f"created post missing id: {slug}")
    return row


def validate_public_counts(before: dict[str, Any], after: dict[str, Any]) -> None:
    for key in ("live_post_publish_count", "live_page_publish_count", "live_publish_count"):
        if before.get(key) != after.get(key):
            raise ValueError(f"public count changed during draft apply: {key}")


def exact_slug_collision(site_url: str, slug: str, authorization: str) -> list[dict[str, Any]]:
    collisions: list[dict[str, Any]] = []
    for endpoint in ("posts", "pages"):
        rows = planner.fetch_collection(
            site_url,
            endpoint,
            authorization,
            context="edit",
            status="publish,draft",
            slug=slug,
            _fields="id,slug,status,link,title,type,content",
        )
        for row in rows:
            row["rest_endpoint"] = endpoint
        collisions.extend(rows)
    return collisions


def fresh_preflight(site_url: str, user: str, password: str):
    articles, final_summary = planner.generate_fresh_articles()
    manifest = planner.load_target_manifest()
    current, media = planner.fetch_live_state(site_url, user, password)
    report = planner.build_report(articles, final_summary, manifest, current, media)
    validate_preflight_report(report)
    return articles, report


def write_artifacts(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "created.json").write_text(
        json.dumps(report["created"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "skipped.json").write_text(
        json.dumps(report["skipped"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "result.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for name in ("created", "skipped"):
        rows = report[name]
        columns = sorted({key for row in rows for key in row}) if rows else ["target_slug"]
        with (output_dir / f"{name}.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
    lines = [
        "# Phase 4 Step B：旧つりくえ！下書き create-only apply",
        "",
        f"- created_count: **{report['created_count']}**",
        f"- skipped_count: **{report['skipped_count']}**",
        f"- review_count: **{report['review_count']}**",
        f"- failed_count: **{report['failed_count']}**",
        f"- public_content_modified_count: **{report['public_content_modified_count']}**",
        f"- media_upload_count: **{report['media_upload_count']}**",
        f"- preflight publish/draft: **{report['before_live_publish_count']} / {report['before_live_draft_count']}**",
        f"- after publish/draft: **{report['after_live_publish_count']} / {report['after_live_draft_count']}**",
        "",
        "## Manual exclusion",
        "",
        "- `aoriika-cooking`: existing published `aoriika-oisiiyo` already covers the same firsthand experience; never POST.",
    ]
    (output_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def apply(site_url: str, user: str, password: str, confirmation: str) -> dict[str, Any]:
    ensure_confirmation(confirmation)
    articles, preflight = fresh_preflight(site_url, user, password)
    article_by_slug = {row["slug"]: row for row in articles}
    plan_by_slug = {row["target_slug"]: row for row in preflight["results"]}
    authorization = basic_auth(user, password)

    created: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []

    for row in preflight["results"]:
        slug = row["target_slug"]
        if slug in MANUAL_EXCLUSIONS:
            skipped.append({
                "target_slug": slug,
                "action": "MANUAL_EXCLUSION",
                "reason": "existing_published_same_firsthand_experience",
                "matched_id": row.get("matched_id"),
                "matched_slug": row.get("matched_slug"),
            })
            continue
        if row["action"] == "SKIP_EXISTING":
            skipped.append({
                "target_slug": slug,
                "action": "SKIP_EXISTING",
                "reason": row.get("reason"),
                "matched_id": row.get("matched_id"),
                "matched_slug": row.get("matched_slug"),
                "matched_status": row.get("matched_status"),
            })
            continue
        if row["action"] != "CREATE_DRAFT":
            raise ValueError(f"unexpected non-create target at apply time: {slug} {row['action']}")

        collisions = exact_slug_collision(site_url, slug, authorization)
        if collisions:
            skipped.append({
                "target_slug": slug,
                "action": "SKIP_RACE_COLLISION",
                "reason": "exact_slug_appeared_after_preflight",
                "matched_id": collisions[0].get("id"),
                "matched_slug": collisions[0].get("slug"),
                "matched_status": collisions[0].get("status"),
            })
            continue

        payload = build_payload(article_by_slug[slug], plan_by_slug[slug])
        try:
            response = post_json(
                f"{site_url.rstrip('/')}/wp-json/wp/v2/posts",
                authorization,
                payload,
            )
            validate_created_post(response, slug)
            verified = get_post(site_url, int(response["id"]), authorization)
            validate_created_post(verified, slug)
            created.append({
                "post_id": int(verified["id"]),
                "slug": verified["slug"],
                "title": html.unescape((verified.get("title") or {}).get("raw") or (verified.get("title") or {}).get("rendered") or article_by_slug[slug]["title"]),
                "status": verified["status"],
                "link": verified.get("link"),
            })
        except Exception as exc:
            failed.append({"target_slug": slug, "error": type(exc).__name__, "message": str(exc)})
            raise

    _after_articles, after = fresh_preflight(site_url, user, password)
    validate_public_counts(preflight, after)

    after_by_slug = {row["target_slug"]: row for row in after["results"]}
    for row in created:
        post_plan = after_by_slug[row["slug"]]
        if post_plan["action"] != "SKIP_EXISTING" or post_plan.get("matched_status") != "draft":
            raise ValueError(f"post-apply idempotency verification failed: {row['slug']}")

    return {
        "mode": "authenticated-phase4-create-only-apply-once",
        "created": created,
        "skipped": skipped,
        "failed": failed,
        "created_count": len(created),
        "skipped_count": len(skipped),
        "review_count": 1,
        "failed_count": len(failed),
        "public_content_modified_count": 0,
        "media_upload_count": 0,
        "before_live_publish_count": preflight["live_publish_count"],
        "before_live_draft_count": preflight["live_draft_count"],
        "after_live_publish_count": after["live_publish_count"],
        "after_live_draft_count": after["live_draft_count"],
        "before_live_post_publish_count": preflight["live_post_publish_count"],
        "after_live_post_publish_count": after["live_post_publish_count"],
        "before_live_page_publish_count": preflight["live_page_publish_count"],
        "after_live_page_publish_count": after["live_page_publish_count"],
        "wordpress_post_create_count": len(created),
        "wordpress_update_count": 0,
        "wordpress_delete_count": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-url", default="https://tsurikue.com")
    parser.add_argument("--output-dir", type=Path, default=Path("reports/old-tsurikue-phase4-create-drafts-apply-once"))
    args = parser.parse_args()
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    confirmation = os.environ.get("PHASE4_CONFIRMATION")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")
    try:
        report = apply(args.site_url, user, password, confirmation or "")
        write_artifacts(args.output_dir, report)
        print(json.dumps({k: v for k, v in report.items() if k not in {"created", "skipped", "failed"}}, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        failure = {"mode":"authenticated-phase4-create-only-apply-once","failed":True,"error":type(exc).__name__,"message":str(exc)}
        (args.output_dir / "failure.json").write_text(json.dumps(failure, ensure_ascii=False, indent=2)+"\n",encoding="utf-8")
        raise


if __name__ == "__main__":
    raise SystemExit(main())
