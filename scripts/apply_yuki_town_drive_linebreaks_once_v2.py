#!/usr/bin/env python3
from __future__ import annotations

import html
import re

import apply_yuki_town_drive_linebreaks_once as base


def text_signature(content: str) -> str:
    """Compare visible character sequence while intentionally ignoring formatting whitespace."""
    text = re.sub(r"<!--.*?-->", "", content, flags=re.S)
    text = re.sub(r"<br\s*/?>", "", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return re.sub(r"\s+", "", text)


base.visible_text = text_signature

if __name__ == "__main__":
    raise SystemExit(base.main())
