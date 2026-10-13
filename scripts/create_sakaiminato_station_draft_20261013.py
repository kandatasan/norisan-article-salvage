#!/usr/bin/env python3
"""Safely create ONE new Sakaiminato WP draft with matched user photos when present.

PR event only previews via authenticated GET.
Main push creates a DRAFT only, never publishes or overwrites another editor's changes.
Images missing from WP media are left as non-rendered comments, not guessed.
"""
from __future__ import annotations
import base64, hashlib, html, json, os, re, sys, urllib.parse, urllib.request
from pathlib import Path

SITE = "https://tsurikue.com"
SOURCE = Path("content/drafts/sakaiminato-station-sightseeing-20261013.json")
SLOT = re.compile(r'<!-- TSURIKUE_IMAGE:([^|<>]+)\|([^|<>]+)\|([^<>]+) -->')
def http(path, auth, payload=None):
    headers={"Authorization":auth,"Accept":"application/json","User-Agent":"tsurikue-sakaiminato-draft/1.0"}
    if payload is not None:headers["Content-Type"]="application/json; charset=utf-8"
    req=urllib.request.Request(SITE+path,headers=headers,
        data=json.dumps(payload,ensure_ascii=False).encode("utf-8") if payload is not None else None,
        method="POST" if payload is not None else "GET")
    with urllib.request.urlopen(req,timeout=60) as r:
        return json.load(r), dict(r.headers)
def get(path,auth):
    return http(path,auth)[0]
def public_count(auth):
    q=urllib.parse.urlencode({"status":"publish","per_page":1,"context":"edit","_fields":"id"})
    return int(http("/wp-json/wp/v2/posts?"+q,auth)[1]["X-WP-Total"])
def existing_slug(slug,auth):
    q=urllib.parse.urlencode({"context":"edit","status":"any","slug":slug,"per_page":30,
                            "_fields":"id,slug,status,title"})
    return get("/wp-json/wp/v2/posts?"+q,auth)
def select_media(filename,auth):
    stem=filename.rsplit(".",1)[0]
    q=urllib.parse.urlencode({"context":"edit","search":stem,"per_page":50,
        "_fields":"id,source_url,media_details,title,mime_type"})
    items=get("/wp-json/wp/v2/media?"+q,auth)
    matches=[]
    for item in items:
        url=item.get("source_url","")
        basename=urllib.parse.unquote(urllib.parse.urlsplit(url).path.rsplit("/",1)[-1])
        details=item.get("media_details") or {}
        detail_name=str(details.get("file") or "").rsplit("/",1)[-1]
        if filename==basename or filename==detail_name:
            if item.get("mime_type","").startswith("image/"):matches.append(item)
    if len(matches)>1:
        raise RuntimeError(f"{filename}: multiple exact WordPress media matches")
    return matches[0] if matches else None
def build(obj,auth):
    blocks=obj["blocks"]
    pieces=[];used=[];missing=[]
    for block in blocks:
        matches=list(SLOT.finditer(block))
        if not matches:
            pieces.append(block);continue
        if len(matches)!=1 or matches[0].span()!=(0,len(block)):
            raise RuntimeError("Image slot must occupy one independent block")
        filename,alt,caption=matches[0].groups()
        item=select_media(filename,auth)
        if item is None:
            # Keep an invisible slot for later matched-media insertion.
            pieces.append(block);missing.append(filename)
            print("PHOTO_NOT_YET_IN_WORDPRESS",filename,flush=True)
            continue
        mid=item["id"];src=item["source_url"]
        esc=lambda x:html.escape(x,quote=True)
        img=(f'<!-- wp:image {{"id":{mid},"sizeSlug":"full","linkDestination":"none"}} -->\n'
             f'<figure class="wp-block-image size-full"><img src="{esc(src)}" alt="{esc(alt)}" '
             f'class="wp-image-{mid}"/><figcaption class="wp-element-caption">{esc(caption)}</figcaption></figure>\n'
             f'<!-- /wp:image -->')
        pieces.append(img);used.append((filename,mid))
        print("EXACT_MEDIA_MATCH",filename,mid,flush=True)
    return "\n\n".join(pieces),used,missing

def execute(mode):
    user=os.getenv("TSURIKUE_WP_USER");password=os.getenv("TSURIKUE_WP_APP_PASSWORD")
    if not user or not password:raise RuntimeError("WordPress credentials missing")
    auth="Basic "+base64.b64encode((user+":"+password).encode()).decode()
    obj=json.loads(SOURCE.read_text(encoding="utf-8"))
    if obj["status"]!="draft" or obj["category_id"]!=7 or obj["slug"]!="sakaiminato-station-sightseeing":
        raise RuntimeError("Unexpected target draft metadata")
    category=get("/wp-json/wp/v2/categories/7?_fields=id,slug,name",auth)
    if category["id"]!=7 or category["slug"]!="sightseeing-leisure":
        raise RuntimeError("Existing category has changed; no writes")
    body,used,missing=build(obj,auth)
    if len(used)+len(missing)!=len(obj["images_expected"]):
        raise RuntimeError("Image slot count differs from manifest")
    if sorted([i[0] for i in used]+missing)!=sorted(obj["images_expected"]):
        raise RuntimeError("Image slot filenames differ from manifest")
    if any(word not in body for word in ["鏡の間","猫娘","一反もめん","境港水産物直売センター","水木しげるロード"]):
        raise RuntimeError("Draft lost principal firsthand content")
    existing=existing_slug(obj["slug"],auth)
    if existing:raise RuntimeError("Slug already exists, no overwrite: "+json.dumps(existing,ensure_ascii=False))
    before=public_count(auth)
    print("PREFLIGHT_OK",obj["slug"],"category",category["name"],"chars",len(body),
          "images_embedded",len(used),"images_pending",len(missing),"published_before",before,flush=True)
    if mode=="check":return
    # Recheck slug and count immediately before authoring.
    if existing_slug(obj["slug"],auth):raise RuntimeError("Concurrent post with same slug, abort")
    payload={"title":obj["title"],"slug":obj["slug"],"status":"draft",
             "categories":[7],"content":body}
    created,_=http("/wp-json/wp/v2/posts",auth,payload)
    pid=created.get("id")
    if not isinstance(pid,int):raise RuntimeError("WordPress did not provide new post ID")
    print("WORDPRESS_DRAFT_CREATED",pid,obj["slug"],flush=True)
    fields="id,slug,status,title,content,categories,featured_media"
    saved=get(f"/wp-json/wp/v2/posts/{pid}?context=edit&_fields={fields}",auth)
    if (saved["id"],saved["slug"],saved["status"])!=(pid,obj["slug"],"draft"):
        raise RuntimeError("Draft identity or status failed verification")
    if saved["title"]["raw"]!=obj["title"] or saved["content"]["raw"]!=body:
        raise RuntimeError("WordPress raw title/content differs; manual audit required")
    if 7 not in saved["categories"] or saved["featured_media"]!=0:
        raise RuntimeError("Unexpected category/featured media")
    after=public_count(auth)
    if before!=after:raise RuntimeError("Published post count changed unexpectedly")
    print("FINAL_VERIFIED_DRAFT",json.dumps({
        "id":pid,"slug":saved["slug"],"status":saved["status"],"title":obj["title"],
        "post_url":SITE+"/?p="+str(pid),"embedded_images":used,"pending_images":missing,
        "content_sha256":hashlib.sha256(body.encode()).hexdigest(),"public_count_unchanged":before
    },ensure_ascii=False),flush=True)

if __name__=="__main__":
    mode=sys.argv[1] if len(sys.argv)>1 else "check"
    if mode not in ("check","apply"):raise SystemExit("mode must be check|apply")
    execute(mode)
