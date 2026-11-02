#!/usr/bin/env python3
"""Read-only WP preflight for user's 2026-11-01 Sakanaction planetarium visit."""
import os,base64,json,urllib.parse,urllib.request
from pathlib import Path
ROOT="https://tsurikue.com"
TARGET_FILENAMES=("img_9085","img_9086","img_9089")
def fetch(path,token):
 req=urllib.request.Request(ROOT+path,headers={"Authorization":token,"Accept":"application/json","User-Agent":"tsurikue-sakanaction-draft-preflight/1.0"})
 with urllib.request.urlopen(req,timeout=55) as r:
  return json.loads(r.read().decode()),dict(r.headers)
def main():
 u=os.getenv("TSURIKUE_WP_USER");p=os.getenv("TSURIKUE_WP_APP_PASSWORD")
 if not u or not p:raise RuntimeError("WP secrets missing")
 token="Basic "+base64.b64encode((u+":"+p).encode()).decode()
 hits=[]
 total=0
 for page in range(1,5):
  q=urllib.parse.urlencode({"context":"edit","per_page":100,"page":page,"orderby":"date","order":"desc","_fields":"id,date,slug,title,source_url,media_details,alt_text,caption,post"})
  try:
   media,hdr=fetch("/wp-json/wp/v2/media?"+q,token)
  except urllib.error.HTTPError as e:
   if e.code==400:break
   raise
  total+=len(media)
  for m in media:
   u=(m.get("source_url") or "")
   filename=urllib.parse.unquote(urllib.parse.urlparse(u).path.rsplit("/",1)[-1]).lower()
   if any(s in filename for s in TARGET_FILENAMES) or any(s in (m.get("slug") or "") for s in TARGET_FILENAMES):
    hits.append({"id":m["id"],"date":m.get("date"),"filename":filename,"source_url":u,"title":m.get("title"),"alt":m.get("alt_text"),"post":m.get("post"),"width":(m.get("media_details") or {}).get("width"),"height":(m.get("media_details") or {}).get("height")})
  if len(media)<100:break
 duplicate={}
 for query in ("サカナクション","プラネタリウム","こども文化科学館"):
  q=urllib.parse.urlencode({"context":"edit","search":query,"per_page":50,"status":"any","_fields":"id,slug,title,status,link"})
  rows,_=fetch("/wp-json/wp/v2/posts?"+q,token)
  duplicate[query]=rows
 cats=[]
 for cid in (7,):
  row,_=fetch("/wp-json/wp/v2/categories/"+str(cid)+"?_fields=id,name,slug",token)
  cats.append(row)
 slugs={}
 for slug in ("sakanaction-goodnight-planetarium","sakanaction-planetarium-hiroshima","sakanaction-planetarium-review"):
  q=urllib.parse.urlencode({"context":"edit","slug":slug,"status":"any","per_page":50,"_fields":"id,slug,status"})
  found,_=fetch("/wp-json/wp/v2/posts?"+q,token)
  slugs[slug]=found
 report={"recent_media_scanned":total,"media_matches":hits,"candidate_duplicates":duplicate,"category_seven":cats,"slug_collisions":slugs,"mode":"READ_ONLY"}
 out=Path("reports/sakanaction-planetarium-preflight")
 out.mkdir(parents=True,exist_ok=True)
 (out/"media-and-posts.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("SAKANACTION_READ_ONLY_WP_PREFLIGHT",json.dumps(report,ensure_ascii=False),flush=True)
if __name__=="__main__":main()
