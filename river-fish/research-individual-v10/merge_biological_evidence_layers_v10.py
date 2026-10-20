#!/usr/bin/env python3
"""Join existing atlas research names, safe held-name groups and distinct eDNA.

This is a manifest ONLY, no modification of previously verified v09 static
biota packs, original v05 SQLite, WordPress or live databases. The three
layers have fundamentally DIFFERENT biological evidence quality.

428 conventional named survey rivers: survey historic names.
40 code-ambiguous historical river NAME buckets: do NOT count physical rivers.
24 new Kanagawa eDNA-only named streams: DNA traces, NOT physical catches.
2 matched former survey river names receive supplemental eDNA method records.
"""
from __future__ import annotations
from collections import Counter,defaultdict
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
V09=ROOT/"research-individual-v09/outputs/manifest_v09.json"
OUT=ROOT/"research-individual-v10/outputs"
def obj(path):return json.loads(Path(path).read_text(encoding="utf-8"))
def run(out):
    original=obj(V09)
    held=obj(OUT/"held_name_only_manifest_v10.json")
    dna=obj(OUT/"kanagawa_2025_tributary_fish_edna_rivers_v10.json")
    if len(original["rivers"])!=428 or len(held["entries"])!=40 or len(dna)!=26:
        raise ValueError("Expected v09+v10 evidence layers missing or changed")
    combined=[]
    old_by_name=defaultdict(list)
    for r in original["rivers"]:
        x={
            "identity_key":r["identity_key"],"source_region":r["source_region"],
            "watershed_name":r["watershed"],"river_name":r["river_name"],
            "river_code_optional":r["river_code_optional"],
            "documentary_evidence_level":"original_national_river_survey_context",
            "legal_river_identity_exact":bool(r["river_code_optional"]),
            "category_method":"historical_national_river_survey",
            "historical_record_contexts":r["historical_contexts"],
            "biological_fish_survey_data_location":"v09 region archives",
            "eDNA_supplement":False,"is_new_external_source_only":False
        }
        combined.append(x);old_by_name[(r["source_region"],r["watershed"],r["river_name"])].append(x)
    if len({r["identity_key"] for r in combined})!=428:raise ValueError("Duplicate original identity")
    for r in held["entries"]:
        key=(r["source_region"],r["survey_watershed"],r["survey_river_label"])
        if key in old_by_name:raise ValueError("Previously-held source name was already in 428")
        x={
            "identity_key":r["identity_key"],
            "source_region":r["source_region"],
            "watershed_name":r["survey_watershed"],
            "river_name":r["survey_river_label"],
            "river_code_optional":None,
            "documentary_evidence_level":"literal_survey_river_name_but_10digit_segment_ambiguous",
            "legal_river_identity_exact":False,
            "category_method":"historical_survey_river_name_multiple_code_candidates",
            "historical_record_contexts":r["historic_record_contexts"],
            "biological_fish_survey_data_location":"v10 held_river_name_biology ZIP, four categories",
            "eDNA_supplement":False,"is_new_external_source_only":False
        }
        combined.append(x)
        old_by_name[key]=[x]
    overlays=0;new_edna=0
    for r in dna:
        name=(r["watershed_name"],r["river_name"])
        key=("kanto",)+name
        original_matches=old_by_name.get(key,[])
        if len(original_matches)>1:raise ValueError("Ambiguous same-name river in source corpus")
        if r["not_present_in_existing_428"]:
            if original_matches:raise ValueError("eDNA new name has an existing research record")
            keyval="edna25_"+hashlib.sha256(json.dumps(["神奈川県",*name],ensure_ascii=False).encode()).hexdigest()[:24]
            x={"identity_key":keyval,"source_region":"kanto",
               "prefecture_documented":"神奈川県",
               "watershed_name":name[0],"river_name":name[1],
               "river_code_optional":None,
               "documentary_evidence_level":"official_prefectural_explicit_2025_tributary_name",
               "legal_river_identity_exact":False,
               "category_method":"prefectural_environmental_DNA_only",
               "historical_record_contexts":0,
               "biological_fish_survey_data_location":"v10 official Kanagawa eDNA fish read-positive file",
               "eDNA_supplement":True,
               "eDNA_manual_label_count":r["recorded_taxon_label_count"],
               "eDNA_year":2025,
               "edna_is_not_live_fish_capture":True,
               "eDNA_source_url":r["source_url"],
               "is_new_external_source_only":True}
            combined.append(x);new_edna+=1
        else:
            if len(original_matches)!=1 or original_matches[0]["documentary_evidence_level"]!="original_national_river_survey_context":
                raise ValueError("eDNA overlap with an old survey river is not independently confirmed")
            original_matches[0]["eDNA_supplement"]=True
            original_matches[0]["eDNA_manual_label_count"]=r["recorded_taxon_label_count"]
            original_matches[0]["eDNA_year"]=2025
            original_matches[0]["edna_is_not_live_fish_capture"]=True
            original_matches[0]["eDNA_source_url"]=r["source_url"]
            overlays+=1
    if new_edna!=24 or overlays!=2 or len(combined)!=492:
        raise ValueError("Provenance layers do not conserve the original river names")
    if sum(x["historical_record_contexts"] for x in combined)!=651435:
        raise ValueError("Original 553351 + held-name 98084 contexts do not match")
    if sum(x.get("eDNA_manual_label_count",0) for x in combined)!=265:
        raise ValueError("Original eDNA manual fish labels not conserved")
    if len({x["identity_key"] for x in combined})!=len(combined):
        raise ValueError("Duplicate river label group ID")
    for x in combined:
        if x["category_method"]=="prefectural_environmental_DNA_only":
            if x["historical_record_contexts"] or x["legal_river_identity_exact"]:
                raise ValueError("eDNA source records may not be treated as direct historical survey")
        if x["category_method"]=="historical_survey_river_name_multiple_code_candidates" and x["legal_river_identity_exact"]:
            raise ValueError("Unproven physical river segments given a false 10-digit identity")
    counts=dict(Counter(x["category_method"] for x in combined))
    summary={
        "original_verifiable_survey_river_names":428,
        "provisional_same_name_segment_ambiguous_labels":40,
        "new_official_prefectural_edna_only_river_names":24,
        "new_eDNA_method_overlays_to_existing_names":2,
        "combined_source_named_river_label_groups":492,
        "sum_of_historic_named_survey_contexts":651435,
        "of_which_original_428_contexts":553351,
        "of_which_held_name_scope_contexts":98084,
        "edna_2025_distinct_taxon_source_labels":265,
        "edna_2025_labels_in_new_24_rivers":sum(x["eDNA_manual_label_count"] for x in combined if x["is_new_external_source_only"]),
        "fish_capture_records_from_edna":0,
        "biological_methods_never_interchangeable":True,
        "40_provisional_name_groups_are_not_40_verified_distinct_physical_rivers":True,
        "source_names_with_no_geocoding_not_assigned_to_prefecture":True,
        "exact_sample_sites_excluded":True,
        "wordPress_and_production_database_unchanged":True,
        "method_group_counts":counts,
        "notes":"492 is a count of distinct display-name EVIDENCE GROUPS from several source methods, not geocoded river bodies or a verified biological species count. The 40 ambiguous labels are shown as their source river NAME only. eDNA detections are kept distinct."
    }
    output=Path(out);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps({"audit":summary,"entries":combined},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (output.parent/"biological_data_layer_summary_v10.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False))
    return summary
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",required=True)
    a=p.parse_args();run(a.out)
