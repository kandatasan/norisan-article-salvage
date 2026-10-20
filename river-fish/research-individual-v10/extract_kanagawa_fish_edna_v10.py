#!/usr/bin/env python3
"""Extract NEW Kanagawa 2025 fish eDNA read-positive historical evidence.

NO specimens, actual fish sightings, fish abundance or current presence is
claimed. Existing 428 river data is not altered. Every positive record is
marked as METHOD=eDNA, from an official prefectural 2025 detection MATRIX.

Conservative input gates:
- exact prefectural Excel URL and pinned SHA256
- sheet header rows 3: watershed, 4: explicitly named tributary
- sheet manual taxa name F, taxa class A = Actinopterygii or lamprey
- J taxa confidence '高' or '中'; low confidence withheld
- >0 sequencing reads (never interpreted as fish count)
- annual collection dates in 2025
- exclude non-river spring/waterworks/section titles
- keep per-river distinct species-label names (not formally verified taxa)
- never store source station IDs, people, municipality, GPS, exact sampling sites
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import re
from audit_kanagawa_edna_matrix_v10 import read_data,clean_river_label,URL,PINNED

ROOT=Path(__file__).resolve().parents[1]
V05=ROOT/"research-individual-v05/outputs/name_first_rivers_v05.csv"
LICENSE="https://www.pref.kanagawa.jp/documents/97797/riyo-kiyaku.pdf"
PARENT="https://www.pref.kanagawa.jp/docs/b4f/suigen/edna.html"
CLASS_FISH={"条鰭綱","ヤツメウナギ綱"}
CONFIDENCE={"高","中"}
BAD_NAMES=re.compile(r"(?:湧水|河口|本流|本川|用水|水路|水道|湖|池|沼|ダム|貯水池|運河)$")
COLUMNS=["evidence_id","prefecture","watershed_name","river_name",
         "category","verbatim_manual_taxon_label","source_taxon_confidence",
         "survey_year","positive_sample_columns",
         "survey_method","reliability","source_url",
         "license_url","method_disclaimer","existing_code_optional",
         "record_status","existing_name_first_identity"]
def existing():
    with V05.open(encoding="utf-8",newline="") as f:
        return {(r["watershed_name"],r["river_name"]):r
                for r in csv.DictReader(f) if r["region"]=="kanto"}
def safe_taxon(t):
    t=t.strip()
    if not t or t in ("-","不明","種不明") or re.search(r"\[|<|>|[^\S ]",t):return False
    if "生息分布詳細不明" in t or "機械的" in t:return False
    return len(t)<=160

def run(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    db=read_data()
    if db[1].get("F")!="種名(手動精査結果)シュメイシュドウセイサケッカ" or db[4].get("P")!="支川名シセンメイ":
        raise ValueError("Original government sheet headings changed")
    basins=db[3];branches=db[4];dates=db[6]
    codes={}
    excluded_stations=Counter()
    all_stations=set()
    for col,raw in branches.items():
        if col=="P":continue
        base=clean_river_label(basins.get(col,""))
        river=clean_river_label(raw)
        if not base or not river:continue
        if not river.endswith(("川","沢")):
            excluded_stations["not_plain_named_river"]+=1;continue
        if BAD_NAMES.search(river):
            excluded_stations["waterbody_or_section"]+=1;continue
        date=str(dates.get(col,"")).strip()
        if not re.fullmatch(r"2025\d{4}",date):
            excluded_stations["not_2025_dated_tributary"]+=1;continue
        codes[col]=(base,river)
        all_stations.add(col)
    if len(codes)<20:raise ValueError("Too few named river eDNA columns")

    records=defaultdict(set)
    class_cnt=Counter();conf_cnt=Counter();held_bad_conf=Counter();held_tax=Counter()
    rows_examined=0
    for num in range(8,783):
        row=db.get(num,{})
        if row.get("A") not in CLASS_FISH:continue
        rows_examined+=1
        confidence=row.get("J","").strip()
        manual=str(row.get("F","")).strip()
        if confidence not in CONFIDENCE:
            held_bad_conf[confidence]+=1;continue
        if not safe_taxon(manual):
            held_tax[manual[:75]]+=1;continue
        for col,(water,river) in codes.items():
            val=row.get(col)
            if not val:continue
            try:reads=float(val)
            except ValueError:continue
            if not math.isfinite(reads) or reads<0:raise ValueError("Impossible sequencing read count")
            if reads>0:
                records[(water,river,manual,confidence)].add(col)
                class_cnt[row["A"]]+=1
                conf_cnt[confidence]+=1
    old=existing()
    entries=[]
    rivers=defaultdict(list)
    for (water,river,taxon,confidence),samples in sorted(records.items()):
        old_row=old.get((water,river))
        status="supplement_for_existing_named_river" if old_row else "new_prefectural_edna_named_river"
        evidence_id=hashlib.sha256(json.dumps([water,river,taxon,confidence,2025],ensure_ascii=False).encode()).hexdigest()[:24]
        row={
            "evidence_id":"edna25_"+evidence_id,
            "prefecture":"神奈川県",
            "watershed_name":water,"river_name":river,
            "category":"fish","verbatim_manual_taxon_label":taxon,
            "source_taxon_confidence":confidence,
            "survey_year":2025,"positive_sample_columns":len(samples),
            "survey_method":"environmental_DNA_positive_sequence_reads",
            "reliability":"candidate_detected_DNA_not_confirmed_organism_present",
            "source_url":URL,"license_url":LICENSE,
            "method_disclaimer":"eDNA positive reads may originate from upstream/external DNA or sequencing uncertainty; not an observed live fish",
            "existing_code_optional":old_row["river_code_optional"] if old_row else "",
            "record_status":status,
            "existing_name_first_identity":old_row["identity_key"] if old_row else ""
        }
        entries.append(row);rivers[(water,river)].append(row)
    if len(rivers)<15 or not entries:
        raise ValueError("Too few conservative river names with independently recorded 2025 fish eDNA")
    groups=[]
    for (water,river),items in sorted(rivers.items()):
        status=items[0]["record_status"]
        if len({r["verbatim_manual_taxon_label"] for r in items})!=len(items):
            raise ValueError("One taxon label appears in both confidence classes without resolution")
        groups.append({
            "prefecture":"神奈川県","watershed_name":water,
            "river_name":river,"detection_method":"eDNA",
            "recorded_taxon_label_count":len(items),
            "high_confidence_taxon_labels":sum(x["source_taxon_confidence"]=="高" for x in items),
            "medium_confidence_taxon_labels":sum(x["source_taxon_confidence"]=="中" for x in items),
            "survey_year":2025,
            "record_status":status,
            "not_present_in_existing_428":status=="new_prefectural_edna_named_river",
            "source_url":URL,
            "publication_disclaimer":"Detected DNA is not proof of living organisms at the exact sampling river or a direct specimen capture",
            "river_geographic_identity":"explicit_watershed_and_tributary_from_official_sheet; exact location not stored"
        })
    csvout=out/"kanagawa_2025_tributary_fish_edna_candidate_labels_v10.csv"
    with csvout.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=COLUMNS);w.writeheader();w.writerows(entries)
    (out/"kanagawa_2025_tributary_fish_edna_rivers_v10.json").write_text(json.dumps(groups,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    report={
        "source_url":URL,"source_sha256":PINNED,"license_url":LICENSE,
        "source_parent_page":PARENT,
        "survey_method":"eDNA_fish_lamprey_detection_2025_not_catch_or_sighting",
        "explicit_tributary_columns_with_2025_date":len(codes),
        "fish_taxon_rows_reviewed":rows_examined,
        "read_positive_unique_manual_labels_with_river":len(entries),
        "recorded_name_rivers_from_prefecture_eDNA":len(rivers),
        "new_name_pairs_not_in_base_428":sum(x["not_present_in_existing_428"] for x in groups),
        "overlap_with_existing_named_river":sum(not x["not_present_in_existing_428"] for x in groups),
        "high_confidence_taxa_records":sum(x["source_taxon_confidence"]=="高" for x in entries),
        "medium_confidence_taxa_records":sum(x["source_taxon_confidence"]=="中" for x in entries),
        "excluded_stations":dict(excluded_stations),
        "excluded_low_confidence_taxa_rows":dict(held_bad_conf),
        "excluded_nonliteral_taxa_names":dict(held_tax),
        "source_method_separate_from_existing_553351_survey_contexts":True,
        "no_existing_biota_db_changed":True,"wordPress_or_mysql_changed":False,
        "fish_live_capture_observations_added":0,
        "no_coordinates_or_detailed_sites_saved":True,
        "rights_note":"Commercial re-use on source page allowed with clear attribution and source modification notice, but third-party rights must be checked separately."
    }
    if report["read_positive_unique_manual_labels_with_river"]!=len(entries) or len(set(x["evidence_id"] for x in entries))!=len(entries):
        raise ValueError("Evidence IDs not unique")
    (out/"kanagawa_2025_edna_fish_provenance_audit_v10.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))
    return report

if __name__=="__main__":
    a=argparse.ArgumentParser();a.add_argument("--out",required=True)
    run(a.parse_args().out)
