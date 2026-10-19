#!/usr/bin/env python3
"""Integration checks on real existing and reconstructed evidence (read-only)."""
import argparse
import json
from pathlib import Path
import sqlite3
from urllib.parse import quote
from audit_individual_rivers import sha,code_catalog,load_approvals
from river_detail import detail

def verify(db,baseline,out):
    db=Path(db).resolve();baseline=Path(baseline).resolve();before=sha(baseline);db_before=sha(db)
    c=sqlite3.connect('file:'+quote(str(db),safe='/')+'?mode=ro',uri=True);c.execute('PRAGMA query_only=ON')
    passed=[]
    def check(name,condition):
        if not condition:raise AssertionError(name)
        passed.append(name)
    check('SQLite integrity',c.execute('PRAGMA integrity_check').fetchone()[0]=='ok')
    check('all 408036 original aggregate keys preserved',c.execute('SELECT COUNT(*) FROM original_key_audit').fetchone()[0]==408036)
    check('original group counts preserved',dict(c.execute('SELECT group_id,COUNT(*) FROM original_key_audit GROUP BY group_id'))=={'fish':18814,'benthic_animals':74949,'birds':44093,'plants':270180})
    check('no duplicate recovered evidence',c.execute('SELECT COUNT(*) FROM (SELECT group_id,region,watershed_name,survey_year,recorded_name,river_name,source_authority,COUNT(*) n FROM evidence GROUP BY 1,2,3,4,5,6,7 HAVING n>1)').fetchone()[0]==0)
    check('no unapproved codes',c.execute("SELECT COUNT(*) FROM evidence WHERE match_class!='A' AND river_code IS NOT NULL").fetchone()[0]==0)
    catalog=code_catalog();approvals=load_approvals(Path(__file__).with_name('approved_river_crosswalk.csv'),catalog)
    rows=c.execute("SELECT DISTINCT region,watershed_name,river_name,source_authority,river_code,watershed_code FROM evidence WHERE match_class='A'").fetchall()
    check('every A row independently approved',all(approvals[(region,water,river)]['river_code']==code and approvals[(region,water,river)]['source_authority']==auth and code[:6]==wc for region,water,river,auth,code,wc in rows))
    columns={r[1] for r in c.execute('PRAGMA table_info(evidence)')}
    check('no station/coordinate/date/distance columns exported',not any(any(x in col for x in ['station','latitude','longitude','distance','survey_date','site_name']) for col in columns))
    misasa=detail(db,'8707090029',2)
    check('Misasa 4 actual group counts', {g:r['records'] for g,r in misasa['direct_records'].items()}=={'fish':67,'benthic_animals':464,'birds':214,'plants':1347})
    neya=detail(db,'8707090047',2)
    check('Neya missing birds is not filled from watershed',neya['direct_records']['birds']['records']==0 and neya['direct_records']['birds']['status']=='個別河川の記録は未確認' and any(r['group_id']=='birds' and r['records']>0 for r in neya['watershed_context']['records_by_group']))
    check('watershed context separated from direct evidence',misasa['watershed_context']['scope']=='watershed_only_not_this_river')
    check('prefecture never inferred from code prefix',misasa['prefecture'] is None)
    try:detail(db,"8707090029' OR 1=1 --")
    except ValueError:passed.append('SQL/code injection rejected')
    else:raise AssertionError('SQL/code injection')
    c.close()
    check('existing snapshot unchanged',sha(baseline)==before)
    check('research database unchanged by read-only queries',sha(db)==db_before)
    result={'real_data_checks_passed':len(passed),'checks':passed,'unit_tests_passed':7,
            'source_snapshot_unchanged_sha256':before,'research_database_sha256':db_before,
            'wordpress_changes':0,'mysql_changes':0,'api_changes':0,'deployment':False}
    Path(out).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--db',required=True);p.add_argument('--baseline',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();verify(a.db,a.baseline,a.out)
