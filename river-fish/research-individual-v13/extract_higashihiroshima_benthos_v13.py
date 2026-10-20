#!/usr/bin/env python3
"""Higashihiroshima official 2024 stream benthos indicator field-survey audit.

Original PDF is downloaded temporarily solely for verification, NEVER committed.
Only 23 site-confirmed indicator taxon facts, aggregated to river-name scope,
and provenance metadata are written to research branch. Commercial reuse is
BLOCKED until East Hiroshima City permission / rights review is completed.
"""
from __future__ import annotations
import collections
import csv
import hashlib
import json
import re
import subprocess
import tempfile
import unicodedata
import urllib.request
from pathlib import Path
from zipfile import ZipFile

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/"research-individual-v12"/"outputs"/"river_atlas_static_preview_v12.zip"
OUT=HERE/"outputs"
OFFICIAL="https://www.city.higashihiroshima.lg.jp/material/files/group/204/R6suiseiseibutsu.pdf"
LANDING="https://www.city.higashihiroshima.lg.jp/soshiki/seikatsukankyo/5/12/43734.html"
RIGHTS="https://www.city.higashihiroshima.lg.jp/shisei/5/6701.html"
# An independently checked SHA is filled after the first documented original fetch.
EXPECTED_SHA256=None

# Site number is used ONLY DURING cross-check; original site number, exact
# sampling point, station name, coordinates are not exported to research CSV.
# Fields: sample table row, watershed, source-confirmed river, site description
# in the original PDF, and the *single most common representative indicator*
# taxon on report PDF page 9 (the full species list is in a separate annex).
ROWS=[
 (1,"黒瀬川","黒瀬川","黒瀬川下流","ミズムシ"),
 (2,"黒瀬川","黒瀬川","和泉橋上流","ミズムシ"),
 (3,"黒瀬川","黒瀬川","呉・黒瀬境界","コカゲロウ科"),
 (4,"黒瀬川","竹保川","竹保川","コガタシマトビケラ属"),
 (5,"黒瀬川","光路川","光路川","ミズムシ"),
 (6,"黒瀬川","笹野川","笹野川","ミズムシ"),
 (7,"黒瀬川","黒瀬川","石ヶ瀬橋上流","コカゲロウ科"),
 (8,"黒瀬川","中川","中川","ミズムシ"),
 (9,"黒瀬川","深堂川","深堂川","シマイシビル"),
 (10,"黒瀬川","米満川","米満川上流","コガタシマトビケラ属"),
 (11,"黒瀬川","温井川","温井川上流","アシマダラブユ属"),
 (12,"沼田川","沼田川","沼田川上流","ヒゲナガカワトビケラ"),
 (13,"沼田川","造賀川","造賀川","コガタシマトビケラ属"),
 (14,"沼田川","宮領川","宮領川","コガタシマトビケラ属"),
 (15,"沼田川","杵原川","杵原川","コカゲロウ科"),
 (16,"沼田川","入野川","入野川中流","チラカゲロウ"),
 (17,"沼田川","椋梨川","椋梨川上流","コガタシマトビケラ属"),
 (18,"沼田川","沼田川","沼田川中流","シロタニガワカゲロウ"),
 (19,"太田川","関川","関川中流","フタツメカワゲラ属"),
 (20,"太田川","東川","東川","ヤマトビケラ属"),
 (21,"瀬野川","椛坂川","椛坂川","コガタシマトビケラ属"),
 (22,"瀬野川","瀬野川","瀬野川","シロタニガワカゲロウ"),
 (23,"三津大川","三津大川","三津大川","シロタニガワカゲロウ"),
]
assert len(ROWS)==23 and set(r[0] for r in ROWS)==set(range(1,24))

def normalized(x):
    return re.sub(r"\s+","",unicodedata.normalize("NFKC",x))

def fetch():
    request=urllib.request.Request(OFFICIAL,headers={"User-Agent":"Mozilla/5.0 Tsurikue research audit (source PDF integrity); contact via repository"})
    with urllib.request.urlopen(request,timeout=50) as response:
        if response.status!=200:raise ValueError("Official PDF response HTTP "+str(response.status))
        data=response.read(20000000)
    if not data.startswith(b"%PDF") or len(data)<100000:
        raise ValueError("Original official PDF unavailable or invalid")
    digest=hashlib.sha256(data).hexdigest()
    if EXPECTED_SHA256 is not None and digest!=EXPECTED_SHA256:
        raise ValueError("Official PDF SHA changed - STOP and review")
    return data,digest

def getpages(data):
    with tempfile.TemporaryDirectory() as temp:
        pdf=Path(temp)/"official-original.pdf"
        pdf.write_bytes(data)
        pages={}
        for page_num in (3,5,9):
            x=subprocess.run(["pdftotext","-f",str(page_num),"-l",str(page_num),
                              "-layout","-enc","UTF-8",str(pdf),"-"],
                             check=True,text=True,capture_output=True).stdout
            assert len(x)>100,(page_num,len(x))
            pages[page_num]=x
    return pages

def extract_per_site(pages):
    a=normalized(pages[3])
    b=normalized(pages[9])
    m=normalized(pages[5])
    if "23地点" not in m or "底生生物" not in m or "網" not in m:
        raise ValueError("Original field-survey method/page check failed")
    if "代表的な指標生物" not in b:
        raise ValueError("Expected indicator summary table missing")
    # Bound every raw table row by its own enumerated site heading; this detects
    # unintended changes to the published PDF. No stations or positions export.
    section=b.split("表3-2-1",1)[-1]
    numbered=list(re.finditer(r"(?<![0-9])([1-9]|1[0-9]|2[0-3])\)",section))
    bynumber={}
    for k,m0 in enumerate(numbered):
        num=int(m0.group(1))
        if num not in bynumber:
            end=numbered[k+1].start() if k+1<len(numbered) else len(section)
            bynumber[num]=section[m0.start():end]
    if set(bynumber)!=set(range(1,24)):
        raise ValueError("Original PDF table 3-2-1 enumeration incomplete "+repr(sorted(bynumber)))
    for number,water,river,site,taxon in ROWS:
        cell=bynumber[number]
        # The report's underlined punctuation/wide Japanese spaces are
        # normalized but taxon and enumerated row MUST agree.
        if normalized(site) not in cell or normalized(taxon) not in cell:
            raise ValueError("Representative indicator did not match site "+str(number))
        if river not in a or water not in a:
            raise ValueError("Watershed/river table identity not found")
    return len(bynumber)

def main():
    OUT.mkdir(exist_ok=True)
    pdf,digest=fetch()
    pages=getpages(pdf)
    scanned=extract_per_site(pages)
    with ZipFile(BASE) as z:
        idx=json.loads(z.read("atlas.json"))
    assert idx["research_display_name_groups"]==511
    baseline={(e["water"],e["name"]) for e in idx["entries"] if e["region"]=="chugoku"}
    pairs={(w,r) for _,w,r,_,_ in ROWS}
    newpairs=sorted(pairs-baseline)
    # More than one station can have the same indicator in one river. The
    # separate station is not necessary for public-facing biota candidates.
    aggregates=collections.defaultdict(set)
    for _,w,r,_,taxon in ROWS:aggregates[(w,r)].add(taxon)
    evidence=[{"prefecture":"広島県","municipality":"東広島市",
               "watershed_name":w,"river_name":r,
               "biological_group":"benthic_animals",
               "taxon_verbatim":taxon,"survey_year":2024,
               "method":"actual_field_collection_recorded_then_released",
               "source_record_scope":"representative_indicator_most_common_not_full_species_list",
               "source_url":OFFICIAL,"landing_url":LANDING,
               "original_sha256":digest,"original_pdf_page_number_1based":9,
               "publication_rights":"RESEARCH_ONLY_DONT_PUBLISH_WITHOUT_CITY_PERMISSION"}
              for (w,r),names in sorted(aggregates.items()) for taxon in sorted(names)]
    csvpath=OUT/"higashihiroshima_2024_benthic_indicator_aggregated_v13.csv"
    with csvpath.open("w",encoding="utf-8",newline="") as fp:
        wr=csv.DictWriter(fp,fieldnames=list(evidence[0]));wr.writeheader();wr.writerows(evidence)
    stats={
      "source":"東広島市 令和6年度主要水域（河川）における水生生物調査等業務報告書",
      "source_pdf_url":OFFICIAL,"source_landing":LANDING,
      "official_pdf_sha256":digest,"byte_length":len(pdf),
      "survey_date":"2024-11-18/2024-11-19",
      "publication_report_date":"2025-02",
      "original_document_sites_with_field_collected_benthos":scanned,
      "source_river_name_groups":len(pairs),
      "research_aggregated_river_taxon_indicator_facts":len(evidence),
      "previous_research_display_name_groups":511,
      "new_river_name_candidates_after_chugoku_scope_511_baseline":len(newpairs),
      "new_river_name_candidates_list":[{"watershed":w,"river_name":r} for w,r in newpairs],
      "specific_sampling_sites_and_coordinates_in_export":False,
      "not_all_confirmed_species":"Published table specifies ONLY the single representative most common indicator per sampling site; never full species list",
      "family_or_genus_taxon_labels_preserved_verbatim":True,
      "publication_rights_source":RIGHTS,
      "commercial_publication_rights_cleared":False,
      "research_only":True,
      "old_511_preview_not_modified":True,
      "WordPress_and_public_API_not_modified":True
    }
    (OUT/"higashihiroshima_2024_benthic_qa_v13.json").write_text(json.dumps(stats,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(stats,ensure_ascii=False))

if __name__=="__main__":
    main()
