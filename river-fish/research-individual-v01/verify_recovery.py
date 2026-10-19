#!/usr/bin/env python3
"""Validate a reconstructed research snapshot against archived source counts."""
import argparse
import json
from pathlib import Path
import sqlite3
from urllib.parse import quote

from audit_individual_rivers import code_catalog, load_approvals, sha
from river_detail import detail

EXPECTED_GROUPS={'fish':18814,'benthic_animals':74949,'birds':44093,'plants':270180}
EXPECTED_CLASSES={'A':84965,'B':569596,'C':24917}
EXPECTED_ORIGINAL={'A':50907,'B':348915,'C':8214}


def verify(db,summary,reference,out):
    meta=json.loads(Path(summary).read_text())
    prior=json.loads(Path(reference).read_text())
    con=sqlite3.connect('file:'+quote(str(Path(db).resolve()),safe='/')+'?mode=ro',uri=True)
    con.execute('PRAGMA query_only=ON')
    checks=[]
    def check(label,condition):
        if not condition:raise AssertionError(label)
        checks.append(label)
    check('SQLite integrity',con.execute('PRAGMA integrity_check').fetchone()[0]=='ok')
    check('36 official archives match archived SHA',len(meta['sources'])==36 and sorted((s['group'],s['region'],s['sha256']) for s in meta['sources'])==sorted((s['group'],s['region'],s['sha256']) for s in prior['sources']))
    check('408036 original keys preserved',dict(con.execute('SELECT group_id,COUNT(*) FROM original_key_audit GROUP BY group_id'))==EXPECTED_GROUPS)
    check('679478 recovered river contexts',dict(con.execute('SELECT match_class,COUNT(*) FROM evidence GROUP BY match_class'))==EXPECTED_CLASSES)
    check('conservative original-key classification preserved',dict(con.execute('SELECT match_class,COUNT(*) FROM original_key_audit GROUP BY match_class'))==EXPECTED_ORIGINAL)
    check('no unapproved code attached',con.execute("SELECT COUNT(*) FROM evidence WHERE match_class!='A' AND river_code IS NOT NULL").fetchone()[0]==0)
    cross=load_approvals(Path(__file__).with_name('approved_river_crosswalk.csv'),code_catalog())
    exact=con.execute("SELECT DISTINCT region,watershed_name,river_name,source_authority,river_code,watershed_code FROM evidence WHERE match_class='A'").fetchall()
    check('all A codes independently approved',all(cross[(reg,water,river)]['river_code']==code and cross[(reg,water,river)]['source_authority']==auth and code[:6]==wc for reg,water,river,auth,code,wc in exact))
    misasa=detail(db,'8707090029',2)
    check('Misasa four direct counts', {g:v['records'] for g,v in misasa['direct_records'].items()}=={'fish':67,'benthic_animals':464,'birds':214,'plants':1347})
    neya=detail(db,'8707090047',2)
    check('Neya missing direct birds stays empty',neya['direct_records']['birds']['records']==0 and any(r['group_id']=='birds' and r['records']>0 for r in neya['watershed_context']['records_by_group']))
    check('prefecture not inferred',misasa['prefecture'] is None)
    check('no detailed-location fields',not any(any(token in row[1] for token in ('station','latitude','longitude','distance','survey_date','site_name')) for table in ('river_evidence','river_context') for row in con.execute('PRAGMA table_info('+table+')')))
    con.close()
    result={'checks_passed':len(checks),'checks':checks,'sqlite_sha256':sha(db),
            'source_report':'prior run key-for-key compared with v27 artifact; recovery run reverified pinned original archives and archived per-source counts',
            'baseline_artifact_retrieved_in_this_run':False}
    Path(out).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--db',required=True);p.add_argument('--summary',required=True)
    p.add_argument('--reference',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();verify(a.db,a.summary,a.reference,a.out)
