#!/usr/bin/env python3
"""Use already uploaded WordPress photos in existing draft 4282. Never upload media."""
import base64, hashlib, html, io, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image, ImageOps

SITE="https://tsurikue.com"; PID=4282; SLUG="tom-and-jerry-exhibition-hiroshima-2026"
TITLE="【広島】そごうのトムとジェリー展に行ってきた！見どころと限定グッズを現地レポ"
PREV_SHA="744480aa4b8d064d948b8d8f50a59288542629c27ecbc7f8055943c2f728fa69"
PLAN=Path("editorial/tom-and-jerry-hiroshima-2026/photo-plan.json")
SLOT=re.compile(r"<!-- TSURIKUE_IMAGE:([^|<>]+)\|([^|<>]+)\|([^<>]+) -->")
# Original owner photos: (filename, original dHash64, aspect ratio).
# The ordered sequence matches the current WordPress article's photo slots.
REF=[
 ("IMG_9053.jpeg","4523232727672f2b",1.333),
 ("IMG_9031(1).jpeg","9982cacccada8483",1.333),
 ("IMG_9032.jpeg","0f0f9595b5b71b19",1.333),
 ("IMG_9033(1).jpeg","1811a325352305e5",1.333),
 ("IMG_9034.jpeg","27373633373139f7",1.333),
 ("IMG_9040.jpeg","1755a3b7a3b3371f",1.333),
 ("IMG_9037.jpeg","072327272b838697",1.333),
 ("IMG_9042.jpeg","f9f97b4b67272f8f",0.750),
 ("IMG_9046.jpeg","3f3f1e16a696562e",1.333),
 ("IMG_9047.jpeg","1f5a19956565174d",1.333),
 ("IMG_9048.jpeg","e23a5a960e0e04dc",1.333),
 ("IMG_9052.jpeg","e1c5256727c76331",1.333),
 ("IMG_9058.jpeg","dcde83756f665313",1.333),
 ("IMG_9063.jpeg","92c2961a8b531198",1.333),
 ("IMG_9068.jpeg","dab6b1b9f1e9d9d3",1.333)
]
def hashtext(x): return hashlib.sha256(x.encode()).hexdigest()
def credential():
    u=os.getenv("TSURIKUE_WP_USER");p=os.getenv("TSURIKUE_WP_APP_PASSWORD")
    if not u or not p: raise RuntimeError("Missing WordPress secrets")
    return "Basic "+base64.b64encode((u+":"+p).encode()).decode()
def get_bytes(url,auth,tries=3):
    headers={"User-Agent":"tsurikue-tom-jerry-wp-media/1.0"}
    if urllib.parse.urlsplit(url).hostname=="tsurikue.com":headers["Authorization"]=auth
    for n in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=45) as r:
                return r.read()
        except (urllib.error.URLError,TimeoutError) as e:
            if n==tries-1:raise
            print("GET_RETRY",n+1,type(e).__name__,flush=True);time.sleep(2*(n+1))
def get_json(path,auth):return json.loads(get_bytes(SITE+path,auth).decode())
def post_json(path,data,auth):
    req=urllib.request.Request(SITE+path,data=json.dumps(data,ensure_ascii=False).encode(),
        headers={"Authorization":auth,"Content-Type":"application/json; charset=utf-8",
                 "Accept":"application/json","User-Agent":"tsurikue-tom-jerry-wp-media/1.0"},method="POST")
    with urllib.request.urlopen(req,timeout=65) as r:return json.loads(r.read().decode())
def wp_post(auth):
    q=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,content,categories,featured_media,author"})
    return get_json("/wp-json/wp/v2/posts/"+str(PID)+"?"+q,auth)
def raw(p):return (p.get("content") or {}).get("raw") or ""
def validate_post(p):
    if (p.get("id"),p.get("slug"),p.get("status"))!=(PID,SLUG,"draft"):
        raise RuntimeError("STOP: incorrect post ID/slug/status")
    if html.unescape((p.get("title") or {}).get("raw") or "")!=TITLE:
        raise RuntimeError("STOP: post title changed")
    if p.get("categories")!=[7] or int(p.get("featured_media") or 0)!=0:
        raise RuntimeError("STOP: category/featured media changed")
    if hashtext(raw(p))!=PREV_SHA:
        raise RuntimeError("STOP: content differs from audited draft; do not overwrite human edit")
def get_media(auth):
    found=[]
    for page in range(1,7):
        q=urllib.parse.urlencode({"context":"edit","per_page":"100","page":str(page),
          "orderby":"date","order":"desc","media_type":"image",
          "_fields":"id,date,slug,source_url,mime_type,media_details"})
        try:rows=get_json("/wp-json/wp/v2/media?"+q,auth)
        except urllib.error.HTTPError as e:
            if page>1 and e.code==400:break
            raise
        if not isinstance(rows,list):raise RuntimeError("Invalid media list")
        found+=rows
        if len(rows)<100:break
    return found
def norm(x):return re.sub(r"[^a-z0-9]","",x.lower())
def dhash(data):
    im=ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("L")
    ratio=im.width/im.height
    im=im.resize((9,8),Image.Resampling.LANCZOS);px=list(im.getdata());bits=0
    for y in range(8):
        for x in range(8):bits=(bits<<1)|(px[y*9+x]>px[y*9+x+1])
    return bits,ratio
def choose(ref,index,rows,auth,cache):
    filename,hx,ratio=ref
    number=re.search(r"IMG_(\d+)",filename,re.I).group(1)
    prefix="img"+number
    packaged=norm("tom-jerry-hiroshima-2026-%02d"%index)
    ranked=[]
    for row in rows:
        url=row.get("source_url") or "";path=urllib.parse.urlsplit(url)
        if path.hostname!="tsurikue.com" or "/wp-content/uploads/" not in path.path:continue
        if row.get("mime_type")!="image/jpeg":continue
        basename=urllib.parse.unquote(path.path.rsplit("/",1)[-1])
        name=norm(basename.rsplit(".",1)[0])
        if not (name.startswith(prefix) or name.startswith(packaged)):continue
        mid=int(row["id"])
        if mid not in cache:cache[mid]=dhash(get_bytes(url,auth))
        fingerprint,aspect=cache[mid]
        ranked.append(((int(hx,16)^fingerprint).bit_count(),abs(aspect-ratio),mid,basename,url))
    if not ranked:raise RuntimeError("STOP: WordPress media not found for "+filename)
    ranked.sort(key=lambda r:(r[0],r[1],-r[2]))
    dist,ar,mid,basename,url=ranked[0]
    if dist>13 or ar>0.06:raise RuntimeError("STOP: image data mismatch "+filename+" distance="+str(dist))
    if len(ranked)>1:
        other=ranked[1]
        if other[0]<=13 and other[0]-dist<3 and cache[other[2]]!=cache[mid]:
            raise RuntimeError("STOP: ambiguous image candidates "+filename)
    return {"source":filename,"id":mid,"filename":basename,"url":url,"dhash_distance":dist}
def replace(raw_body,slots,byname):
    result=raw_body
    for filename,alt,caption in slots:
        m=byname[filename]
        element=('<!-- wp:image {"id":'+str(m["id"])+',"sizeSlug":"full","linkDestination":"none"} -->\n'
          '<figure class="wp-block-image size-full"><img src="'+html.escape(m["url"],quote=True)+'" alt="'
          +html.escape(alt,quote=True)+'" class="wp-image-'+str(m["id"])+'"/>'
          '<figcaption class="wp-element-caption">'+html.escape(caption)+'</figcaption></figure>\n<!-- /wp:image -->')
        marker="<!-- TSURIKUE_IMAGE:"+filename+"|"+alt+"|"+caption+" -->"
        if result.count(marker)!=1:raise RuntimeError("STOP: photo marker mismatch "+filename)
        result=result.replace(marker,element,1)
    if SLOT.findall(result) or result.count("<!-- wp:image ")!=len(slots):
        raise RuntimeError("STOP: photo slots or blocks invalid")
    return result
def main(mode):
    if mode not in ("check","apply"):raise RuntimeError("Use check or apply")
    plan=json.loads(PLAN.read_text(encoding="utf-8"))
    names=[r[0] for r in REF]
    if len(names)!=15 or plan.get("selected_photos")!=names:raise RuntimeError("STOP: selected photo list drift")
    auth=credential()
    before=wp_post(auth);validate_post(before);body=raw(before)
    slots=SLOT.findall(body)
    if [x[0] for x in slots]!=names:raise RuntimeError("STOP: article image slot list drift")
    print("DRAFT_PREFLIGHT_OK",PID,"draft",len(slots),hashtext(body),flush=True)
    rows=get_media(auth);print("WP_MEDIA_ROWS",len(rows),flush=True)
    cache={};mapped=[choose(ref,i,rows,auth,cache) for i,ref in enumerate(REF,1)]
    if len({m["id"] for m in mapped})!=15:raise RuntimeError("STOP: duplicate media ID")
    for m in mapped:
        print("MATCH",json.dumps({k:v for k,v in m.items() if k!="url"},ensure_ascii=False),flush=True)
    new=replace(body,slots,{m["source"]:m for m in mapped})
    out=Path("reports/tom-jerry-existing-media");out.mkdir(parents=True,exist_ok=True)
    report={"post_id":PID,"slug":SLUG,"status":"draft","media_count":15,
      "old_content_sha256":hashtext(body),"target_content_sha256":hashtext(new),
      "media":[{k:v for k,v in m.items() if k!="url"} for m in mapped]}
    (out/"preflight.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    if mode=="check":
        print("READ_ONLY_MEDIA_MATCH_SUCCEEDED",flush=True);return
    second=wp_post(auth);validate_post(second)
    if raw(second)!=body or any(second.get(k)!=before.get(k) for k in
       ("id","slug","status","title","featured_media","categories","author")):
        raise RuntimeError("STOP: concurrent WordPress change")
    try:result=post_json("/wp-json/wp/v2/posts/"+str(PID),{"content":new},auth)
    except (urllib.error.URLError,TimeoutError) as e:
        print("POST_UNCERTAIN_VERIFYING",type(e).__name__,flush=True)
        result=None # Never automatically retry an uncertain write.
    if result and (result.get("id")!=PID or result.get("status")!="draft"):
        raise RuntimeError("STOP: unexpected response to update")
    after=wp_post(auth)
    for key in ("id","slug","status","title","featured_media","categories","author"):
        if after.get(key)!=before.get(key):raise RuntimeError("STOP: metadata changed "+key)
    if raw(after)!=new:raise RuntimeError("STOP: updated WordPress content not verified")
    report.update({"action":"UPDATE_EXISTING_MEDIA_ONLY","after_content_sha256":hashtext(raw(after)),
                   "media_uploads":0,"wordpress_writes":1})
    (out/"result.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print("DRAFT_IMAGES_INSERTED_VERIFIED",PID,len(mapped),hashtext(raw(after)),flush=True)
if __name__=="__main__":main(sys.argv[1] if len(sys.argv)>1 else "check")
