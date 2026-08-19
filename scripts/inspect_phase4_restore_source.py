#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import old_tsurikue_phase4_create_plan_dry_run as planner

REPORT_ROOT = Path("reports/phase4-restore-source")


def media_ids(content: str) -> list[int]:
    result: list[int] = []
    for match in re.finditer(r"wp-image-(\d+)|\"id\"\s*:\s*(\d+)", content):
        media_id = int(match.group(1) or match.group(2))
        if media_id not in result:
            result.append(media_id)
    return result


def inspect(config_path: Path) -> dict:
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    articles, final_summary = planner.generate_fresh_articles()
    matches = [row for row in articles if row.get("slug") == cfg["slug"]]
    if len(matches) != 1:
        raise RuntimeError(f"expected one generated article; found {len(matches)}")
    article = matches[0]
    content = article.get("content") or ""
    title = article.get("title") or ""
    ids = media_ids(content)
    full_content = cfg["salvage_marker"] + "\n" + content
    snippet_matches = {snippet: (snippet in content) for snippet in cfg.get("inspect_snippets", [])}

    if title != cfg["expected_title"]:
        raise RuntimeError(f"generated title mismatch: {title!r}")
    if ids != cfg["expected_media_ids"]:
        raise RuntimeError(f"generated media mismatch: {ids}")
    if not all(snippet_matches.values()):
        raise RuntimeError(f"generated source missing expected snippets: {snippet_matches}")

    report = {
        "mode": "LOCAL_SOURCE_ONLY",
        "wordpress_read_count": 0,
        "wordpress_write_count": 0,
        "slug": cfg["slug"],
        "title": title,
        "media_ids": ids,
        "content_length": len(content),
        "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
        "full_content_length": len(full_content),
        "full_content_sha256": hashlib.sha256(full_content.encode()).hexdigest(),
        "snippet_matches": snippet_matches,
        "phase4_summary": final_summary,
    }

    out = REPORT_ROOT / cfg["slug"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "content.html").write_text(full_content, encoding="utf-8")
    lines = [
        f"# {cfg['slug']} Phase 4 restore source inspection",
        "",
        "- mode: **LOCAL SOURCE ONLY**",
        "- wordpress_read_count: **0**",
        "- wordpress_write_count: **0**",
        f"- slug: **{cfg['slug']}**",
        f"- title: {title}",
        f"- media_ids: **{', '.join(map(str, ids))}**",
        f"- content_length: **{len(content)}**",
        f"- content_sha256: `{report['content_sha256']}`",
        f"- full_content_length: **{len(full_content)}**",
        f"- full_content_sha256: `{report['full_content_sha256']}`",
        f"- expected_snippets_matched: **{sum(snippet_matches.values())}/{len(snippet_matches)}**",
    ]
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
