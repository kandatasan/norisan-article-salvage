#!/usr/bin/env python3
"""Auditable, conservative Kyushu original-river-name triage.

Official MLIT distribution table proves SOME watershed+river-name pairs.
It does not include ten-digit river codes, so no candidate here is A-rated.
Never assign prefecture, tributary, or biota to a specific river by guessing.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re
from probe_kyushu_official_page import BASINS,SOURCE,TableReader,fetch
ROOT=Path(__file__).resolve().parents[1]
SOURCE_SHA="36d0cfacef4c6fffbb0df7b2019aeadcdb0a5b3e554894a0c236263894077489"
CATEGORY_IDS={"fish","benthic_animals","birds","plants"}

def rows(path):
    with Path(path).open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))

def parse_pairs(html):
    parser=TableReader();parser.feed(html)
    result={}
    for cells in parser.rows:
        if len(cells)<2:continue
        water="".join(cells[0].split())
        if water not in BASINS:continue
        if water in result:raise ValueError("Duplicate watershed row: "+water)
        names=[re.sub(r"\s+","","".join(line.split())) for line in cells[1].splitlines() if line.strip()]
        if not names or any(len(n)>35 for n in names):raise ValueError("Missing/invalid official river names in "+water)
        result[water]=sorted(set(names))
    if set(result)!=BASINS:raise ValueError("Official basins changed or incomplete: "+repr(sorted(BASINS-set(result))))
    return result

def build(out,html=None,original_sha=None):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    if html is None:
        raw,html,_=fetch();actual=hashlib.sha256(raw).hexdigest()
    else:actual=original_sha
    if actual!=SOURCE_SHA:raise ValueError("Official web source checksum changed: approval halted")
    official=parse_pairs(html)
    national=rows(ROOT/"national-codes-staged/river_codes_national_v07.csv")
    official_river={}
    for x in national:
        official_river.setdefault((x["watershed_name"],x["river_name"]),set()).add(x["river_code"])
    source=rows(ROOT/"research-individual-v01/outputs/river_counts.csv")
    kyushu=[r for r in source if r["region"]=="kyushu" and r["match_class"]=="B"]
    nonempty={r["watershed"] for r in kyushu}
    if len(nonempty)!=20 or set(nonempty)!=BASINS:
        raise ValueError("Source B water basins differ from official 20-basin list")
    if len(kyushu)!=286 or sum(int(r["recovered_records"]) for r in kyushu)!=115062:
        raise ValueError("Original Kyushu B count changed")
    grouped=defaultdict(list)
    for r in kyushu:
        if r["group"] not in CATEGORY_IDS or not r["river"]:raise ValueError("Source B row invalid")
        grouped[(r["watershed"],r["river"])].append(r)
    if len(grouped)!=92:raise ValueError("Unexpected distinct Kyushu B river-name contexts")

    pairrows=[]
    for watershed,rivers in sorted(official.items()):
        for river in rivers:
            candidates=sorted(official_river.get((watershed,river),[]))
            pairrows.append({
                "watershed_name":watershed,"river_name":river,
                "catalog_matches":len(candidates),
                "catalog_unique_code_candidate":candidates[0] if len(candidates)==1 else "",
                "source_url":SOURCE,"status":"official_name_pair_not_10digit_code_confirmation"
            })

    queue=[];summary=Counter()
    for (watershed,river),groups in sorted(grouped.items()):
        names=official.get(watershed,[])
        official_confirmed=river in names
        codes=sorted(official_river.get((watershed,river),[]))
        unique=len(codes)==1
        total=sum(int(x["recovered_records"]) for x in groups)
        if official_confirmed and unique:
            tier="B_source_pair_and_unique_catalog_candidate_not_A"
            summary["corroborated_named_pairs"]+=1
            summary["corroborated_contexts"]+=total
        elif official_confirmed:
            tier="B_official_pair_code_ambiguous_or_missing"
            summary["official_pair_unresolved_contexts"]+=total
        elif unique:
            tier="B_unique_catalog_candidate_no_independent_official_pair"
            summary["single_catalog_only_contexts"]+=total
        else:
            tier="B_no_unique_code_and_no_source_pair"
            summary["other_unresolved_contexts"]+=total
        summary["all_unresolved_contexts"]+=total
        for x in groups:
            queue.append({
                "region":"kyushu","watershed_name":watershed,"river_name":river,
                "category":x["group"],
                "recovered_records":x["recovered_records"],
                "literal_names_not_species":x["distinct_literal_names_not_species"],
                "year_min":x["year_min"],"year_max":x["year_max"],
                "independent_kyushu_mlit_name_pair":official_confirmed,
                "national_candidate_count":len(codes),
                "unapproved_unique_catalog_code_candidate":codes[0] if unique else "",
                "triage":tier,
                "independent_source_url":SOURCE if official_confirmed else "",
                "match_class":"B",
                "is_approved_individual_river":False
            })
    fields=list(queue[0])
    with (out/"kyushu_B_triage_v04.csv").open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(queue)
    with (out/"official_watershed_river_pairs_v04.csv").open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(pairrows[0]));w.writeheader();w.writerows(pairrows)
    data={
      "source_url":SOURCE,"source_sha256":actual,"license_note":"Independent official names are not a 10-digit code ledger. W05 geographic product excluded due to noncommercial license.",
      "official_watersheds":len(official),"official_name_pairs":len(pairrows),
      "source_B_group_rows":len(kyushu),
      "source_B_distinct_pairs":len(grouped),
      "recovered_B_contexts":summary["all_unresolved_contexts"],
      "independently_confirmed_name_pairs_with_unique_catalog_candidate":summary["corroborated_named_pairs"],
      "independently_confirmed_name_pair_contexts":summary["corroborated_contexts"],
      "other_B_contexts":summary["all_unresolved_contexts"]-summary["corroborated_contexts"],
      "B_remain_B":True,
      "new_A_rivers":0,
      "new_A_contexts":0,
      "public_wordpress_deployed":False,
      "db_modified":False,
      "source_river_code_proof":"not_available",
      "next_step":"Find independent region-specific code ledger or explicitly licensed code/name geographic reference, then promote only cross-verified items"
    }
    if data["official_watersheds"]!=20 or data["source_B_distinct_pairs"]!=92:
        raise ValueError("Kyushu source count mismatch")
    if sum(int(x["recovered_records"]) for x in queue)!=data["recovered_B_contexts"]:
        raise ValueError("Conservation failed")
    (out/"kyushu_audit_v04.json").write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(data,ensure_ascii=False))
    return data

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",required=True)
    a=p.parse_args();build(a.out)
