#!/usr/bin/env python3
"""Read-only river-detail contract: direct records and watershed fallback split."""
import argparse
import csv
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import quote
from audit_individual_rivers import ROOT,CATEGORIES

def detail(db,river_code,limit=20,approvals=None):
    if not re.fullmatch(r'\d{10}',river_code):raise ValueError('10-digit river code required')
    if not 1<=limit<=100:raise ValueError('limit must be 1..100')
    with (ROOT/'national-codes-staged/river_codes_national_v07.csv').open(encoding='utf-8') as f:
        river=next((r for r in csv.DictReader(f) if r['river_code']==river_code),None)
    if river is None:raise ValueError('Unknown river code')
    c=sqlite3.connect('file:'+quote(str(Path(db).resolve()),safe='/')+'?mode=ro',uri=True)
    c.execute('PRAGMA query_only=ON');c.row_factory=sqlite3.Row
    mapping=[]
    path=Path(approvals) if approvals else Path(__file__).with_name('approved_river_crosswalk.csv')
    with path.open(encoding='utf-8') as f:
        mapping=[r for r in csv.DictReader(f) if r['river_code']==river_code]
    result={'river_code':river_code,'river_name':river['river_name'],'watershed_code':river['watershed_code'],
            'watershed_name':river['watershed_name'],'prefecture':None,'prefecture_status':'not_inferred',
            'direct_records':{},'watershed_context':None,
            'notice':'Historical literal survey names, not current presence or verified species counts. No detailed locations.'}
    for group,label in CATEGORIES.items():
        total,names,first,last=c.execute('SELECT COUNT(*),COUNT(DISTINCT recorded_name),MIN(survey_year),MAX(survey_year) FROM approved_individual_river WHERE river_code=? AND group_id=?',(river_code,group)).fetchone()
        records=c.execute('SELECT survey_year,recorded_name,source_url FROM approved_individual_river WHERE river_code=? AND group_id=? ORDER BY survey_year,recorded_name LIMIT ?',(river_code,group,limit)).fetchall()
        result['direct_records'][group]={'label':label,'status':'individual_river_records_confirmed' if total else '個別河川の記録は未確認',
             'records':total,'literal_names_not_species':names,'year_min':first,'year_max':last,
             'items':[dict(r) for r in records],'has_more':total>len(records)}
    if len(mapping)==1:
        m=mapping[0]
        table='original_key_audit' if c.execute("SELECT 1 FROM sqlite_master WHERE name='original_key_audit'").fetchone() else 'collapsed_keys'
        rows=c.execute(f'SELECT group_id,COUNT(*) records,COUNT(DISTINCT recorded_name) literal_names_not_species,MIN(survey_year) year_min,MAX(survey_year) year_max FROM {table} WHERE region=? AND watershed_name=? GROUP BY group_id',(m['region'],m['watershed_name'])).fetchall()
        result['watershed_context']={'scope':'watershed_only_not_this_river','region':m['region'],
            'watershed_name':m['watershed_name'],'records_by_group':[dict(r) for r in rows],
            'notice':'This separate context never fills missing individual-river records.'}
    c.close();return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--db',required=True);p.add_argument('--river-code',required=True);p.add_argument('--limit',type=int,default=20)
    a=p.parse_args();print(json.dumps(detail(a.db,a.river_code,a.limit),ensure_ascii=False,indent=2))
