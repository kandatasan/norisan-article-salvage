#!/usr/bin/env python3
"""Restore source provenance for verified original keys without baseline bytes.

Only for recovery of the research snapshot. The original GitHub Actions DB
was compared key-for-key with the 36 pinned source archives in the prior run;
this module retains those original keys after a transient workspace reset.
It does not claim a fresh byte comparison with the unavailable artifact.
"""
import argparse
import json
from pathlib import Path
import sqlite3

from audit_individual_rivers import sources

EXPECTED = {'fish': 18814, 'benthic_animals': 74949,
            'birds': 44093, 'plants': 270180}


def restore(database, reference):
    reports = json.loads(Path(reference).read_text())
    entries = {(s['group'], s['region']): s for s in sources()}
    for report in reports['sources']:
        key = report['group'], report['region']
        pinned = entries.pop(key)
        if report['sha256'] != pinned['checksum_sha256'] or report['source_url'] != pinned['source_url']:
            raise ValueError('Pinned source disagrees with archived report')
    if entries or len(reports['sources']) != 36:
        raise ValueError('Expected 36 audited sources')
    con = sqlite3.connect(database)
    try:
        for report in reports['sources']:
            key = report['group'], report['region']
            collapsed = con.execute('SELECT COUNT(*) FROM collapsed_keys WHERE group_id=? AND region=?', key).fetchone()[0]
            recovered = con.execute('SELECT COUNT(*) FROM evidence WHERE group_id=? AND region=?', key).fetchone()[0]
            if (collapsed,recovered) != (report['collapsed_records'],report['recovered_records']):
                raise ValueError(f'Archived source counts changed: {key}')
        actual = dict(con.execute('SELECT group_id,COUNT(*) FROM collapsed_keys GROUP BY group_id'))
        if actual != EXPECTED or sum(actual.values()) != 408036:
            raise ValueError(f'Reconstructed original-key group counts changed: {actual}')
        if dict(con.execute('SELECT match_class,COUNT(*) FROM collapsed_keys GROUP BY match_class')) != {'A':50907,'B':348915,'C':8214}:
            raise ValueError('Original-key classifications changed')
        con.executescript('''
        CREATE TEMP TABLE source_lookup AS
        SELECT group_id,region,MIN(source_url) source_url,MIN(source_sha256) source_sha256,
               COUNT(DISTINCT source_url) url_count,COUNT(DISTINCT source_sha256) sha_count
        FROM evidence GROUP BY group_id,region;
        CREATE TABLE original_key_audit AS
        SELECT k.group_id,k.region,k.watershed_name,k.survey_year,k.recorded_name,
               k.match_class,k.has_any_approved_river,k.has_river_name,
               'pinned_original_keyset_verified_prior_run' source_audit_status,
               s.source_url,
               CASE WHEN k.group_id='fish' THEN '' ELSE s.source_sha256 END source_archive_sha256
        FROM collapsed_keys k JOIN source_lookup s
          ON k.group_id=s.group_id AND k.region=s.region;
        CREATE UNIQUE INDEX original_key ON original_key_audit
          (group_id,region,watershed_name,survey_year,recorded_name);
        ''')
        if con.execute('SELECT COUNT(*) FROM source_lookup WHERE url_count!=1 OR sha_count!=1').fetchone()[0]:
            raise ValueError('A group-region has multiple source archives')
        if con.execute('SELECT COUNT(*) FROM original_key_audit').fetchone()[0] != 408036:
            raise ValueError('A source key was lost during reconstruction')
        if con.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Reconstructed DB integrity check failed')
        con.commit()
    finally:
        con.close()


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--db',required=True);p.add_argument('--reference',required=True)
    a=p.parse_args();restore(a.db,a.reference)
