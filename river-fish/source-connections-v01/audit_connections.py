#!/usr/bin/env python3
"""Measure base JSON and the published article's embedded source layer together."""
import argparse,hashlib,json,math,re,sys,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'research-20261021'))
from audit_live_atlas_fish_coverage_v01 import load_live,summarize
from build_source_connections import build,validate_targets
ARTICLE='https://tsurikue.com/japan-river-atlas/'
def read_public_layer():
 req=urllib.request.Request(ARTICLE+'?source_fish_audit='+str(time.time_ns()),headers={'User-Agent':'tsurikue-source-fish-audit/1.0','Cache-Control':'no-cache'})
 with urllib.request.urlopen(req,timeout=75) as r:raw=r.read(2_000_001)
 if len(raw)>2_000_000:raise ValueError('Unexpected article size')
 text=raw.decode('utf-8');found=re.findall(r'const SOURCE_FISH_V01 = (\{[^\n]+\});',text)
 if len(found)!=1:raise ValueError('Published source layer missing or ambiguous')
 return json.loads(found[0])
def coverage(atlas,labels,layer):
 validate_targets(atlas,layer)
 if layer!=build():raise ValueError('Published layer differs from the reviewed release')
 base=summarize(atlas,labels)
 positive={r['survey_river_group_id'] for r in labels['entries'] if r['fish_name_in_source_records']}
 positive-={e['id'] for e in atlas['entries'] if e['kind']=='historical_survey_river_name_multiple_code_candidates'}
 new_ids={g['id'] for g in layer['groups'] if not g['navigation_target_id']}
 extension_ids={g['navigation_target_id'] or g['id'] for g in layer['groups']}
 if len(extension_ids)!=layer['group_count']:raise ValueError('Duplicate navigation group')
 numerator=len(positive|extension_ids)
 denominator=base['river_name_display_groups']+len(new_ids)
 target=math.ceil(denominator/2)
 return {'schema':'tsurikue-combined-fish-coverage-v01','status':'SOURCE_NAME_GROUP_COVERAGE_NOT_PHYSICAL_RIVER_COUNT',
  'base_json_only':base,'embedded_source_groups':len(extension_ids),'embedded_source_records':layer['record_count'],
  'new_name_groups_added_to_denominator':len(new_ids),'existing_groups_with_additional_sources':len(extension_ids)-len(new_ids),
  'additional_qualifying_groups':len(extension_ids-positive),'fish_evidence_groups':numerator,
  'river_name_display_groups':denominator,'coverage_percent':round(100*numerator/denominator,1),
  'target_percent':50,'target_groups':target,'additional_qualifying_groups_needed':max(0,target-numerator),
  'denominator_is_not_frozen':True,'watershed_only_and_identity_hold_exclusions_unchanged':True,
  'source_records_not_current_presence':True,'precise_locations_and_held_records_not_added':True}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--projected',action='store_true');a=p.parse_args()
 atlas,ash=load_live('atlas.json');labels,lsh=load_live('river_fish_label_counts_v25.json')
 layer=build() if a.projected else read_public_layer();report=coverage(atlas,labels,layer)
 report.update({'verified_in_published_article':not a.projected,'article_url':ARTICLE,'base_atlas_sha256':ash,'base_label_counts_sha256':lsh})
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print('COMBINED_FISH_COVERAGE',json.dumps({k:v for k,v in report.items() if k!='base_json_only'},ensure_ascii=False))
