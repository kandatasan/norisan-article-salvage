// Source references extend navigation only; the pinned base files stay intact.
const SOURCE_FISH_V01 = __SOURCE_FISH_DATA_V01__;
function mergeSourceFishV01(base){
 if(SOURCE_FISH_V01.schema!=="tsurikue-source-fish-connections-v01"||
    !SOURCE_FISH_V01.no_precise_locations_or_river_codes||!SOURCE_FISH_V01.held_records_excluded)
  throw Error("追加資料の形式が一致しません");
 const out={...base,entries:base.entries.map(e=>({...e})),links:base.links.map(l=>({...l}))};
 const byId=new Map(out.entries.map(e=>[e.id,e]));
 for(const g of SOURCE_FISH_V01.groups){
  let e=g.navigation_target_id?byId.get(g.navigation_target_id):null;
  if(g.navigation_target_id&&(!e||e.name!==g.river||e.water!==g.watershed||
    e.kind==="official_watershed_name_only_v21"||e.kind==="historical_survey_river_name_multiple_code_candidates"||
    (e.kind==="official_river_name_only_v21"&&e.source_prefecture!==g.prefecture)))throw Error("追加資料の河川名対応が変わっています");
  if(!e){
   if(byId.has(g.id))throw Error("追加資料のIDが重複しています");
   e={id:g.id,name:g.river,water:g.watershed,region:null,kind:"prefectural_source_fish_reference_v01",old:{},edna:null,is_a_verified_individual_physical_river:false};
   out.entries.push(e);byId.set(e.id,e);
  }
  if(e.sourceFishV01)throw Error("追加資料を二重に読み込んでいます");
  e.sourceFishV01=g;
  if(!out.links.some(l=>l.river_id===e.id&&l.prefecture===g.prefecture&&l.water===g.watershed))
   out.links.push({prefecture:g.prefecture,water:g.watershed,river_id:e.id});
 }
 return out;
}
function addSourceFishV01(map,e){
 if(!e.sourceFishV01)return;
 for(const r of e.sourceFishV01.records){
  addFish(map,r.recorded_name,{method:r.method_label,years:[r.survey_year],sources:[r.source_url]});
  const f=map.get(r.recorded_name);if(!f)continue;
  if(!f.sourceNotesV01)f.sourceNotesV01=new Set();
  f.sourceNotesV01.add(r.method_label+"｜"+(r.survey_year===null?"調査年は資料から特定できません":r.survey_year+"年")+"｜"+r.source_locator);
 }
}
function mergeSourceMetaV01(meta){
 const rows=new Map(meta.entries.map(x=>[x.survey_river_group_id,{...x}]));
 for(const e of atlas.entries){
  if(!e.sourceFishV01)continue;
  const row=rows.get(e.id)||{survey_river_group_id:e.id,historical_fish_literal_name_count:0,environmental_DNA_fish_literal_name_rows:0};
  row.source_reference_fish_label_count=e.sourceFishV01.literal_fish_label_count;
  rows.set(e.id,row);
 }
 return {...meta,entries:[...rows.values()]};
}
function mergeSourceReverseV01(index){
 const lookups=new Map(index.lookups.map(x=>[x.recorded_fish_name,{...x,river_survey_groups:x.river_survey_groups.map(g=>({...g,method_flags:[...g.method_flags]}))}]));
 for(const e of atlas.entries){
  const g=e.sourceFishV01;if(!g)continue;
  for(const name of new Set(g.records.map(r=>r.recorded_name))){
   if(master?.taxa?.[name]?.classification_status==="not_fish")continue;
   let row=lookups.get(name);
   if(!row){row={recorded_fish_name:name,river_survey_groups:[],reference_count:0};lookups.set(name,row)}
   let ref=row.river_survey_groups.find(x=>x.river_id===e.id);
   const nav={prefecture:g.prefecture,navigation_water:g.watershed};
   if(!ref){ref={river_id:e.id,river_name:e.name,watershed_name:e.water,source_river_kind:e.kind,original_navigation_paths:[nav],method_flags:[],physical_river_identification_approved:false};row.river_survey_groups.push(ref)}
   if(!ref.method_flags.includes("PUBLISHED_SOURCE_FISH_REFERENCE"))ref.method_flags.push("PUBLISHED_SOURCE_FISH_REFERENCE");
   if(!ref.original_navigation_paths.some(n=>n.prefecture===nav.prefecture&&n.navigation_water===nav.navigation_water))ref.original_navigation_paths.push(nav);
   row.reference_count=row.river_survey_groups.length;
  }
 }
 return {...index,lookups:[...lookups.values()].sort((a,b)=>a.recorded_fish_name.localeCompare(b.recorded_fish_name,"ja"))};
}
