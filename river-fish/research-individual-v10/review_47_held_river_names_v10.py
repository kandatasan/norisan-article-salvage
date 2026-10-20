#!/usr/bin/env python3
"""Evaluate 47 held named-river survey identities at river-NAME granularity.

Do not approve a physical river or guess one of several legal 10-digit codes.
If all competing same-name codes share ONE 6-digit watershed, a separate
river-name-level "multiple possible segments" research bundle can preserve
the old original survey observations without inventing their exact segment.
Other/compound/lake names stay held.
"""
from __future__ import annotations
from collections import Counter,defaultdict
import csv,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/"research-individual-v05/outputs/name_first_held_for_review_v05.csv"
CODES=ROOT/"national-codes-staged/river_codes_national_v07.csv"
def rows(path):
    with Path(path).open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def audit(out):
    held=rows(OLD);catalog=rows(CODES)
    if len(held)!=47 or sum(int(r["historical_record_contexts"]) for r in held)!=101210:
        raise ValueError("Unknown previous held research")
    matched=defaultdict(set)
    for row in catalog:
        matched[(row["watershed_name"],row["river_name"])].add(row["river_code"])
    items=[];sums=Counter()
    for r in held:
        key=(r["watershed_name"],r["river_name"])
        codes=sorted(matched.get(key,set()))
        stems={c[:6] for c in codes}
        claimed=int(r["national_code_candidates"])
        if len(codes)!=claimed:raise ValueError("National catalog code counts changed for "+repr(key))
        contexts=int(r["historical_record_contexts"])
        if r["reason"]=="same_name_in_watershed_multiple_codes":
            if len(codes)<=1:raise ValueError("Expected multiple codes")
            if len(stems)==1:
                decision="river_name_only_multiple_segments_one_watershed"
                sums["candidate_name_buckets"]+=1;sums["candidate_contexts"]+=contexts
            else:
                decision="hold_multiple_official_watershed_code_roots"
                sums["mixed_code_root_hold"]+=1;sums["mixed_code_root_contexts"]+=contexts
        else:
            decision="hold_nonriver_composite_or_survey_section"
            sums["nonriver_or_section_hold"]+=1;sums["nonriver_or_section_contexts"]+=contexts
        item={"source_region":r["region"],"survey_watershed":r["watershed_name"],
              "survey_river_label":r["river_name"],"source_held_reason":r["reason"],
              "current_physical_river_approval":False,
              "candidate_10digit_code_count":len(codes),
              "distinct_6digit_watershed_roots":len(stems),
              "candidate_parent_watershed_codes":sorted(stems),
              "historical_contexts":contexts,"new_name_level_decision":decision,
              "claim_of_unique_physical_river":False,
              "future_ui_label":"同名・複数区間の資料掲載名。位置と河川コードは未確定"}
        items.append(item)
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
    data={"baseline_428_rivers_unchanged":True,"baseline_553351_contexts_unchanged":True,
          "source_held_name_labels":len(items),"source_held_contexts":101210,
          "classification":dict(sums),"items":items,
          "no_name_bundle_is_a_legal_10digit_river_identity":True,
          "nonriver_lakes_not_adopted":True,
          "historical_biology_not_current_biological_presence":True,
          "production_unchanged":True}
    out.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in data.items() if k!="items"},ensure_ascii=False))
    return data
if __name__=="__main__":audit(sys.argv[1])
