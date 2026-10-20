#!/usr/bin/env python3
"""Extract distinct source fish LABELS for editorial triage, without assigning stars."""
from pathlib import Path
from zipfile import ZipFile
import json,csv,collections
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"research-individual-v15"/"outputs"/"river_fish_first_static_preview_v15.zip"
OUT=Path(__file__).resolve().parent/"outputs"
OUT.mkdir(parents=True,exist_ok=True)
counts=collections.Counter();types=collections.defaultdict(set)
with ZipFile(SRC) as z:
    atlas=json.loads(z.read("atlas.json"))
    for e in atlas["entries"]:
        p=e.get("old",{}).get("fish")
        if p:
            d=json.loads(z.read(p))
            seq=d["labels"] if "labels" in d else d["records"]
            for x in seq:
                s=x["recorded_name"].strip()
                if s:counts[s]+=1;types[s].add("historical")
        if e.get("edna"):
            d=json.loads(z.read(e["edna"]))
            for x in d["records"]:
                if x["group"]=="fish":
                    s=x["name"].strip()
                    if s:counts[s]+=1;types[s].add("edna")
assert len(counts)==639,len(counts)
out=OUT/"fish_639_taxon_labels_for_editor_v16.csv"
with out.open("w",newline="",encoding="utf-8") as f:
    w=csv.writer(f);w.writerow(["recorded_name","river_name_group_appearances","methods"])
    w.writerows((s,n,"+".join(sorted(types[s]))) for s,n in sorted(counts.items(),key=lambda x:x[0]))
print("VERIFIED DISTINCT LABELS",len(counts))
print("EXAMPLE "+str(counts.most_common(25)))
