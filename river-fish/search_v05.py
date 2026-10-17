#!/usr/bin/env python3
"""v0.5 fish-search prototype: separate official survey from curated sources.

The official workbook has no prefecture column. A prefecture filter therefore
returns curated records ONLY until a separately verified watershed/geography
crosswalk is available. Never infer precise occurrence sites.
"""
import argparse
import csv
import json
import re
from pathlib import Path
from search_v04 import search as curated_search, rows, norm, FILTERS

ROOT=Path(__file__).resolve().parent
OFFICIAL="official_chugoku_watershed_year_fish_v05.csv"

def fish_matches(query,label,aliases):
    return not query or any(norm(query) in norm(s) for s in [label]+aliases.get(label,[]))

def search(name='',prefecture='',watershed='',year='',alien='all',limit=50,offset=0,root=ROOT):
    if alien not in FILTERS:raise ValueError("Invalid alien filter")
    if year and not re.fullmatch(r'(?:19|20)\d{2}',str(year)):
        raise ValueError("Year must be four digits")
    if not (0<=offset and 1<=limit<=200):raise ValueError("Invalid pagination")
    aliases={}
    for x in rows('akaza_local_names_v03.csv',root):
        aliases.setdefault(x['standard_name'],[]).append(x['alias'])
    legal={x['recorded_name']:x for x in rows('legal_designations_v04.csv',root)}
    official=[]
    # A prefecture is NOT present in the official dataset. Do not guess it.
    if not prefecture:
        with (Path(root)/OFFICIAL).open(encoding='utf-8-sig',newline='') as f:
            r=csv.DictReader(f)
            expected=['watershed','survey_year','recorded_name','source_url','source_sha256']
            if r.fieldnames!=expected:raise ValueError('Unexpected official-staging schema')
            for x in r:
                species=x['recorded_name']
                if not fish_matches(name,species,aliases):continue
                if watershed and norm(watershed) not in norm(x['watershed']):continue
                if year and year!=x['survey_year']:continue
                law=legal.get(species)
                is_regulated=bool(law and law['legal_status']=='specified_alien')
                # Origin is unreviewed even when the species is regulated nationally.
                if alien not in ('all','unknown') and not (alien=='regulated' and is_regulated):
                    continue
                if alien=='unknown' or alien=='all' or (alien=='regulated' and is_regulated):
                    official.append({
                        'record_type':'official_census_watershed_year',
                        'fish':species,'watershed':x['watershed'],
                        'survey_year':x['survey_year'],
                        'prefecture':None,'geographic_scope':'中国地方・水系単位',
                        'origin':'unknown','legal_status':'specified_alien' if is_regulated else 'unreviewed',
                        'source_url':x['source_url'],'source_sha256':x['source_sha256'],
                    })
    curated=[]
    # Older narrative references have no survey year: exclude if year was requested.
    if not year:
        r=curated_search(name=name,prefecture=prefecture,watershed=watershed,alien=alien,root=root)
        curated=[dict(x,record_type='curated_report_not_direct_census') for x in r['records']]
    results=official+curated
    return {
        'total':len(results),'official_count':len(official),'curated_count':len(curated),
        'records':results[offset:offset+limit],'limit':limit,'offset':offset,
        'notes':[
            '国交省の公式データは水系・調査年度で表示します。詳細な採集地点は公開しません。',
            '都道府県で絞ると、県との対応が確認された手作業の出典記録だけが対象です。公式調査データは県別未分類です。',
            '外来種区分の未判定は在来種ではありません。データにない魚は非生息を意味しません。',
            '河川紹介記事・漁業対象魚の記載と現地調査の確認種を混同しません。',
        ],
    }

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--name',default='')
    p.add_argument('--prefecture',default='')
    p.add_argument('--watershed',default='')
    p.add_argument('--year',default='')
    p.add_argument('--alien',choices=FILTERS,default='all')
    p.add_argument('--limit',type=int,default=20)
    p.add_argument('--offset',type=int,default=0)
    args=p.parse_args()
    print(json.dumps(search(**vars(args)),ensure_ascii=False,indent=2))
