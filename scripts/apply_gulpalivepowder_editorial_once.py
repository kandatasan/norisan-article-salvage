#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os
from pathlib import Path
import apply_editorial_draft_once as updater

CONFIG=Path('editorial/gulpalivepowder/config.json')
EXPECTED_OLD_SHA='a5e286e336b10578782a0e15c8c797ca9e8f3d67a1980430fc8599cc3a2ed0e8'

def main():
    user=os.environ.get('TSURIKUE_WP_USER'); password=os.environ.get('TSURIKUE_WP_APP_PASSWORD')
    if not user or not password: raise SystemExit('BLOCKED_MISSING_SECRETS')
    cfg,full=updater.load_package(CONFIG); auth=updater.auth_header(user,password)
    before=updater.fetch_post(cfg,auth); current=updater.raw_field(before,'content'); sha=hashlib.sha256(current.encode()).hexdigest()
    if cfg['editorial_marker'] in current:
        # Safe only when the generic updater already placed exactly this package.
        action=updater.validate_target(before,cfg,full)
        if action!='ALREADY_UP_TO_DATE': raise RuntimeError('editorial marker exists but package is not exact current content')
    elif sha!=EXPECTED_OLD_SHA:
        raise RuntimeError(f'current content hash changed: {sha}')
    report=updater.apply(CONFIG)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0

if __name__=='__main__': raise SystemExit(main())
