#!/usr/bin/env python3
"""Set the already verified IMG_9053 WordPress media as featured image of unpublished draft 4282."""
import base64,hashlib,json,os,sys,urllib.parse,urllib.request,urllib.error,html,time
from pathlib import Path
SITE="https://tsurikue.com";PID=4282;MEDIA_ID=4301
SLUG="tom-and-jerry-exhibition-hiroshima-2026"
TITLE="【広島】そごうのトムとジェリー展に行ってきた！見どころと限定グッズを現地レポ"
BODY_SHA="0bc144dcbcdc7c76afedf87f1f15bead24b347323034facd83678e6e29dbd3e2"
def auth():
    u=os.getenv("TSURIKUE_WP_USER"); p=os.getenv("TSURIKUE_WP_APP_PASSWORD")
    if not u or not p:raise RuntimeError("Missing WP secrets")
    return "Basic "+base64.b64encode((u+":"+p).encode()).decode()
def request(path,token,payload=None):
    headers={"Authorization":token,"Accept":"application/json","User-Agent":"tsurikue-tom-jerry-featured-image/1.0"}
    method="POST" if payload is not None else "GET"
    if payload is not None:headers["Content-Type"]="application/json; charset=utf-8"
    data=json.dumps(payload).encode() if payload is not None else None
    req=urllib.request.Request(SITE+path,data=data,headers=headers,method=method)
    tries=1 if method=="POST" else 3
    for i in range(tries):
        try:
            with urllib.request.urlopen(req,timeout=55) as r:return json.loads(r.read().decode())
        except (urllib.error.URLError,TimeoutError) as err:
            if i==tries-1:raise
            print("GET_RETRY",type(err).__name__,i+1,flush=True);time.sleep(i+2)
def post(token):
    q=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,categories,featured_media,author,content"})
    return request("/wp-json/wp/v2/posts/"+str(PID)+"?"+q,token)
def validate(post,expected_featured):
    if (post.get("id"),post.get("slug"),post.get("status"))!=(PID,SLUG,"draft"):
        raise RuntimeError("STOP: unexpected post/status/slug")
    if html.unescape((post.get("title") or {}).get("raw") or "")!=TITLE:
        raise RuntimeError("STOP: unexpected title")
    if post.get("categories")!=[7] or int(post.get("featured_media") or 0)!=expected_featured:
        raise RuntimeError("STOP: changed category or featured media")
    body=(post.get("content") or {}).get("raw") or ""
    if hashlib.sha256(body.encode()).hexdigest()!=BODY_SHA or body.count('<!-- wp:image ')!=15:
        raise RuntimeError("STOP: WordPress article no longer equals previously verified 15-photo draft")
    if 'class="wp-image-4301"' not in body:
        raise RuntimeError("STOP: proposed cover is not in article content")
    return body
def main(mode):
    if mode not in ("check","apply"):raise RuntimeError("check or apply")
    token=auth()
    before=post(token)
    validate(before,0)
    media=request("/wp-json/wp/v2/media/4301?context=edit&_fields=id,mime_type,source_url",token)
    url=media.get("source_url") or ""
    parsed=urllib.parse.urlsplit(url)
    if (int(media.get("id") or 0)!=MEDIA_ID or media.get("mime_type")!="image/jpeg" or
        parsed.hostname!="tsurikue.com" or not parsed.path.lower().endswith("/img_9053.jpg")):
        raise RuntimeError("STOP: featured media identity does not match user's original photo")
    print("COVER_PREFLIGHT_OK",PID,MEDIA_ID,url,flush=True)
    if mode=="check":return
    try:
        request("/wp-json/wp/v2/posts/"+str(PID),token,{"featured_media":MEDIA_ID})
    except (urllib.error.URLError,TimeoutError) as err:
        print("POST_UNCERTAIN_CHECKING",type(err).__name__,flush=True)
    after=post(token);validate(after,MEDIA_ID)
    for field in ("id","slug","status","title","categories","author","content"):
        if after.get(field)!=before.get(field):raise RuntimeError("STOP: unrelated WP draft field changed: "+field)
    out=Path("reports/tom-jerry-featured-image");out.mkdir(parents=True,exist_ok=True)
    report={"post_id":PID,"slug":SLUG,"status":"draft","featured_media_before":0,"featured_media_after":MEDIA_ID,
        "photo_source":url,"article_sha256":BODY_SHA,"wp_media_uploads":0,"other_post_updates":0}
    (out/"result.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print("COVER_APPLIED_AND_VERIFIED",json.dumps(report,ensure_ascii=False),flush=True)
if __name__=="__main__":main(sys.argv[1] if len(sys.argv)>1 else "check")
