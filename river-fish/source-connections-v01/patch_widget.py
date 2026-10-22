#!/usr/bin/env python3
"""Patch one exact, reviewed executable widget script, preserving all prose."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BASE_SCRIPT_SHA256='17dbfd134a7e643e5383c1db15dd597b4e3bb21596d64ecd66c6a6e61eaa0f8d'
MARKER='const SOURCE_FISH_V01 = '
def sha(text):return hashlib.sha256(text.encode()).hexdigest()
def payload():return json.loads((ROOT/'fish_source_connections_v01.json').read_text())
def extension():
 data=json.dumps(payload(),ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
 return (ROOT/'widget_connections.js').read_text().replace('__SOURCE_FISH_DATA_V01__',data)
def patch_script(script):
 if sha(script)!=BASE_SCRIPT_SHA256:raise ValueError('Live widget changed; inspect before updating')
 replacements=[
 ('const FETCH_LIMIT=40;',extension()+'\nconst FETCH_LIMIT=40;'),
 ('atlas=result[0];master=result[1];','atlas=mergeSourceFishV01(result[0]);master=result[1];'),
 ('e.source_only_name_evidence_v21?(e.source_label_type','e.sourceFishV01?"【資料に魚名掲載】":e.source_only_name_evidence_v21?(e.source_label_type'),
 ('if(e.source_only_name_evidence_v21){sourceOnlyDetail(e);return;}','if(e.source_only_name_evidence_v21&&!e.sourceFishV01){sourceOnlyDetail(e);return;}'),
 ('fishGroups=Array.from(map.values()).sort','addSourceFishV01(map,e);\n  fishGroups=Array.from(map.values()).sort'),
 ('if(current.source_only_name_evidence_v21){sourceOnlyDetail(current);return;}','if(current.source_only_name_evidence_v21&&!current.sourceFishV01){sourceOnlyDetail(current);return;}'),
 ('for(const m of ["過去の調査記録","DNA検出"])','for(const m of ["過去の調査記録","DNA検出","資料の確認種表","河川環境の説明","底生生物調査での魚類記録"])'),
 ('const years=Array.from(row.dates).sort','if(row.sourceNotesV01){const notes=node("details");notes.appendChild(node("summary","資料の記録区分・調査年"));for(const text of row.sourceNotesV01)notes.appendChild(node("p",text,"note"));card.appendChild(notes);}\n const years=Array.from(row.dates).sort'),
 ('selected.slice(0,displayed).forEach','if(current.sourceFishV01)for(const text of current.sourceFishV01.scope_notes){const note=node("p",text,"note");note.style.gridColumn="1 / -1";$("fishlist").appendChild(note);}\n selected.slice(0,displayed).forEach'),
 ('if(!e||e.source_only_name_evidence_v21)return;','if(!e||(e.source_only_name_evidence_v21&&!e.sourceFishV01))return;'),
 ('if(!reverseIndexV24)reverseIndexV24=await load("fish_to_river_reverse_v24.json");','if(!reverseIndexV24)reverseIndexV24=mergeSourceReverseV01(await load("fish_to_river_reverse_v24.json"));'),
 ('?"DNA検出（捕獲記録ではない）":"過去の魚類調査"','?"DNA検出（捕獲記録ではない）":x==="PUBLISHED_SOURCE_FISH_REFERENCE"?"県・市の公開資料に記録":"過去の魚類調査"'),
 ('const original=!e.source_only_name_evidence_v21;','const original=!e.source_only_name_evidence_v21;'),
 ('const status=original?','const status=e.sourceFishV01?"県・市の公開資料に魚名掲載":original?'),
 ('if(!riverMetaV25)riverMetaV25=await load("river_fish_label_counts_v25.json");','if(!atlas)return;\n  if(!riverMetaV25)riverMetaV25=mergeSourceMetaV01(await load("river_fish_label_counts_v25.json"));'),
 ('||x.fish_meta.environmental_DNA_fish_literal_name_rows>0)','||x.fish_meta.environmental_DNA_fish_literal_name_rows>0||x.fish_meta.source_reference_fish_label_count>0)'),
 ]
 for old,new in replacements:
  if script.count(old)!=1:raise ValueError('Widget fragment missing or ambiguous: '+old[:80])
  script=script.replace(old,new,1)
 return script

def replace_widget(body):
 pat=re.compile(r'<script>([\s\S]*?)</script>')
 matches=[m for m in pat.finditer(body) if 'const DATA_ROOT' in m.group(1)]
 if len(matches)!=1:raise ValueError('Expected one atlas executable script')
 m=matches[0];before=m.group(1);after=patch_script(before)
 return body[:m.start(1)]+after+body[m.end(1):]
