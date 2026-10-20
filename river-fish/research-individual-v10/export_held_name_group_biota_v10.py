#!/usr/bin/env python3
"""Preserve old 47-held biological records as SAFE qualified river-name buckets.

Physical river segment vs legal 10-digit code remains unresolved in all
new name buckets. Only source-bureau+watershed+recorded name uniquely
identified labels are exported. 6 nonriver/multiname inputs are never
treated as rivers. Parent-basin conflicts not corroborated by bureau stay held.

This does NOT modify the 428 original named-river SQLite, 553351 original
named-river contexts, production WordPress or MySQL. The new bundles are
METHOD=historic_named_river_survey, IDENTITY=unresolved legal river segment.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import csv,hashlib,json
from pathlib import Path
import re,sqlite3
from urllib.parse import quote
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
V05_SHA="dfa193bc882dfbc1dc3c30dc226bf81bc2e3754007069fed1b25e3007f4c1dd1"
CATEGORIES=("fish","benthic_animals","birds","plants")
AUTHORITIES={
 "hokkaido":"北海道開発局","tohoku":"東北地方整備局","kanto":"関東地方整備局",
 "hokuriku":"北陸地方整備局","chubu":"中部地方整備局","kinki":"近畿地方整備局",
 "chugoku":"中国地方整備局","shikoku":"四国地方整備局","kyushu":"九州地方整備局"
}
def digest(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""):h.update(b)
    return h.hexdigest()
def encode(v):
    return (json.dumps(v,ensure_ascii=False,separators=(",",":"),sort_keys=True)+"\n").encode("utf-8")
def add(z,path,v):
    if not re.fullmatch(r"held_[a-f0-9]{24}/(fish|benthic_animals|birds|plants)\.json",path):
        raise ValueError("Unsafe export path")
    i=ZipInfo(path,date_time=(1980,1,1,0,0,0));i.compress_type=ZIP_DEFLATED;i.external_attr=0o644<<16
    z.writestr(i,encode(v),compress_type=ZIP_DEFLATED,compresslevel=9)
def run(database,review,out):
    database=Path(database).resolve();review=Path(review)
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    if digest(database)!=V05_SHA:raise ValueError("Base survey v05 SQLite SHA changed")
    audit=json.loads(review.read_text(encoding="utf-8"))
    eligible=[r for r in audit["items"] if r["new_name_level_decision"].startswith("river_name_only_")]
    if not eligible or len(eligible)+sum(not r["new_name_level_decision"].startswith("river_name_only_") for r in audit["items"])!=47:
        raise ValueError("Source held labels incomplete")
    expected=sum(int(r["historical_contexts"]) for r in eligible)
    c=sqlite3.connect("file:"+quote(str(database),safe="/")+"?mode=ro",uri=True)
    c.execute("PRAGMA query_only=ON")
    names=[]
    group_rows=Counter()
    try:
        with ZipFile(out/"held_river_name_biology_v10.zip","w",compression=ZIP_DEFLATED,compresslevel=9) as z:
            for e in eligible:
                region,water,river=e["source_region"],e["survey_watershed"],e["survey_river_label"]
                if region not in AUTHORITIES:raise ValueError("Unknown source bureau region")
                source=AUTHORITIES[region]
                key="held_"+hashlib.sha256(json.dumps([region,source,water,river],ensure_ascii=False).encode()).hexdigest()[:24]
                context=c.execute("""
                    SELECT r.id,r.match_class,r.target_scope,r.river_code,r.source_authority
                    FROM river_context r
                    JOIN watersheds w ON r.watershed_id=w.id
                    WHERE w.region=? AND w.watershed_name=? AND r.river_name=?
                """,(region,water,river)).fetchall()
                if len(context)!=1 or context[0][1:]!=("B","individual_river",None,source):
                    raise ValueError("Existing source B river-name identity changed "+repr((water,river,context)))
                ctx=context[0][0]
                total=0
                categories={}
                for cat in CATEGORIES:
                    raw=c.execute("""
                        SELECT l.recorded_name,COUNT(*) AS n,MIN(e.survey_year),MAX(e.survey_year),
                               s.source_url,s.source_sha256
                        FROM river_evidence e
                        JOIN sources s ON s.id=e.source_id
                        JOIN labels l ON l.id=e.label_id
                        WHERE e.river_context_id=? AND s.group_id=?
                        GROUP BY l.recorded_name,s.source_url,s.source_sha256
                        ORDER BY l.recorded_name,s.source_url
                    """,(ctx,cat)).fetchall()
                    pername=defaultdict(lambda:{"historical_contexts":0,"first_year":None,"last_year":None,"sources":[]})
                    for label,n,first,last,url,sha in raw:
                        t=pername[label]
                        t["historical_contexts"]+=n
                        if first is not None:t["first_year"]=first if t["first_year"] is None else min(first,t["first_year"])
                        if last is not None:t["last_year"]=last if t["last_year"] is None else max(last,t["last_year"])
                        t["sources"].append({"url":url,"original_archive_sha256":sha,
                                             "historical_contexts":n,"first_year":first,"last_year":last})
                    records=[{"recorded_name":label,**v} for label,v in sorted(pername.items())]
                    count=sum(v["historical_contexts"] for v in records)
                    total+=count
                    doc={
                        "schema":"v10_provisional_river_name_only",
                        "river_label_group_key":key,
                        "source_region":region,"source_authority":source,
                        "survey_watershed":water,"survey_river_label":river,
                        "category":cat,"historic_record_contexts":count,
                        "distinct_literal_labels_not_taxonomic_species":len(records),
                        "records":records,
                        "physical_river_or_segment_identification":"UNRESOLVED",
                        "ten_digit_river_code":None,
                        "display_caution":"複数の10桁河川コードが同じ原本掲載名に対応。特定の河川区間を同定した記録とは扱わない。",
                        "current_presence_not_established":True,
                        "exact_sites_not_stored":True
                    }
                    add(z,key+"/"+cat+".json",doc)
                    categories[cat]={"historic_contexts":count,"literal_name_labels":len(records)}
                    group_rows[cat]+=count
                if total!=int(e["historical_contexts"]):
                    raise ValueError("Original named held source counts inconsistent "+repr((water,river,total)))
                names.append({"identity_key":key,"source_region":region,"survey_watershed":water,
                    "survey_river_label":river,"historic_record_contexts":total,
                    "categories":categories,
                    "provisional_reason":e["new_name_level_decision"],
                    "not_a_verified_single_river_identity":True,
                    "code_roots_for_review":e["candidate_parent_watershed_codes"]})
        if sum(v["historic_record_contexts"] for v in names)!=expected:
            raise ValueError("Grand total of held source records changed")
        with ZipFile(out/"held_river_name_biology_v10.zip") as z:
            if len(z.namelist())!=len(eligible)*4:raise ValueError("Missing 4 classification panels")
            if sum(json.loads(z.read(name))["historic_record_contexts"] for name in z.namelist())!=expected:
                raise ValueError("Post-archive hash/count mismatch")
        result={
            "source_baseline_v05_SHA256":V05_SHA,
            "existing_428_river_identities_unchanged":True,
            "existing_553351_river_contexts_unchanged":True,
            "original_47_held_name_identities":47,
            "eligible_additional_river_label_groups":len(names),
            "new_qualified_name_group_historical_contexts":expected,
            "new_four_category_panels":4*len(names),
            "held_or_invalid_name_labels":47-len(names),
            "categorical_context_counts":dict(group_rows),
            "does_not_identify_legal_river_segment":True,
            "does_not_duplicate_old_428_river_assemblies":True,
            "no_wordpress_or_mysql_changes":True,
            "raw_survey_coordinates_excluded":True
        }
        (out/"held_name_only_manifest_v10.json").write_bytes(encode({"stats":result,"entries":names}))
        (out/"held_name_only_review_v10.json").write_bytes(encode(result))
        print(json.dumps(result,ensure_ascii=False))
        return result
    finally:c.close()

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--db",required=True)
    p.add_argument("--review",required=True);p.add_argument("--out",required=True)
    a=p.parse_args();run(a.db,a.review,a.out)
