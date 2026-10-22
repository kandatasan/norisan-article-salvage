import copy,importlib.util,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from build_source_connections import build,read_csv,validate_targets
from patch_widget import patch_script,sha,BASE_SCRIPT_SHA256
from audit_connections import coverage
spec=importlib.util.spec_from_file_location('wp_source_patch',ROOT.parents[1]/'scripts/apply_river_source_connections_20261022.py')
wp=importlib.util.module_from_spec(spec);spec.loader.exec_module(wp)
def fixtures():
 layer=build();entries=[];links=[];labels=[]
 for g in layer['groups']:
  ident=g['navigation_target_id']
  if not ident:continue
  historic=ident.startswith('rn_')
  entries.append(dict(id=ident,name=g['river'],water=g['watershed'],source_prefecture=g['prefecture'],kind='historical_national_river_survey' if historic else 'official_river_name_only_v21'))
  links.append(dict(prefecture=g['prefecture'],water=g['watershed'],river_id=ident))
  if historic:labels.append(dict(survey_river_group_id=ident,historical_fish_literal_name_count=1,environmental_DNA_fish_literal_name_rows=0,fish_name_in_source_records=True))
 entries.append(dict(id='identity-held',name='同名川',water='別水系',kind='historical_survey_river_name_multiple_code_candidates'))
 labels.append(dict(survey_river_group_id='identity-held',historical_fish_literal_name_count=1,environmental_DNA_fish_literal_name_rows=0,fish_name_in_source_records=True))
 entries.append(dict(id='watershed',name='水系のみ',water='水系のみ',kind='official_watershed_name_only_v21'))
 atlas=dict(entries=entries,links=links,fish_only_mvp=True,location_sensitive_data_excluded=True,fish_editorial_work_is_still_unverified=True,strictly_source_named_river_groups_not_geographically_unique_rivers=True)
 meta=dict(schema='tsurikue-original-survey-fish-label-counts-v25',entries=labels,original_source_groups=len(labels),historical_fish_labels_do_not_confirm_current_presence=True,DNA_positive_labels_do_not_mean_capture_or_visual_confirmation=True,is_recorded_name_label_count_not_distinct_taxonomic_species=True)
 return atlas,meta,layer
class ConnectionsTest(unittest.TestCase):
 def test_regeneration_and_source_scopes(self):
  layer=build();stored=json.loads((ROOT/'fish_source_connections_v01.json').read_text());self.assertEqual(layer,stored)
  self.assertEqual((layer['group_count'],layer['record_count']),(31,261))
  hh=[r for g in layer['groups'] for r in g['records'] if r['source_id']=='HH23']
  self.assertEqual(len(hh),72);self.assertEqual({r['survey_year'] for r in hh},{2023})
  self.assertFalse({'ミナミメダカ','ドジョウ','アブラボテ','アカザ'} & {r['recorded_name'] for r in hh})
  self.assertTrue(any(r['source_literal_label']=='ｺｲ(型不明)' for r in hh))
  self.assertEqual(sum(r['source_id']=='SH22' for g in layer['groups'] for r in g['records']),94)
  self.assertTrue(all(r['survey_year'] is None for g in layer['groups'] for r in g['records'] if r['source_id']=='SH22'))
  self.assertEqual(sum(r['source_id']=='HINO_ADVISER_2025_MAIN_TABLE' for g in layer['groups'] for r in g['records']),57)
  for g in layer['groups']:
   self.assertFalse(g['individual_physical_river_identity_approved'])
   for key in ('station','coordinate','latitude','longitude','river_code','reported_individual_count'):
    self.assertNotIn(key,g)
    for row in g['records']:self.assertNotIn(key,row)
 def test_no_watershed_records_or_held_river_join(self):
  atlas,_,layer=fixtures();validate_targets(atlas,layer)
  target=next(e for e in atlas['entries'] if e['id'].startswith('official21'))
  for kind in ('official_watershed_name_only_v21','historical_survey_river_name_multiple_code_candidates'):
   bad=copy.deepcopy(atlas);next(e for e in bad['entries'] if e['id']==target['id'])['kind']=kind
   with self.assertRaises(ValueError):validate_targets(bad,layer)
 def test_changed_name_or_prefecture_stops_join(self):
  atlas,_,layer=fixtures();target=next(e for e in atlas['entries'] if e['id'].startswith('official21'))
  for key in ('source_prefecture','name','water'):
   bad=copy.deepcopy(atlas);next(e for e in bad['entries'] if e['id']==target['id'])[key]='別の値'
   with self.assertRaises(ValueError):validate_targets(bad,layer)
 def test_coverage_retains_holds_and_updates_denominator(self):
  atlas,meta,layer=fixtures();report=coverage(atlas,meta,layer)
  self.assertEqual(report['base_json_only']['fish_evidence_groups_excluding_identity_holds'],3)
  self.assertEqual(report['additional_qualifying_groups'],28)
  self.assertEqual(report['new_name_groups_added_to_denominator'],16)
  self.assertEqual(report['fish_evidence_groups'],31)
  self.assertEqual(report['river_name_display_groups'],32)
  self.assertEqual(report['base_json_only']['watershed_only_entries_excluded_from_denominator'],1)
  bad=copy.deepcopy(layer);bad['groups'][0]['records'][0]['recorded_name']='未審査名'
  with self.assertRaises(ValueError):coverage(atlas,meta,bad)
 def test_widget_patch_is_surgical_and_idempotent(self):
  body=(ROOT.parents[1]/'content/drafts/river-atlas-seo-20261021.html').read_text()
  before=wp.get_script(body);self.assertEqual(sha(before.group(1)),BASE_SCRIPT_SHA256)
  edited,action=wp.edit_body(body);after=wp.get_script(edited)
  self.assertEqual(action,'UPDATED_WIDGET_SCRIPT_ONLY')
  self.assertEqual(body[:before.start(1)],edited[:after.start(1)])
  self.assertEqual(body[before.end(1):],edited[after.end(1):])
  self.assertEqual(wp.edit_body(edited),(edited,'ALREADY_CURRENT'))
  with self.assertRaises(ValueError):wp.edit_body(body.replace('const FETCH_LIMIT=40;','const FETCH_LIMIT=41;'))
if __name__=='__main__':unittest.main()
