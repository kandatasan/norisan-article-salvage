#!/usr/bin/env python3
"""Public watershed-level CSV search with conservative invasive-species flags.

Works standalone with curated_fish_records_v03.csv, akaza_local_names_v03.csv,
alien_origin_v04.csv, and legal_designations_v04.csv in the same directory.
"""
import argparse
import csv
import json
import unicodedata
from pathlib import Path

ROOT=Path(__file__).resolve().parent
FILTERS=('all','alien','foreign','domestic','native','regulated','unknown')


def rows(filename,root=ROOT):
    with (Path(root)/filename).open('r',encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))


def norm(text):
    return unicodedata.normalize('NFKC',str(text or '')).casefold().strip()


def search(name='',prefecture='',watershed='',alien='all',root=ROOT):
    if alien not in FILTERS:
        raise ValueError('不正なフィルター: '+alien)
    origin={}
    for r in rows('alien_origin_v04.csv',root):
        if r['origin_category'] not in ('foreign_alien','domestic_alien','native'):
            raise ValueError('不正な外来種区分')
        k=(r['prefecture'],r['watershed'],r['recorded_name'])
        if k in origin and origin[k]['origin_category']!=r['origin_category']:
            raise ValueError('矛盾する外来種判定')
        origin[k]=r
    legal={r['recorded_name']:r for r in rows('legal_designations_v04.csv',root)}
    aliases={}
    for r in rows('akaza_local_names_v03.csv',root):
        aliases.setdefault(r['standard_name'],[]).append({'name':r['alias'],'locality_label':r['region']})
    results=[]
    for r in rows('curated_fish_records_v03.csv',root):
        fish=r['recorded_name'];pref=r['prefecture'];water=r['watershed']
        if name and not any(norm(name) in norm(candidate) for candidate in [fish]+[a['name'] for a in aliases.get(fish,[]) ]):
            continue
        if prefecture and norm(prefecture) not in norm(pref):
            continue
        if watershed and norm(watershed) not in norm(water):
            continue
        origin_info=origin.get((pref,water,fish))
        origin_code=origin_info['origin_category'] if origin_info else 'unknown'
        law_info=legal.get(fish)
        legal_code=law_info['legal_status'] if law_info else 'unreviewed'
        include={'all':True,'alien':origin_code in ('foreign_alien','domestic_alien'),
            'foreign':origin_code=='foreign_alien','domestic':origin_code=='domestic_alien',
            'native':origin_code=='native','regulated':legal_code=='specified_alien',
            'unknown':origin_code=='unknown'}[alien]
        if not include:
            continue
        results.append({
            'fish':fish,'prefecture':pref,'watershed':water,
            'local_names':aliases.get(fish,[]),
            'origin':origin_code,'origin_source':origin_info['source_url'] if origin_info else None,
            'legal_status':legal_code,'legal_source':law_info['source_url'] if law_info else None,
            'record_kind':r['evidence_type'],'survey_year':r['survey_year'] or None,
            'source':{'title':r['source_title'],'url':r['source_url']},
        })
    return {'total_records':len(results),'records':results,
        'notice':'未判定は在来種ではありません。資料に記載がない魚も不在とは限りません。掲載は生息の現在性や釣り場を保証しません。'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description='つりくえ！川の魚CSV検索／外来種フィルター試作')
    p.add_argument('--name',default='')
    p.add_argument('--prefecture',default='')
    p.add_argument('--watershed',default='')
    p.add_argument('--alien',choices=FILTERS,default='all')
    args=p.parse_args()
    print(json.dumps(search(args.name,args.prefecture,args.watershed,args.alien),ensure_ascii=False,indent=2))
