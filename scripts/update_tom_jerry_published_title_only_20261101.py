#!/usr/bin/env python3
"""Apply user-selected headline only to already published post 4282, with full safeguards.
The old permalink stays unchanged because a tested slug rename did not yield a 301.
"""
import base64,hashlib,html,json,os,re,sys,urllib.parse,urllib.request,time,urllib.error
from pathlib import Path
SITE="https://tsurikue.com";PID=4282
SLUG="tom-and-jerry-exhibition-hiroshima-2026"
OLD_TITLE="【広島】そごうのトムとジェリー展に行ってきた！見どころと限定グッズを現地レポ"
NEW_TITLE="トムとジェリー展に行ってきた！見どころ・所要時間・限定グッズを写真で紹介【広島そごう会場】"
BODY_SHA="4e91ed9241e30faae4d220ca2552f84e5ddef3acf4aa3f66e2acbce1f88b69d9"
MEDIA_IDS={4301,4314,4317,4315,4313,4308,4309,4305,4306,4304,4303,4300,4295,4286,4287}
def digest(x):return hashlib.sha256(x.encode()).hexdigest()
def auth():
    u=os.getenv("TSURIKUE_WP_USER");p=os.getenv("TSURIKUE_WP_APP_PASSWORD")
    if not u or not p:raise RuntimeError("STOP: no WordPress secrets")
    return "Basic "+base64.b64encode((u+":"+p).encode()).decode()
def api(path,token,body=None,headers=False):
    h={"Authorization":token,"Accept":"application/json","User-Agent":"tsurikue-title-only-safe-update/1.0"}
    if body is not None:h["Content-Type"]="application/json; charset=utf-8"
    req=urllib.request.Request(SITE+path,headers=h,method="POST" if body is not None else "GET",
        data=json.dumps(body,ensure_ascii=False).encode() if body is not None else None)
    for i in range(1 if body is not None else 3):
        try:
            with urllib.request.urlopen(req,timeout=60) as r:
                data=json.loads(r.read().decode())
                return (data,dict(r.headers)) if headers else data
        except (urllib.error.URLError,TimeoutError) as err:
            if body is not None or i==2:raise
            print("GET_RETRY",i+1,type(err).__name__,flush=True);time.sleep(i+2)
def getpost(t):
    q=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,content,categories,author,featured_media,link"})
    return api("/wp-json/wp/v2/posts/"+str(PID)+"?"+q,t)
def title(p):return html.unescape((p.get("title") or {}).get("raw") or "")
def raw(p):return (p.get("content") or {}).get("raw") or ""
def verify(p,expected_title):
    if (p.get("id"),p.get("slug"),p.get("status"))!=(PID,SLUG,"publish"):
        raise RuntimeError("STOP: expected published article identity changed")
    if title(p)!=expected_title or p.get("categories")!=[7] or int(p.get("featured_media") or 0)!=4301:
        raise RuntimeError("STOP: unexpected title, category, cover")
    if digest(raw(p))!=BODY_SHA:raise RuntimeError("STOP: article body edited since last audited version")
    images=re.findall(r'<!-- wp:image\b.*?<!-- /wp:image -->',raw(p),re.S)
    ids=[]
    for img in images:
        m=re.search(r'wp-image-(\d+)',img)
        if not m:raise RuntimeError("STOP: image ID not present")
        ids.append(int(m.group(1)))
    if len(ids)!=15 or len(set(ids))!=15 or set(ids)!=MEDIA_IDS:
        raise RuntimeError("STOP: changed photo set")
    if p.get("link")!="https://tsurikue.com/"+SLUG+"/":
        raise RuntimeError("STOP: permalink no longer canonical")
def counts(t):
    result={}
    for end in ["posts","pages"]:
        q=urllib.parse.urlencode({"context":"edit","status":"publish","per_page":"1","_fields":"id"})
        _,hdr=api("/wp-json/wp/v2/"+end+"?"+q,t,headers=True)
        result[end]=int(hdr.get("X-WP-Total",0))
    return result
def main(mode):
    if mode not in ("check","apply"):raise RuntimeError("check or apply")
    t=auth();before=getpost(t)
    print("LIVE_META",json.dumps({
        "id":before.get("id"),"slug":before.get("slug"),"status":before.get("status"),
        "title":title(before),"content_sha256":digest(raw(before)),
        "featured_media":before.get("featured_media"),"link":before.get("link")
    },ensure_ascii=False),flush=True)
    verify(before,OLD_TITLE)
    print("TITLE_ONLY_PREFLIGHT_OK",json.dumps({"id":PID,"status":"publish","slug_unchanged":SLUG,
      "new_title":NEW_TITLE,"photos":15,"featured_media":4301},ensure_ascii=False),flush=True)
    if mode=="check":return
    before_counts=counts(t)
    again=getpost(t);verify(again,OLD_TITLE)
    if any(again.get(k)!=before.get(k) for k in
       ("id","slug","status","title","content","categories","author","featured_media","link")):
        raise RuntimeError("STOP: concurrent editor change")
    try:
        response=api("/wp-json/wp/v2/posts/"+str(PID),t,{"title":NEW_TITLE})
        if response.get("id")!=PID:raise RuntimeError("STOP: unexpected write response")
    except (urllib.error.URLError,TimeoutError) as err:
        print("UNCERTAIN_POST_VERIFY_WITH_GET",type(err).__name__,flush=True)
    after=getpost(t);verify(after,NEW_TITLE)
    for field in ("id","slug","status","content","categories","author","featured_media","link"):
        if after.get(field)!=before.get(field):
            raise RuntimeError("STOP: unintended change in "+field)
    after_counts=counts(t)
    if after_counts!=before_counts:raise RuntimeError("STOP: published counts changed")
    result={"result":"TITLE_ONLY_SAVED_AND_VERIFIED","post_id":PID,"status":"publish",
        "old_title":OLD_TITLE,"new_title":NEW_TITLE,"retained_slug":SLUG,
        "new_slug_pending_redirect":"tom-and-jerry-exhibition-review",
        "photo_count":15,"featured_media":4301,"body_sha256":BODY_SHA,
        "public_before":before_counts,"public_after":after_counts}
    path=Path("reports/tom-jerry-title-only")
    path.mkdir(parents=True,exist_ok=True)
    (path/"result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("TITLE_ONLY_UPDATED_VERIFIED",json.dumps(result,ensure_ascii=False),flush=True)
if __name__=="__main__":main(sys.argv[1] if len(sys.argv)>1 else "check")
