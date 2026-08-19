#!/usr/bin/env python3
from __future__ import annotations

import hashlib
from pathlib import Path

import old_tsurikue_phase4_create_plan_dry_run as planner

SLUG = "sayori-taberu"
EXPECTED_TITLE = "サヨリ実食編。『姫ひじきの塩』で塩焼きシンプルだけど味わい深いね。"
EXPECTED_CONTENT_SHA256 = "0c89d543869f9d0a0e4d48d75804c504913dff18c5243319e125f4116d9a09ec"
REPORT_DIR = Path("reports/sayori-taberu-source-body")


def main() -> int:
    articles, _summary = planner.generate_fresh_articles()
    matches = [row for row in articles if row.get("slug") == SLUG]
    if len(matches) != 1:
        raise RuntimeError(f"expected one generated article; found {len(matches)}")
    article = matches[0]
    title = article.get("title") or ""
    content = article.get("content") or ""
    sha = hashlib.sha256(content.encode()).hexdigest()
    if title != EXPECTED_TITLE:
        raise RuntimeError(f"title mismatch: {title!r}")
    if sha != EXPECTED_CONTENT_SHA256:
        raise RuntimeError(f"content sha mismatch: {sha}")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "content.html").write_text(content, encoding="utf-8")
    summary = (
        "# sayori-taberu preserved source body\n\n"
        "- mode: **LOCAL SOURCE ONLY**\n"
        "- wordpress_read_count: **0**\n"
        "- wordpress_write_count: **0**\n"
        f"- title: {title}\n"
        f"- content_sha256: `{sha}`\n\n"
        "## Preserved source body\n\n"
        "```html\n"
        + content
        + "\n```\n"
    )
    (REPORT_DIR / "summary.md").write_text(summary, encoding="utf-8")
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
