#!/usr/bin/env python3
"""Add two compact informational tables to unpublished Sakaiminato WP draft 4138.
Pull request runs a read-only audit; main push updates content only after comparing
exact current raw body. No photos, metadata, other posts, or publication status modified.
"""
from __future__ import annotations
import os, sys, json, re, base64, hashlib, urllib.request, urllib.parse
from pathlib import Path
SITE="https://tsurikue.com"
POST_ID=4138
SLUG="sakaiminato-station-sightseeing"
BASE=Path("content/revisions/sakaiminato-station-20261013-stamp-quest.json")
REV=Path("content/revisions/sakaiminato-station-20261013-info-tables.json")
def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()
def join(obj):
    return "\n\n".join(obj["blocks"])
def validate(base,rev):
    for o in (base,rev):
        if (o["slug"],o["status"],o["category_id"])!=(SLUG,"draft",7):
            raise RuntimeError("Wrong post identity/category/status")
    old=base["blocks"];new=rev["blocks"]
    idxs=[i for i,b in enumerate(old) if "水木しげる記念館には専用駐車場がないので" in b]
    if len(idxs)!=1:raise RuntimeError("Original insertion anchor missing or ambiguous")
    idx=idxs[0]
    if new[:idx]!=old[:idx] or new[idx+5:]!=old[idx+1:]:
        raise RuntimeError("Change detected outside exactly one information section")
    replacement=new[idx:idx+5]
    if len(replacement)!=5:raise RuntimeError("Unexpected new block count")
    if sum("<!-- wp:table" in b for b in replacement)!=2:
        raise RuntimeError("Expected two Gutenberg tables")
    if sum(replacement[2].count("<tr>") for _ in range(1))!=9 or replacement[4].count("<tr>")!=6:
        raise RuntimeError("Expected 8 station rows and 5 visitor rows + headers")
    for text in ("みなとーる","観光案内所","0859-47-0121","コインロッカー",
                 "ローソン境港浜ノ町店","夕凪の湯","境港水産物直売センター","みどりの窓口","ICOCA"):
        if text not in "".join(replacement):raise RuntimeError("Search-intent gap "+text)
    oldbody=join(base);newbody=join(rev)
    old_slots=re.findall(r'<!-- TSURIKUE_IMAGE:[^>]+-->',oldbody)
    if old_slots!=re.findall(r'<!-- TSURIKUE_IMAGE:[^>]+-->',newbody) or len(old_slots)!=15:
        raise RuntimeError("User's image placements changed")
    for pat in (r'wp-image-\d+',r'\[blog_parts id="\d+"\]'):
        if re.findall(pat,oldbody)!=re.findall(pat,newbody):
            raise RuntimeError("Unexpected image or ad changes")
    if "<h1" in newbody.lower():raise RuntimeError("Unexpected H1 in body")
    if newbody.count("<!-- wp:table")!=2 or newbody.count("<!-- /wp:table -->")!=2:
        raise RuntimeError("Gutenberg table block imbalance")
    if (newbody.count("<!-- wp:")-newbody.count("<!-- /wp:")) != (
         oldbody.count("<!-- wp:")-oldbody.count("<!-- /wp:")):
        raise RuntimeError("Gutenberg block delta mismatch")
    if "摩尼車" not in newbody or "猫娘" not in newbody or "一反もめん" not in newbody:
        raise RuntimeError("Firsthand experience lost")
    print("CONTENT_AUDIT_OK",json.dumps({
        "post_id":POST_ID,"before_length":len(oldbody),"after_length":len(newbody),
        "new_information_tables":2,"data_rows":13,"untouched_photo_slots":15,
        "area_changed":"station info section only"
    },ensure_ascii=False),flush=True)
    return oldbody,newbody
def req(path,auth,payload=None):
    headers={"Authorization":auth,"Accept":"application/json","User-Agent":"tsurikue-station-tables/1.0"}
    if payload is not None:headers["Content-Type"]="application/json; charset=utf-8"
    request=urllib.request.Request(SITE+path,headers=headers,
          method="POST" if payload is not None else "GET",
          data=json.dumps(payload,ensure_ascii=False).encode() if payload is not None else None)
    with urllib.request.urlopen(request,timeout=60) as response:
        return json.load(response), dict(response.headers)
def fetch(auth):
    query=urllib.parse.urlencode({"context":"edit",
       "_fields":"id,slug,status,title,content,author,categories,featured_media"})
    return req(f"/wp-json/wp/v2/posts/{POST_ID}?{query}",auth)[0]
def count_published(auth):
    q=urllib.parse.urlencode({"context":"edit","status":"publish","per_page":1,"_fields":"id"})
    return int(req("/wp-json/wp/v2/posts?"+q,auth)[1]["X-WP-Total"])
def main(mode):
    user=os.getenv("TSURIKUE_WP_USER");pw=os.getenv("TSURIKUE_WP_APP_PASSWORD")
    if not user or not pw:raise RuntimeError("WordPress secrets missing")
    auth="Basic "+base64.b64encode((user+":"+pw).encode()).decode()
    base=json.loads(BASE.read_text(encoding="utf-8"))
    revised=json.loads(REV.read_text(encoding="utf-8"))
    old,new=validate(base,revised)
    row=fetch(auth)
    if (row["id"],row["slug"],row["status"])!=(POST_ID,SLUG,"draft"):
        raise RuntimeError("Unexpected live WordPress post/status")
    if row["categories"]!=[7] or row["title"]["raw"]!=revised["title"]:
        raise RuntimeError("Title/category changed")
    if row["content"]["raw"]!=old:
        raise RuntimeError("Live draft changed since previous revision; never overwrite editor changes. SHA "+sha(row["content"]["raw"]))
    published_before=count_published(auth)
    print("WORDPRESS_READ_ONLY_PREFLIGHT_OK",POST_ID,row["status"],sha(old),flush=True)
    if mode=="check":return
    current=fetch(auth)
    if current["content"]["raw"]!=old or current["status"]!="draft":
        raise RuntimeError("Concurrent editor change; no update")
    try:
        req(f"/wp-json/wp/v2/posts/{POST_ID}",auth,{"content":new})
        saved=fetch(auth)
        for field in ("id","slug","status","title","author","categories","featured_media"):
            if saved[field]!=row[field]:
                raise RuntimeError("Protected WordPress field changed: "+field)
        if saved["content"]["raw"]!=new:
            raise RuntimeError("Saved content mismatch")
        rendered=saved["content"].get("rendered","")
        if ("みなとーる" not in rendered or "ローソン境港浜ノ町店" not in rendered
              or rendered.count("<table")!=2):
            raise RuntimeError("Rendered WordPress tables mismatch")
        if count_published(auth)!=published_before:
            raise RuntimeError("Unexpected change in number of published posts")
        print("LIVE_WORDPRESS_DRAFT_VERIFIED",json.dumps({
            "id":POST_ID,"slug":SLUG,"status":"draft",
            "title":revised["title"],"tables":2,"rows":13,
            "photo_slots":15,"body_sha256":sha(new),
            "editor_url":SITE+"/wp-admin/post.php?post=4138&action=edit"
        },ensure_ascii=False),flush=True)
    except Exception:
        try:
            latest=fetch(auth)
            if latest["content"]["raw"]==new:
                req(f"/wp-json/wp/v2/posts/{POST_ID}",auth,{"content":old})
                print("CONDITIONAL_ROLLBACK_OK",flush=True)
            else:
                print("ROLLBACK_SKIPPED_UNMATCHED_BODY",flush=True)
        except Exception as e:
            print("ROLLBACK_FAILED",str(e),flush=True)
        raise
if __name__=="__main__":
    mode=sys.argv[1] if len(sys.argv)>1 else "check"
    if mode not in ("check","apply"):raise SystemExit("check/apply only")
    main(mode)
