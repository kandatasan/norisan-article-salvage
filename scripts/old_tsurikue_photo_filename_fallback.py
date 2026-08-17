#!/usr/bin/env python3
"""GET-only filename reconciliation using recovered old-tsurikue photo references."""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from old_tsurikue_photo_reconciliation import (
    EXPECTED_TARGETS,
    basic_auth,
    fetch_media,
    load_inputs,
    normalized_filename,
    write_artifacts,
)

HERE = Path(__file__).resolve().parent
REFS_FILE = HERE / "old_tsurikue_recovered_photo_refs.tsv"
RAW_AUDIT_IMAGE_REFS = 481


def load_refs(path: Path = REFS_FILE) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        for line_no, row in enumerate(reader, 1):
            if len(row) != 4:
                raise ValueError(f"invalid recovered ref row {line_no}")
            slug, order, filename, heading = row
            if not slug or not filename:
                raise ValueError(f"missing slug/filename at row {line_no}")
            rows.append({"slug": slug, "order": int(order), "filename": filename, "heading": heading})
    return rows


def _copy_suffix_alias(filename: str) -> str | None:
    key = normalized_filename(filename)
    stem, ext = os.path.splitext(key)
    match = re.match(r"^(.*)-(\d+)$", stem)
    if not match:
        return None
    base = match.group(1)
    # Avoid treating generic image-1.jpg as image.jpg. The old WordPress copy suffix
    # fallback is only enabled for stems that already contain a digit (IMG_2471-1, UUIDs, etc.).
    if not re.search(r"\d", base):
        return None
    return base + ext


def build_indexes(media: list[dict[str, Any]]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    exact: dict[str, list[dict[str, Any]]] = defaultdict(list)
    aliases: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in media:
        src = str(item.get("source_url") or "")
        key = normalized_filename(src)
        if not key:
            continue
        exact[key].append(item)
        alias_keys = {key}
        stem, ext = os.path.splitext(key)
        match = re.match(r"^(.*)-(\d+)$", stem)
        if match and re.search(r"\d", match.group(1)):
            alias_keys.add(match.group(1) + ext)
        for alias in alias_keys:
            aliases[alias].append(item)
    return exact, aliases


def match_ref(ref: dict[str, Any], exact: dict[str, list[dict[str, Any]]], aliases: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    key = normalized_filename(ref["filename"])
    exact_matches = exact.get(key, [])
    result = "PLACEHOLDER"
    match: dict[str, Any] | None = None
    reason = "recovered ref; no unique filename match"
    if len(exact_matches) == 1:
        match = exact_matches[0]
        result = "MATCH_FILENAME"
        reason = "unique normalized filename match from recovered ref"
    elif len(exact_matches) > 1:
        reason = "ambiguous normalized filename; automatic insertion blocked"
    else:
        alias = _copy_suffix_alias(ref["filename"])
        alias_matches = aliases.get(alias, []) if alias else []
        if len(alias_matches) == 1:
            match = alias_matches[0]
            result = "MATCH_FILENAME"
            reason = "unique WordPress copy-suffix filename match from recovered ref"
        elif len(alias_matches) > 1:
            reason = "ambiguous WordPress copy-suffix filename; automatic insertion blocked"
    placeholder_text = "" if match else f"【写真差し込み：旧画像{ref['order']} / {ref['filename']} / {ref['heading'] or '見出し不明'}】"
    return {
        "target_slug": ref["slug"],
        "archive_url": "recovered:2-recovered-articles.md",
        "nearest_heading": ref["heading"],
        "image_order": ref["order"],
        "legacy_image_url": "",
        "legacy_filename": ref["filename"],
        "context_before": "",
        "context_after": "",
        "result": result,
        "matched_media_id": match.get("id") if match else None,
        "matched_media_source_url": match.get("source_url") if match else None,
        "hash_distance": None,
        "confidence_reason": reason,
        "placeholder_text": placeholder_text,
    }


def build_report(targets: list[dict[str, Any]], refs: list[dict[str, Any]], media: list[dict[str, Any]]) -> dict[str, Any]:
    target_slugs = [row["slug"] for row in targets]
    ref_slugs = {row["slug"] for row in refs}
    unknown = ref_slugs - set(target_slugs)
    if unknown:
        raise ValueError(f"recovered refs contain unknown targets: {sorted(unknown)}")
    exact, aliases = build_indexes(media)
    results = [match_ref(ref, exact, aliases) for ref in refs]
    counts = Counter(row["result"] for row in results)
    return {
        "mode": "authenticated-photo-filename-recovered-fallback-dry-run",
        "targets": len(targets),
        "lexus_targets": 0,
        "live_media_count": len(media),
        "archive_articles_ok": len(targets),
        "archive_articles_failed": 0,
        "archive_image_refs": len(refs),
        "raw_audit_image_refs": RAW_AUDIT_IMAGE_REFS,
        "recovered_ref_note": "363 deduplicated usable photo positions extracted from recovered HTML; 481 is the earlier raw reference audit including duplicate/source-version references.",
        "MATCH_FILENAME": counts["MATCH_FILENAME"],
        "MATCH_HASH_STRONG": 0,
        "CANDIDATE_HASH": 0,
        "PLACEHOLDER": counts["PLACEHOLDER"],
        "ARCHIVE_UNAVAILABLE": 0,
        "wordpress_write_count": 0,
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-url", default="https://tsurikue.com")
    parser.add_argument("--refs", type=Path, default=REFS_FILE)
    parser.add_argument("--output-dir", type=Path, default=Path("reports/old-tsurikue-photo-filename-fallback"))
    args = parser.parse_args()
    user = os.environ.get("TSURIKUE_WP_USER")
    password = os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")
    targets, _ = load_inputs()
    if len(targets) != EXPECTED_TARGETS:
        raise RuntimeError("target count changed")
    refs = load_refs(args.refs)
    media = fetch_media(args.site_url, basic_auth(user, password))
    report = build_report(targets, refs, media)
    write_artifacts(args.output_dir, report)
    print(json.dumps({k: v for k, v in report.items() if k != "results"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
