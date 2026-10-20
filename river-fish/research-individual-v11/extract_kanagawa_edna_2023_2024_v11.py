#!/usr/bin/env python3
"""Extract *DNA detections only* from five SHA-pinned Kanagawa official XLSX.

Five distinct original datasets: 2023 source fish, 2023 source insects,
2023 prefecturewide fish, 2024 source vertebrate/invertebrate, 2024
prefecturewide vertebrate/invertebrate. Methods and years are never merged
with historical specimen/visual surveys or v10 2025 fish detections.

Biological labels are verbatim (not validated species); 2023 fish workbook
has NO identification-confidence column, so confidence is "not_reported".
Insect/invertebrate read positives are NOT direct proof of benthic organisms.
No site IDs, coordinates, detailed station locations or participant data export.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile
import csv
import hashlib
import json
import math
import posixpath
import re

from scan_kanagawa_edna_2023_2024_v11 import BASE, SOURCES, get, N, R

HERE = Path(__file__).resolve().parent
BASELINE = HERE.parent / "research-individual-v10/outputs/research_biological_method_layers_v10.json"
OUT = HERE / "outputs"
PINS = {
    "2023_source_fish": "60c18a87a9522c5f8bd0ba90021d58a663a5b3696f5592a033ff85f8ed78d62a",
    "2023_source_insects": "50865de054e4ac12c097ca4ee8e880713f45b3947cd30364684854079e3957fc",
    "2023_prefecturewide_fish": "6292c5829709c7677abf83c6e18437205ea3b3d3964c9bf67a4f2086bce7d48c",
    "2024_source_vertebrates_invertebrates": "fdfc28f2c470625429334e603d62d212b4f7bb5c4bb3bd521c91c500397ab11a",
    "2024_prefecturewide_vertebrates_invertebrates": "0655f626405ae5a883ae2dba1589277f381fee170a2a2bf6735a304ca58b1258",
}
# Fixed mapping based on observed, independently SHA-checked column headings.
# In modern files row 3 contains water-system names, row 4 tributaries,
# row 5 dates. The 2023 fish matrices instead put survey dates on row 6.
CONFIG = {
    "2023_source_fish": dict(year=2023,sheet="R5魚類",start=7,name="E",cl="A",conf=None,date=6),
    "2023_prefecturewide_fish": dict(year=2023,sheet="R5プロジェクト_魚類",start=7,name="E",cl="A",conf=None,date=6),
    "2023_source_insects": dict(year=2023,sheet="結果まとめ(種落ち)",start=7,name="F",cl="A",conf="H",date=5),
    "2024_source_vertebrates_invertebrates": dict(year=2024,sheet="結果まとめ(種落ち)",start=7,name="G",cl="B",conf="I",date=5),
    "2024_prefecturewide_vertebrates_invertebrates": dict(year=2024,sheet="結果まとめ(種落ち)",start=7,name="F",cl="A",conf="H",date=5),
}
LICENSE = "https://www.pref.kanagawa.jp/documents/97797/riyo-kiyaku.pdf"
PARENT = "https://www.pref.kanagawa.jp/docs/b4f/suigen/edna.html"
BAD_RIVER = re.compile(r"脇|付近|周辺|小河川|用水|水路|湧水|河口|本流|本川|ダム|貯水|水道|運河|地点|橋|公園|支川")
COLUMNS = ["evidence_id","prefecture","watershed_name","river_name","river_code_optional",
           "survey_year","biological_group","verbatim_source_taxon_label","taxonomic_class_verbatim",
           "identification_confidence_verbatim","positive_station_columns_aggregate",
           "survey_method","source_dataset_key","source_file_sha256","source_url","source_page_url",
           "usage_policy_url","existing_v10_display_name_group","record_status","reliability_note"]

def read_sheet(data, sheetname):
    with ZipFile(BytesIO(data)) as z:
        files=set(z.namelist())
        wb=ET.fromstring(z.read("xl/workbook.xml"))
        rel=ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        rels={el.get("Id"):el.get("Target") for el in rel}
        strings=[]
        if "xl/sharedStrings.xml" in files:
            strings=["".join(t.text or "" for t in s.iter(f"{{{N}}}t"))
                     for s in ET.fromstring(z.read("xl/sharedStrings.xml")).findall(f"{{{N}}}si")]
        for s in wb.findall(f".//{{{N}}}sheets/{{{N}}}sheet"):
            if s.get("name") != sheetname:
                continue
            target=rels[s.get(f"{{{R}}}id")]
            path=target.lstrip("/") if target.startswith("/") else posixpath.normpath("xl/"+target)
            root=ET.fromstring(z.read(path))
            rows={}
            for r in root.findall(f".//{{{N}}}sheetData/{{{N}}}row"):
                vals={}
                for c in r.findall(f"{{{N}}}c"):
                    col=re.sub(r"\d","",c.get("r",""))
                    v=c.find(f"{{{N}}}v")
                    value=v.text or "" if v is not None else ""
                    if c.get("t")=="s" and value.isdecimal():
                        value=strings[int(value)]
                    elif c.get("t")=="inlineStr":
                        value="".join(t.text or "" for t in c.iter(f"{{{N}}}t"))
                    if value!="":
                        vals[col]=str(value).strip()
                rows[int(r.get("r"))]=vals
            return rows
        raise ValueError("Expected scientific result sheet not found: "+sheetname)

def river_clean(v):
    v=str(v).strip()
    v=re.split(r"[\u30a1-\u30ff]",v,maxsplit=1)[0].strip()
    if BAD_RIVER.search(v) or len(v)>12:
        return None
    if re.fullmatch(r"[\u4e00-\u9fff々ヶぁ-んー]{1,12}",v) and v.endswith(("川","沢")):
        return v
    return None

def extract_year(v):
    v=str(v).strip()
    if not v: return None
    if re.fullmatch(r"\d{5}(\.0+)?",v):
        return (datetime(1899,12,30)+timedelta(days=float(v))).year
    m=re.search(r"20(2[34])(?:年度|年|[-/.]|[01]\d[0-3]\d)",v)
    if m: return int("20"+m.group(1))
    if re.fullmatch(r"202[34]\d{4}",v): return int(v[:4])
    return None

def biological_group(cl, source_key):
    # The source defines biological DNA from water; this is never specimen evidence.
    if source_key.endswith("_fish") and source_key.startswith("2023"):
        return "fish_edna" if cl in ("硬骨魚綱","条鰭綱","頭甲綱","ヤツメウナギ綱") else None
    if cl in ("硬骨魚綱","条鰭綱","頭甲綱","ヤツメウナギ綱"):
        return "fish_edna"
    if cl=="鳥綱":
        return "bird_edna_not_visual_observation"
    if cl=="昆虫綱":
        return "insect_edna_not_proven_benthic"
    if cl in ("軟甲綱","二枚貝綱","鰓脚綱","ミミズ綱","貧毛綱","腹足綱","トビムシ目","クモ綱","被喉綱"):
        return "other_invertebrate_edna_not_proven_benthic"
    # Terrestrial mammal DNA etc. isn't direct evidence for the four catalog windows.
    return None

def valid_name(v):
    if not v or len(v)>160 or v in ("-","不明","種不明"):
        return False
    if re.search(r"[\r\n\t<>]",v):
        return False
    return True

def numeric_positive(raw):
    try:
        x=float(raw)
    except (ValueError,TypeError):
        return False
    if not math.isfinite(x) or x<0:
        raise ValueError("Impossible sequencing read value")
    return x>0

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    base=json.loads(BASELINE.read_text(encoding="utf-8"))
    assert base["audit"]["combined_source_named_river_label_groups"]==492
    baseline_keys={(x["watershed_name"],x["river_name"]) for x in base["entries"] if x["source_region"]=="kanto"}
    assert baseline_keys
    allrows=[]
    audits=[]
    river_source_groups=defaultdict(lambda:defaultdict(set))
    cross_source_labels=defaultdict(set)
    for source_key,filename in SOURCES.items():
        spec=CONFIG[source_key]
        data=get(BASE+filename)
        sha=hashlib.sha256(data).hexdigest()
        if sha != PINS[source_key]:
            raise ValueError("Official original SHA changed: "+source_key)
        rows=read_sheet(data,spec["sheet"])
        # Fail closed if metadata column layout is changed.
        hdr=rows.get(6,{})
        if not hdr.get(spec["name"],"").startswith(("種名","参考")) and "種名" not in hdr.get(spec["name"],""):
            raise ValueError("Unexpected taxon heading for "+source_key)
        if spec["conf"] and "信頼度" not in (hdr.get(spec["conf"],"")+rows.get(1,{}).get(spec["conf"],"")):
            raise ValueError("Unexpected eDNA confidence heading for "+source_key)
        basinrow=rows.get(3,{})
        branchrow=rows.get(4,{})
        daterow=rows.get(spec["date"],{})
        cols={}
        excluded=Counter()
        for col,branch in branchrow.items():
            water=river_clean(basinrow.get(col,""))
            river=river_clean(branch)
            if not water or not river:
                if branch not in ("","-"):
                    excluded["not_explicit_named_river_and_water_system"]+=1
                continue
            dy=extract_year(daterow.get(col,""))
            if dy!=spec["year"]:
                excluded["other_year_or_unreadable_date"]+=1
                continue
            cols[col]=(water,river)
        if not cols:
            raise ValueError("No dated named tributary columns for "+source_key)
        source_evidence=defaultdict(set)
        low=Counter();cl_counts=Counter();raw_positive=0
        for row_no in range(spec["start"], max(rows)+1):
            row=rows.get(row_no,{})
            cl=row.get(spec["cl"],"")
            group=biological_group(cl,source_key)
            if not group:
                continue
            name=row.get(spec["name"],"").strip()
            if not valid_name(name):
                continue
            conf=row.get(spec["conf"],"").strip() if spec["conf"] else "not_reported"
            if spec["conf"] and conf not in ("高","中"):
                low[conf or "missing"]+=1
                continue
            for col,(water,river) in cols.items():
                if numeric_positive(row.get(col,"")):
                    key=(water,river,group,name,cl,conf)
                    source_evidence[key].add(col)
                    raw_positive+=1
                    cl_counts[group]+=1
        for (water,river,group,name,cl,conf),sitecols in sorted(source_evidence.items()):
            key=(spec["year"],water,river,group,name)
            cross_source_labels[key].add(source_key)
            evidence_id=hashlib.sha256(json.dumps(
                [source_key,spec["year"],water,river,group,name,conf],ensure_ascii=False
            ).encode("utf-8")).hexdigest()[:24]
            exists=(water,river) in baseline_keys
            entry={
                "evidence_id":"edna"+str(spec["year"])[2:]+"_"+evidence_id,
                "prefecture":"神奈川県","watershed_name":water,"river_name":river,
                "river_code_optional":"","survey_year":spec["year"],
                "biological_group":group,"verbatim_source_taxon_label":name,
                "taxonomic_class_verbatim":cl,"identification_confidence_verbatim":conf,
                "positive_station_columns_aggregate":len(sitecols),
                "survey_method":"environmental_DNA_positive_sequence_reads_not_capture",
                "source_dataset_key":source_key,"source_file_sha256":sha,
                "source_url":BASE+filename,"source_page_url":PARENT,"usage_policy_url":LICENSE,
                "existing_v10_display_name_group":bool(exists),
                "record_status":"additional_eDNA_method_year_on_v10_display_name" if exists else "new_official_edna_named_river_candidate",
                "reliability_note":"DNA detected in water; no proof of live animals or benthic habitat at that site; source label may represent multiple species"
            }
            allrows.append(entry)
            river_source_groups[(water,river)][spec["year"]].add(group)
        audits.append({
            "source_dataset_key":source_key,"survey_year":spec["year"],
            "official_xlsx_url":BASE+filename,"official_xlsx_sha256":sha,
            "sheet_name":spec["sheet"],"source_confidence_column":spec["conf"],
            "confidence_missing_in_original":spec["conf"] is None,
            "source_name_column":spec["name"],"survey_date_row":spec["date"],
            "validated_named_tributary_station_columns":len(cols),
            "positive_dna_station_taxon_cells_aggregate":raw_positive,
            "distinct_source_taxon_river_labels":len(source_evidence),
            "named_rivers_with_dna":len({(x[0],x[1]) for x in source_evidence}),
            "biological_group_positive_cells":dict(cl_counts),
            "held_taxon_rows_bad_or_missing_confidence":dict(low),
            "excluded_geographic_headers":dict(excluded),
            "no_direct_capture_observation":True,"no_precise_sites_exported":True})
        print(json.dumps({"source":source_key,"named_rivers":audits[-1]["named_rivers_with_dna"],
                          "labels":len(source_evidence),"category_positive_cells":dict(cl_counts)},ensure_ascii=False))
    if not allrows:
        raise RuntimeError("No verified eDNA read positives found")
    # Different 2023 programs may report the same river/taxon/year. Preserve
    # every source evidence row, but count unique river+label+year only once.
    newkeys=sorted(set(river_source_groups)-baseline_keys)
    groups=[]
    for water,river in sorted(river_source_groups):
        subset=[r for r in allrows if r["watershed_name"]==water and r["river_name"]==river]
        years=sorted(set(r["survey_year"] for r in subset))
        groups.append({"prefecture":"神奈川県","watershed_name":water,"river_name":river,
            "river_code_optional":None,"years":years,"eDNA_only":True,
            "source_dataset_keys":sorted(set(r["source_dataset_key"] for r in subset)),
            "eDNA_category_keys":sorted(set(r["biological_group"] for r in subset)),
            "eDNA_source_rows_not_unique_species":len(subset),
            "distinct_year_taxon_group_labels":len({(r["survey_year"],r["biological_group"],r["verbatim_source_taxon_label"]) for r in subset}),
            "not_in_v10_display_groups":(water,river) in newkeys,
            "legal_river_segment_verified":False,
            "no_live_specimen_or_capture_claim":True})
    csvfile=OUT/"kanagawa_2023_2024_edna_evidence_v11.csv"
    with csvfile.open("w",encoding="utf-8",newline="") as fp:
        w=csv.DictWriter(fp,fieldnames=COLUMNS);w.writeheader();w.writerows(sorted(allrows,key=lambda r:(r["survey_year"],r["watershed_name"],r["river_name"],r["biological_group"],r["verbatim_source_taxon_label"],r["source_dataset_key"])))
    (OUT/"kanagawa_2023_2024_edna_river_groups_v11.json").write_text(json.dumps(groups,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    audit={
        "method":"eDNA positive sequencing read, never specimen capture/observation",
        "source_site":PARENT,"usage_policy":LICENSE,
        "source_originals_verified_by_sha":len(audits),
        "source_audits":audits,
        "read_positive_source_rows":len(allrows),
        "unique_year_river_category_taxon_labels_across_2023_2024":len(cross_source_labels),
        "multiple_2023_source_rows_are_kept_but_not_double_counted":len(allrows)-len(cross_source_labels),
        "2023_2024_named_river_groups_with_eDNA":len(groups),
        "new_candidate_name_groups_not_in_v10_492":len(newkeys),
        "new_candidate_name_pairs":[{"watershed_name":a,"river_name":b} for a,b in newkeys],
        "v10_base_label_groups_preserved":492,
        "v10_2025_edna_counts_preserved_separately":265,
        "new_combined_display_name_group_candidates_approx":492+len(newkeys),
        "new_direct_fish_capture_records":0,
        "eDNA_insects_or_invertebrates_not_assumed_confirmed_benthic_animals":True,
        "birds_from_eDNA_not_assumed_visual_or_specimen":True,
        "source_has_no_confidence_scale_in_2023_fish_files":True,
        "all_10_digit_river_codes_optional":True,
        "all_precise_sampling_sites_and_personal_details_excluded":True,
        "production_WordPress_API_MySQL_unchanged":True
    }
    if len(set(x["evidence_id"] for x in allrows))!=len(allrows):
        raise ValueError("Duplicated source evidence IDs")
    if any(r["survey_method"]!="environmental_DNA_positive_sequence_reads_not_capture" for r in allrows):
        raise ValueError("Capture/eDNA methods mixed")
    (OUT/"kanagawa_2023_2024_edna_provenance_qa_v11.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("EXTRACTION_FINAL",json.dumps({k:v for k,v in audit.items() if k not in ("source_audits","new_candidate_name_pairs")},ensure_ascii=False))
    return audit

if __name__=="__main__":
    main()
