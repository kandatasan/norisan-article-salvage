#!/usr/bin/env python3
"""Research-only prefecture -> documented watershed -> source river -> 4 biology categories.

Never infer that EVERY listed watershed tributary actually flows inside the
chosen prefecture. A prefecture source establishes only an evidence-limited
prefecture/watershed context, unless it itself names a particular river.

The v05 biota SQLite is read-only and remains unchanged. No live site access.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import csv
import hashlib
import json
from pathlib import Path
import sqlite3
from urllib.parse import quote
ROOT=Path(__file__).resolve().parents[1]
BASE_SHA="dfa193bc882dfbc1dc3c30dc226bf81bc2e3754007069fed1b25e3007f4c1dd1"
LEVELS={"watershed","river"}
GROUPS={"fish":"魚類","benthic_animals":"底生動物","birds":"鳥類","plants":"植物"}

def source_rows(path):
    with Path(path).open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()

def load_existing_official_mentions():
    """Only rows whose official source explicitly states the watershed."""
    entries=[]
    def add(pref,water,river,kind,origin,source_id,url,date,scope):
        if not pref or not water or not url.startswith("https://"):
            raise ValueError("Invalid official provenance")
        if kind not in LEVELS:raise ValueError("Unrecognized official source scope")
        if kind=="watershed" and river:raise ValueError("Watershed-only evidence cannot claim direct river")
        if kind=="river" and not river:raise ValueError("River mention must include exact name")
        entries.append({
            "prefecture":pref,"watershed":water,"river":river or "",
            "kind":kind,"source_registry":origin,"source_id":source_id,
            "source_url":url,"source_date":date or "","source_scope":scope
        })
    for r in source_rows(ROOT/"remaining_32pref_source_mentions_v14.csv"):
        typ=r["label_type"]
        if typ=="planning_region":continue
        water=r["watershed_explicit_in_source"]
        if not water:continue
        if typ=="watershed":
            if r["name_as_written"]!=water:raise ValueError("v14 official watershed name mismatch")
            add(r["prefecture"],water,"","watershed","v14",r["mention_id"],r["source_page_url"],r["page_date_if_available"],r["source_document_scope"])
        elif typ=="river":
            add(r["prefecture"],water,r["name_as_written"],"river","v14",r["mention_id"],r["source_page_url"],r["page_date_if_available"],r["source_document_scope"])
    for r in source_rows(ROOT/"multi_prefecture_source_mentions_v13.csv"):
        typ=r["evidence_kind"]
        if typ not in LEVELS:continue
        water=r["watershed_explicit_in_source"]
        if not water:continue
        if typ=="watershed":
            if r["literal_name"]!=water:raise ValueError("v13 official watershed mismatch")
            add(r["prefecture"],water,"","watershed","v13",r["evidence_id"],r["source_url"],r["source_as_of_if_stated"],r["source_scope"])
        elif typ=="river":
            add(r["prefecture"],water,r["literal_name"],"river","v13",r["evidence_id"],r["source_url"],r["source_as_of_if_stated"],r["source_scope"])
    for r in source_rows(ROOT/"chugoku_second_class_watersheds_v10.csv"):
        add(r["prefecture"],r["watershed_label_as_written"],"","watershed","v10",r["record_id"],r["source_page_url"],r["source_page_updated_date_if_verified"],r["source_coverage"])
    for r in source_rows(ROOT/"river_registry_hiroshima_v01.csv"):
        if r["record_status"]!="source_name_confirmed":continue
        add(r["prefecture"],r["watershed"],r["river_name"],"river","hiroshima_v01",r["river_id"],r["source_url"],r["source_document_year"],"historic_prefecture_river_registry")
    for r in source_rows(ROOT/"yamaguchi_river_municipality_mentions_v10.csv"):
        add(r["prefecture"],r["watershed_label_as_written"],r["river_name_as_written"],"river","yamaguchi_v10",r["evidence_id"],r["source_url"],r["page_last_updated"],r["source_document_context"])
    return entries

def compute(db,out):
    db=Path(db).resolve();out=Path(out)
    if sha(db)!=BASE_SHA:raise ValueError("v05 DB source checksum changed")
    pref_rows=source_rows(ROOT/"japan_prefectures_v06.csv")
    prefs={r["prefecture_name"]:r["jis_prefecture_code"] for r in pref_rows}
    if len(prefs)!=47 or len(set(prefs.values()))!=47:raise ValueError("Prefecture master changed")
    official=load_existing_official_mentions()
    if set(x["prefecture"] for x in official)-set(prefs):raise ValueError("Official mention cites unknown prefecture")
    conn=sqlite3.connect("file:"+quote(str(db),safe="/")+"?mode=ro",uri=True)
    conn.execute("PRAGMA query_only=ON");conn.row_factory=sqlite3.Row
    try:
        if conn.execute("SELECT COUNT(*) FROM name_first_rivers WHERE review_status='eligible'").fetchone()[0]!=428:
            raise ValueError("Unexpected named river identity count")
        if conn.execute("SELECT COUNT(*) FROM name_first_evidence").fetchone()[0]!=553351:
            raise ValueError("Unexpected named river evidence count")
        river_data=[dict(r) for r in conn.execute("""
          SELECT identity_key,region,source_authority,watershed_name,river_name,
                 river_code,code_confidence,survey_record_contexts
          FROM name_first_rivers WHERE review_status='eligible'
          ORDER BY region,watershed_name,river_name
        """)]
        surveyed=defaultdict(list)
        for river in river_data:surveyed[river["watershed_name"]].append(river)
        watersheds_by_pair=defaultdict(list)
        for ev in official:watersheds_by_pair[(ev["prefecture"],ev["watershed"])].append(ev)
        links=[];held=[];unmatched=[];proof_river=defaultdict(list)
        all_mentions=set()
        for (pref,water),evidence in sorted(watersheds_by_pair.items()):
            matches=surveyed.get(water,[])
            regions={r["region"] for r in matches}
            pair=(pref,water)
            if not matches:
                unmatched.append({"prefecture":pref,"watershed":water,"documentary_evidence":len(evidence),
                                  "status":"official_name_only_no_covered_biota_river"})
                continue
            if len(regions)!=1:
                held.append({"prefecture":pref,"watershed":water,"possible_source_regions":sorted(regions),
                             "reason":"same_watershed_name_under_multiple_survey_authorities",
                             "evidence_urls":sorted({e["source_url"] for e in evidence})})
                continue
            # This is an official prefecture document entry-point, NOT a
            # confirmed prefecture location for every river in the watershed.
            region=next(iter(regions))
            linked_rivers=[]
            for river in matches:
                exact=[e for e in evidence if e["kind"]=="river" and e["river"]==river["river_name"]]
                if exact:
                    proof_river[(pref,water,river["identity_key"])]=exact
                linked_rivers.append(river)
            links.append({
                "prefecture":pref,"jis_prefecture_code":prefs[pref],
                "watershed":water,"survey_region":region,
                "surveyed_river_name_ids":len(linked_rivers),
                "surveyed_river_contexts":sum(int(r["survey_record_contexts"]) for r in linked_rivers),
                "watershed_official_mentions":sum(e["kind"]=="watershed" for e in evidence),
                "river_official_mentions":sum(e["kind"]=="river" for e in evidence),
                "official_evidence_urls":sorted({e["source_url"] for e in evidence}),
                "navigation_status":"prefecture_official_watershed_name_and_survey_name_agree",
                "no_claim_all_watershed_rivers_within_prefecture":True,
                "no_verified_physical_tributary_relationship":True
            })
        all_links={(x["prefecture"],x["watershed"]) for x in links}
        for x in links:
            if not x["official_evidence_urls"]:raise ValueError("Uncited prefecture/watershed link")
        seen={(l["prefecture"],l["watershed"]) for l in links}
        if len(seen)!=len(links):raise ValueError("Duplicated prefecture watershed links")
        # Stream records once, keeping only sample labels per category in
        # memory; all-source counts are determined from the immutable v05 DB.
        grouped={}
        for r in conn.execute("""
            SELECT n.identity_key,s.group_id,COUNT(*) AS n_records,
                   COUNT(DISTINCT e.label_id) AS literal_names,
                   MIN(e.survey_year) AS year_min,MAX(e.survey_year) AS year_max
            FROM name_first_rivers n
            JOIN name_first_context_links k ON k.identity_key=n.identity_key
            JOIN river_evidence e ON e.river_context_id=k.context_id
            JOIN sources s ON s.id=e.source_id
            WHERE n.review_status='eligible'
            GROUP BY n.identity_key,s.group_id
        """):
            grouped[(r["identity_key"],r["group_id"])]={
                "record_contexts":r["n_records"],"literal_names_not_species":r["literal_names"],
                "year_min":r["year_min"],"year_max":r["year_max"]
            }
        if sum(g["record_contexts"] for g in grouped.values())!=553351:
            raise ValueError("Source-record conservation failed")
        # Only enrich with two example name labels per group; these are public
        # historic survey names, never precise observation points.
        example={}
        for r in conn.execute("""
            SELECT n.identity_key,s.group_id,e.survey_year,lb.recorded_name,s.source_url
            FROM name_first_rivers n
            JOIN name_first_context_links k ON k.identity_key=n.identity_key
            JOIN river_evidence e ON e.river_context_id=k.context_id
            JOIN sources s ON s.id=e.source_id JOIN labels lb ON lb.id=e.label_id
            WHERE n.review_status='eligible'
            ORDER BY n.identity_key,s.group_id,e.survey_year,lb.recorded_name
        """):
            key=(r["identity_key"],r["group_id"])
            a=example.setdefault(key,[])
            if len(a)<2:a.append({"survey_year":r["survey_year"],"recorded_name":r["recorded_name"],
                                  "source_url":r["source_url"]})
        for river in river_data:
            river["biota"]={}
            for group,label in GROUPS.items():
                q=grouped.get((river["identity_key"],group),{
                    "record_contexts":0,"literal_names_not_species":0,
                    "year_min":None,"year_max":None
                })
                river["biota"][group]={"category_label":label,**q,"examples":example.get((river["identity_key"],group),[])}
        # Every prefecture is a valid UI choice, with explicit zero coverage.
        region_list=[]
        for pref,code in sorted(prefs.items(),key=lambda p:p[1]):
            l=[x for x in links if x["prefecture"]==pref]
            region_list.append({
                "prefecture":pref,"code":code,
                "available_watersheds":len(l),
                "status":"research_watershed_entries_available" if l else "no_correlated_watershed_yet"
            })
        pairs=[]
        for link in links:
            waters=sorted(surveyed[link["watershed"]],key=lambda r:r["river_name"])
            for riv in waters:
                direct=proof_river.get((link["prefecture"],link["watershed"],riv["identity_key"]),[])
                pairs.append({
                    "prefecture":link["prefecture"],"watershed":link["watershed"],
                    "identity_key":riv["identity_key"],"river_name":riv["river_name"],
                    "individual_river_explicit_prefecture_mentions":len(direct),
                    "individual_river_prefecture_evidence_urls":sorted({e["source_url"] for e in direct}),
                    "river_location_in_prefecture":"source_mentioned" if direct else "unverified",
                    "river_is_within_referenced_watershed":"survey_source_name_only"
                })
        # Link-to-river is navigational, not a new observation or an inferred river location.
        if not links or not pairs:raise ValueError("No prefecture navigation entries were built")
        out.mkdir(parents=True,exist_ok=True)
        def write(name,cols,rows):
            with (out/name).open("w",encoding="utf-8",newline="") as f:
                w=csv.DictWriter(f,fieldnames=cols,extrasaction="ignore");w.writeheader();w.writerows(rows)
        write("prefecture_watershed_navigation_v06.csv",
              ["prefecture","jis_prefecture_code","watershed","survey_region",
               "surveyed_river_name_ids","surveyed_river_contexts",
               "watershed_official_mentions","river_official_mentions","navigation_status"],links)
        write("prefecture_river_navigation_v06.csv",
              ["prefecture","watershed","identity_key","river_name",
               "individual_river_explicit_prefecture_mentions","river_location_in_prefecture"],pairs)
        write("unlinked_official_watersheds_v06.csv",
              ["prefecture","watershed","documentary_evidence","status"],unmatched)
        report={
            "version":"v06","source_db_sha256":BASE_SHA,
            "prefectures_offered":47,"official_prefecture_source_rows":len(official),
            "official_prefecture_watershed_pairs":len(watersheds_by_pair),
            "linked_prefecture_watershed_pairs":len(links),
            "prefectures_with_verified_documentary_navigation":len({l["prefecture"] for l in links}),
            "prefectures_pending_matching_documentary_navigation":47-len({l["prefecture"] for l in links}),
            "prefecture_to_survey_river_display_links":len(pairs),
            "river_links_with_direct_official_prefecture_river_mention":sum(bool(x["individual_river_explicit_prefecture_mentions"]) for x in pairs),
            "unmatched_documented_watershed_pairs":len(unmatched),
            "withheld_multiple_survey_region_watershed_labels":len(held),
            "unmatched_examples":unmatched[:25],"held_ambiguities":held,
            "original_named_rivers_unchanged":len(river_data),
            "original_name_first_biota_contexts_unchanged":sum(g["record_contexts"] for g in grouped.values()),
            "navigation_is_documentary_not_geographic":True,
            "river_prefecture_not_inferred_from_watershed":True,
            "prefecture_does_not_imply_all_tributaries_inside":True,
            "code_not_required":True,"watershed_has_no_biota_panel":True,
            "sensitive_survey_coordinates_included":False,
            "production_modified":False
        }
        (out/"prefecture_navigation_audit_v06.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        data={"schema_version":"research-pref-nav-v06",
              "prefectures":region_list,
              "prefecture_watershed_entries":links,
              "prefecture_river_links":pairs,
              "rivers":river_data,
              "notice":"Prefecture source mentions a watershed. Rivers listed below belong to that named watershed in research survey records; individual river locations within the prefecture are unverified unless separately documented. Historical survey names are not current biological presence."}
        (out/"river_atlas_navigation_v06.json").write_text(json.dumps(data,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
        print(json.dumps({k:v for k,v in report.items() if k not in ("unmatched_examples","held_ambiguities")},ensure_ascii=False))
        return report
    finally:conn.close()

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--biota-db",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    compute(a.biota_db,a.out)
