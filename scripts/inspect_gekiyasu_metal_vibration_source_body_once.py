#!/usr/bin/env python3
from __future__ import annotations

import hashlib
from pathlib import Path

import old_tsurikue_phase4_create_plan_dry_run as planner

SLUG = "gekiyasu-metal-vibration"
EXPECTED_TITLE = "激安メタルバイブレーション(鉄板バイブ)ゲキブルブレードをインプレッション！"
REPORT_DIR = Path("reports/gekiyasu-metal-vibration-source-body")


def main() -> int:
    articles, _summary = planner.generate_fresh_articles()
    matches = [row for row in articles if row.get("slug") == SLUG]
    if len(matches) != 1:
        raise RuntimeError(f"expected one generated article; found {len(matches)}")
    article = matches[0]
    title = article.get("title") or ""
    content = article.get("content") or ""
    if title != EXPECTED_TITLE:
        raise RuntimeError(f"title mismatch: {title!r}")
    sha = hashlib.sha256(content.encode()).hexdigest()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "content.html").write_text(content, encoding="utf-8")
    summary = (
        "# gekiyasu-metal-vibration preserved source body\n\n"
        "- mode: **LOCAL SOURCE ONLY**\n"
        "- wordpress_read_count: **0**\n"
        "- wordpress_write_count: **0**\n"
        f"- title: {title}\n"
        f"- content_sha256: `{sha}`\n\n"
        "## Preserved source body\n\n```html\n" + content + "\n```\n"
    )
    (REPORT_DIR / "summary.md").write_text(summary, encoding="utf-8")
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
