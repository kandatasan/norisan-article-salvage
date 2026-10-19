#!/usr/bin/env python3
"""Normalize repeated provenance and labels; expose unchanged read-only views."""
import argparse
import gzip
from pathlib import Path
import shutil
import sqlite3
from urllib.parse import quote

def compact(source,out):
    source=Path(source).resolve();out=Path(out).resolve()
    if out.exists():raise FileExistsError('Never overwrite snapshot')
    c=sqlite3.connect(out,uri=True);c.execute('PRAGMA foreign_keys=ON')
    c.execute('ATTACH DATABASE ? AS old',('file:'+quote(str(source),safe='/')+'?mode=ro',))
    c.executescript('''
    CREATE TABLE sources(id INTEGER PRIMARY KEY,group_id TEXT NOT NULL,region TEXT NOT NULL,source_url TEXT NOT NULL,source_sha256 TEXT NOT NULL,
                         UNIQUE(group_id,region,source_url,source_sha256));
    INSERT INTO sources(group_id,region,source_url,source_sha256)
       SELECT DISTINCT group_id,region,source_url,source_archive_sha256 FROM old.original_key_audit
       UNION SELECT DISTINCT group_id,region,source_url,source_sha256 FROM old.evidence ORDER BY 1,2;
    CREATE TABLE watersheds(id INTEGER PRIMARY KEY,region TEXT NOT NULL,watershed_name TEXT NOT NULL,UNIQUE(region,watershed_name));
    INSERT INTO watersheds(region,watershed_name) SELECT DISTINCT region,watershed_name FROM old.original_key_audit ORDER BY 1,2;
    CREATE TABLE labels(id INTEGER PRIMARY KEY,recorded_name TEXT NOT NULL UNIQUE);
    INSERT INTO labels(recorded_name) SELECT DISTINCT recorded_name FROM old.original_key_audit ORDER BY 1;
    CREATE TABLE river_context(id INTEGER PRIMARY KEY,watershed_id INTEGER NOT NULL REFERENCES watersheds(id),river_name TEXT,
      source_authority TEXT,river_code TEXT,watershed_code TEXT,match_class TEXT,target_scope TEXT,match_reason TEXT,
      code_source_url TEXT,code_source_page TEXT,publication_note TEXT,
      UNIQUE(watershed_id,river_name,source_authority,match_class),
      CHECK((match_class='A' AND length(river_code)=10 AND substr(river_code,1,6)=watershed_code) OR
            (match_class!='A' AND river_code IS NULL AND watershed_code IS NULL)));
    INSERT INTO river_context(watershed_id,river_name,source_authority,river_code,watershed_code,match_class,target_scope,match_reason,code_source_url,code_source_page,publication_note)
      SELECT DISTINCT w.id,e.river_name,e.source_authority,e.river_code,e.watershed_code,e.match_class,e.target_scope,e.match_reason,e.code_source_url,e.code_source_page,e.publication_note
      FROM old.evidence e JOIN watersheds w ON e.region=w.region AND e.watershed_name=w.watershed_name;
    CREATE TABLE river_evidence(id INTEGER PRIMARY KEY,source_id INTEGER NOT NULL REFERENCES sources(id),
       river_context_id INTEGER NOT NULL REFERENCES river_context(id),label_id INTEGER NOT NULL REFERENCES labels(id),
       survey_year TEXT NOT NULL,source_rows INTEGER NOT NULL,
       UNIQUE(source_id,river_context_id,label_id,survey_year));
    INSERT INTO river_evidence(source_id,river_context_id,label_id,survey_year,source_rows)
       SELECT s.id,r.id,l.id,e.survey_year,e.source_rows FROM old.evidence e
       JOIN sources s ON e.group_id=s.group_id AND e.region=s.region AND e.source_url=s.source_url AND e.source_sha256=s.source_sha256
       JOIN watersheds w ON e.region=w.region AND e.watershed_name=w.watershed_name
       JOIN river_context r ON r.watershed_id=w.id AND r.river_name=e.river_name AND r.source_authority=e.source_authority AND r.match_class=e.match_class
       JOIN labels l ON e.recorded_name=l.recorded_name;
    CREATE TABLE original_keys(id INTEGER PRIMARY KEY,source_id INTEGER NOT NULL REFERENCES sources(id),watershed_id INTEGER NOT NULL REFERENCES watersheds(id),
       label_id INTEGER NOT NULL REFERENCES labels(id),survey_year TEXT NOT NULL,match_class TEXT NOT NULL,
       has_any_approved_river INTEGER NOT NULL,has_river_name INTEGER,source_audit_status TEXT NOT NULL,
       UNIQUE(source_id,watershed_id,label_id,survey_year));
    INSERT INTO original_keys(source_id,watershed_id,label_id,survey_year,match_class,has_any_approved_river,has_river_name,source_audit_status)
       SELECT s.id,w.id,l.id,k.survey_year,k.match_class,k.has_any_approved_river,k.has_river_name,k.source_audit_status FROM old.original_key_audit k
       JOIN sources s ON s.group_id=k.group_id AND s.region=k.region AND s.source_url=k.source_url AND s.source_sha256=k.source_archive_sha256
       JOIN watersheds w ON w.region=k.region AND w.watershed_name=k.watershed_name
       JOIN labels l ON l.recorded_name=k.recorded_name;
    CREATE INDEX context_river_code ON river_context(river_code);
    CREATE INDEX evidence_river ON river_evidence(river_context_id,source_id,survey_year);
    CREATE INDEX original_water ON original_keys(watershed_id,source_id,survey_year);
    CREATE VIEW evidence AS SELECT s.group_id,s.region,w.watershed_name,e.survey_year,l.recorded_name,
       r.river_name,r.source_authority,r.river_code,r.watershed_code,r.match_class,r.target_scope,r.match_reason,
       s.source_url,s.source_sha256,e.source_rows,r.code_source_url,r.code_source_page,r.publication_note
       FROM river_evidence e JOIN river_context r ON e.river_context_id=r.id JOIN watersheds w ON r.watershed_id=w.id
       JOIN sources s ON e.source_id=s.id JOIN labels l ON e.label_id=l.id;
    CREATE VIEW approved_individual_river AS SELECT * FROM evidence WHERE match_class='A' AND target_scope='individual_river';
    CREATE VIEW original_key_audit AS SELECT s.group_id,s.region,w.watershed_name,k.survey_year,l.recorded_name,
       k.match_class,k.has_any_approved_river,k.has_river_name,k.source_audit_status,s.source_url,s.source_sha256 source_archive_sha256
       FROM original_keys k JOIN sources s ON k.source_id=s.id JOIN watersheds w ON k.watershed_id=w.id JOIN labels l ON k.label_id=l.id;
    CREATE VIEW watershed_history AS SELECT * FROM original_key_audit;
    ''')
    for table in ['evidence','original_key_audit']:
        expected=c.execute(f'SELECT COUNT(*) FROM old.{table}').fetchone()[0]
        actual=c.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
        if expected!=actual:raise ValueError('Normalization lost rows: '+table)
    if c.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('Broken normalized references')
    if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Broken normalized snapshot')
    c.commit();c.close()
    with out.open('rb') as src,gzip.open(str(out)+'.gz','wb',compresslevel=9) as dst:shutil.copyfileobj(src,dst)
    print('COMPACT',out.stat().st_size,Path(str(out)+'.gz').stat().st_size)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();compact(a.source,a.out)
