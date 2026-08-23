#!/usr/bin/env python3
from pathlib import Path

SOURCE = Path('scripts/apply_ux_resale_rewrite_once.py')
text = SOURCE.read_text(encoding='utf-8')
needle = '<!-- wp:paragraph {"align":"center"} -->'
fixed = '<!-- wp:paragraph {{"align":"center"}} -->'
if text.count(needle) != 1:
    raise RuntimeError(f'expected exactly one alignment marker, got {text.count(needle)}')
text = text.replace(needle, fixed, 1)
ns = {'__name__': 'ux_resale_rewrite_v2_runtime', '__file__': str(SOURCE)}
exec(compile(text, str(SOURCE), 'exec'), ns)
raise SystemExit(ns['main']())
