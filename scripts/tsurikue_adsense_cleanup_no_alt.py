#!/usr/bin/env python3
"""Run the AdSense cleanup while deliberately leaving every image alt unchanged."""
from __future__ import annotations

import importlib.util
import pathlib
import sys

MODULE_PATH = pathlib.Path(__file__).with_name("tsurikue_adsense_cleanup.py")
spec = importlib.util.spec_from_file_location("tsurikue_adsense_cleanup_base", MODULE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load {MODULE_PATH}")
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)

EXPECTED_BLANK_ALTS = 183


def keep_blank_alts(content: str, post_id: int, title: str, actions: list) -> str:
    """Do not modify alt attributes in this run."""
    return content


def verify_after_apply_without_alt(site_url: str, user: str, app_password: str) -> None:
    documents = base.fetch_authenticated_documents(site_url, user, app_password)
    rows = [(doc, base.transform(doc)) for doc in documents]
    summary = base.summarize(rows)
    if (
        summary.edit_memos
        or summary.legacy_replacements
        or summary.link_replacements
        or summary.alt_additions
        or summary.remaining_edit_memos
        or summary.remaining_legacy_terms
        or summary.remaining_dead_links
        or summary.remaining_blank_alts != EXPECTED_BLANK_ALTS
    ):
        raise SystemExit(f"Post-apply verification failed: {summary}")


base.fill_blank_alts = keep_blank_alts
base.EXPECTED_COUNTS = {
    "documents": 21,
    "edit_memos": 4,
    "legacy_replacements": 34,
    "link_replacements": 1,
    "alt_additions": 0,
    "remaining_edit_memos": 0,
    "remaining_legacy_terms": 0,
    "remaining_dead_links": 0,
    "remaining_blank_alts": EXPECTED_BLANK_ALTS,
}
base.verify_after_apply = verify_after_apply_without_alt


if __name__ == "__main__":
    raise SystemExit(base.main())
