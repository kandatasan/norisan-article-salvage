#!/usr/bin/env python3
from __future__ import annotations
import base64,bz2,json,re
from pathlib import Path
SLUG='gulpalivepowder'
REPORT=Path('reports/gulpalivepowder-photo-matches')
BUNDLE=Path('scripts/old_tsurikue_phase2_photo_matches.bz2.b64')
REFS=Path('scripts/old_tsurikue_recovered_photo_refs.tsv')
def main():
    raw=bz2.decompress(base64.b64decode(BUNDLE.read_text(encoding='utf-8'))).decode('utf-8','replace')
    REPORT.mkdir(parents=True,exist_ok=True)
    (REPORT/'decoded-phase2.txt').write_text(raw,encoding='utf-8')
    lines=[ln for ln in raw.splitlines() if SLUG.casefold() in ln.casefold()]
    refs=[ln for ln in REFS.read_text(encoding='utf-8').splitlines() if ln.startswith(SLUG+'\t')]
    # Also collect plausible filename tokens on matched lines for a compact summary.
    filenames=[]
    for ln in lines+refs:
        for name in re.findall(r'(?i)(?:[A-Za-z0-9_\-]+\.(?:jpg|jpeg|png|webp))',ln):
            if name not in filenames: filenames.append(name)
    summary=(
      '# gulpalivepowder photo-match inspection\n\n'
      '- mode: **LOCAL DATA ONLY**\n'
      '- wordpress_read_count: **0**\n'
      '- wordpress_write_count: **0**\n'
      f'- phase2_matching_lines: **{len(lines)}**\n'
      f'- recovered_ref_lines: **{len(refs)}**\n'
      f'- filenames_found: **{", ".join(filenames) if filenames else "(none)"}**\n\n'
      '## Phase2 lines\n\n```text\n'+'\n'.join(lines)+'\n```\n\n'
      '## Recovered reference lines\n\n```text\n'+'\n'.join(refs)+'\n```\n'
    )
    (REPORT/'summary.md').write_text(summary,encoding='utf-8'); print(summary); return 0
if __name__=='__main__': raise SystemExit(main())
