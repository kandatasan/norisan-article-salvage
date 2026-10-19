#!/usr/bin/env python3
"""Split/reassemble the research-only compressed SQLite under upload limits."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3

CHUNK = 7_500_000


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as source:
        for piece in iter(lambda: source.read(1024*1024), b''):
            h.update(piece)
    return h.hexdigest()


def split(database, out):
    database=Path(database);out=Path(out)
    out.mkdir(parents=True,exist_ok=True)
    gz=Path(str(database)+'.gz')
    if not gz.exists():
        with database.open('rb') as source, gzip.open(gz,'wb',compresslevel=9) as target:
            shutil.copyfileobj(source,target)
    parts=[]
    with gz.open('rb') as source:
        for index in range(100):
            content=source.read(CHUNK)
            if not content:break
            path=out/f'river_individual_research.sqlite.gz.part{index:03d}'
            if path.exists():raise FileExistsError(path)
            path.write_bytes(content)
            parts.append({'name':path.name,'bytes':len(content),'sha256':digest(path)})
    manifest={'format':'gzip-split-v1','database_name':'river_individual_research.sqlite',
              'database_bytes':database.stat().st_size,'database_sha256':digest(database),
              'gzip_bytes':gz.stat().st_size,'gzip_sha256':digest(gz),'parts':parts}
    (out/'snapshot_parts.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def assemble(directory, output):
    directory=Path(directory);output=Path(output)
    meta=json.loads((directory/'snapshot_parts.json').read_text())
    if meta['format']!='gzip-split-v1' or output.exists():raise ValueError('Manifest invalid or output exists')
    with output.open('wb') as target:
        for part in meta['parts']:
            path=directory/part['name']
            if not path.is_file() or path.stat().st_size!=part['bytes'] or digest(path)!=part['sha256']:
                raise ValueError('Part missing or changed: '+part['name'])
            with path.open('rb') as source:shutil.copyfileobj(source,target)
    if digest(output)!=meta['gzip_sha256'] or output.stat().st_size!=meta['gzip_bytes']:
        raise ValueError('Reassembled gzip SHA/size differs')
    restored=output.with_suffix('')
    if restored.exists():raise FileExistsError(restored)
    with gzip.open(output,'rb') as source,restored.open('wb') as target:shutil.copyfileobj(source,target)
    if digest(restored)!=meta['database_sha256'] or restored.stat().st_size!=meta['database_bytes']:
        raise ValueError('Reassembled SQLite SHA/size differs')
    con=sqlite3.connect(f'file:{restored.resolve()}?mode=ro',uri=True)
    if con.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('SQLite integrity failed')
    con.close()
    return restored


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['split','assemble'])
    p.add_argument('--database');p.add_argument('--parts-dir',required=True);p.add_argument('--output')
    a=p.parse_args()
    if a.action=='split':print(json.dumps(split(a.database,a.parts_dir),indent=2))
    else:print(assemble(a.parts_dir,a.output))
