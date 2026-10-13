#!/usr/bin/env python3
"""Create one unpublished Hiroshima-Koizu-Sakaiminato first-hand day-trip draft.

PR is READ ONLY. Merge to main creates a new draft (status=draft) only.
Uses EXACT media for seven source photos when present; otherwise retains
invisible slot comments for owner-provided photos not yet in WP media.
Never changes the earlier WordPress post 4138.
"""
from __future__ import annotations
import os,sys,json,re,html,base64,hashlib,urllib.parse,urllib.request,urllib.error,time
from pathlib import Path

SITE="https://tsurikue.com"
SOURCE=Path("content/drafts/hiroshima-koizu-sakaiminato-daytrip-20261013.json")
SLUG="hiroshima-koizu-sakaiminato-day-trip"
CATEGORY=7
SLOT=re.compile(r'<!-- TSURIKUE_IMAGE:([^|<>]+)\|([^|<>]+)\|([^<>]+) -->')
def sha(s):return hashlib.sha256(s.encode("utf-8")).hexdigest()
def esc(s):return html.escape(s,quote=True)
def request(path,auth,payload=None):
    hdr={"Authorization":auth,"Accept":"application/json","User-Agent":"tsurikue-daytrip-draft/1.0"}
    if payload is not None:hdr["Content-Type"]="application/json; charset=utf-8"
    req=urllib.request.Request(SITE+path,headers=hdr,
      data=json.dumps(payload,ensure_ascii=False).encode("utf-8") if payload is not None else None,
      method="POST" if payload is not None else "GET")
    for i in range(3):
        try:
            with urllib.request.urlopen(req,timeout=80) as r:return json.load(r),dict(r.headers)
        except urllib.error.HTTPError as exc:
            if payload is None and exc.code in (429,502,503,504) and i<2:
                time.sleep((i+1)*3)
                continue
            raise
def get(path,auth):return request(path,auth)[0]
def search_posts(auth,text,limit=60):
    q=urllib.parse.urlencode({"context":"edit","status":"any","search":text,
        "per_page":limit,"_fields":"id,slug,status,title,link"})
    return get("/wp-json/wp/v2/posts?"+q,auth)
def posts_by_slug(auth,slug):
    q=urllib.parse.urlencode({"context":"edit","status":"any","slug":slug,
        "per_page":25,"_fields":"id,slug,status,title"})
    return get("/wp-json/wp/v2/posts?"+q,auth)
def direct_post(auth,id):
    q=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,link,categories"})
    return get(f"/wp-json/wp/v2/posts/{id}?{q}",auth)
def recent_media(auth):
    q=urllib.parse.urlencode({"context":"edit","per_page":100,"page":1,
        "orderby":"date","order":"desc","_fields":"id,source_url,mime_type,media_details"})
    return get("/wp-json/wp/v2/media?"+q,auth)
def match_media(filename,items):
    # Original chat photos are iPhone IMG_8712(1).jpeg etc.
    # WP uploads may normalize them to lowercase img_8712.jpg.
    x=re.fullmatch(r"IMG_(\d{4})(?:\(\d+\))?\.jpe?g",filename,re.I)
    if not x:raise RuntimeError("Unknown original photo filename "+filename)
    num=x.group(1)
    hits=[]
    for item in items:
        basename=urllib.parse.unquote(urllib.parse.urlsplit(item.get("source_url","")).path.rsplit("/",1)[-1])
        details=(item.get("media_details") or {}).get("file","").rsplit("/",1)[-1]
        variants={basename.lower(),details.lower()}
        if variants & {f"img_{num}.jpeg",f"img_{num}.jpg"}:
            if item.get("mime_type","")=="image/jpeg":hits.append(item)
    if len(hits)>1:
        print("AMBIGUOUS_UPLOADED_OWNER_PHOTO",filename,[i["id"] for i in hits],flush=True)
        return None
    return hits[0] if hits else None
def assemble(doc,items):
    photos=[];pending=[];blocks=[]
    for block in doc["blocks"]:
        m=SLOT.fullmatch(block)
        if not m:
            if "TSURIKUE_IMAGE:" in block:raise RuntimeError("Malformed photo slot "+block[:60])
            blocks.append(block);continue
        filename,alt,caption=m.groups()
        media=match_media(filename,items)
        if media is None:
            blocks.append(block);pending.append(filename)
            print("PHOTO_SLOT_PENDING_MEDIA",filename,flush=True)
            continue
        mid=media["id"]
        detail=media.get("media_details") or {}
        sized=(detail.get("sizes") or {}).get("large") or {}
        url=sized.get("source_url") or media.get("source_url")
        if not url or not url.startswith("https://tsurikue.com/wp-content/uploads/"):
            raise RuntimeError("Untrusted WordPress media URL "+filename)
        width=sized.get("width") or detail.get("width")
        height=sized.get("height") or detail.get("height")
        dim=f' width="{int(width)}" height="{int(height)}"' if width and height else ""
        size='large' if sized else 'full'
        block=(f'<!-- wp:image {{"id":{mid},"sizeSlug":"{size}","linkDestination":"none"}} -->\n'
               f'<figure class="wp-block-image size-{size}"><img src="{esc(url)}" '
               f'alt="{esc(alt)}" class="wp-image-{mid}"{dim}/>'
               f'<figcaption class="wp-element-caption">{esc(caption)}</figcaption></figure>\n'
               f'<!-- /wp:image -->')
        blocks.append(block);photos.append((filename,mid))
        print("EXACT_PHOTO_FOUND",filename,mid,flush=True)
    if len(photos)+len(pending)!=len(doc["images_expected"]):
        raise RuntimeError("User photo slots count mismatch")
    if [x[0] for x in photos]+pending:
        slots=[x for x in doc["blocks"] if SLOT.fullmatch(x)]
        names=[SLOT.fullmatch(x).group(1) for x in slots]
        if names!=doc["images_expected"]:raise RuntimeError("Owner image order altered")
    body="\n\n".join(blocks)
    if body.count("<!-- wp:table")!=1:raise RuntimeError("Route table missing")
    if body.count("<!-- wp:heading -->")!=7:raise RuntimeError("Unexpected H2 count")
    if re.search(r'<h1\b',body,re.I):raise RuntimeError("Do not duplicate H1")
    for t in ("6:00","10:00〜12:00","12枚で2,000円","甘エビを1,000円分","すし若","PLANT-5","50円","境港駅"):
        if t not in body:raise RuntimeError("Missing exact travel fact "+t)
    if "[blog_parts" in body or "px.a8.net" in body:raise RuntimeError("Unrequested affiliate detected")
    print("ARTICLE_CONTENT_AUDIT_OK",json.dumps({
        "slug":SLUG,"body_characters":len(body),"images_embedded":photos,
        "pending_photo_slots":pending,"first_hand_facts":True,
        "timeline_table":1,"post_status":"draft"
    },ensure_ascii=False),flush=True)
    return body,photos,pending
def main(mode):
    u=os.getenv("TSURIKUE_WP_USER");p=os.getenv("TSURIKUE_WP_APP_PASSWORD")
    if not u or not p:raise RuntimeError("WordPress access not connected")
    auth="Basic "+base64.b64encode((u+":"+p).encode()).decode()
    doc=json.loads(SOURCE.read_text(encoding="utf-8"))
    if (doc["slug"],doc["status"],doc["category_id"])!=(SLUG,"draft",CATEGORY):
        raise RuntimeError("Source metadata unexpected")
    if posts_by_slug(auth,SLUG):
        raise RuntimeError("Article with exact slug already exists. Stop before overwriting/duplicating")
    category=get(f"/wp-json/wp/v2/categories/{CATEGORY}?_fields=id,slug,name",auth)
    if category["id"]!=CATEGORY or category["slug"]!="sightseeing-leisure":
        raise RuntimeError("Category identity changed")
    station=direct_post(auth,4138)
    if (station["slug"],station["status"])!=("sakaiminato-station-sightseeing","publish"):
        raise RuntimeError("Linked station sightseeing article missing or unpublished")
    market=direct_post(auth,4045)
    if (market["slug"],market["status"])!=("sakaiminato-seafood-market","publish"):
        raise RuntimeError("Linked seafood article missing or unpublished")
    for query in ("小伊津","広島","境港","日帰り"):
        results=search_posts(auth,query)
        print("EXISTING_ARTICLE_SEARCH",json.dumps({
            "q":query,"candidates":[{"id":x["id"],"title":x["title"]["rendered"],
                    "slug":x["slug"],"status":x["status"]} for x in results[:25]]
        },ensure_ascii=False),flush=True)
        for item in results:
            title=re.sub(r"<[^>]+>","",item["title"]["rendered"])
            # Existing separate locality/history articles are fine, but avoid another
            # Hiroshima + Koizu + Sakaiminato actual route draft.
            if ("広島" in title and ("小伊津" in title or "境港" in title) and
                ("モデルコース" in title or "日帰り" in title)):
                raise RuntimeError("Possible duplicate route article "+str(item["id"])+": "+title)
    media=recent_media(auth)
    # One targeted backfill lookup for owner photos that moved beyond the latest
    # 100 media attachments, instead of quietly dropping a genuine uploaded photo.
    for filename in doc["images_expected"]:
        if match_media(filename,media) is None:
            digits=re.fullmatch(r"IMG_(\d{4})(?:\(\d+\))?\.jpe?g",filename,re.I)
            if digits:
                q=urllib.parse.urlencode({"context":"edit","search":digits.group(1),
                    "per_page":50,"_fields":"id,source_url,mime_type,media_details"})
                extras=get("/wp-json/wp/v2/media?"+q,auth)
                existing_ids={x["id"] for x in media}
                for item in extras:
                    if item["id"] not in existing_ids:
                        media.append(item);existing_ids.add(item["id"])
    body,embedded,pending=assemble(doc,media)
    print("WP_PRECHECK_OK",json.dumps({
        "related_post_id":4138,"related_status":station["status"],
        "post_slug_available":SLUG,"category":category["name"],
        "new_post_requested_status":"draft","photos_total":7,
        "photo_embedded":len(embedded),"photo_pending":len(pending)
    },ensure_ascii=False),flush=True)
    if mode=="check":return
    # Recheck duplicate after the PR was merged and right before the POST.
    if posts_by_slug(auth,SLUG):raise RuntimeError("Same-slug post appeared concurrently")
    payload={"title":doc["title"],"slug":SLUG,"status":"draft",
             "categories":[CATEGORY],"content":body,"excerpt":doc["excerpt"]}
    result=request("/wp-json/wp/v2/posts",auth,payload)[0]
    postid=result.get("id")
    if not isinstance(postid,int):raise RuntimeError("Created post ID not returned; inspect WordPress manually")
    saved=get("/wp-json/wp/v2/posts/"+str(postid)+"?context=edit&_fields=id,slug,status,title,content,categories,featured_media,excerpt",auth)
    if (saved["id"],saved["slug"],saved["status"])!=(postid,SLUG,"draft"):
        raise RuntimeError("Saved identity/status differs")
    if saved["title"]["raw"]!=doc["title"] or saved["content"]["raw"]!=body or saved["categories"]!=[CATEGORY]:
        raise RuntimeError("Saved title/content/category mismatch")
    if saved["featured_media"]!=0:raise RuntimeError("Unexpected cover image assigned")
    if saved["excerpt"]["raw"]!=doc["excerpt"]:raise RuntimeError("Excerpt mismatch")
    print("FINAL_NEW_DRAFT_VERIFIED",json.dumps({
        "post_id":postid,"slug":SLUG,"status":"draft","title":doc["title"],
        "photo_blocks":len(embedded),"photo_slots_pending":pending,
        "body_sha256":sha(body),
        "editor_url":SITE+"/wp-admin/post.php?post="+str(postid)+"&action=edit"
    },ensure_ascii=False),flush=True)
if __name__=="__main__":
    mode=sys.argv[1] if len(sys.argv)>1 else "check"
    if mode not in ("check","apply"):raise SystemExit("mode check|apply")
    main(mode)
