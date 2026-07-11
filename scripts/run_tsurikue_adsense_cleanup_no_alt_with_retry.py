#!/usr/bin/env python3
"""Run the no-alt AdSense cleanup with bounded retries for transient REST failures."""
from __future__ import annotations

import sys
import time
import urllib.error
from pathlib import Path

import tsurikue_adsense_cleanup_no_alt as no_alt

cleanup = no_alt.base
_original_request_json = cleanup.request_json


def request_json_with_retry(*args, **kwargs):
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            return _original_request_json(*args, **kwargs)
        except urllib.error.URLError as error:
            last_error = error
            if attempt < 3:
                time.sleep(attempt * 3)
    assert last_error is not None
    raise last_error


def output_dir_from_argv() -> Path:
    try:
        index = sys.argv.index("--output-dir")
        return Path(sys.argv[index + 1])
    except (ValueError, IndexError):
        return Path("reports/tsurikue-adsense-cleanup-no-alt")


cleanup.request_json = request_json_with_retry

try:
    raise SystemExit(cleanup.main())
except urllib.error.URLError as error:
    output_dir = output_dir_from_argv()
    output_dir.mkdir(parents=True, exist_ok=True)
    reason = getattr(error, "reason", None)
    safe_detail = f"URLError: {type(reason).__name__}: {reason}"
    (output_dir / "connection-error-detail.txt").write_text(
        safe_detail, encoding="utf-8"
    )
    raise
