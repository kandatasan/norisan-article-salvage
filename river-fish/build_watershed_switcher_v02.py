#!/usr/bin/env python3
"""Generate v02 mobile-first atlas from actual national code CSVs, offline only."""
import argparse
import json
from pathlib import Path
from build_watershed_switcher_v01 import build
HERE=Path(__file__).resolve().parent
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True)
    args=p.parse_args()
    out=Path(args.out)
    out.mkdir(parents=True,exist_ok=True)
    data=build()
    template=(HERE/"watershed-switcher-v02/index.html").read_text(encoding="utf-8")
    datajs="window.RIVER_ATLAS="+json.dumps(data,ensure_ascii=False,separators=(",",":"))+";\n"
    (out/"index.html").write_text(template,encoding="utf-8")
    (out/"data.js").write_text(datajs,encoding="utf-8")
    (out/"standalone.html").write_text(template.replace('<script src="data.js"></script>',"<script>"+datajs+"</script>"),encoding="utf-8")
    assert len(data["watersheds"])==5475
    assert sum(len(w[2]) for w in data["watersheds"])==35430
    assert '8707090029' in datajs
    print("v02 built",len(data["watersheds"]),"watersheds")
if __name__=="__main__":main()
