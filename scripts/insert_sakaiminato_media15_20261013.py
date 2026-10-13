#!/usr/bin/env python3
"""Safely replace 15 invisible owner-photo slots with verified WordPress media blocks.

On PR: authenticated GET only, no posts/images modified.
On merge to main: content-only update to existing unpublished post ID 4138.
No new media uploads; retain author's alt text/captions and original image order.
"""
from __future__ import annotations
import os,sys,re,html,json,base64,hashlib,urllib.request,urllib.parse
from pathlib import Path

SITE="https://tsurikue.com"
POST_ID=4138
SLUG="sakaiminato-station-sightseeing"
DATA=Path("content/revisions/sakaiminato-station-20261013-info-tables.json")
BASE_SHA="a10d5b788729147686299b9db7c3dee476792857226e270a37c756563852aa21"
SLOTS=re.compile(r"<!-- TSURIKUE_IMAGE:([^|<>]+)\|([^|<>]+)\|([^<>]+) -->")
# Real live WP attachment IDs confirmed in authenticated 2026-10-13 read-only audit.
# WordPress normalized original IMG_NNNN.jpeg names to img_nnnn.jpg.
MATCH={
"8760":4113, "8758":4107, "8757":4108,
"8725":4127, "8726":4121, "8723":4129,
"8762":4110, "8728":4125, "8730":4126,
"8729":4117, "8732":4123, "8731":4118,
"8734":4119, "8738":4115, "8727":4116
}
def sha(s):return hashlib.sha256(s.encode("utf-8")).hexdigest()
def esc(s):return html.escape(s,quote=True)
def request(path,auth,data=None):
    headers={"Authorization":auth,"Accept":"application/json","User-Agent":"tsurikue-photos-4138/1.0"}
    if data is not None:headers["Content-Type"]="application/json; charset=utf-8"
    r=urllib.request.Request(SITE+path,headers=headers,
        data=json.dumps(data,ensure_ascii=False).encode("utf-8") if data is not None else None,
        method="POST" if data is not None else "GET")
    with urllib.request.urlopen(r,timeout=90) as f:return json.load(f),dict(f.headers)
def get_post(auth):
    q=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,content,author,categories,featured_media"})
    return request(f"/wp-json/wp/v2/posts/{POST_ID}?{q}",auth)[0]
def published_count(auth):
    q=urllib.parse.urlencode({"context":"edit","status":"publish","per_page":1,"_fields":"id"})
    return int(request("/wp-json/wp/v2/posts?"+q,auth)[1]["X-WP-Total"])
def get_media(auth):
    q=urllib.parse.urlencode({"context":"edit","per_page":100,"page":1,"orderby":"date","order":"desc",
        "_fields":"id,date,source_url,media_details,mime_type"})
    data=request("/wp-json/wp/v2/media?"+q,auth)[0]
    found={x["id"]:x for x in data if x["id"] in MATCH.values()}
    # When recent uploads push some older ones off page1, a single targeted GET for ID is allowed.
    for med_id in MATCH.values():
        if med_id not in found:
            q=urllib.parse.urlencode({"context":"edit",
                "_fields":"id,date,source_url,media_details,mime_type"})
            found[med_id]=request(f"/wp-json/wp/v2/media/{med_id}?{q}",auth)[0]
    return found
def photo(media,filename,alt,caption):
    name=re.match(r"IMG_(\d{4})(?:\(\d+\))?\.jpe?g$",filename,re.I)
    if not name:raise RuntimeError("Unknown user photo filename: "+filename)
    num=name.group(1)
    if num not in MATCH:raise RuntimeError("Image not approved: "+num)
    med_id=MATCH[num]; item=media.get(med_id)
    if not item:raise RuntimeError("Media ID disappeared: "+str(med_id))
    fullname=urllib.parse.unquote(urllib.parse.urlsplit(item.get("source_url","")).path.rsplit("/",1)[-1])
    expected_name=f"img_{num}.jpg"
    if fullname.lower()!=expected_name:
        raise RuntimeError("Filename/media ID mismatch: "+filename+" => "+fullname)
    if item.get("mime_type")!="image/jpeg":
        raise RuntimeError("Wrong MIME type for "+filename)
    full=item["source_url"]
    if not full.startswith(SITE+"/wp-content/uploads/2026/10/"):
        raise RuntimeError("Unexpected media path: "+full)
    meta=item.get("media_details") or {}
    sizes=meta.get("sizes") or {}
    large=sizes.get("large") or sizes.get("medium_large") or {}
    url=large.get("source_url") or full
    w=large.get("width") or meta.get("width")
    h=large.get("height") or meta.get("height")
    if not url.startswith(SITE+"/wp-content/uploads/"):
        raise RuntimeError("Unexpected resized image URL "+url)
    if w and h:
        dimensions=f' width="{int(w)}" height="{int(h)}"'
    else:dimensions=""
    markup=(
        f'<!-- wp:image {{"id":{med_id},"sizeSlug":"large","linkDestination":"none"}} -->\n'
        f'<figure class="wp-block-image size-large"><img src="{esc(url)}" alt="{esc(alt)}" '
        f'class="wp-image-{med_id}"{dimensions}/><figcaption class="wp-element-caption">{esc(caption)}</figcaption></figure>\n'
        f'<!-- /wp:image -->'
    )
    print("IMAGE_MATCH",filename,"attachment",med_id,"display",url,
          "dimensions",str(w)+"x"+str(h),flush=True)
    return markup,med_id
def transform(doc,med):
    raw="\n\n".join(doc["blocks"])
    expected=doc["images_expected"]
    images=[]
    def replace(m):
        filename,alt,caption=m.groups()
        markup,image_id=photo(med,filename,alt,caption)
        images.append((filename,image_id))
        return markup
    new=SLOTS.sub(replace,raw)
    if len(images)!=15 or len(set(x[1] for x in images))!=15:
        raise RuntimeError("15 unique article photos required")
    if [x[0] for x in images]!=expected:
        raise RuntimeError("Original owner photo sequence changed")
    if "TSURIKUE_IMAGE" in new or new.count("<!-- wp:image ")!=15 or new.count("<!-- /wp:image -->")!=15:
        raise RuntimeError("Placeholder conversion incomplete")
    if new.count("<!-- wp:table ")!=2 or new.count("<!-- /wp:table -->")!=2:
        raise RuntimeError("Station info tables modified")
    if re.findall(r'<h[123][^>]*>.*?</h[123]>',raw,re.S)!=re.findall(r'<h[123][^>]*>.*?</h[123]>',new,re.S):
        raise RuntimeError("Heading altered")
    if re.findall(r'href="([^"]+)"',raw)!=re.findall(r'href="([^"]+)"',new):
        raise RuntimeError("Affiliate/internal URL altered")
    stripped=SLOTS.sub("",raw)
    stripped_new=re.sub(r'<!-- wp:image \{.*?\} -->.*?<!-- /wp:image -->',"",new,flags=re.S)
    if stripped!=stripped_new:raise RuntimeError("Text or positioning other than photo slots changed")
    for text in ("一反もめん","猫娘","摩尼車","主印","境港水産物直売センター","みなとーる"):
        if text not in new:raise RuntimeError("First-hand or useful source lost: "+text)
    if re.search(r'<h1\b',new,re.I):raise RuntimeError("Unexpected duplicate H1")
    print("PREFLIGHT_IMAGE_BLOCKS_OK",json.dumps({
        "post_id":POST_ID,"image_count":len(images),"media_ids":[i for _,i in images],
        "before_chars":len(raw),"after_chars":len(new),
        "info_tables":2,"status_requested":"draft"
    },ensure_ascii=False),flush=True)
    return raw,new,images
def main(mode):
    u=os.getenv("TSURIKUE_WP_USER");p=os.getenv("TSURIKUE_WP_APP_PASSWORD")
    if not u or not p:raise RuntimeError("WP credentials missing")
    token="Basic "+base64.b64encode((u+":"+p).encode()).decode()
    doc=json.loads(DATA.read_text(encoding="utf-8"))
    if (doc["slug"],doc["status"],doc["category_id"])!=(SLUG,"draft",7):
        raise RuntimeError("Draft source metadata changed")
    current=get_post(token)
    if (current["id"],current["slug"],current["status"])!=(POST_ID,SLUG,"draft"):
        raise RuntimeError("Unexpected WordPress draft identity")
    if current["title"]["raw"]!=doc["title"] or current["categories"]!=[7]:
        raise RuntimeError("Title/category changed since edit")
    if sha(current["content"]["raw"])!=BASE_SHA:
        raise RuntimeError("Someone changed draft after prior audit; refusing overwrite. "+sha(current["content"]["raw"]))
    media=get_media(token)
    before,after,images=transform(doc,media)
    if current["content"]["raw"]!=before:
        raise RuntimeError("Expected saved text not an exact match")
    print("READ_ONLY_DRAFT_MEDIA_PREFLIGHT_OK",sha(before),sha(after),flush=True)
    if mode=="check":return
    check=get_post(token)
    if check["content"]["raw"]!=before or check["status"]!="draft":
        raise RuntimeError("Concurrent human edit; no WordPress write")
    public_before=published_count(token)
    tried=False
    try:
        tried=True
        request(f"/wp-json/wp/v2/posts/{POST_ID}",token,{"content":after})
        saved=get_post(token)
        for k in ("id","slug","status","title","categories","featured_media","author"):
            if saved[k]!=current[k]:raise RuntimeError("Protected WordPress field changed: "+k)
        if saved["content"]["raw"]!=after:raise RuntimeError("Saved Gutenberg text differs")
        rendered=saved["content"].get("rendered","")
        if rendered.count("<img ")!=15 and rendered.count("<img")!=15:
            raise RuntimeError("Rendered article image count not 15")
        for _,id in images:
            if f"wp-image-{id}" not in rendered:
                raise RuntimeError("Rendered image ID not found "+str(id))
        if rendered.count("<table")!=2:
            raise RuntimeError("Tables were lost in rendering")
        if published_count(token)!=public_before:
            raise RuntimeError("Published post count altered")
        print("FINAL_DRAFT_15_IMAGES_VERIFIED",json.dumps({
            "post_id":POST_ID,"status":"draft","article_image_blocks":15,
            "image_ids":[i for _,i in images],"table_count":2,
            "body_sha256":sha(after),"editor_url":SITE+"/wp-admin/post.php?post=4138&action=edit",
            "published_post_count_unchanged":public_before
        },ensure_ascii=False),flush=True)
    except Exception:
        if tried:
            try:
                now=get_post(token)
                if now["content"]["raw"]==after:
                    request(f"/wp-json/wp/v2/posts/{POST_ID}",token,{"content":before})
                    print("CONDITIONAL_ROLLBACK_COMPLETE",flush=True)
                else:print("ROLLBACK_SKIPPED_CONCURRENT_CHANGE",flush=True)
            except Exception as e:print("ROLLBACK_FAILED_MANUAL_REVIEW_NEEDED",str(e),flush=True)
        raise
if __name__=="__main__":
    mode=sys.argv[1] if len(sys.argv)>1 else "check"
    if mode not in ("check","apply"):raise SystemExit("check or apply")
    main(mode)
