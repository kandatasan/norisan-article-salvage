#!/usr/bin/env python3
"""Run the dead-link cleanup with three known orphan label paragraphs removed.

The base analyzer handles the 23 target links. These exact paragraphs are
separate labels whose linked lists/paragraphs disappear, so they must disappear
with them rather than remain as meaningless headings.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

BASE_PATH = pathlib.Path(__file__).with_name("tsurikue_internal_link_dry_run.py")
spec = importlib.util.spec_from_file_location("tsurikue_internal_link_base", BASE_PATH)
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
assert spec.loader
spec.loader.exec_module(base)

ORPHAN_LABELS = {
    "華火の詳しい体験はこちら",
    "いろは寿司をもう少し味わう",
    "次のごはん旅へ",
}

_base_transform = base.transform


def remove_orphan_labels(content: str) -> str:
    """Delete only Gutenberg paragraphs whose visible text exactly matches a known orphan label."""

    def replace(match):
        inner = match.groupdict().get("html") or match.group(0)
        return "" if base.text(inner) in ORPHAN_LABELS else match.group(0)

    return base.WP_P_RE.sub(replace, content)


def transform(content: str):
    result = _base_transform(content)
    result.updated = remove_orphan_labels(result.updated)
    return result


base.transform = transform


if __name__ == "__main__":
    raise SystemExit(base.main())
