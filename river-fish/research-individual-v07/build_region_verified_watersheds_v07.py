#!/usr/bin/env python3
"""Research-only v07: resolve some held same-name WATERSHED NAVIGATION links.

No change to biological record attribution, biological SQLite, city/river
locations, or published site. A prefecture->watershed link is documentary,
NOT a claim that all listed tributaries flow inside the prefecture.

2014 MLIT code spec: 81..89 are national major-basin supervising
administrative bureaus (NOT prefecture); 01..47 second-class codes use
river-mouth prefecture (NOT every part of the river). Detect same-name
local 2nd-class code under the selected prefecture and withhold.
https://www.cgr.mlit.go.jp/kasen/code/pdf/01siyousyo201404.pdf
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import csv
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
V06=ROOT/"research-individual-v06"
SOURCES={
 "mlit_2014_code_spec":"https://www.cgr.mlit.go.jp/kasen/code/pdf/01siyousyo201404.pdf",
 "mlit_current_6digit_registry":"https://nlftp.mlit.go.jp/ksj/gml/codelist/WaterSystemCodeCd.html"
}
REGION_MAJOR_CODE={
 "hokkaido":"81","tohoku":"82","kanto":"83","hokuriku":"84",
 "chubu":"85","kinki":"86","chugoku":"87","shikoku":"88","kyushu":"89"
}

def readcsv(p):
    with Path(p).open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))

def build(out,source=None,previous_audit=None):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    source=Path(source or V06/"outputs/river_atlas_navigation_v06.json")
    previous_audit=Path(previous_audit or V06/"outputs/prefecture_navigation_audit_v06.json")
    data=json.loads(source.read_text(encoding="utf-8"))
    prev=json.loads(previous_audit.read_text(encoding="utf-8"))
    if (prev["original_named_rivers_unchanged"]!=428 or
        prev["original_name_first_biota_contexts_unchanged"]!=553351 or
        prev["linked_prefecture_watershed_pairs"]!=56 or
        prev["withheld_ambiguous_prefecture_watershed_pairs"]!=39 or
        len(data["rivers"])!=428 or len(data["prefectures"])!=47):
        raise ValueError("v06 base changed; must manually audit proposed promotions")
    pref_codes={x["prefecture"]:x["code"] for x in data["prefectures"]}
    national=defaultdict(list)
    for row in readcsv(ROOT/"national-codes-staged/watershed_codes_national_v07.csv"):
        national[row["watershed_name"]].append(row["watershed_code"])
    indexed_rivers=defaultdict(list)
    for x in data["rivers"]:indexed_rivers[x["watershed_name"]].append(x)
    # Original official sources contain explicit documentary name and
    # optional river name, never newly invent a per-river local address.
    sys.path.insert(0,str(V06.resolve()))
    from build_prefecture_navigation_v06 import load_existing_official_mentions,PREF_ALLOWED_SOURCE_REGIONS
    official=defaultdict(list)
    for e in load_existing_official_mentions():
        official[(e["prefecture"],e["watershed"])].append(e)

    new_entries=[]
    new_river_links=[]
    manual_queue=[]
    review=[]
    for held in prev["held_ambiguities"]:
        pref,water=held["prefecture"],held["watershed"]
        cause=held["reason"]
        item={"prefecture":pref,"watershed":water,"old_hold_reason":cause,
              "new_decision":"remain_held","review_reason":cause,
              "mainstream_code_candidate":None,"source_region":None,
              "prefecture_official_urls":sorted({e["source_url"] for e in official.get((pref,water),[])})}
        if cause!="multiple_national_watershed_codes_same_name":
            review.append(item);manual_queue.append(item);continue
        evidence=official.get((pref,water),[])
        matching=indexed_rivers.get(water,[])
        regions={x["region"] for x in matching}
        if not evidence or not matching or len(regions)!=1:
            item["review_reason"]="missing_official_or_survey_evidence";review.append(item);manual_queue.append(item);continue
        region=next(iter(regions))
        item["source_region"]=region
        if region not in PREF_ALLOWED_SOURCE_REGIONS[pref] or region not in REGION_MAJOR_CODE:
            item["review_reason"]="prefecture_vs_source_admin_region_conflict";review.append(item);manual_queue.append(item);continue
        # This 8x test checks supervising bureau of 1st-class system, not prefecture.
        candidates=sorted(national.get(water,[]))
        first_class_prefix=REGION_MAJOR_CODE[region]
        eligible=[c for c in candidates if c[:2]==first_class_prefix]
        if len(eligible)!=1:
            item["review_reason"]="no_unique_major_basin_in_survey_bureau";review.append(item);manual_queue.append(item);continue
        maj=eligible[0]
        item["mainstream_code_candidate"]=maj
        if not (len(maj)==6 and maj.isdigit() and 81<=int(maj[:2])<=89):
            raise ValueError("Unexpected nationally coded major watershed")
        # Same-name local second-class basin could be meant in the prefecture
        # document, even though the survey river is another 1st-class basin.
        # That difference cannot be resolved using source region alone.
        conflicting_local=[c for c in candidates if c[:2]==pref_codes[pref]]
        if conflicting_local:
            item["review_reason"]="local_second_class_same_name_possible_in_source_prefecture"
            item["local_name_code_collision"]=conflicting_local
            review.append(item);manual_queue.append(item);continue
        # The research river names must all explicitly come from this
        # administrative survey region and watershed. A confirmed 10-digit
        # river code, if present, must agree with the 6-digit major basin code.
        bad=[r["river_code"] for r in matching if r["river_code"] and r["river_code"][:6]!=maj]
        if bad:
            item["review_reason"]="approved_individual_river_code_disagrees_with_basin"
            item["conflicting_river_codes"]=bad
            review.append(item);manual_queue.append(item);continue
        # Distinct within current officially managed basin catalog; now
        # allow users to find survey rivers from this prefecture/basin entrance.
        # This does not establish the local prefecture of ANY particular river.
        item["new_decision"]="added_as_documentary_navigation_only"
        item["review_reason"]="unique_independent_major_basin_code_for_source_bureau_without_same_name_local_second_class"
        item["basis_urls"]=[SOURCES["mlit_2014_code_spec"],SOURCES["mlit_current_6digit_registry"]]
        item["linked_river_name_ids"]=len(matching)
        review.append(item)
        named={x["river"] for x in evidence if x["kind"]=="river"}
        direct_proof={r["river_name"] for r in matching if r["river_name"] in named}
        ent={
            "prefecture":pref,"jis_prefecture_code":pref_codes[pref],
            "watershed":water,"survey_region":region,
            "surveyed_river_name_ids":len(matching),
            "surveyed_river_contexts":sum(int(r["survey_record_contexts"]) for r in matching),
            "watershed_official_mentions":sum(e["kind"]=="watershed" for e in evidence),
            "river_official_mentions":sum(e["kind"]=="river" for e in evidence),
            "official_evidence_urls":sorted({e["source_url"] for e in evidence}),
            "navigation_status":"major_basin_region_independently_correlated_to_prefecture_official_named_watershed",
            "identity_basis":"unique_6digit_national_major_watershed_in_survey_bureau_no_local_name_collision",
            "documented_basin_code":maj,
            "region_code_evidence_urls":item["basis_urls"],
            "direct_verified_crosscheck_names":[],
            "no_claim_all_watershed_rivers_within_prefecture":True,
            "no_verified_physical_tributary_relationship":True
        }
        new_entries.append(ent)
        for r in matching:
            direct=[e for e in evidence if e["kind"]=="river" and e["river"]==r["river_name"]]
            new_river_links.append({
                "prefecture":pref,"watershed":water,
                "identity_key":r["identity_key"],"river_name":r["river_name"],
                "individual_river_explicit_prefecture_mentions":len(direct),
                "individual_river_prefecture_evidence_urls":sorted({e["source_url"] for e in direct}),
                "river_location_in_prefecture":"source_mentioned" if direct else "unverified",
                "river_is_within_referenced_watershed":"survey_source_name_only"
            })
    if len(review)!=39 or len(review)!=len(new_entries)+len(manual_queue):
        raise ValueError("Held candidates not accounted for")
    if any(x["old_hold_reason"]!="multiple_national_watershed_codes_same_name" for x in review if x["new_decision"]!="remain_held"):
        raise ValueError("Region conflict mistakenly promoted")
    oldlinks={(x["prefecture"],x["watershed"]) for x in data["prefecture_watershed_entries"]}
    if any((x["prefecture"],x["watershed"]) in oldlinks for x in new_entries):
        raise ValueError("Previously linked basin reconsidered as new")
    all_entrances=data["prefecture_watershed_entries"]+new_entries
    all_river_links=data["prefecture_river_links"]+new_river_links
    if len({(x["prefecture"],x["watershed"]) for x in all_entrances})!=len(all_entrances):
        raise ValueError("Duplicated prefecture and basin")
    if len({(x["prefecture"],x["watershed"],x["identity_key"]) for x in all_river_links})!=len(all_river_links):
        raise ValueError("Duplicated navigation river")
    if any(x["prefecture"]=="熊本県" and x["watershed"]=="大野川" for x in new_entries):
        raise ValueError("Dangerous local name collision in Kumamoto Oita Ono")
    if any(x["prefecture"]=="愛媛県" and x["watershed"]=="渡川" for x in new_entries):
        raise ValueError("Dangerous local name collision in Ehime Kochi Watari")
    if any(x["prefecture"]=="佐賀県" and x["watershed"]=="那珂川" for x in new_entries):
        raise ValueError("Kyushu/Kanto Nakagawa mixing")
    for p in data["prefectures"]:
        p["available_watersheds"]=sum(x["prefecture"]==p["prefecture"] for x in all_entrances)
        p["status"]="research_watershed_entries_available" if p["available_watersheds"] else "no_correlated_watershed_yet"
    data.update({
        "schema_version":"research-pref-nav-v07",
        "prefecture_watershed_entries":all_entrances,
        "prefecture_river_links":all_river_links,
        "notice":"Navigational PREFECTURE/BASIN link only. Each river's real location within the prefecture is unverified unless listed in independent prefecture river evidence. Historical four-category survey labels are unchanged.",
        "source_region_code_evidence_urls":SOURCES
    })
    report={
      "version":"v07","prev_v06_basin_entries":len(oldlinks),
      "prev_v06_river_links":len(data["prefecture_river_links"])-len(new_river_links),
      "held_from_v06":len(review),
      "now_added_major_basin_documentary_entries":len(new_entries),
      "still_held_after_major_basin_check":len(manual_queue),
      "new_prefecture_to_river_display_links":len(new_river_links),
      "total_navigation_entries":len(all_entrances),
      "total_prefecture_river_display_links":len(all_river_links),
      "prefectures_with_navigation":sum(p["available_watersheds"]>0 for p in data["prefectures"]),
      "full_47_prefecture_options":len(data["prefectures"]),
      "underlying_river_name_identities_unchanged":len(data["rivers"]),
      "underlying_biota_contexts_unchanged":sum(int(r["survey_record_contexts"]) for r in data["rivers"]),
      "independently_verified_national_bureau_code":"81..89, administrative only, NOT prefecture",
      "second_class_prefecture_code_means_river_mouth_not_entire_basin":True,
      "national_source_spec_urls":SOURCES,
      "no_site_or_mysql_changes":True,
      "no_physical_river_prefecture_inference":True,
      "biota_scope_only_individual_rivers":True,
      "same_name_local_secondclass_collisions_remaining":sum(
          x["review_reason"]=="local_second_class_same_name_possible_in_source_prefecture" for x in manual_queue),
      "held_examples":manual_queue
    }
    if report["underlying_biota_contexts_unchanged"]!=553351:
        raise ValueError("Biota conservation failed")
    (out/"prefecture_navigation_audit_v07.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (out/"river_atlas_navigation_v07.json").write_text(json.dumps(data,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    (out/"basin_collision_review_v07.json").write_text(json.dumps(review,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    with (out/"new_watershed_navigation_v07.csv").open("w",newline="",encoding="utf-8") as f:
        cols=["prefecture","watershed","documented_basin_code","survey_region","surveyed_river_name_ids","surveyed_river_contexts","navigation_status"]
        w=csv.DictWriter(f,fieldnames=cols,extrasaction="ignore");w.writeheader();w.writerows(new_entries)
    print(json.dumps({k:v for k,v in report.items() if k!="held_examples"},ensure_ascii=False))
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",required=True)
    p.add_argument("--v06-json");p.add_argument("--v06-audit")
    a=p.parse_args();build(a.out,a.v06_json,a.v06_audit)
