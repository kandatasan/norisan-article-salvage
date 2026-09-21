#!/usr/bin/env python3
from __future__ import annotations

import base64, json, os, urllib.parse, urllib.request
from pathlib import Path

SITE="https://tsurikue.com"
UA="tsurikue-audit-sugai-media-20260921/1.0"
POST_ID=3865
SLUG="sugai-tsubugai"
TITLE='広島で「ツブガイ」と呼ぶスガイはうまい！味・茹で方と磯遊びの思い出'
TARGETS={"img_8439.jpeg","img_8440.jpeg","img_8441.jpeg","img_8442.jpeg","img_8439.jpg","img_8440.jpg","img_8441.jpg","img_8442.jpg"}
REPORT=Path("reports/sugai-media-audit-20260921")

def auth():
    u=os.environ["TSURIKUE_WP_USER"]; p=os.environ["TSURIKUE_WP_APP_PASSWORD"]
    return "Basic "+base64.b64encode(f"{u}:{p}".encode()).decode()

def get(path):
    req=urllib.request.Request(SITE+path,headers={"Authorization":auth(),"Accept":"application/json","User-Agent":UA},method="GET")
    with urllib.request.urlopen(req,timeout=45) as r:
        body=r.read().decode()
        return json.loads(body) if body else None, dict(r.headers.items())

def main():
    q=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,featured_media"})
    post,_=get(f"/wp-json/wp/v2/posts/{POST_ID}?{q}")
    title=(post.get("title") or {}).get("raw") or (post.get("title") or {}).get("rendered") or ""
    if post.get("slug")!=SLUG or post.get("status")!="draft" or title!=TITLE:
        raise RuntimeError("target draft identity mismatch")
    if int(post.get("featured_media") or 0)!=0:
        raise RuntimeError("target draft already has featured media")

    q=urllib.parse.urlencode({
        "context":"edit","per_page":100,"page":1,"orderby":"date","order":"desc",
        "_fields":"id,date,slug,source_url,media_details,alt_text,caption,title"
    })
    rows,_=get(f"/wp-json/wp/v2/media?{q}")
    matches=[]
    for row in rows:
        url=row.get("source_url") or ""
        filename=urllib.parse.unquote(urllib.parse.urlparse(url).path.rsplit("/",1)[-1]).casefold()
        if filename in TARGETS:
            details=row.get("media_details") or {}
            matches.append({
                "id":int(row.get("id") or 0),
                "date":row.get("date"),
                "filename":filename,
                "source_url":url,
                "width":int(details.get("width") or 0),
                "height":int(details.get("height") or 0),
                "alt_text":row.get("alt_text") or "",
            })
    matches.sort(key=lambda x:x["filename"])
    expected_names={"img_8439","img_8440","img_8441","img_8442"}
    stems={m["filename"].rsplit(".",1)[0] for m in matches}
    if stems!=expected_names:
        raise RuntimeError(f"expected exactly 4 target uploads, got stems={sorted(stems)} matches={matches}")

    REPORT.mkdir(parents=True,exist_ok=True)
    data={
        "result":"SUCCESS","post_id":POST_ID,"slug":SLUG,"status":"draft",
        "featured_media":0,"matches":matches,"wordpress_write_count":0
    }
    (REPORT/"result.json").write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=[
        "# Sugai media audit 2026-09-21","",
        "- result: **SUCCESS**",f"- post_id: **{POST_ID}**","- status: **draft**",
        f"- slug: **{SLUG}**","- wordpress_write_count: **0**","",
        "## Matched uploads"
    ]
    for m in matches:
        lines.append(f"- media #{m['id']} / {m['filename']} / {m['width']}x{m['height']} / {m['source_url']}")
    (REPORT/"summary.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps(data,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
