#!/usr/bin/env python3
"""Rewrite Tom & Jerry as follow-along SEO story with scene-soft-breaks without changing 15 original media blocks.

PR: check only. main push: exact-content-guarded content-only update.
The original editorial template is a pre-image snapshot; the actual WP post stays authoritative.
"""
import base64
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PID=4282
SLUG="tom-and-jerry-exhibition-hiroshima-2026"
TITLE="【広島】そごうのトムとジェリー展に行ってきた！見どころと限定グッズを現地レポ"
SITE="https://tsurikue.com"
PREV_SHA="b14c9c983fd47f65bd05ef33e8fcc74325ed6057186954ab72ef9bc6b71c419e"
BASE=Path("editorial/tom-and-jerry-hiroshima-2026/revisions/period-breaks-20261101.html")
NEW=Path("editorial/tom-and-jerry-hiroshima-2026/revisions/followalong-seo-20261101.html")
PLAN=Path("editorial/tom-and-jerry-hiroshima-2026/photo-plan.json")
IMAGE=re.compile(r"<!-- wp:image\b.*?<!-- /wp:image -->",re.S)
SLOT=re.compile(r"<!-- TSURIKUE_IMAGE:([^|<>]+)\|([^|<>]+)\|([^<>]+) -->")

def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def auth():
    user=os.getenv("TSURIKUE_WP_USER")
    pw=os.getenv("TSURIKUE_WP_APP_PASSWORD")
    if not user or not pw:raise RuntimeError("STOP: WordPress credentials unavailable")
    return "Basic "+base64.b64encode((user+":"+pw).encode()).decode()

def api(path,token,payload=None):
    headers={"Authorization":token,"Accept":"application/json",
             "User-Agent":"tsurikue-tom-jerry-prose-rhythm/1.0"}
    method="POST" if payload is not None else "GET"
    if payload is not None:headers["Content-Type"]="application/json; charset=utf-8"
    request=urllib.request.Request(SITE+path,headers=headers,method=method,
        data=json.dumps(payload,ensure_ascii=False).encode() if payload is not None else None)
    for attempt in range(3 if method=="GET" else 1):
        try:
            with urllib.request.urlopen(request,timeout=55) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError,TimeoutError) as e:
            if method=="POST" or attempt==2:raise
            print("RETRY_READ",type(e).__name__,attempt+1,flush=True)
            time.sleep(2*(attempt+1))

def get_wp(token):
    query=urllib.parse.urlencode({"context":"edit","_fields":
        "id,slug,status,title,categories,featured_media,author,content"})
    return api("/wp-json/wp/v2/posts/"+str(PID)+"?"+query,token)

def raw(post):
    return (post.get("content") or {}).get("raw") or ""

def protect(post):
    if (post.get("id"),post.get("slug"),post.get("status"))!=(PID,SLUG,"draft"):
        raise RuntimeError("STOP: wrong post identity/status")
    if html.unescape((post.get("title") or {}).get("raw") or "")!=TITLE:
        raise RuntimeError("STOP: article title changed")
    if post.get("categories")!=[7] or int(post.get("featured_media") or 0)!=4301:
        raise RuntimeError("STOP: categories or cover unexpectedly changed")
    if digest(raw(post))!=PREV_SHA:
        raise RuntimeError("STOP: live WordPress post has changed since last audit; do not overwrite it")

def inject(template,slots,images):
    result=template
    for (name,alt,cap),image in zip(slots,images):
        needle="<!-- TSURIKUE_IMAGE:"+name+"|"+alt+"|"+cap+" -->"
        if result.count(needle)!=1:raise RuntimeError("STOP: missing or duplicate image marker "+name)
        result=result.replace(needle,image,1)
    if SLOT.search(result):raise RuntimeError("STOP: unfilled image marker")
    return result

def prepare(post):
    current=raw(post)
    images=IMAGE.findall(current)
    original=BASE.read_text("utf-8")
    revised=NEW.read_text("utf-8")
    base_slots=SLOT.findall(original)
    new_slots=SLOT.findall(revised)
    mapping=json.loads(PLAN.read_text("utf-8"))["media_mapping"]
    expected=[(r["source"],int(r["wp_media_id"])) for r in mapping]
    if len(images)!=15 or len(base_slots)!=15 or len(new_slots)!=15 or sorted(new_slots)!=sorted(base_slots):
        raise RuntimeError("STOP: photo count or metadata set changed")
    if len({x[0] for x in base_slots})!=15 or len({x[0] for x in new_slots})!=15:
        raise RuntimeError("STOP: duplicate photo slot")
    if [x[0] for x in base_slots]!=[x[0] for x in expected]:
        raise RuntimeError("STOP: photo manifest does not match article")
    for img,(_,mid),(_,alt,cap) in zip(images,expected,base_slots):
        if "wp-image-"+str(mid)+'"' not in img:
            raise RuntimeError("STOP: verified image order/ID mismatch "+str(mid))
        if 'alt="'+html.escape(alt,quote=True)+'"' not in img:
            raise RuntimeError("STOP: image alt unexpectedly changed "+str(mid))
        if "<figcaption" not in img:
            raise RuntimeError("STOP: missing image caption "+str(mid))
    cfg=json.loads(Path("editorial/tom-and-jerry-hiroshima-2026/config.json").read_text("utf-8"))
    # The original package writer prepended two identity markers, before any Gutenberg blocks.
    identity_prefix=cfg["salvage_marker"]+"\n"+cfg["editorial_marker"]+"\n"
    recreated=identity_prefix+inject(original,base_slots,images)
    if recreated!=current:
        first=next((i for i,(a,b) in enumerate(zip(recreated,current)) if a!=b),min(len(recreated),len(current)))
        raise RuntimeError(f"STOP: live WordPress reconstruction mismatch at byte {first}; lengths {len(recreated)}/{len(current)}")
    existing_images={slot[0]:img for slot,img in zip(base_slots,images)}
    reordered_images=[existing_images[slot[0]] for slot in new_slots]
    new=identity_prefix+inject(revised,new_slots,reordered_images)
    if IMAGE.findall(new)!=reordered_images or sorted(IMAGE.findall(new))!=sorted(images):
        raise RuntimeError("STOP: existing image Gutenberg blocks changed during reordering")
    if len(set(re.findall(r'wp-image-(\d+)',new)))!=15:
        raise RuntimeError("STOP: duplicate or missing media IDs")
    if new.count("<!-- wp:table")!=1 or current.count("<!-- wp:table")!=1:
        raise RuntimeError("STOP: original pricing table missing or duplicated")
    old_table=re.search(r"<!-- wp:table -->.*?<!-- /wp:table -->",current,re.S)
    new_table=re.search(r"<!-- wp:table -->.*?<!-- /wp:table -->",new,re.S)
    if not old_table or not new_table or old_table.group()!=new_table.group():
        raise RuntimeError("STOP: official fee table contents changed")
    if not 8<=new.count("<!-- wp:heading")<=15:
        raise RuntimeError("STOP: revised story section headings missing/unexpected")
    if new.count("<!-- wp:paragraph -->")!=45:
        raise RuntimeError("STOP: unexpected paragraph count")
    if new.count("<br>")!=43:
        raise RuntimeError("STOP: missing soft line breaks within scenes")
    if new.count("<!-- wp:image ")!=15 or new.count("<!-- /wp:image -->")!=15:
        raise RuntimeError("STOP: inconsistent existing image blocks")
    if new==current:raise RuntimeError("STOP: no text changes")
    return new

def main(mode):
    if mode not in ("check","apply"):raise RuntimeError("mode must be check/apply")
    token=auth()
    current=get_wp(token)
    protect(current)
    new=prepare(current)
    out=Path("reports/tom-jerry-followalong-seo")
    out.mkdir(parents=True,exist_ok=True)
    report={"post_id":PID,"slug":SLUG,"status":"draft",
        "featured_media":4301,"image_count":15,"current_body_sha256":PREV_SHA,
        "new_body_sha256":digest(new),"paragraphs_before":99,"paragraphs_after":45,
        "changed_fields":["content"],"photo_uploads":0}
    (out/"preflight.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print("READ_ONLY_FOLLOWALONG_PREFLIGHT_OK",json.dumps(report,ensure_ascii=False),flush=True)
    if mode=="check":return
    second=get_wp(token)
    protect(second)
    if raw(second)!=raw(current) or any(second.get(k)!=current.get(k) for k in
         ("id","slug","status","title","categories","featured_media","author")):
        raise RuntimeError("STOP: concurrent live edit")
    try:
        submitted=api("/wp-json/wp/v2/posts/"+str(PID),token,{"content":new})
        if submitted.get("id")!=PID or submitted.get("status")!="draft":
            raise RuntimeError("STOP: unexpected WordPress update response")
    except (urllib.error.URLError,TimeoutError) as err:
        print("UNCERTAIN_WRITE_DO_NOT_RETRY",type(err).__name__,flush=True)
    saved=get_wp(token)
    for key in ("id","slug","status","title","categories","featured_media","author"):
        if saved.get(key)!=current.get(key):
            raise RuntimeError("STOP: protected WordPress field changed: "+key)
    if raw(saved)!=new or IMAGE.findall(raw(saved))!=IMAGE.findall(raw(current)):
        raise RuntimeError("STOP: saved WordPress body/images did not match guarded edit")
    report["after_body_sha256"]=digest(raw(saved))
    report["result"]="UPDATED_AND_VERIFIED"
    (out/"result.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print("FOLLOWALONG_DRAFT_UPDATED_VERIFIED",json.dumps(report,ensure_ascii=False),flush=True)

if __name__=="__main__":
    main(sys.argv[1] if len(sys.argv)>1 else "check")
