#!/usr/bin/env python3
"""Update the existing, unpublished Sakaiminato WordPress draft with first-hand stamp-quest details.
PR=read only. Main merge=update exact post 4138 content only, with SHA/body preflight.
Photos remain invisible editorial slots until uploaded/licensed. No indoor image published here.
"""
from __future__ import annotations
import os,sys,json,re,hashlib,base64,urllib.parse,urllib.request
from pathlib import Path

SITE="https://tsurikue.com"
ID=4138; SLUG="sakaiminato-station-sightseeing"
BASE=Path("content/drafts/sakaiminato-station-sightseeing-20261013.json")
REV=Path("content/revisions/sakaiminato-station-20261013-stamp-quest.json")

def sha(s):return hashlib.sha256(s.encode("utf-8")).hexdigest()

def validate(base,rev):
    if (base["slug"],rev["slug"],rev["status"],rev["category_id"])!=(SLUG,SLUG,"draft",7):
        raise RuntimeError("Source metadata mismatch")
    before="\n\n".join(base["blocks"])
    after="\n\n".join(rev["blocks"])
    oldmark="<h2 class=\"wp-block-heading\">鬼太郎妖怪倉庫に初めて入ったら、猫娘がちょい怖かった</h2>"
    nextmark="<h2 class=\"wp-block-heading\">水木しげる記念館まで足を延ばすのもあり</h2>"
    for s in (before,after):
        if s.count(oldmark)!=1 or s.count(nextmark)!=1:
            raise RuntimeError("Target headings changed")
    # all material before and after targeted attraction section must remain untouched
    if before.split(oldmark)[0]!=after.split(oldmark)[0]:
        raise RuntimeError("Unexpected change before attraction")
    if before.split(nextmark)[1]!=after.split(nextmark)[1]:
        raise RuntimeError("Unexpected change outside attraction")
    if sorted(re.findall(r'href="([^"]+)"',before))!=sorted(re.findall(r'href="([^"]+)"',after)):
        raise RuntimeError("Outbound or affiliate URL modified")
    for phrase in ("5カ所","好きな4種類","金運","交通安全","摩尼車","主印","自分で見つけてね",
                   "鏡の間","猫娘","鬼太郎妖怪倉庫","開運ノ札"):
        if phrase not in after:raise RuntimeError("Owner's first-hand story missing: "+phrase)
    # Source photos have not been uploaded to WP, must not turn into broken images or
    # publish indoor photography without an explicit venue clearance.
    expected=rev["images_expected"]
    slotfilenames=re.findall(r'<!-- TSURIKUE_IMAGE:([^|<>]+)\|',after)
    if sorted(expected)!=sorted(slotfilenames):
        raise RuntimeError("Image manifest and invisible slots differ")
    if re.search(r'<img\b',after,re.I):
        raise RuntimeError("Images cannot be injected until permission/source verified")
    if re.search(r'<h1\b',after,re.I):raise RuntimeError("Do not duplicate H1")
    if any("摩尼車" in f for f in expected):
        raise RuntimeError("Author deliberately requested no mani wheel photo")
    if (before.count("<!-- wp:")-before.count("<!-- /wp:"))!=(
        after.count("<!-- wp:")-after.count("<!-- /wp:")):
        raise RuntimeError("Gutenberg block balance changed")
    print("EDITORIAL_PREFLIGHT_OK",json.dumps({
        "post_id":ID,"old_length":len(before),"new_length":len(after),
        "added_length":len(after)-len(before),
        "photo_slots_before":len(base["images_expected"]),
        "photo_slots_after":len(expected),"actual_photo_blocks":0,
        "scope":"妖怪倉庫 H2 only"
    },ensure_ascii=False),flush=True)
    return before,after

def http(path,token,payload=None):
    hdr={"Authorization":token,"Accept":"application/json",
         "User-Agent":"tsurikue-stampquest-draft/1.0"}
    if payload is not None:hdr["Content-Type"]="application/json; charset=utf-8"
    req=urllib.request.Request(SITE+path,headers=hdr,
          method="POST" if payload is not None else "GET",
          data=json.dumps(payload,ensure_ascii=False).encode("utf-8") if payload is not None else None)
    with urllib.request.urlopen(req,timeout=60) as resp:
        return json.load(resp),dict(resp.headers)
def post(token):
    query=urllib.parse.urlencode({"context":"edit",
        "_fields":"id,slug,status,title,content,featured_media,author,categories"})
    return http(f"/wp-json/wp/v2/posts/{ID}?{query}",token)[0]
def published(token):
    query=urllib.parse.urlencode({"context":"edit","status":"publish","per_page":1,"_fields":"id"})
    return int(http("/wp-json/wp/v2/posts?"+query,token)[1]["X-WP-Total"])
def main(mode):
    u=os.getenv("TSURIKUE_WP_USER");p=os.getenv("TSURIKUE_WP_APP_PASSWORD")
    if not u or not p:raise RuntimeError("Missing WP secrets")
    token="Basic "+base64.b64encode((u+":"+p).encode()).decode()
    olddoc=json.loads(BASE.read_text(encoding="utf-8"))
    newdoc=json.loads(REV.read_text(encoding="utf-8"))
    before,after=validate(olddoc,newdoc)
    row=post(token)
    if (row["id"],row["slug"],row["status"])!=(ID,SLUG,"draft"):
        raise RuntimeError("Post ID, slug or draft status changed; refuse update")
    if row["title"]["raw"]!=newdoc["title"] or row["categories"]!=[7]:
        raise RuntimeError("Existing title/categories changed; no overwrite")
    if row["content"]["raw"]!=before:
        raise RuntimeError("WordPress draft was edited since baseline; abort without writes. Live SHA "+sha(row["content"]["raw"]))
    orig_featured=row["featured_media"]
    old_count=published(token)
    print("WORDPRESS_READ_ONLY_VERIFIED",ID,SLUG,"status=draft","SHA",sha(before),flush=True)
    if mode=="check":return
    fresh=post(token)
    if fresh["content"]["raw"]!=before or fresh["status"]!="draft":
        raise RuntimeError("Concurrent human change; abort")
    attempted=False
    try:
        attempted=True
        http(f"/wp-json/wp/v2/posts/{ID}",token,{"content":after})
        saved=post(token)
        for f in ("id","slug","status","title","featured_media","author","categories"):
            if saved[f]!=row[f]:raise RuntimeError("Protected post metadata changed: "+f)
        if saved["featured_media"]!=orig_featured:
            raise RuntimeError("Featured media changed")
        if saved["content"]["raw"]!=after:
            raise RuntimeError("WordPress saved text differs from approved revised draft")
        if published(token)!=old_count:
            raise RuntimeError("Published post count changed")
        if "主印" not in saved["content"].get("rendered",""):
            raise RuntimeError("Revised first-hand stamp content absent from rendered draft")
        print("LIVE_DRAFT_VERIFIED",json.dumps({
            "post_id":ID,"slug":SLUG,"status":"draft","url":SITE+"/wp-admin/post.php?post=4138&action=edit",
            "body_sha256":sha(after),"photos_pending":len(newdoc["images_expected"]),
            "published_count_unchanged":old_count
        },ensure_ascii=False),flush=True)
    except Exception:
        if attempted:
            try:
                now=post(token)
                if now["content"]["raw"]==after:
                    http(f"/wp-json/wp/v2/posts/{ID}",token,{"content":before})
                    print("CONDITIONAL_ROLLBACK_SUCCESS",ID,flush=True)
                else:print("ROLLBACK_SKIPPED_BODY_WAS_CHANGED_EXTERNALLY",ID,flush=True)
            except Exception as e:print("CONDITIONAL_ROLLBACK_FAILURE",str(e),flush=True)
        raise
if __name__=="__main__":
    mode=sys.argv[1] if len(sys.argv)>1 else "check"
    if mode not in ("check","apply"):raise SystemExit("check/apply only")
    main(mode)
