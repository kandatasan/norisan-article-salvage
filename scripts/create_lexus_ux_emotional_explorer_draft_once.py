#!/usr/bin/env python3
from __future__ import annotations
import base64, html, json, os, re, urllib.parse, urllib.request, hashlib
from pathlib import Path
from typing import Any

SITE="https://tsurikue.com"
BASE=SITE+"/wp-json/wp/v2"
UA="tsurikue-create-lexus-emotional-draft/1.0"
TITLE="レクサスUXの特別仕様車エモーショナルエクスプローラーはお得？実際に選んだ理由"
SLUG="lexus-ux-emotional-explorer"
CATEGORY_ID=11
FEATURED_MEDIA=2197
EXPECTED_MEDIA={
    2197:"/wp-content/uploads/2026/06/IMG_3929.jpeg",
    2211:"/wp-content/uploads/2026/06/IMG_3557.jpeg",
    2210:"/wp-content/uploads/2026/06/IMG_1136.jpeg",
}
LINKED_SLUGS={"ux-mitsumori","ux-koukai","lexus-ux-interior","lexus-ux-used"}
SALVAGE_MARKER=f"<!-- lexus-salvage:v1 slug={SLUG} source=lexus-diary.com/multi -->"
EDITORIAL_MARKER=f"<!-- tsurikue-editorial:v1 slug={SLUG} -->"
ARTICLE_PATH=Path("editorial/lexus-ux-emotional-explorer/article.html")
REPORT_DIR=Path("reports/lexus-ux-emotional-explorer-draft")

def auth_header(user:str,password:str)->str:
    return "Basic "+base64.b64encode(f"{user}:{password}".encode()).decode()

def req(path:str,auth:str,method:str="GET",payload:dict[str,Any]|None=None):
    data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode("utf-8")
    headers={"Authorization":auth,"Accept":"application/json","User-Agent":UA}
    if data is not None:
        headers["Content-Type"]="application/json; charset=utf-8"
    r=urllib.request.Request(BASE+path,data=data,headers=headers,method=method)
    with urllib.request.urlopen(r,timeout=60) as x:
        return json.loads(x.read().decode()),dict(x.headers)

def count_published(endpoint:str,auth:str)->int:
    q=urllib.parse.urlencode({"context":"edit","status":"publish","per_page":"1","_fields":"id"})
    _,h=req(f"/{endpoint}?{q}",auth)
    return int(h.get("X-WP-Total","0"))

def public_counts(auth:str)->dict[str,int]:
    p=count_published("posts",auth)
    g=count_published("pages",auth)
    return {"posts":p,"pages":g,"total":p+g}

def full_content()->str:
    article=ARTICLE_PATH.read_text(encoding="utf-8").strip()+"\n"
    full=SALVAGE_MARKER+"\n"+EDITORIAL_MARKER+"\n"+article
    if re.search(r"<h1\b",full,re.I):
        raise RuntimeError("BODY_H1_FOUND")
    if '[blog_parts id="2843"]' not in full:
        raise RuntimeError("GULLIVER_BANNER_MISSING")
    if "4B65SD+8DUSHE+9QU+NVHCY" not in full:
        raise RuntimeError("GULLIVER_TEXT_AD_MISSING")
    for slug in LINKED_SLUGS:
        if f"https://tsurikue.com/{slug}/" not in full:
            raise RuntimeError(f"INTERNAL_LINK_MISSING {slug}")
    return full

def validate_category(auth:str):
    q=urllib.parse.urlencode({"context":"edit","_fields":"id,name,slug,parent"})
    row,_=req(f"/categories/{CATEGORY_ID}?{q}",auth)
    if int(row.get("id") or 0)!=CATEGORY_ID or row.get("slug")!="lexus-ux":
        raise RuntimeError("CATEGORY_MISMATCH")

def validate_media(auth:str):
    for mid,path in EXPECTED_MEDIA.items():
        q=urllib.parse.urlencode({"context":"edit","_fields":"id,status,source_url"})
        row,_=req(f"/media/{mid}?{q}",auth)
        actual=urllib.parse.unquote(urllib.parse.urlparse(row.get("source_url") or "").path)
        if int(row.get("id") or 0)!=mid or actual.casefold()!=path.casefold():
            raise RuntimeError(f"MEDIA_MISMATCH {mid} {actual}")

def validate_destinations(auth:str):
    for slug in LINKED_SLUGS:
        q=urllib.parse.urlencode({"context":"edit","slug":slug,"status":"publish","per_page":"10","_fields":"id,slug,status"})
        rows,_=req(f"/posts?{q}",auth)
        if len(rows)!=1 or rows[0].get("status")!="publish":
            raise RuntimeError(f"DESTINATION_NOT_PUBLISHED {slug}")

def find_existing(auth:str):
    q=urllib.parse.urlencode({"context":"edit","slug":SLUG,"status":"any","per_page":"20","_fields":"id,slug,status,title,content,categories,featured_media"})
    rows,_=req(f"/posts?{q}",auth)
    return rows

def main():
    user=os.environ.get("TSURIKUE_WP_USER")
    password=os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("BLOCKED_MISSING_SECRETS")
    auth=auth_header(user,password)
    before=public_counts(auth)
    validate_category(auth)
    validate_media(auth)
    validate_destinations(auth)
    full=full_content()
    rows=find_existing(auth)
    action="CREATE"
    post_id=None
    if rows:
        if len(rows)!=1:
            raise RuntimeError("DUPLICATE_SLUG")
        row=rows[0]
        current=((row.get("content") or {}).get("raw") or (row.get("content") or {}).get("rendered") or "")
        title=html.unescape(((row.get("title") or {}).get("raw") or (row.get("title") or {}).get("rendered") or ""))
        cats=[int(x) for x in (row.get("categories") or [])]
        if row.get("status")!="draft":
            raise RuntimeError(f"EXISTING_NON_DRAFT {row.get('status')}")
        if current.strip()==full.strip() and title==TITLE and CATEGORY_ID in cats and int(row.get("featured_media") or 0)==FEATURED_MEDIA:
            action="ALREADY_UP_TO_DATE"
            post_id=int(row["id"])
        else:
            raise RuntimeError("EXISTING_DRAFT_DIFFERS_REFUSING_OVERWRITE")
    else:
        payload={"title":TITLE,"slug":SLUG,"content":full,"status":"draft","categories":[CATEGORY_ID],"featured_media":FEATURED_MEDIA}
        row,_=req("/posts",auth,method="POST",payload=payload)
        if row.get("status")!="draft" or row.get("slug")!=SLUG:
            raise RuntimeError("CREATE_RESPONSE_INVALID")
        post_id=int(row["id"])

    q=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,content,categories,featured_media,link"})
    after_row,_=req(f"/posts/{post_id}?{q}",auth)
    after=public_counts(auth)
    if after!=before:
        raise RuntimeError(f"PUBLISHED_COUNTS_CHANGED {before} -> {after}")
    content=((after_row.get("content") or {}).get("raw") or "")
    title=html.unescape(((after_row.get("title") or {}).get("raw") or ""))
    if after_row.get("status")!="draft" or after_row.get("slug")!=SLUG or title!=TITLE:
        raise RuntimeError("POSTCREATE_STATE_MISMATCH")
    if int(after_row.get("featured_media") or 0)!=FEATURED_MEDIA:
        raise RuntimeError("FEATURED_MEDIA_MISMATCH")
    if CATEGORY_ID not in [int(x) for x in (after_row.get("categories") or [])]:
        raise RuntimeError("CATEGORY_NOT_SET")
    if content.strip()!=full.strip():
        raise RuntimeError("CONTENT_MISMATCH")

    report={"ok":True,"action":action,"post_id":post_id,"slug":SLUG,"status":"draft","title":TITLE,"featured_media":FEATURED_MEDIA,"category_id":CATEGORY_ID,"media_checked":sorted(EXPECTED_MEDIA),"linked_slugs":sorted(LINKED_SLUGS),"public_before":before,"public_after":after,"content_sha256":hashlib.sha256(content.encode()).hexdigest(),"publish_count":0}
    REPORT_DIR.mkdir(parents=True,exist_ok=True)
    (REPORT_DIR/"result.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (REPORT_DIR/"summary.md").write_text("\n".join(["# Lexus UX Emotional Explorer draft","",f"- action: **{action}**",f"- post_id: **{post_id}**","- status: **draft**",f"- public_before: **{before['total']}**",f"- public_after: **{after['total']}**",f"- featured_media: **{FEATURED_MEDIA}**"])+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
