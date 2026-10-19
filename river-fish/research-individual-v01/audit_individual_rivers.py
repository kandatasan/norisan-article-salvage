#!/usr/bin/env python3
"""Read pinned MLIT source archives; restore river-level evidence, never locations.

Independent research output only. No WordPress/API/MySQL writes or deployments.
Requires the existing source registries and national river-code CSVs in ../.
"""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import gzip
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
import sqlite3
import urllib.request
from zipfile import ZipFile
import xml.etree.ElementTree as ET
try:
    from lxml import etree as FAST_XML
except ImportError:
    FAST_XML = None

ROOT = Path(__file__).resolve().parents[1]
M = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
CATEGORIES = {'fish':'魚類','benthic_animals':'底生動物','birds':'鳥類','plants':'植物'}
REQUIRED = {'category':'生物項目','authority':'地整','watershed':'水系',
            'year':'調査年度','name':'種名','river':'河川名'}
INDEX = 'https://www.nilim.go.jp/lab/fbg/ksnkankyo/dl_00_index.html'
TERMS = 'https://www.nilim.go.jp/lab/fbg/ksnkankyo/Mokj_chui.htm'

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def sources():
    fish=json.loads((ROOT/'nationwide_sources_v06.json').read_text())
    out=[dict(x,group='fish',region=x['region_id']) for x in fish['region_sources']]
    for group,file in [('benthic_animals','benthic_sources_v19.json'),
                       ('birds','bird_sources_v25.json'),('plants','plant_sources_v27.json')]:
        for x in json.loads((ROOT/'biota'/file).read_text())['regions']:
            out.append(dict(x,group=group))
    return out

def obtain(source,raw_dir,download=False):
    p=Path(raw_dir)/source['source_url'].rsplit('/',1)[-1]
    if not p.exists():
        if not download:raise FileNotFoundError(p)
        p.parent.mkdir(parents=True,exist_ok=True)
        req=urllib.request.Request(source['source_url'],headers={'User-Agent':'tsurikue-river-research/1.0'})
        temp=p.with_suffix('.part')
        with urllib.request.urlopen(req,timeout=180) as r, temp.open('wb') as f:
            if r.status!=200 or r.url!=source['source_url']:raise ValueError('Unexpected response')
            n=0
            while b:=r.read(1024*1024):
                n+=len(b)
                if n>260_000_000:raise ValueError('Oversized ZIP')
                f.write(b)
        if sha(temp)!=source['checksum_sha256']:raise ValueError('Source SHA256 changed')
        temp.replace(p)
    if sha(p)!=source['checksum_sha256']:raise ValueError('Cached source SHA256 mismatch')
    return p

def source_rows(path,member):
    """Header-driven selection: plants need not use the same river column.

    Read only authority/category/watershed/year/literal name/river. Never read
    station names/numbers, distances, precise dates, coordinates or abundance.
    """
    with ZipFile(path) as outer:
        files=[i for i in outer.infolist() if not i.is_dir()]
        if len(files)!=1 or files[0].filename!=member or files[0].file_size>220_000_000:
            raise ValueError('Workbook member or size changed')
        book=outer.read(member)
    with ZipFile(BytesIO(book)) as z:
        if z.getinfo('xl/worksheets/sheet1.xml').file_size>1_800_000_000:
            raise ValueError('Oversized sheet')
        strings=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            with z.open('xl/sharedStrings.xml') as f:
                context=ET.iterparse(f,events=('start','end'));_,root=next(context)
                for event,e in context:
                    if event=='end' and e.tag==M+'si':
                        strings.append(''.join(t.text or '' for t in e.iter(M+'t')))
                        e.clear();root.clear()
        mapping=None
        with z.open('xl/worksheets/sheet1.xml') as f:
            if FAST_XML is not None:
                context=FAST_XML.iterparse(f,events=('end',),tag=M+'row',
                                          huge_tree=True,no_network=True,resolve_entities=False)
            else:
                context=ET.iterparse(f,events=('start','end'));_,root=next(context)
            for event,row in context:
                if event!='end' or row.tag!=M+'row':continue
                values={}
                for cell in row.findall(M+'c'):
                    col=re.match(r'[A-Z]+',cell.get('r','')).group()
                    if mapping is not None and col not in mapping:continue
                    value=cell.findtext(M+'v') or ''
                    if cell.get('t')=='s':value=strings[int(value)] if value else ''
                    elif cell.get('t')=='inlineStr':value=''.join(t.text or '' for t in cell.iter(M+'t'))
                    values[col]=value.strip()
                if mapping is None:
                    mapping={}
                    for field,label in REQUIRED.items():
                        found=[col for col,v in values.items() if v==label]
                        if len(found)!=1:raise ValueError('Missing/ambiguous header: '+label)
                        mapping[found[0]]=field
                    yield {'_header':values,'_mapping':mapping}
                else:
                    yield {mapping[c]:values.get(c,'') for c in mapping}
                row.clear()
                if FAST_XML is not None:
                    parent=row.getparent()
                    while row.getprevious() is not None:del parent[0]
                else:root.clear()

def valid(r):
    return (bool(r['watershed'] and r['name']) and
            re.fullmatch(r'(?:19|20)\d{2}',r['year']) is not None and r['year']<='2026'
            and len(r['watershed'])<=80 and len(r['name'])<=150
            and not any(v[0] in '=+-@' for v in (r['watershed'],r['name'])))

def code_catalog():
    with (ROOT/'national-codes-staged/river_codes_national_v07.csv').open(encoding='utf-8',newline='') as f:
        rows=list(csv.DictReader(f))
    return {x['river_code']:x for x in rows}

def load_approvals(path,catalog):
    out={}
    if not path:return out
    with Path(path).open(encoding='utf-8',newline='') as f:
        for r in csv.DictReader(f):
            code=r['river_code'];v=catalog.get(code)
            if not v or (v['river_name'],v['watershed_name'],v['watershed_code'])!=(r['river_name'],r['watershed_name'],r['watershed_code']):
                raise ValueError('Approval disagrees with national registry')
            if not re.fullmatch(r'\d{10}',code) or code[:6]!=r['watershed_code']:
                raise ValueError('Invalid approved code')
            if not r['code_source_url'].startswith('https://www.cgr.mlit.go.jp/kasen/code/pdf/'):
                raise ValueError('Unreviewed approval provenance')
            key=(r['region'],r['watershed_name'],r['river_name'])
            if key in out:raise ValueError('Ambiguous approval')
            out[key]=r
    return out

def classify(region,water,river,authority,approvals,candidates):
    if not water:return 'D',None,'missing watershed'
    if not river:return 'C',None,'original river field empty; watershed context only'
    approved=approvals.get((region,water,river))
    if approved and authority==approved['source_authority']:
        return 'A',approved,'exact source authority + watershed + river; independently checked code ledger'
    n=len(candidates.get((water,river),[]))
    return 'B',None,f'original river name retained; {n} exact national name-pair candidates; not approved'

def audit_source(source,path,con,approvals,candidates):
    group=source['group'];region=source['region'];unique=Counter();raw=Counter()
    iterator=source_rows(path,source['xlsx_member']);meta=next(iterator)
    categories=Counter();authorities=Counter()
    for r in iterator:
        raw['source_rows']+=1;categories[r['category']]+=1
        if r['category']!=CATEGORIES[group]:raw['excluded_category']+=1;continue
        if not valid(r):raw['excluded_invalid']+=1;continue
        raw['accepted_source_rows']+=1
        if r['river']:raw['source_rows_with_river_name']+=1
        authorities[r['authority']]+=1
        unique[(r['watershed'],r['year'],r['name'],r['river'],r['authority'])]+=1
    base=defaultdict(set);base_named=set();class_counts=Counter();rows=[]
    for (water,year,name,river,authority),n in sorted(unique.items()):
        status,a,reason=classify(region,water,river,authority,approvals,candidates)
        base[(water,year,name)].add(status)
        if river:base_named.add((water,year,name))
        class_counts[status]+=1
        rows.append((group,region,water,year,name,river,authority,
                     a['river_code'] if a else None,a['watershed_code'] if a else None,
                     status,'individual_river' if river else 'watershed',reason,
                     source['source_url'],source['checksum_sha256'],n,
                     a['code_source_url'] if a else None,a['code_source_page'] if a else None,
                     'research_only; no detailed locations; public release requires review'))
    con.executemany('INSERT INTO evidence VALUES ('+','.join('?'*18)+')',rows)
    base_counts=Counter()
    for (water,year,name),ss in base.items():
        # Parent is A only if every recovered variant is approved A.
        state='A' if ss=={'A'} else ('D' if 'D' in ss else ('B' if 'B' in ss else 'C'))
        base_counts[state]+=1
        con.execute('INSERT INTO collapsed_keys VALUES (?,?,?,?,?,?,?,?,?)',
                    (group,region,water,year,name,state,int('A' in ss),int((water,year,name) in base_named),','.join(sorted(ss))))
    expected=source.get('expected_aggregated_records')
    if group=='fish':
        expected=json.loads((ROOT/'nationwide-staged'/region/'manifest.json').read_text())['aggregated_records']
    if expected is not None and len(base)!=expected:raise ValueError(f'{region}/{group}: baseline mismatch {len(base)} != {expected}')
    result=dict(raw,group=group,region=region,original_categories=dict(categories),authorities=dict(authorities),
                source_url=source['source_url'],sha256=source['checksum_sha256'],member=source['xlsx_member'],
                header_mapping=meta['_mapping'],omitted_original_column_labels=[v for c,v in meta['_header'].items() if c not in meta['_mapping']],
                collapsed_records=len(base),collapsed_records_with_river_name=len(base_named),
                recovered_records=len(rows),recovered_class_counts=dict(class_counts),collapsed_class_counts=dict(base_counts),
                classification_granularity='exact labels; original collapsed keys and recovered river variants counted separately')
    return result

SCHEMA='''
CREATE TABLE evidence(group_id TEXT,region TEXT,watershed_name TEXT,survey_year TEXT,recorded_name TEXT,
 river_name TEXT,source_authority TEXT,river_code TEXT,watershed_code TEXT,match_class TEXT,
 target_scope TEXT,match_reason TEXT,source_url TEXT,source_sha256 TEXT,source_rows INTEGER,
 code_source_url TEXT,code_source_page TEXT,publication_note TEXT,
 CHECK(match_class IN ('A','B','C','D')),
 CHECK((match_class='A' AND length(river_code)=10 AND substr(river_code,1,6)=watershed_code) OR
       (match_class!='A' AND river_code IS NULL AND watershed_code IS NULL)));
CREATE TABLE collapsed_keys(group_id TEXT,region TEXT,watershed_name TEXT,survey_year TEXT,recorded_name TEXT,
 match_class TEXT,has_any_approved_river INTEGER,has_river_name INTEGER,child_classes TEXT,
 PRIMARY KEY(group_id,region,watershed_name,survey_year,recorded_name));
CREATE VIEW approved_individual_river AS SELECT * FROM evidence WHERE match_class='A' AND target_scope='individual_river';
CREATE VIEW watershed_history AS SELECT * FROM collapsed_keys;
'''

def write_csv(path,headers,rows):
    with Path(path).open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f);w.writerow(headers);w.writerows(rows)

def finish(con,out,source_reports,base_sha):
    con.executescript('''CREATE INDEX river_search ON evidence(river_code,group_id,survey_year);
    CREATE INDEX watershed_search ON evidence(region,watershed_name,group_id);
    CREATE INDEX name_search ON evidence(recorded_name,group_id);''')
    con.commit()
    if con.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('SQLite integrity failure')
    groups=con.execute('SELECT group_id,COUNT(*),COUNT(DISTINCT recorded_name),MIN(survey_year),MAX(survey_year),SUM(has_river_name),SUM(has_any_approved_river) FROM collapsed_keys GROUP BY group_id').fetchall()
    water=con.execute('SELECT region,watershed_name,group_id,COUNT(*),COUNT(DISTINCT recorded_name),MIN(survey_year),MAX(survey_year),SUM(has_river_name),SUM(has_any_approved_river) FROM collapsed_keys GROUP BY region,watershed_name,group_id ORDER BY region,watershed_name,group_id').fetchall()
    river=con.execute('SELECT region,watershed_name,river_name,river_code,group_id,COUNT(*),COUNT(DISTINCT recorded_name),MIN(survey_year),MAX(survey_year),match_class FROM evidence GROUP BY region,watershed_name,river_name,river_code,group_id,match_class ORDER BY region,watershed_name,river_name,group_id').fetchall()
    write_csv(out/'group_counts.csv',['group','collapsed_records','distinct_literal_names_not_species','year_min','year_max','keys_with_river_name','keys_with_any_A'],groups)
    write_csv(out/'watershed_counts.csv',['region','watershed','group','collapsed_records','distinct_literal_names_not_species','year_min','year_max','keys_with_river_name','keys_with_any_A'],water)
    write_csv(out/'river_counts.csv',['region','watershed','river','river_code','group','recovered_records','distinct_literal_names_not_species','year_min','year_max','match_class'],river)
    summary={'audit_version':'1.0','input_git_commit':base_sha,'production_mysql':'unverified; no direct connection',
             'public_api':'previously observed two 20-row pages only; not bulk scanned; no new API requests',
             'source_index':INDEX,'usage_terms':TERMS,'exact_station_fields_exported':False,
             'taxonomically_verified_species_count':None,'name_identity_rule':'literal labels; no taxonomic merging',
             'groups':dict((r[0],dict(zip(['records','literal_names','year_min','year_max','keys_with_river_name','keys_with_any_A'],r[1:]))) for r in groups),
             'collapsed_records':con.execute('SELECT COUNT(*) FROM collapsed_keys').fetchone()[0],
             'recovered_records':con.execute('SELECT COUNT(*) FROM evidence').fetchone()[0],
             'collapsed_classes':dict(con.execute('SELECT match_class,COUNT(*) FROM collapsed_keys GROUP BY match_class')),
             'recovered_classes':dict(con.execute('SELECT match_class,COUNT(*) FROM evidence GROUP BY match_class')),
             'sources':source_reports}
    n=summary['collapsed_records'];summary['collapsed_class_percent']={c:round(summary['collapsed_classes'].get(c,0)*100/n,4) for c in 'ABCD'}
    (out/'audit_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    return summary

def main():
    p=argparse.ArgumentParser();p.add_argument('--raw-dir',required=True);p.add_argument('--out',required=True)
    p.add_argument('--regions',nargs='+',default=['chugoku']);p.add_argument('--download',action='store_true')
    p.add_argument('--download-only',action='store_true');p.add_argument('--approvals');p.add_argument('--input-commit',required=True)
    a=p.parse_args();selected=[s for s in sources() if a.regions==['all'] or s['region'] in a.regions]
    available=[];errors=[]
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures={ex.submit(obtain,s,a.raw_dir,a.download):s for s in selected}
        for fut in as_completed(futures):
            s=futures[fut]
            try:available.append((s,fut.result()));print('SOURCE_OK',s['region'],s['group'],flush=True)
            except Exception as e:errors.append(dict(region=s['region'],group=s['group'],error=str(e)));print('SOURCE_ERROR',errors[-1],flush=True)
    if a.download_only:return
    out=Path(a.out)
    if out.exists():raise FileExistsError('Never overwrite prior research output')
    out.mkdir(parents=True)
    catalog=code_catalog();approvals=load_approvals(a.approvals,catalog);candidates=defaultdict(list)
    for v in catalog.values():candidates[(v['watershed_name'],v['river_name'])].append(v['river_code'])
    con=sqlite3.connect(out/'individual_river_research.sqlite');con.executescript(SCHEMA);reports=[]
    for s,path in sorted(available,key=lambda x:(x[0]['region'],x[0]['group'])):
        report=audit_source(s,path,con,approvals,candidates);reports.append(report);con.commit()
        print('AUDITED',s['region'],s['group'],report['collapsed_records'],report['recovered_class_counts'],flush=True)
    summary=finish(con,out,reports,a.input_commit);con.close()
    summary['unavailable_sources']=errors
    (out/'audit_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    with (out/'individual_river_research.sqlite').open('rb') as src, gzip.open(out/'individual_river_research.sqlite.gz','wb',compresslevel=9) as dst:
        import shutil;shutil.copyfileobj(src,dst)
    files={f.name:sha(f) for f in out.iterdir() if f.is_file()}
    (out/'checksums.json').write_text(json.dumps(files,indent=2)+'\n')
    print('DONE',json.dumps({k:summary[k] for k in ['collapsed_records','recovered_records','collapsed_classes','recovered_classes']},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
