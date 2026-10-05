#!/usr/bin/env python3
from __future__ import annotations
import base64,json,os,urllib.parse,urllib.request
from pathlib import Path
SITE='https://tsurikue.com'; BASE=SITE+'/wp-json/wp/v2'; POST_ID=3981; SLUG='tanto-four-adults-rear-seat'
AUTH='Basic '+base64.b64encode(f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()).decode()
H={'Authorization':AUTH,'Accept':'application/json','User-Agent':'tsurikue-tanto-four-adults-media-audit/1.0'}
def req(path):
 r=urllib.request.Request(BASE+path,headers=H,method='GET')
 with urllib.request.urlopen(r,timeout=60) as x:return json.loads(x.read().decode()),dict(x.headers)
def main():
 q=urllib.parse.urlencode({'context':'edit','_fields':'id,slug,status,title,content,featured_media'})
 p,_=req(f'/posts/{POST_ID}?{q}')
 if int(p.get('id') or 0)!=POST_ID or p.get('slug')!=SLUG or p.get('status')!='draft':raise RuntimeError('TARGET_DRAFT_MISMATCH')
 rows=[]
 for page in range(1,4):
  try:
   q=urllib.parse.urlencode({'context':'edit','media_type':'image','per_page':100,'page':page,'orderby':'date','order':'desc','after':'2026-10-04T00:00:00','_fields':'id,date,slug,source_url,media_details,alt_text,caption,title'})
   r,_=req('/media?'+q); rows+=r
  except Exception:break
 out={'post':{'id':p['id'],'slug':p['slug'],'status':p['status'],'title':p['title'],'featured_media':p['featured_media']},'recent_media_count':len(rows),'recent_media':rows}
 Path('reports/tanto-four-adults-media-audit').mkdir(parents=True,exist_ok=True)
 Path('reports/tanto-four-adults-media-audit/result.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
