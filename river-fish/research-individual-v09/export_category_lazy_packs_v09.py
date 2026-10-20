#!/usr/bin/env python3
"""Export ALL historical named-river biology labels as lazy-loadable category JSON.

Input: pinned v08 read-only SQLite. Output: 9 deterministic ZIP archives
(one per bureau region), 1,712 per-river category JSON documents (including
zero-record windows), a manifest and integrity report. Extract ZIPs to an
ordinary static HTTPS directory when deployment is approved; this script does
NOT deploy. No coordinates, prefecture assertions or species normalizations.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import quote
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED

INPUT_SHA="a8098d63ab09ac8860811563cc7757ef011d9a784ebc48f8c4aef29979502c10"
EXPECTED_RIVERS=428
EXPECTED_CONTEXTS=553351
EXPECTED_LABEL_PAIRS=254574
EXPECTED_CATEGORY_WINDOWS=EXPECTED_RIVERS*4
CATEGORIES=("fish","benthic_animals","birds","plants")
DISPLAY={"fish":"魚類","benthic_animals":"底生動物","birds":"鳥類","plants":"植物"}
REGIONS=("hokkaido","tohoku","kanto","hokuriku","chubu","kinki","chugoku","shikoku","kyushu")

def filehash(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for part in iter(lambda:f.read(1048576),b""):h.update(part)
    return h.hexdigest()

def encoded(obj):
    return (json.dumps(obj,ensure_ascii=False,separators=(",",":"),sort_keys=True)+"\n").encode("utf-8")

def zip_write(z,name,obj):
    if name.startswith("/") or ".." in name.split("/") or not re.fullmatch(r"[a-z0-9_./-]+",name):
        raise ValueError("Unsafe archive path: "+name)
    zi=ZipInfo(name,date_time=(1980,1,1,0,0,0))
    zi.compress_type=ZIP_DEFLATED
    zi.external_attr=(0o644<<16)
    z.writestr(zi,encoded(obj),compress_type=ZIP_DEFLATED,compresslevel=8)

def build(src,out):
    src=Path(src).resolve();out=Path(out)
    if filehash(src)!=INPUT_SHA:raise ValueError("Pinned v08 individual biology source SHA changed")
    if out.exists() and list(out.iterdir()):
        raise FileExistsError("Will not overwrite research category packs")
    out.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect("file:"+quote(str(src),safe="/")+"?mode=ro",uri=True)
    c.execute("PRAGMA query_only=ON")
    zips={}
    counters=Counter()
    packstats=defaultdict(lambda:Counter())
    manifests=[]
    try:
        if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok":raise ValueError("Source SQLite invalid")
        source_map={sid:{"url":url,"archive_sha256":hashval}
                    for sid,url,hashval in c.execute(
                        "SELECT source_id,source_url,source_sha256 FROM source_catalog")}
        # Use v08 pre-verified category summaries so that all four windows can
        # be served, even if the input has no records for a category.
        windows=defaultdict(dict)
        for key,category,contexts,names,year_min,year_max in c.execute("""
            SELECT identity_key,category,historical_contexts,literal_name_count,
                   first_survey_year,last_survey_year FROM category_summary
        """):
            if category not in CATEGORIES:raise ValueError("Unexpected source category")
            windows[key][category]={"historical_contexts":contexts,
                "literal_labels_not_species":names,"year_min":year_min,"year_max":year_max}
        rows=list(c.execute("""
            SELECT identity_key,source_region,source_authority,watershed_name,
                   river_name,river_code,evidence_confidence,survey_contexts
            FROM river ORDER BY source_region,watershed_name,river_name,identity_key
        """))
        if len(rows)!=EXPECTED_RIVERS or len(windows)!=EXPECTED_RIVERS:
            raise ValueError("Lost river identities")
        if len(source_map)<1:raise ValueError("No origin documents")
        zips={region:ZipFile(out/(region+".zip"),"w",compression=ZIP_DEFLATED,compresslevel=8)
              for region in REGIONS}
        for ident,region,auth,water,river,code,confidence,river_total in rows:
            if not re.fullmatch(r"rn_[0-9a-f]{24}",ident):raise ValueError("Unsafe identity key")
            if region not in REGIONS:raise ValueError("Unrecognized survey bureau region")
            if set(windows[ident])!=set(CATEGORIES):raise ValueError("Missing category windows for river")
            manifest_row={"identity_key":ident,"source_region":region,"source_authority":auth,
                          "watershed":water,"river_name":river,"river_code_optional":code,
                          "code_confidence":confidence,
                          "historical_contexts":river_total,
                          "categories":{}}
            subtotal=0
            for category in CATEGORIES:
                summary=windows[ident][category]
                labels=[]
                hist=0
                proofrows=0
                for taxonid,recorded,n,ymin,ymax in c.execute("""
                    SELECT taxon_key,recorded_name,historical_contexts,
                           first_survey_year,last_survey_year
                    FROM literal_taxon_label
                    WHERE identity_key=? AND category=?
                    ORDER BY historical_contexts DESC,recorded_name,taxon_key
                """,(ident,category)):
                    doc=[]
                    for sid,contexts,dmin,dmax in c.execute("""
                        SELECT source_id,historical_contexts,year_min,year_max
                        FROM taxon_source_proof
                        WHERE taxon_key=? ORDER BY source_id
                    """,(taxonid,)):
                        p=source_map[sid]
                        doc.append({"source_url":p["url"],"source_archive_sha256":p["archive_sha256"],
                                    "historical_contexts":contexts,"year_min":dmin,"year_max":dmax})
                        proofrows+=1
                    if not doc or sum(q["historical_contexts"] for q in doc)!=n:
                        raise ValueError("Missing or inconsistent original citation for "+str(taxonid))
                    labels.append({"recorded_name":recorded,"historical_contexts":n,
                                   "year_min":ymin,"year_max":ymax,"source_evidence":doc})
                    hist+=n
                if len(labels)!=summary["literal_labels_not_species"] or hist!=summary["historical_contexts"]:
                    raise ValueError("Per-category full list differs from v08 summary")
                relative=f"{region}/{ident}/{category}.json"
                doc={"schema":"river-category-historical-v09",
                     "river_identity":ident,"source_authority":auth,
                     "survey_region":region,"watershed":water,"river_name":river,
                     "river_code_optional":code,
                     "category":category,"category_name":DISPLAY[category],
                     **summary,
                     "literal_taxon_names_not_taxonomically_normalized":True,
                     "source_scope":"individual_named_river_only",
                     "not_current_distribution":True,
                     "zero_means_no_captured_survey_record_not_absence":True,
                     "no_precise_survey_site_or_coordinate":True,
                     "labels":labels}
                zip_write(zips[region],relative,doc)
                manifest_row["categories"][category]={"file":relative,**summary}
                packstats[region]["category_json_files"]+=1
                packstats[region]["literal_label_rows"]+=len(labels)
                packstats[region]["source_proof_rows"]+=proofrows
                packstats[region]["historical_contexts"]+=hist
                counters["category_json_files"]+=1
                counters["literal_label_rows"]+=len(labels)
                counters["source_proof_rows"]+=proofrows
                counters["historical_contexts"]+=hist
                subtotal+=hist
            if subtotal!=river_total:raise ValueError("Per-river sum differs from original research")
            manifests.append(manifest_row)
            packstats[region]["rivers"]+=1
        for z in zips.values():z.close()
        zips={}
        if counters["category_json_files"]!=EXPECTED_CATEGORY_WINDOWS:
            raise ValueError("Missing four-category files")
        if counters["historical_contexts"]!=EXPECTED_CONTEXTS:
            raise ValueError("Historical context conservation failed")
        if counters["literal_label_rows"]!=EXPECTED_LABEL_PAIRS:
            raise ValueError("Original literal name pair conservation failed")
        # Independently parse EACH compressed JSON file from the generated
        # archives to detect corruption and verify no unanticipated files.
        checked=Counter()
        packs=[]
        for region in REGIONS:
            path=out/(region+".zip")
            with ZipFile(path) as z:
                seen=set()
                for name in z.namelist():
                    if name in seen:raise ValueError("Duplicate ZIP member")
                    seen.add(name)
                    if not name.startswith(region+"/"):raise ValueError("Region pack mixed")
                    data=json.loads(z.read(name))
                    if data["schema"]!="river-category-historical-v09":
                        raise ValueError("Unexpected static category data")
                    if data["category"] not in CATEGORIES or data["survey_region"]!=region:
                        raise ValueError("Mixing categories or source region")
                    if len(data["labels"])!=data["literal_labels_not_species"]:
                        raise ValueError("Bad category label payload")
                    if sum(l["historical_contexts"] for l in data["labels"])!=data["historical_contexts"]:
                        raise ValueError("Bad category total")
                    if any("lat" in k or "longitude" in k or "municipality" in k for k in data):
                        raise ValueError("Location information must not be disclosed")
                    checked["files"]+=1
                    checked["labels"]+=len(data["labels"])
                    checked["historical_contexts"]+=data["historical_contexts"]
                if len(seen)!=packstats[region]["category_json_files"]:
                    raise ValueError("Region archive entry count differs")
            packs.append({"region":region,"archive_file":path.name,"archive_bytes":path.stat().st_size,
                          "archive_sha256":filehash(path),**dict(packstats[region])})
        if checked["files"]!=counters["category_json_files"] or checked["labels"]!=counters["literal_label_rows"] or checked["historical_contexts"]!=counters["historical_contexts"]:
            raise ValueError("ZIP reconstruction audit failed")
        manifest={"schema":"research-static-packs-v09",
                  "deploy_note":"After manual review, extract each region zip into one static root; then fetch categories by manifest categories[group].file on SAME origin. Do not fetch ZIP members directly over HTTP.",
                  "input_v08_db_sha256":INPUT_SHA,
                  "regions":packs,"rivers":manifests,
                  "no_network_no_site_deployment":True,
                  "no_prefecture_or_site_coordinates":True,
                  "category_values_are_historical_survey_literal_labels_not_taxonomic_species_counts":True}
        (out/"manifest_v09.json").write_bytes(encoded(manifest))
        report={"version":"v09","source_db_sha256":INPUT_SHA,
                "region_archives":len(packs),
                "individual_named_rivers":len(manifests),
                "category_json_files":checked["files"],
                "all_literal_label_rows":checked["labels"],
                "all_historical_contexts":checked["historical_contexts"],
                "category_zero_windows":sum(1 for m in manifests for q in m["categories"].values()
                                            if q["historical_contexts"]==0),
                "full_taxonomic_names_included":False,
                "source_literal_labels_included":True,
                "per_label_years_and_original_source_urls_included":True,
                "zero_windows_explicitly_retained":True,
                "river_code_optional":True,
                "category_json_is_lazy_loadable_after_extracting_archives":True,
                "static_files_not_yet_deployed":True,
                "production_wordpress_mysql_changed":False,
                "archives":packs}
        (out/"export_integrity_v09.json").write_bytes(encoded(report))
        print(json.dumps({k:v for k,v in report.items() if k!="archives"},ensure_ascii=False))
        return report
    finally:
        for z in zips.values():z.close()
        c.close()

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",required=True);ap.add_argument("--out",required=True)
    a=ap.parse_args();build(a.source,a.out)
