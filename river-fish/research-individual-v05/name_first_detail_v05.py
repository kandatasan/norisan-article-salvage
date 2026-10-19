#!/usr/bin/env python3
"""Safe, read-only lookups for the name-first individual-river biology index.

Usage:
 python name_first_detail_v05.py --db ... --region kyushu --watershed 筑後川 --list-rivers
 python name_first_detail_v05.py --db ... --region kyushu --watershed 筑後川 --river 宝満川
 python name_first_detail_v05.py --db ... --identity-key rn_...
Never fall back to watershed-level evidence or infer a prefecture.
"""
import argparse
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import quote

LABELS={"fish":"魚類","benthic_animals":"底生動物","birds":"鳥類","plants":"植物"}
def connect(db):
    c=sqlite3.connect("file:"+quote(str(Path(db).resolve()),safe="/")+"?mode=ro",uri=True)
    c.execute("PRAGMA query_only=ON")
    c.row_factory=sqlite3.Row
    return c

def lookup(c,region=None,watershed=None,river=None,authority=None,identity_key=None,limit=15,list_rivers=False):
    if not 1<=limit<=80:raise ValueError("limit must be 1..80")
    if identity_key:
        if not re.fullmatch(r"rn_[0-9a-f]{24}",identity_key):
            raise ValueError("Malformed identity key")
        matches=c.execute("""
            SELECT * FROM name_first_rivers
            WHERE identity_key=? AND review_status='eligible'
        """,(identity_key,)).fetchall()
    elif list_rivers:
        if not region or not watershed or river:raise ValueError("Region and watershed required to list rivers")
        return {
            "region":region,"watershed":watershed,
            "rivers":[dict(row) for row in c.execute("""
                SELECT identity_key,river_name,river_code,code_confidence,
                       survey_record_contexts
                FROM name_first_rivers
                WHERE review_status='eligible' AND region=? AND watershed_name=?
                ORDER BY river_name
            """,(region,watershed))],
            "notice":"Survey river labels, not geocoded points; no prefecture is inferred."
        }
    else:
        if not (region and watershed and river):
            raise ValueError("Region, watershed, and river name must all be specified")
        rows=c.execute("""
            SELECT * FROM name_first_rivers
            WHERE review_status='eligible' AND region=? AND watershed_name=?
              AND river_name=?
        """,(region,watershed,river)).fetchall()
        matches=[row for row in rows if authority is None or row["source_authority"]==authority]
    if not matches:return {"status":"not_in_verified_name_index","direct_records":None}
    if len(matches)>1:
        return {"status":"ambiguous_source_authority",
                "choices":[{"identity_key":r["identity_key"],"source_authority":r["source_authority"]} for r in matches]}
    info=dict(matches[0]);key=info["identity_key"]
    by_category={}
    for group,label in LABELS.items():
        total,names,first,last=c.execute("""
            SELECT COUNT(*),COUNT(DISTINCT recorded_name),MIN(survey_year),MAX(survey_year)
            FROM name_first_evidence WHERE identity_key=? AND group_id=?
        """,(key,group)).fetchone()
        samples=[dict(row) for row in c.execute("""
            SELECT survey_year,recorded_name,source_url
            FROM name_first_evidence
            WHERE identity_key=? AND group_id=?
            ORDER BY survey_year,recorded_name LIMIT ?
        """,(key,group,limit))]
        by_category[group]={
            "label":label,
            "status":"source_documented_named_river" if total else "個別河川の調査記録は未確認",
            "historical_record_contexts":total,
            "literal_labels_not_verified_species":names,
            "year_min":first,"year_max":last,
            "items":samples,"has_more":total>len(samples)
        }
    return {
        "status":"name_first_river_record",
        "identity_key":key,
        "region_source":info["region"],"source_authority":info["source_authority"],
        "watershed_name":info["watershed_name"],"river_name":info["river_name"],
        "river_code_optional":info["river_code"],
        "code_confidence":info["code_confidence"],
        "prefecture":None,"prefecture_status":"not_inferred",
        "biota":by_category,
        "watershed_only_data_used":False,
        "notice":"Historic survey river-name evidence. Code-less records are identified by region+authority+watershed+literal river name; physical river identity, current presence and species-level taxonomy are not independently verified. No site coordinates."
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--db",required=True)
    p.add_argument("--region");p.add_argument("--watershed");p.add_argument("--river")
    p.add_argument("--authority");p.add_argument("--identity-key")
    p.add_argument("--limit",type=int,default=15)
    p.add_argument("--list-rivers",action="store_true")
    a=p.parse_args()
    c=connect(a.db)
    try:r=lookup(c,a.region,a.watershed,a.river,a.authority,a.identity_key,a.limit,a.list_rivers)
    finally:c.close()
    print(json.dumps(r,ensure_ascii=False,indent=2))

if __name__=="__main__":main()
