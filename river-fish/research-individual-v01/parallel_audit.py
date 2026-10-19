#!/usr/bin/env python3
"""Bounded three-process audit with reusable SHA-identified source caches."""
import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
import sqlite3
from audit_individual_rivers import (sources,sha,obtain,code_catalog,load_approvals,
                                    audit_source,SCHEMA,finish)

def worker(s,raw_dir,cache,approvals):
    path=obtain(s,raw_dir,False)
    catalog=code_catalog();approved=load_approvals(approvals,catalog);candidates=defaultdict(list)
    for v in catalog.values():candidates[(v['watershed_name'],v['river_name'])].append(v['river_code'])
    stem=s['region']+'_'+s['group'];cache=Path(cache)
    db=cache/(stem+'.sqlite');report=cache/(stem+'.json')
    signature={'source_sha':s['checksum_sha256'],'code_sha':sha(Path(__file__).with_name('audit_individual_rivers.py')),'approval_sha':sha(approvals)}
    if db.exists() and report.exists():
        previous=json.loads(report.read_text())
        if previous['cache_signature']==signature:return str(db),previous
        raise ValueError('Stale cache; use a new cache directory')
    c=sqlite3.connect(db);c.executescript(SCHEMA)
    r=audit_source(s,path,c,approved,candidates);c.commit();c.close()
    r['cache_signature']=signature;report.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    return str(db),r

def main():
    p=argparse.ArgumentParser();p.add_argument('--raw-dir',required=True);p.add_argument('--cache',required=True)
    p.add_argument('--out',required=True);p.add_argument('--approvals',required=True);p.add_argument('--input-commit',required=True)
    p.add_argument('--seed-output');a=p.parse_args();cache=Path(a.cache);cache.mkdir(parents=True,exist_ok=True)
    out=Path(a.out)
    if out.exists():raise FileExistsError('Never overwrite audit output')
    out.mkdir(parents=True)
    if a.seed_output:
        seed=Path(a.seed_output);m=json.loads((seed/'audit_summary.json').read_text())
        for report in m['sources']:
            stem=report['region']+'_'+report['group'];db=cache/(stem+'.sqlite')
            c=sqlite3.connect(db);c.executescript(SCHEMA);c.execute('ATTACH DATABASE ? AS src',(str(seed/'individual_river_research.sqlite'),))
            for table in ['evidence','collapsed_keys']:
                c.execute(f'INSERT INTO {table} SELECT * FROM src.{table} WHERE group_id=? AND region=?',(report['group'],report['region']))
            c.commit();c.close()
            report['cache_signature']={'source_sha':report['sha256'],'code_sha':sha(Path(__file__).with_name('audit_individual_rivers.py')),'approval_sha':sha(a.approvals)}
            (cache/(stem+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    reports=[];errors=[];con=sqlite3.connect(out/'individual_river_research.sqlite');con.executescript(SCHEMA)
    with ProcessPoolExecutor(max_workers=3) as ex:
        futures={ex.submit(worker,s,a.raw_dir,cache,a.approvals):s for s in sources()}
        for f in as_completed(futures):
            s=futures[f]
            try:
                db,r=f.result();con.execute('ATTACH DATABASE ? AS src',(db,))
                for t in ['evidence','collapsed_keys']:con.execute(f'INSERT INTO {t} SELECT * FROM src.{t}')
                con.commit();con.execute('DETACH DATABASE src');reports.append(r)
                print('AUDITED',s['region'],s['group'],r['collapsed_records'],r['recovered_class_counts'],flush=True)
            except Exception as e:
                errors.append({'region':s['region'],'group':s['group'],'error':str(e)})
                print('UNVERIFIED',s['region'],s['group'],str(e),flush=True)
    summary=finish(con,out,reports,a.input_commit);con.close();summary['unavailable_sources']=errors
    (out/'audit_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print('COMPLETE',summary['collapsed_records'],summary['recovered_class_counts'] if 'recovered_class_counts' in summary else summary['recovered_classes'],flush=True)

if __name__=='__main__':main()
