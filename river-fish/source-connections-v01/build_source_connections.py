#!/usr/bin/env python3
"""Build source-scoped fish references for the existing atlas widget.

The original staged ledgers stay unapproved and unchanged. This release selects
already source-checked, non-held references for coarse river-name display only.
No sampling sites, coordinates, individual counts, river codes, or new taxonomy.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
RESEARCH=ROOT.parent/'research-20261021'
sys.path.insert(0,str(RESEARCH))
import build_river_fish_layer_v02 as v02
import build_chugoku_sh22_fish_index_v01 as sh22
SCHEMA='tsurikue-source-fish-connections-v01'
HH_URL='https://www.city.higashihiroshima.lg.jp/material/files/group/19/R5suiseiseibutsu2.pdf'
# Reviewed navigation targets, never fuzzy matching. National-source IDs were
# separately checked against the existing river-identity audit. Other targets
# are prefectural name-directory groups; this does not approve a physical river ID.
TARGETS={
 ('島根県','斐伊川','斐伊川'):'rn_6808b48361d1c1d4ef56db04',
 ('鳥取県','日野川','日野川'):'rn_b3c42a0a2b5b0c62ef1c4521',
 ('鳥取県','日野川','法勝寺川'):'rn_42867e2b3502b7d37077f7d1',
 ('広島県','八幡川','八幡川'):'official21_71f8799928486abbf6523517',
 ('広島県','太田川','東川'):'official21_3386614cc962ba5488fd66d5',
 ('広島県','太田川','関川'):'official21_51a5103f617e4eb09598dbc8',
 ('広島県','沼田川','入野川'):'official21_3baba68a08f2b4aa42320b3c',
 ('広島県','沼田川','宮領川'):'official21_5c9aa1cc487ef9052dadf408',
 ('広島県','沼田川','沼田川'):'official21_9d16e4c84d6b76d4c0d0122d',
 ('広島県','瀬野川','瀬野川'):'official21_cae3c02f8aebecd169b0460c',
 ('広島県','黒瀬川','中川'):'official21_844dc7d0f3e4457f05eda9d7',
 ('広島県','黒瀬川','温井川'):'official21_a8afb834ef5144a9d1a7427a',
 ('広島県','黒瀬川','竹保川'):'official21_fc013da33bc0f865e31771ba',
 ('広島県','黒瀬川','笹野川'):'official21_a56562accddd301ca5560368',
 ('広島県','黒瀬川','黒瀬川'):'official21_f35c812ea8d17a1da83d7457',
}
METHODS={
 'official_survey_summary':'資料の確認種表',
 'official_environment_narrative':'河川環境の説明',
 'prefectural_environment_narrative':'河川環境の説明',
 'official_positive_count_table':'資料の確認種表',
 'municipal_benthic_survey_fish_observation':'底生生物調査での魚類記録',
}
def read_csv(path):
 with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def make_record(r):
 kind=r['evidence_kind']
 if kind not in METHODS:raise ValueError('Unreviewed evidence kind')
 year=r.get('survey_year')
 return {k:v for k,v in {
  'recorded_name':r['recorded_name'],'source_literal_label':r.get('source_literal_label',r['recorded_name']),
  'survey_year':int(year) if year not in ('',None) else None,
  'source_id':r['source_id'],'source_url':r['source_url'],'source_locator':r['source_locator'],
  'evidence_kind':kind,'method_label':METHODS[kind],
  'scope_note':r.get('source_uncertainty') or r.get('claim') or '資料に記載された河川の調査記録。川全域・現在の生息を示すものではありません。',
 }.items()}
def build():
 base=v02.build(v02.load_csv(v02.INPUT),v02.load_csv(v02.HIROSHIMA))
 groups={}
 def add(p,w,n,records,scope):
  key=(p,w,n)
  group=groups.setdefault(key,{'prefecture':p,'watershed':w,'river':n,'records':[],'scope_notes':[]})
  group['records'].extend(make_record(r) for r in records)
  if scope not in group['scope_notes']:group['scope_notes'].append(scope)
 for g in base['river_groups']:
  if g['prefecture']=='島根県':continue # use the completed, source-checked SH22 layer below
  add(g['prefecture'],g['watershed'],g['river'],g['fish_labels'],
      '河川環境の説明は採集調査表と区別し、資料に書かれた範囲で表示しています。')
 sh=sh22.build(sh22.load_csv(sh22.BASE_INPUT),sh22.load_csv(sh22.ADDITIONS_INPUT))
 for g in sh['river_groups']:add(g['prefecture'],g['watershed'],g['river'],g['fish_labels'],g['source_scope_note'])
 hino=read_csv(RESEARCH/'hinogawa_diadr_fish_records_v01.csv')
 if len(hino)!=57:raise ValueError('HINO25 source inventory changed')
 for r in hino:
  if (r['verification_status']!='official_pdf_table_image_checked' or r['integration_status']!='research_only'
      or r['fish_publication_approval']!='not_approved' or int(r['reported_individual_count'])<=0):
   raise ValueError('HINO25 source status changed')
  add('鳥取県','日野川',r['river_as_published'],[dict(r,recorded_name=r['fish_name_as_published'],evidence_kind='official_positive_count_table')],
      '日野川・法勝寺川を別の列で掲載した表の記録です。非公表欄は収録せず、採集地点・調査区間は特定していません。')
 hh=read_csv(ROOT/'higashihiroshima_2023_fish.csv')
 if len(hh)!=72 or len({(r['watershed'],r['river']) for r in hh})!=19:raise ValueError('HH23 reviewed inventory changed')
 for r in hh:
  if (r['source_url']!=HH_URL or r['survey_year']!='2023' or r['prefecture']!='広島県'
      or r['conservation_review']!='not_flagged_in_source_fish_row'):
   raise ValueError('HH23 source metadata changed')
  add(r['prefecture'],r['watershed'],r['river'],[r],
      '2023年度の底生生物調査で、その他の水生生物の魚類欄に記録されたものです。魚類専用の網羅調査ではありません。')
 result=[]
 for key,g in sorted(groups.items()):
  g['id']='srcfish_'+hashlib.sha256('|'.join(key).encode()).hexdigest()[:24]
  g['navigation_target_id']=TARGETS.get(key)
  seen=set();records=[]
  for r in g['records']:
   k=tuple(r[x] for x in ('recorded_name','survey_year','source_id','source_locator'))
   if k not in seen:records.append(r);seen.add(k)
  g['records']=sorted(records,key=lambda r:(r['recorded_name'],r['source_id'],r['survey_year'] or 0))
  g['literal_fish_label_count']=len({r['recorded_name'] for r in records})
  g['individual_physical_river_identity_approved']=False
  result.append(g)
 if len(result)!=31:raise ValueError('Expected 31 source river groups')
 return {'schema':SCHEMA,'release':'2026-10-22-source-reference-display',
  'display_scope':'SOURCE_PUBLISHED_RIVER_FISH_REFERENCES_ONLY',
  'no_precise_locations_or_river_codes':True,'held_records_excluded':True,
  'historical_records_not_current_presence':True,'original_staged_approval_flags_unchanged':True,
  'group_count':len(result),'record_count':sum(len(g['records']) for g in result),'groups':result}
def validate_targets(atlas,supplement):
 if supplement.get('schema')!=SCHEMA or supplement.get('group_count')!=len(supplement.get('groups',[])):
  raise ValueError('Invalid source supplement')
 by_id={e['id']:e for e in atlas['entries']}
 for g in supplement['groups']:
  if not g['records'] or g['individual_physical_river_identity_approved'] is not False:raise ValueError('Invalid source scope')
  target=g['navigation_target_id']
  if target:
   e=by_id.get(target)
   if e is None or (e['name'],e['water'])!=(g['river'],g['watershed']):raise ValueError('Reviewed navigation target changed')
   if e['kind'] in ('official_watershed_name_only_v21','historical_survey_river_name_multiple_code_candidates'):
    raise ValueError('Do not join watershed-only or identity-held entry')
   if e['kind']=='official_river_name_only_v21' and e.get('source_prefecture')!=g['prefecture']:
    raise ValueError('Prefecture name-directory mismatch')
  elif g['id'] in by_id:raise ValueError('Source group ID collision')
 return True
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--atlas',type=Path);args=p.parse_args()
 data=build()
 if args.atlas:validate_targets(json.loads(args.atlas.read_text()),data)
 args.out.parent.mkdir(parents=True,exist_ok=True)
 args.out.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n')
 print('SOURCE_FISH_CONNECTIONS_READY',json.dumps({'groups':data['group_count'],'records':data['record_count'],'reviewed_existing_targets':len(TARGETS),'new_source_groups':len(data['groups'])-len(TARGETS)},ensure_ascii=False))
