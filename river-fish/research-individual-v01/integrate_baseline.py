#!/usr/bin/env python3
"""Verify existing 408k snapshot read-only; overlay independent source audit.

Uninspected source groups are D (reinspection pending), NOT assumed riverless.
Collapsed-key and recovered-river record denominators are always kept separate.
"""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
from urllib.parse import quote

from audit_individual_rivers import ROOT,sha,write_csv

def integrate(baseline,manifest,research_db,out):
    baseline=Path(baseline).resolve();research_db=Path(research_db).resolve();out=Path(out)
    meta=json.loads(Path(manifest).read_text())
    if sha(baseline)!=meta['database_sha256']:raise ValueError('Baseline SHA mismatch')
    c=sqlite3.connect('file:'+quote(str(baseline),safe='/')+'?mode=ro',uri=True)
    c.execute('PRAGMA query_only=ON')
    if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Baseline corrupt')
    counts=dict(c.execute('SELECT group_id,COUNT(*) FROM survey_evidence GROUP BY group_id'))
    if counts!=meta['group_counts'] or sum(counts.values())!=meta['total_survey_rows']:
        raise ValueError('Baseline counts mismatch')
    duplicate=c.execute('SELECT COUNT(*) FROM (SELECT group_id,region,watershed_name,survey_year,recorded_name,COUNT(*) n FROM survey_evidence GROUP BY 1,2,3,4,5 HAVING n>1)').fetchone()[0]
    if duplicate:raise ValueError('Baseline duplicate keys')
    if research_db.parent!=out:raise ValueError('Output must be the research DB folder')
    r=sqlite3.connect(research_db)
    # Explicit URI read-only attachment: original snapshot cannot be changed.
    r.execute('ATTACH DATABASE ? AS old',('file:'+quote(str(baseline),safe='/')+'?mode=ro',))
    inspected=r.execute('SELECT DISTINCT group_id,region FROM collapsed_keys').fetchall()
    for group,region in inspected:
        for left,right in [('collapsed_keys','old.survey_evidence'),('old.survey_evidence','collapsed_keys')]:
            sql=f'SELECT COUNT(*) FROM (SELECT watershed_name,survey_year,recorded_name FROM {left} WHERE group_id=? AND region=? EXCEPT SELECT watershed_name,survey_year,recorded_name FROM {right} WHERE group_id=? AND region=?)'
            if r.execute(sql,(group,region,group,region)).fetchone()[0]:
                raise ValueError(f'Original/recovered keyset differs: {group}/{region}')
    r.executescript('''
    CREATE TABLE original_key_audit AS
    SELECT b.group_id,b.region,b.watershed_name,b.survey_year,b.recorded_name,
      coalesce(k.match_class,'D') AS match_class,
      coalesce(k.has_any_approved_river,0) AS has_any_approved_river,
      k.has_river_name AS has_river_name,
      CASE WHEN k.group_id IS NULL THEN 'source_not_reinspected' ELSE 'pinned_original_keyset_verified' END AS source_audit_status,
      b.source_url,b.source_archive_sha256
    FROM old.survey_evidence b LEFT JOIN collapsed_keys k
      ON b.group_id=k.group_id AND b.region=k.region AND b.watershed_name=k.watershed_name
      AND b.survey_year=k.survey_year AND b.recorded_name=k.recorded_name;
    CREATE UNIQUE INDEX original_key ON original_key_audit(group_id,region,watershed_name,survey_year,recorded_name);
    ''')
    r.commit()
    group_rows=c.execute('SELECT group_id,COUNT(*),COUNT(DISTINCT recorded_name),MIN(survey_year),MAX(survey_year) FROM survey_evidence GROUP BY group_id').fetchall()
    water_rows=c.execute('SELECT region,watershed_name,group_id,COUNT(*),COUNT(DISTINCT recorded_name),MIN(survey_year),MAX(survey_year) FROM survey_evidence GROUP BY region,watershed_name,group_id ORDER BY region,watershed_name,group_id').fetchall()
    region_rows=c.execute('SELECT region,group_id,COUNT(*),COUNT(DISTINCT recorded_name),MIN(survey_year),MAX(survey_year) FROM survey_evidence GROUP BY region,group_id ORDER BY region,group_id').fetchall()
    write_csv(out/'baseline_group_counts.csv',['group','records','distinct_literal_names_not_species','year_min','year_max'],group_rows)
    write_csv(out/'baseline_watershed_counts.csv',['region','watershed','group','records','distinct_literal_names_not_species','year_min','year_max'],water_rows)
    write_csv(out/'baseline_region_counts.csv',['region','group','records','distinct_literal_names_not_species','year_min','year_max'],region_rows)
    classes=dict(r.execute('SELECT match_class,COUNT(*) FROM original_key_audit GROUP BY match_class'))
    per_group=r.execute('SELECT group_id,match_class,COUNT(*) FROM original_key_audit GROUP BY group_id,match_class').fetchall()
    write_csv(out/'baseline_link_classes.csv',['group','match_class','records'],per_group)
    national=list(csv.DictReader((ROOT/'national-codes-staged/river_codes_national_v07.csv').open(encoding='utf-8')))
    waters=list(csv.DictReader((ROOT/'national-codes-staged/watershed_codes_national_v07.csv').open(encoding='utf-8')))
    watercodes={x['watershed_code'] for x in waters}
    duplicates=CounterTuple=lambda rows,key:len(rows)-len({tuple(r[k] for k in key) for r in rows})
    result={'baseline_artifact_run':39130312796,'baseline_artifact_id':12137787609,
      'baseline_artifact_head_commit':'af62f05cf1a86eec07a8e7a3b541fd010985b5ad',
      'baseline_db_sha256':sha(baseline),'baseline_count':sum(counts.values()),'baseline_group_counts':counts,
      'baseline_literal_names_all_groups':c.execute('SELECT COUNT(DISTINCT recorded_name) FROM survey_evidence').fetchone()[0],
      'baseline_region_watershed_pairs':c.execute('SELECT COUNT(*) FROM (SELECT DISTINCT region,watershed_name FROM survey_evidence)').fetchone()[0],
      'baseline_distinct_watershed_labels':c.execute('SELECT COUNT(DISTINCT watershed_name) FROM survey_evidence').fetchone()[0],
      'original_snapshot_individual_river_not_null':c.execute('SELECT COUNT(*) FROM survey_evidence WHERE verified_individual_river IS NOT NULL').fetchone()[0],
      'original_snapshot_prefecture_not_null':c.execute('SELECT COUNT(*) FROM survey_evidence WHERE verified_prefecture IS NOT NULL').fetchone()[0],
      'taxonomically_confirmed_species_count':None,'baseline_duplicate_keys':duplicate,
      'river_code_rows':len(national),'river_code_duplicates':duplicates(national,['river_code']),
      'watershed_code_rows':len(waters),'watershed_code_duplicates':duplicates(waters,['watershed_code']),
      'river_name_labels':len({x['river_name'] for x in national}),
      'river_rows_without_watershed_code_match':sum(x['watershed_code'] not in watercodes for x in national),
      'inspected_baseline_records':r.execute('SELECT COUNT(*) FROM collapsed_keys').fetchone()[0],
      'baseline_class_counts':classes,
      'baseline_class_percent':{s:round(classes.get(s,0)*100/sum(counts.values()),4) for s in 'ABCD'},
      'baseline_keys_with_any_A':r.execute('SELECT SUM(has_any_approved_river) FROM original_key_audit').fetchone()[0],
      'baseline_keys_with_original_river_name_verified':r.execute('SELECT SUM(has_river_name) FROM original_key_audit').fetchone()[0],
      'recovered_river_variant_class_counts':dict(r.execute('SELECT match_class,COUNT(*) FROM evidence GROUP BY match_class')),
      'source_coverage':inspected,'mysql_production':'unverified','api_entire_dataset':'unverified',
      'prefecture_presence_not_inferred':True,
      'parent_class_rule':'A only if every recovered variant A; B if any named-unapproved variant; C if verified unnamed variant; D for uninspected source. Parent A count differs from keys with any A.',
      'baseline_rows_are_aggregated_water_year_name_not_raw_observations':True}
    (out/'baseline_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    r.execute('DETACH DATABASE old');r.close();c.close()
    if sha(baseline)!=meta['database_sha256']:raise ValueError('Read-only baseline changed')
    with research_db.open('rb') as src,gzip.open(out/(research_db.name+'.gz'),'wb',compresslevel=9) as dst:shutil.copyfileobj(src,dst)
    files={f.name:sha(f) for f in out.iterdir() if f.is_file() and f.name!='checksums.json'}
    (out/'checksums.json').write_text(json.dumps(files,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--baseline',required=True);p.add_argument('--manifest',required=True);p.add_argument('--research-db',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();integrate(a.baseline,a.manifest,a.research_db,a.out)
