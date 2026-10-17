#!/usr/bin/env python3
"""Stage local river-name ↔ national river-code *candidates*, never approvals.

A matched name and watershed is a useful REVIEW candidate, NOT proof that
a 10-digit ID applies to that prefecture/municipality river. Same names recur.
v0.2 local mentions have NO independently confirmed watershed and are only
matched by name. No fish occurrences, coordinates or tributary inference.
"""
import argparse
import csv
import json
from collections import Counter,defaultdict
from pathlib import Path
import unicodedata

HERE=Path(__file__).resolve().parent
OFFICIAL=HERE/"national-codes-staged/river_codes_national_v07.csv"
LOCAL=HERE/"river_registry_hiroshima_v01.csv"
MENTIONS=HERE/"river_name_mentions_hiroshima_v02.csv"
FIELDS=["local_evidence_id","local_evidence_type","prefecture_in_source",
        "municipality_in_source","river_name_in_source","watershed_in_source",
        "source_url","candidate_river_code","candidate_watershed_name",
        "match_basis","candidate_count_for_evidence","review_status",
        "identity_approved","prefecture_attribution_approved","fish_attribution_approved"]
RIVER_FIELDS=["river_code","river_name","watershed_code","watershed_name",
              "code_region_prefix","source_url","identity_status","site_status"]

def norm(text):
    return unicodedata.normalize("NFKC",str(text or "")).strip().casefold()

def table(path,fields=None):
    with Path(path).open(encoding="utf-8-sig",newline="") as fd:
        reader=csv.DictReader(fd)
        if fields is not None and reader.fieldnames!=fields:
            raise ValueError("Unexpected CSV columns for "+str(path))
        return list(reader)

def local_evidence(root=HERE):
    root=Path(root)
    verified=table(root/"river_registry_hiroshima_v01.csv")
    mentions=table(root/"river_name_mentions_hiroshima_v02.csv")
    if len(verified)!=66 or len(mentions)!=98:
        raise ValueError("Local source inventory changed; review before rebuilding")
    records=[]
    for x in verified:
        if x["record_status"]!="source_name_confirmed":
            raise ValueError("Unverified base source")
        records.append({"id":x["river_id"],"kind":"river_register_2021",
                        "prefecture":x["prefecture"],
                        "municipality":x["municipality_example"],
                        "river_name":x["river_name"],"watershed":x["watershed"],
                        "url":x["source_url"]})
    for x in mentions:
        if x["watershed_review_status"]!="unverified" or x["watershed_name"]:
            raise ValueError("New mentions have accidentally inferred watersheds")
        records.append({"id":x["mention_id"],"kind":"municipality_listing",
                        "prefecture":x["prefecture"],
                        "municipality":x["municipality_listing"],
                        "river_name":x["river_name"],"watershed":"",
                        "url":x["source_url"]})
    ids=[x["id"] for x in records]
    if len(set(ids))!=len(ids):raise ValueError("Ambiguous local evidence ID")
    return records

def compute_candidates(root=HERE):
    root=Path(root)
    official=table(root/"national-codes-staged/river_codes_national_v07.csv",RIVER_FIELDS)
    name_index=defaultdict(list)
    pair_index=defaultdict(list)
    for row in official:
        if row["identity_status"]!="coded_name_only_not_geographically_verified":
            raise ValueError("Official code already linked without review")
        name_index[norm(row["river_name"])].append(row)
        if row["watershed_name"]:
            pair_index[(norm(row["river_name"]),norm(row["watershed_name"]))].append(row)
    all_candidates=[]
    review_counts=Counter()
    local=local_evidence(root)
    for evidence in local:
        if evidence["watershed"]:
            match_basis="exact_name_and_source_watershed"
            matches=pair_index.get((norm(evidence["river_name"]),norm(evidence["watershed"])),[])
        else:
            match_basis="exact_name_only_no_source_watershed"
            matches=name_index.get(norm(evidence["river_name"]),[])
        unique={m["river_code"]:m for m in matches}
        matches=[unique[code] for code in sorted(unique)]
        match_type=("no_code_candidate" if len(matches)==0 else
                    "multiple_codes_need_review" if len(matches)>1 else
                    "single_code_still_unverified")
        review_counts[evidence["kind"]+"__"+match_type]+=1
        for x in matches or [None]:
            row=[evidence["id"],evidence["kind"],evidence["prefecture"],
                 evidence["municipality"],evidence["river_name"],evidence["watershed"],
                 evidence["url"],x["river_code"] if x else "",
                 x["watershed_name"] if x else "",
                 match_basis if x else "no_match_with_current_scope",
                 len(matches),match_type,
                 "false","false","false"]
            all_candidates.append(dict(zip(FIELDS,row)))
    return all_candidates,{
        "base_registry_evidence":66,
        "municipality_mention_evidence":98,
        "total_local_evidence":len(local),
        "candidate_rows_including_no_matches":len(all_candidates),
        "candidate_counts_by_evidence_and_status":dict(sorted(review_counts.items())),
        "approved_identity_links":0,
        "approved_prefecture_links":0,
        "approved_fish_occurrence_links":0,
        "scope":"source name and sometimes source watershed, no confirmed code-to-location mapping",
        "publication_status":"research_only",
        "notes":"Even unique name+watershed combinations are NOT approved as geographic identity or fish observation. Two-digit MLIT prefix is not prefecture."
    }

def export(output,rows,summary):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    with (output/"hiroshima_river_code_candidates_v08.csv").open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
    (output/"river_code_candidates_manifest_v08.json").write_text(
        json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True)
    x=p.parse_args()
    rows,meta=compute_candidates()
    export(x.out,rows,meta)
    print(json.dumps(meta,ensure_ascii=False,indent=2))
