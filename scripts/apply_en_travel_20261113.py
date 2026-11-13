"""Safely enhance existing English Travel posts with exact-block edits.

The supplied WXR is a comparison snapshot, never an authority to overwrite a
newer WordPress edit. Read each live post before any write and stop on drift.
"""
from __future__ import annotations
import hashlib
import html
import json
import re
import urllib.parse
from pathlib import Path

def _hash(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def _build(current, edits):
    revised = current
    for index, edit in enumerate(edits, 1):
        anchor = edit["anchor"]
        fragment = edit["fragment"]
        kind = edit["mode"]
        if not anchor or not fragment or revised.count(anchor) != 1:
            raise RuntimeError(f"EN_TRAVEL_ANCHOR_MISMATCH edit={index}")
        if kind == "insert_after":
            revised = revised.replace(anchor, anchor + "\n\n" + fragment, 1)
        elif kind == "insert_before":
            revised = revised.replace(anchor, fragment + "\n\n" + anchor, 1)
        elif kind == "replace":
            revised = revised.replace(anchor, fragment, 1)
        else:
            raise RuntimeError(f"Unsupported edit type: {kind}")
    return revised

def _same_metadata(before, after):
    return all(before.get(k) == after.get(k) for k in (
        "id", "slug", "status", "featured_media", "categories", "author"
    ))

def apply_en_travel(config_path, cfg, authorization, api):
    fetch_post_by_id, raw_field, public_counts, post_json, site_url, get_json = api
    if cfg.get("operation") != "enhance_english_travel_20261113":
        raise RuntimeError("Unknown operation")
    targets = cfg.get("targets") or []
    if not targets or len({t.get("post_id") for t in targets}) != len(targets):
        raise RuntimeError("Missing or duplicate travel targets")

    counts_before = public_counts(authorization)
    plans = []
    for target in targets:
        pid = int(target["post_id"])
        original = fetch_post_by_id(pid, authorization)
        title = html.unescape(raw_field(original, "title"))
        if (
            original.get("id") != pid
            or original.get("slug") != target["slug"]
            or original.get("status") != target["status"]
            or title != target["title"]
            or int(target.get("required_category", 0)) not in (original.get("categories") or [])
        ):
            raise RuntimeError(f"EN_TRAVEL_IDENTITY_DRIFT post={pid}")
        current = raw_field(original, "content")
        marker = target["marker"]
        if marker in current:
            raise RuntimeError(f"EN_TRAVEL_ALREADY_EDITED_OR_DRIFT post={pid}")
        if _hash(current) != target["expected_current_content_sha256"]:
            raise RuntimeError(f"EN_TRAVEL_LIVE_CONTENT_DRIFT post={pid}")
        for media_id, expected_path in (target.get("expected_media") or {}).items():
            q = urllib.parse.urlencode({"context": "edit", "_fields": "id,source_url"})
            media, _ = get_json(
                f"{site_url}/wp-json/wp/v2/media/{int(media_id)}?{q}", authorization
            )
            actual_path = urllib.parse.unquote(
                urllib.parse.urlsplit(media.get("source_url") or "").path
            ).casefold()
            if media.get("id") != int(media_id) or actual_path != expected_path.casefold():
                raise RuntimeError(f"EN_TRAVEL_MEDIA_DRIFT post={pid} media={media_id}")
        revised = _build(current, target["edits"])
        if revised == current or revised.count(marker) != 1:
            raise RuntimeError(f"EN_TRAVEL_BAD_TRANSFORMATION post={pid}")
        old_ids = set(re.findall(r"\bwp-image-(\d+)\b", current))
        new_ids = set(re.findall(r"\bwp-image-(\d+)\b", revised))
        expected_new = set((target.get("expected_media") or {}).keys())
        if not old_ids.issubset(new_ids) or new_ids - old_ids != expected_new:
            raise RuntimeError(f"EN_TRAVEL_IMAGE_SET_DRIFT post={pid}")
        affiliate_url = "https://www.discovercars.com/?a_aid=tsurikue"
        if revised.count(affiliate_url) > 1:
            raise RuntimeError(f"EN_TRAVEL_DUPLICATE_AFFILIATE post={pid}")
        if (
            target["slug"] == "sakaiminato-mizuki-road-english"
            and "Video was not allowed" not in revised
        ):
            raise RuntimeError("Warehouse photo permission note missing")
        if (
            target["slug"] == "matsue-vogel-park-english"
            and ('rel="sponsored nofollow noopener"' not in revised
                 or "This is an affiliate link" not in revised)
        ):
            raise RuntimeError("Rental advertising disclosure missing")
        plans.append({
            "target": target,
            "before": original,
            "current": current,
            "revised": revised
        })
        print("EN_TRAVEL_PREFLIGHT_OK", pid, target["slug"], _hash(current), flush=True)

    if public_counts(authorization) != counts_before:
        raise RuntimeError("Published counts changed during preflight")
    written = []
    try:
        results = []
        for plan in plans:
            target = plan["target"]
            pid = int(target["post_id"])
            live = fetch_post_by_id(pid, authorization)
            if not _same_metadata(plan["before"], live) or raw_field(live, "content") != plan["current"]:
                raise RuntimeError(f"EN_TRAVEL_CHANGED_BEFORE_WRITE post={pid}")
            response = post_json(
                f"{site_url}/wp-json/wp/v2/posts/{pid}",
                authorization, {"content": plan["revised"]}
            )
            written.append(plan)
            if (
                response.get("id") != pid
                or response.get("slug") != target["slug"]
                or response.get("status") != target["status"]
            ):
                raise RuntimeError(f"EN_TRAVEL_UPDATE_RESPONSE_DRIFT post={pid}")
            after = fetch_post_by_id(pid, authorization)
            if (
                not _same_metadata(plan["before"], after)
                or html.unescape(raw_field(after, "title")) != target["title"]
                or raw_field(after, "content").strip() != plan["revised"].strip()
            ):
                raise RuntimeError(f"EN_TRAVEL_READBACK_MISMATCH post={pid}")
            results.append({
                "post_id": pid, "slug": target["slug"], "status": target["status"],
                "before_sha256": _hash(plan["current"]),
                "after_sha256": _hash(raw_field(after, "content")),
                "added_media": sorted(target.get("expected_media") or {}),
                "featured_media": after.get("featured_media")
            })
        counts_after = public_counts(authorization)
        if counts_after != counts_before:
            raise RuntimeError("EN_TRAVEL_PUBLISH_COUNT_CHANGED")
        report = {
            "results": results, "counts_before": counts_before,
            "counts_after": counts_after
        }
        output = Path("reports/en-travel-photos-san-in-20261113")
        output.mkdir(parents=True, exist_ok=True)
        (output / "result.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (output / "summary.md").write_text(
            "# English Travel rewrite: verified\n\n"
            + "\n".join(
                f"- {v['slug']} (post {v['post_id']}, {v['status']}): "
                f"{v['before_sha256']} -> {v['after_sha256']}"
                for v in results
            ) + "\n", encoding="utf-8"
        )
        print("EN_TRAVEL_ALL_POSTS_VERIFIED", json.dumps(report, ensure_ascii=False), flush=True)
        return report
    except Exception:
        for plan in reversed(written):
            pid = int(plan["target"]["post_id"])
            try:
                live = fetch_post_by_id(pid, authorization)
                if (
                    _same_metadata(plan["before"], live)
                    and raw_field(live, "content").strip() == plan["revised"].strip()
                ):
                    post_json(
                        f"{site_url}/wp-json/wp/v2/posts/{pid}",
                        authorization, {"content": plan["current"]}
                    )
                    print("EN_TRAVEL_ROLLBACK_ATTEMPTED", pid, flush=True)
                else:
                    print("EN_TRAVEL_ROLLBACK_SKIPPED_CHANGED_POST", pid, flush=True)
            except Exception as rollback_error:
                print("EN_TRAVEL_ROLLBACK_FAILED", pid, type(rollback_error).__name__, flush=True)
        raise
