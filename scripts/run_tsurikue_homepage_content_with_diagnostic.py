#!/usr/bin/env python3
"""Run homepage content cleanup and save a credential-free failure detail."""
from __future__ import annotations

import sys
from pathlib import Path

import tsurikue_homepage_content as cleanup


def output_dir_from_argv() -> Path:
    try:
        index = sys.argv.index("--output-dir")
        return Path(sys.argv[index + 1])
    except (ValueError, IndexError):
        return Path("reports/tsurikue-homepage-content")


try:
    raise SystemExit(cleanup.main())
except Exception as error:
    output_dir = output_dir_from_argv()
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_detail = f"{type(error).__name__}: {error}"
    (output_dir / "failure-detail.txt").write_text(
        safe_detail,
        encoding="utf-8",
    )
    raise
