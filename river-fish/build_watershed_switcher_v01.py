#!/usr/bin/env python3
"""Build offline national watershed explorer from committed MLIT code CSVs."""
import argparse
import csv
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
SRC=HERE/"national-codes-staged"
UI=HERE/"watershed-switcher-v01"

def read(name):
    with (SRC/name).open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def build():
    rivers=read("river_codes_national_v07.csv")
    watersheds=read("watershed_codes_national_v07.csv")
    assert len(rivers)==35449 and len(watersheds)==5475
    assert len({r["watershed_code"] for r in watersheds})==len(watersheds)
    print("river headers", list(rivers[0]))
    codekey=next(k for k in ("river_code","riverCode") if k in rivers[0])
    namekey=next(k for k in ("river_name","riverName") if k in rivers[0])
    names={r["watershed_code"]:r["watershed_name"] for r in watersheds}
    groups={k:[] for k in names}
    unresolved=[]
    for r in rivers:
        code=r[codekey]
        if len(code)!=10 or not code.isdigit(): raise ValueError("Invalid river code "+code)
        item=[code,r[namekey]]
        if code[:6] in groups:groups[code[:6]].append(item)
        else:unresolved.append(item)
    assert len(unresolved)==19, f"Unexpected unmatched river count: {len(unresolved)}"
    return {"version":1,"watersheds":[[k,names[k],groups[k]] for k in names],
            "unmatchedCount":len(unresolved),"source":"MLIT official code list; geographic prefecture not inferred"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True)
    args=p.parse_args()
    out=Path(args.out)
    out.mkdir(parents=True,exist_ok=True)
    data=build()
    (out/"index.html").write_text((UI/"index.html").read_text(encoding="utf-8"),encoding="utf-8")
    (out/"data.js").write_text("window.RIVER_ATLAS="+json.dumps(data,ensure_ascii=False,separators=(",",":"))+";\n",encoding="utf-8")
    html=(UI/"index.html").read_text(encoding="utf-8")
    datajs=(out/"data.js").read_text(encoding="utf-8")
    (out/"standalone.html").write_text(html.replace('<script src="data.js"></script>',"<script>"+datajs+"</script>"),encoding="utf-8")
    print("watersheds",len(data["watersheds"]),"ota rivers",len(next(w[2] for w in data["watersheds"] if w[0]=="870709")))

if __name__=="__main__":main()
