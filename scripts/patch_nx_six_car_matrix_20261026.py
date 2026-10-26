#!/usr/bin/env python3
"""Correct eight officially verified cells of NX rival matrix, preserving all WP metadata."""
import os, re, json, base64, hashlib, html, urllib.request, urllib.parse
from pathlib import Path

BASE="https://tsurikue.com"
POST_ID=4268
SLUG="lexus-nx-rival-suv"
TABLES={"safety":"nx-rivals-safety","comfort":"nx-rivals-comfort"}
COLORS={"○":"#19634b","△":"#7c5b19","×":"#944252","—":"#6b7280"}
CHANGES=[
 ("safety","運転者の異常を検知して<br>減速・停車を支援",4,"—","○"),
 ("comfort","前席シートを<br>温める",5,"—","○"),
 ("comfort","前席シートから<br>熱気を逃がす",5,"—","×"),
 ("comfort","ステアリングを<br>温める",5,"—","○"),
 ("comfort","運転席位置を<br>記憶する",3,"—","○"),
 ("comfort","運転席位置を<br>記憶する",5,"—","×"),
 ("comfort","フロントガラスに<br>速度などを表示",4,"—","×"),
 ("comfort","フロントガラスに<br>速度などを表示",5,"—","△")
]
CELL=re.compile(r'<td style="([^"]+)">([^<]*)</td>')

def api(path,auth,payload=None):
    data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode()
    req=urllib.request.Request(BASE+path,data=data,method="GET" if data is None else "POST",
       headers={"Authorization":auth,"User-Agent":"tsurikue-nx-rivals-six-car-audit/1.0",
       "Content-Type":"application/json; charset=utf-8","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=80) as res:
        return json.loads(res.read().decode()),dict(res.headers)

def fetch(auth):
    q=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,content,featured_media,categories,author,excerpt"})
    return api("/wp-json/wp/v2/posts/"+str(POST_ID)+"?"+q,auth)[0]

def raw(row): return row["content"]["raw"]

def snapshot(r):
    return (r["id"],r["slug"],r["status"],html.unescape(r["title"].get("raw") or r["title"].get("rendered","")),
      r["featured_media"],tuple(sorted(r["categories"])),r["author"],r.get("excerpt",{}).get("raw",""))

def public_counts(auth):
    results=[]
    for endpoint in ("posts","pages"):
        q=urllib.parse.urlencode({"context":"edit","status":"publish","per_page":1,"_fields":"id"})
        _,head=api("/wp-json/wp/v2/"+endpoint+"?"+q,auth)
        results.append(int(head.get("X-WP-Total",0)))
    return results

def patch_one(source,kind,label,col,old,new):
    table=source.find('id="'+TABLES[kind]+'"')
    end=source.find('<!-- /wp:html -->',table)
    if table<0 or end<0: raise RuntimeError("Missing "+kind+" table")
    idx=source.find(label,table)
    if idx<table or idx>=end or source.find(label,idx+len(label))<end and source.find(label,idx+len(label))!=-1:
        raise RuntimeError("Target label absent/ambiguous "+label)
    start=source.rfind("<tr>",table,idx)
    stop=source.find("</tr>",idx)+len("</tr>")
    if start<table or stop>end: raise RuntimeError("Ambiguous target row "+label)
    row=source[start:stop]
    cells=list(CELL.finditer(row))
    if len(cells)!=6 or not 0<=col<6: raise RuntimeError("Unexpected columns")
    cell=cells[col]
    style,value=cell.group(1),cell.group(2)
    if value==new and ("color:"+COLORS[new]+"!important") in style:
        return source,"ALREADY_CORRECT"
    if value!=old or ("color:"+COLORS[old]+"!important") not in style:
        raise RuntimeError(f"{label} col {col} was edited or unexpected: {value}")
    new_style=style.replace("color:"+COLORS[old]+"!important","color:"+COLORS[new]+"!important",1)
    replacement='<td style="'+new_style+'">'+new+'</td>'
    updated_row=row[:cell.start()]+replacement+row[cell.end():]
    return source[:start]+updated_row+source[stop:],"UPDATE"

def main():
    user=os.environ["TSURIKUE_WP_USER"];password=os.environ["TSURIKUE_WP_APP_PASSWORD"]
    auth="Basic "+base64.b64encode((user+":"+password).encode()).decode()
    before=fetch(auth)
    if before["id"]!=POST_ID or before["slug"]!=SLUG or before["status"] not in ("publish","draft"):
        raise RuntimeError("Wrong WordPress target")
    content=raw(before)
    if "<!-- tsurikue-editorial:v1 slug=lexus-nx-rival-suv -->" not in content:
        raise RuntimeError("Editorial content marker missing")
    edited=content
    results=[]
    for spec in CHANGES:
        edited,action=patch_one(edited,*spec)
        results.append({"row":spec[1],"col":spec[2],"old":spec[3],"new":spec[4],"action":action})
    if len(edited)!=len(content):
        raise RuntimeError("Unexpected HTML length change")
    if edited.count('class="tsq-nx-rival-table"')!=3 or edited.count('[blog_parts id="2843"]')!=1:
        raise RuntimeError("Table or affiliate changed")
    for block in ("html","paragraph","heading","list","shortcode","image"):
        op=len(re.findall("<!-- wp:"+block+r"(?= | -->)",edited))
        cl=edited.count("<!-- /wp:"+block+" -->")
        if op!=cl: raise RuntimeError("Broken Gutenberg blocks "+block)
    published=public_counts(auth)
    latest=fetch(auth)
    if snapshot(latest)!=snapshot(before) or raw(latest)!=content:
        raise RuntimeError("Concurrent WordPress edit")
    action="UPDATE" if edited!=content else "ALREADY_CORRECT"
    if action=="UPDATE":
        saved,_=api("/wp-json/wp/v2/posts/"+str(POST_ID),auth,{"content":edited})
        if saved.get("id")!=POST_ID or saved.get("status")!=before["status"]:
            raise RuntimeError("Update changed status or id")
    after=fetch(auth)
    if snapshot(after)!=snapshot(before) or raw(after)!=edited or public_counts(auth)!=published:
        raise RuntimeError("Saved HTML, metadata, or published counts differ")
    report={"post_id":POST_ID,"slug":SLUG,"status":after["status"],"action":action,
      "cells":results,"write_count":int(action=="UPDATE"),"publish_count":0,
      "published_counts_before":published,"published_counts_after":public_counts(auth),
      "sha_before":hashlib.sha256(content.encode()).hexdigest(),
      "sha_after":hashlib.sha256(edited.encode()).hexdigest()}
    dest=Path("reports/nx-six-car-20261026");dest.mkdir(parents=True,exist_ok=True)
    (dest/"result.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("NX_SIX_CAR_AUDIT_VERIFIED",json.dumps(report,ensure_ascii=False),flush=True)

if __name__=="__main__": main()
