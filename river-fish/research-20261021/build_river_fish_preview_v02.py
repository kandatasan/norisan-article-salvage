#!/usr/bin/env python3
"""Single-file offline preview for the v02 source-backed fish/river layer."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from build_river_fish_layer_v02 import build, load_csv, INPUT, HIROSHIMA, SCHEMA
from build_river_fish_preview import HTML


def render(layer):
    if layer["schema"] != SCHEMA or layer["status"] != "RESEARCH_ONLY_NOT_FOR_LIVE_SITE":
        raise ValueError("Not the approved research-only layer")
    data = json.dumps(layer, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    page = HTML.replace("tsurikue-source-named-river-fish-v01", SCHEMA)
    page = page.replace("__EMBEDDED_LAYER__", data)
    page = page.replace("各県の過去の資料に記載された魚名", "各県の過去の資料に記載された魚名（広島県の河川環境概説を追加）")
    if "__EMBEDDED_LAYER__" in page or SCHEMA not in page:
        raise ValueError("Preview data not embedded")
    return page


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    layer = build(load_csv(INPUT), load_csv(HIROSHIMA))
    if args.out.exists():
        raise FileExistsError("Refusing to overwrite preview")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(layer), encoding="utf-8")
    print("RIVER_FISH_V02_OFFLINE_PREVIEW", json.dumps({
        "rivers": len(layer["river_groups"]), "fish_names": len(layer["fish_reverse_index"]),
        "research_only": True, "site_updated": False
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
