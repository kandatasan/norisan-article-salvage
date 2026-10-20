#!/usr/bin/env python3
"""Read-only paginated original survey names per individual river and category.

Examples:
 --region chugoku --watershed 太田川 --river 三篠川 --category fish
 --region kyushu --watershed 筑後川 --river 宝満川 --category benthic_animals
 --identity-key rn_... --category plants --offset 40
These are verbatim taxon LABELS, not taxonomically validated species.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import quote
GROUPS={"fish":"魚類","benthic_animals":"底生動物","birds":"鳥類","plants":"植物"}

def connect(path):
    c=sqlite3.connect("file:"+quote(str(Path(path).resolve()),safe="/")+"?mode=ro",uri=True)
    c.execute("PRAGMA query_only=ON");c.row_factory=sqlite3.Row
    return c

def read(c,region=None,watershed=None,river=None,identity_key=None,category="fish",limit=20,offset=0):
    if category not in GROUPS:raise ValueError("Unsupported group")
    if not 1<=limit<=80 or not 0<=offset<=100000:raise ValueError("Invalid pagination")
    if identity_key:
        if not re.fullmatch(r"rn_[0-9a-f]{24}",identity_key):raise ValueError("Malformed river identity")
        matches=c.execute("SELECT * FROM river WHERE identity_key=?",(identity_key,)).fetchall()
    else:
        if not (region and watershed and river):raise ValueError("All region/watershed/river labels required")
        matches=c.execute("""
            SELECT * FROM river WHERE source_region=? AND watershed_name=? AND river_name=?
        """,(region,watershed,river)).fetchall()
    if not matches:return {"status":"not_in_research_river_index","category":category,"items":[]}
    if len(matches)>1:
        return {"status":"ambiguous_name_requires_identity_key","category":category,
                "choices":[{"identity_key":x["identity_key"],"authority":x["source_authority"]} for x in matches]}
    r=dict(matches[0])
    sums={x["category"]:dict(x) for x in c.execute("""
        SELECT category,historical_contexts,literal_name_count,first_survey_year,last_survey_year
        FROM category_summary WHERE identity_key=?
    """,(r["identity_key"],))}
    total=sums[category]["literal_name_count"]
    rows=[]
    for t in c.execute("""
        SELECT taxon_key,recorded_name,historical_contexts,first_survey_year,last_survey_year,cited_source_count
        FROM literal_taxon_label
        WHERE identity_key=? AND category=?
        ORDER BY historical_contexts DESC,recorded_name ASC,taxon_key ASC
        LIMIT ? OFFSET ?
    """,(r["identity_key"],category,limit,offset)):
        doc=list(c.execute("""
            SELECT p.historical_contexts,p.year_min,p.year_max,
                s.source_url,s.source_sha256
            FROM taxon_source_proof p
            JOIN source_catalog s ON p.source_id=s.source_id
            WHERE p.taxon_key=?
            ORDER BY s.source_url
        """,(t["taxon_key"],)))
        rows.append({
           "literal_recorded_name":t["recorded_name"],
           "historical_contexts":t["historical_contexts"],
           "survey_year_min":t["first_survey_year"],
           "survey_year_max":t["last_survey_year"],
           "sources":[dict(x) for x in doc],
           "scientific_species_identity_verified":False
        })
    return {
       "status":"named_river_historical_labels",
       "river_identity":r["identity_key"],
       "source_region":r["source_region"],"source_authority":r["source_authority"],
       "watershed_name":r["watershed_name"],"river_name":r["river_name"],
       "river_code_optional":r["river_code"],
       "prefecture":None,
       "prefecture_geographic_status":"not_inferred",
       "four_categories":{k:{
           "category_label":GROUPS[k],
           "historical_contexts":v["historical_contexts"],
           "literal_labels_not_species":v["literal_name_count"],
           "survey_year_min":v["first_survey_year"],
           "survey_year_max":v["last_survey_year"]
       } for k,v in sums.items()},
       "selected_category":category,
       "selected_category_label":GROUPS[category],
       "offset":offset,"page_size":limit,
       "total_literal_names_not_species":total,
       "has_more":offset+len(rows)<total,
       "items":rows,
       "source_scope":"individual_named_river_only",
       "caution":"Not number of individuals, not verified taxonomic species counts, not current presence. 0 means no captured survey record, not absence. No watershed-level records assigned to an individual river."
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--db",required=True);p.add_argument("--region")
    p.add_argument("--watershed");p.add_argument("--river")
    p.add_argument("--identity-key");p.add_argument("--category",default="fish",choices=list(GROUPS))
    p.add_argument("--limit",type=int,default=20);p.add_argument("--offset",type=int,default=0)
    args=p.parse_args();c=connect(args.db)
    try:d=read(c,args.region,args.watershed,args.river,args.identity_key,args.category,args.limit,args.offset)
    finally:c.close()
    print(json.dumps(d,ensure_ascii=False,indent=2))

if __name__=="__main__":main()
