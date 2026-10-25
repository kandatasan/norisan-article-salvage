#!/usr/bin/env python3
"""Replace only the pinned atlas executable script in published WP post 4240."""
from __future__ import annotations
import base64,hashlib,json,os,re,sys,urllib.parse,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'river-fish/source-connections-v01'))
from patch_widget import BASE_SCRIPT_SHA256,extension,patch_script,sha
from build_source_connections import build,validate_targets
SITE='https://tsurikue.com';POST_ID=4240
TITLE='日本の河川図鑑｜全国の河川名・水系・生き物を都道府県から探す'
APPROVED_PREVIOUS_WIDGET_SHA256='573d61b513881306b9f931e5a99cdc94320f2f141b5c72cb34939edd2d17eafc'
PROTECTED=('id','slug','status','title','excerpt','featured_media','categories','author','template')
def request(path,auth,body=None):
 headers={'Authorization':auth,'Accept':'application/json','User-Agent':'tsurikue-source-connections/1.0'}
 if body is not None:headers['Content-Type']='application/json; charset=utf-8'
 req=urllib.request.Request(SITE+path,headers=headers,method='GET' if body is None else 'POST',data=None if body is None else json.dumps(body,ensure_ascii=False).encode())
 with urllib.request.urlopen(req,timeout=90) as resp:return json.load(resp)
def fetch(auth):
 return request('/wp-json/wp/v2/posts/4240?'+urllib.parse.urlencode({'context':'edit','_fields':','.join(PROTECTED+('modified_gmt','content'))}),auth)
def get_script(body):
 matches=[m for m in re.finditer(r'<script>([\s\S]*?)</script>',body) if 'const DATA_ROOT' in m.group(1)]
 if len(matches)!=1:raise ValueError('Atlas script missing or ambiguous')
 return matches[0]
def edit_body(body):
 m=get_script(body);script=m.group(1)
 # Idempotency requires the exact generated script, not merely a marker.
 candidate=Path('content/drafts/river-atlas-seo-20261021.html').read_text()
 original=get_script(candidate).group(1)
 expected=patch_script(original)
 if script==expected:return body,'ALREADY_CURRENT'
 if sha(script) not in {BASE_SCRIPT_SHA256,APPROVED_PREVIOUS_WIDGET_SHA256}:raise ValueError('Pinned widget script has changed; no write')
 after=body[:m.start(1)]+expected+body[m.end(1):]
 if body[:m.start(1)]!=after[:m.start(1)] or body[m.end(1):]!=after[m.start(1)+len(expected):]:raise ValueError('Non-script body changed')
 return after,'UPDATED_WIDGET_SCRIPT_ONLY'
def main(mode):
 user=os.environ.get('TSURIKUE_WP_USER');password=os.environ.get('TSURIKUE_WP_APP_PASSWORD')
 if not user or not password:raise ValueError('WordPress connection is unavailable')
 auth='Basic '+base64.b64encode((user+':'+password).encode()).decode()
 current=fetch(auth)
 if (current['id'],current['slug'],current['status'],current['featured_media'],current['title']['raw'])!=(POST_ID,'japan-river-atlas','publish',4238,TITLE):raise ValueError('Article identity or protected metadata changed')
 from audit_live_atlas_fish_coverage_v01 import load_live
 atlas,_=load_live('atlas.json');validate_targets(atlas,build())
 before=current['content']['raw'];after,action=edit_body(before)
 print('SOURCE_WIDGET_PREFLIGHT',json.dumps({'post_id':POST_ID,'status':current['status'],'action':action,'before_sha256':sha(before),'after_sha256':sha(after),'original_widget_sha256':sha(get_script(before).group(1)),'source_groups':build()['group_count'],'source_records':build()['record_count']},ensure_ascii=False),flush=True)
 if mode=='check':return
 latest=fetch(auth)
 if latest!=current:raise ValueError('Concurrent WordPress edit detected; no write')
 if action!='ALREADY_CURRENT':request('/wp-json/wp/v2/posts/4240',auth,{'content':after})
 saved=fetch(auth)
 if any(saved[k]!=current[k] for k in PROTECTED):raise ValueError('Protected WordPress metadata changed')
 if saved['content']['raw']!=after:raise ValueError('Saved body differs from the exact patch')
 if get_script(saved['content']['rendered']).group(1)!=get_script(after).group(1):raise ValueError('Rendered widget differs from saved source')
 print('SOURCE_WIDGET_WORDPRESS_VERIFIED',json.dumps({'action':action,'post_id':POST_ID,'slug':saved['slug'],'status':saved['status'],'featured_media':saved['featured_media'],'title':saved['title']['raw'],'protected_metadata_unchanged':True,'prose_and_other_html_unchanged':True,'content_sha256':sha(after),'widget_sha256':sha(get_script(after).group(1))},ensure_ascii=False),flush=True)
if __name__=='__main__':
 mode=sys.argv[1] if len(sys.argv)>1 else 'check'
 if mode not in ('check','apply'):raise SystemExit('check or apply')
 main(mode)
