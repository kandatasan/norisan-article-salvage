#!/usr/bin/env python3
from __future__ import annotations
import scripts.compress_karato_market_20260909 as m

_orig=m.compress

def compress_fixed(content):
    out=_orig(content)
    # Preserve the exact user-supplied Google Maps URL.
    out=out.replace('https://maps.app.goo.gl/SLQJDZufufnp5B9?g_st=ic','https://maps.app.goo.gl/SLQJDZufufpfnp5B9?g_st=ic')
    return out

m.compress=compress_fixed

if __name__=='__main__':
    m.main()
