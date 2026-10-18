#!/usr/bin/env python3
"""Audit MLIT river-version bird survey archives, WITHOUT importing observations.

Verify exact URL from current official download index; inspect real archive
content, hash, only first four allowed columns C/F/G/J, and aggregate statistics.
Sensitive locations / observation station columns are NEVER read or emitted.
Bird category is accepted only if original worksheet literally says 鳥類.
No WordPress or deployed data changes. Separate audit from approved import.
"""
import argparse
from collections import Counter
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
from zipfile import ZipFile
from import_national_benthic_v19 import (
    excel_rows_benthic, APPROVED_COLUMNS, VALID_REGIONS
)
from audit_official_source_index_v21 import INDEX
from import_national_benthic_v19 import source_verified_in_official_index, fetch, MAX_ZIP

REGION_NUMBERS={r:f"{i:02d}" for i,r in enumerate(VALID_REGIONS,81)}
EXPECTED_CATEGORY="鳥類"
MAX_SOURCE_ROWS=1_000_000
BASE="https://www.nilim.go.jp/lab/fbg/ksnkankyo/download/slist/"

def audit(region, raw):
    if region not in REGION_NUMBERS:
        raise ValueError("Unapproved survey region")
    num=REGION_NUMBERS[region]
    url=f"{BASE}RT{num}_B04.zip"
    sha=hashlib.sha256(raw).hexdigest()
    with ZipFile(BytesIO(raw)) as z:
        members=[x for x in z.infolist() if not x.is_dir()]
        if len(members)!=1 or not members[0].filename.endswith(".xlsx"):
            raise ValueError("Bird official archive member list needs review")
        mem=members[0]
        if not mem.filename.startswith(f"RT{num}_B04/") or (
            ".." in Path(mem.filename).parts or mem.file_size<=0 or mem.file_size>220_000_000):
            raise ValueError("Unexpected bird workbook member")
        member=mem.filename
    categories=Counter()
    reject=Counter()
    distinct=set()
    source_rows=0
    accepted=0
    for r in excel_rows_benthic(raw,member):
        source_rows+=1
        if source_rows>MAX_SOURCE_ROWS:
            raise ValueError("Too many original bird-list rows")
        cat=r.get("C","")
        categories[cat or "<empty>"]+=1
        if cat!=EXPECTED_CATEGORY:
            reject["other_category"]+=1
            continue
        watershed=r.get("F","").strip()
        year=r.get("G","").strip()
        name=r.get("J","").strip()
        if not watershed or not name:
            reject["missing_watershed_or_name"]+=1
            continue
        if (len(watershed)>80 or len(name)>150 or
            any(label[0] in "=+-@" for label in (watershed,name))):
            reject["unsafe_literal_label"]+=1
            continue
        if not re.fullmatch(r"(?:19|20)[0-9]{2}",year) or year>"2026":
            reject["invalid_year"]+=1
            continue
        accepted+=1
        distinct.add((watershed,year,name))
    if source_rows<50 or accepted<20 or len(distinct)<15:
        raise ValueError("Bird worksheet category absent or insufficient; manual review")
    if accepted/source_rows<0.85:
        raise ValueError("Bird worksheet category ambiguous or unexpectedly mixed")
    result={
        "region":region,"official_category":EXPECTED_CATEGORY,
        "source_url":url,"source_sha256":sha,
        "xlsx_member":member,"checked_schema":APPROVED_COLUMNS,
        "original_source_rows":source_rows,
        "accepted_source_rows":accepted,
        "unique_watershed_year_literal_name_records":len(distinct),
        "unique_watersheds":len({r[0] for r in distinct}),
        "distinct_literal_names_not_species_count":len({r[2] for r in distinct}),
        "year_min":min(y for _,y,_ in distinct),"year_max":max(y for _,y,_ in distinct),
        "original_categories":dict(categories),
        "rejected_rows":dict(reject),
        "scope":"official_region_watershed_year_only",
        "precise_locations_collected":False,
        "survey_station_columns_read":False,
        "taxonomy_identity_verified":False,
        "individual_river_presence_verified":False,
        "wordpress_modified":False,
        "status":"audit_only_not_approved_for_import"
    }
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--region",required=True,choices=VALID_REGIONS)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    num=REGION_NUMBERS[args.region]
    url=f"{BASE}RT{num}_B04.zip"
    if not source_verified_in_official_index(url,INDEX):
        raise ValueError("B04 source not directly linked from official national index")
    raw=fetch(url,MAX_ZIP)
    result=audit(args.region,raw)
    out=Path(args.out)
    out.parent.mkdir(parents=True,exist_ok=True)
    if out.exists():raise FileExistsError("Audit metadata cannot overwrite prior data")
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("MLIT_BIRD_OFFICIAL_AUDIT "+json.dumps(result,ensure_ascii=False))
if __name__=="__main__":
    main()
