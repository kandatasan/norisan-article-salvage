#!/usr/bin/env python3
"""Replace 19 scoped CTN blog-part buttons with untouched A8 official text material 002.

Read-only preflight on PR; guarded WordPress writes only on main.
Does not edit shared blog parts, other ads, site theme or user-provided A8 markup.
"""
from __future__ import annotations
import base64, hashlib, json, os, re, sys, urllib.parse, urllib.request
from pathlib import Path

SITE="https://tsurikue.com"
OUT=Path("reports/ctn-official-002-20261110")
POSTS={
2222:("ux-resale",1),2240:("ux-mitsumori",1),2329:("ux300h",0),2517:("ux-koukai",1),
2948:("lexus-ux-used",1),2956:("lexus-ux-price",1),2962:("lexus-ux-discount",1),
3570:("lexus-ux-emotional-explorer",1),3601:("lexus-ux250h-used-vs-ux300h",1),
3604:("lexus-ux-vs-nx",1),3606:("lexus-ux-vs-lbx",1),3608:("lexus-lbx-regret",0),
3611:("lexus-lbx-options",1),3614:("car-sell-high",1),3835:("goodbuy",1),
3863:("lexus-lbx-cheap",1),3936:("lexus-lbx-price",1),3945:("lexus-lbx-used",1),
3965:("tanto-6years-review",0),3973:("tanto-used-best-year",1),
4004:("tanto-model-history",0),3767:("landcruiser-fj-price",1),
3816:("landcruiser-fj-cheap",1)
}
OLD_SC=re.compile(r'<!-- wp:shortcode -->\s*\[blog_parts id="(?:2184|3788|2846)"\]\s*<!-- /wp:shortcode -->')
TOP='tsq-ctn-cta-20261110 top'
BOTTOM='tsq-ctn-cta-20261110 bottom'
NEW_MARKER='tsq-ctn-official-002-20261110'
A8='<a href="https://px.a8.net/svt/ejp?a8mat=3Z8YF4+7VEGL6+5I4S+5YRHE" rel="nofollow">【CTN一括車査定】</a>\n<img border="0" width="1" height="1" src="https://www11.a8.net/0.gif?a8mat=3Z8YF4+7VEGL6+5I4S+5YRHE" alt="">'
META=("id","slug","status","title","featured_media","categories","author")

STYLE="""<style>
.tsq-ctn-official-002-20261110{max-width:480px;width:100%;margin:0 auto;text-align:center}
.tsq-ctn-official-002-20261110 .tsq-ctn-free-lead{font-size:15px;font-weight:700;line-height:1.55;color:#29466e;margin:0 auto 9px}
.tsq-ctn-official-002-20261110 > a{
display:block!important;box-sizing:border-box!important;width:100%!important;
padding:15px 16px!important;border:1px solid #11703a!important;
border-radius:10px!important;background:#17864c!important;color:#fff!important;
text-decoration:none!important;text-align:center!important;
font-size:17px!important;line-height:1.6!important;font-weight:700!important;
box-shadow:0 3px 0 rgba(8,76,39,.18);transition:background .15s ease
}
.tsq-ctn-official-002-20261110 > a:hover{background:#116e3b!important;color:#fff!important}
.tsq-ctn-official-002-20261110 > a:focus-visible{outline:3px solid #f8ac3a!important;outline-offset:3px}
@media(max-width:480px){
.tsq-ctn-official-002-20261110 > a{font-size:16px!important;padding:15px 10px!important}
}
</style>"""

NEW_BLOCK=('<!-- wp:html -->\n'+STYLE+'\n'
           +'<div class="'+NEW_MARKER+'">\n'
           +'<div class="tsq-ctn-free-lead">無料で試してみる</div>\n'
           +A8+'\n</div>\n<!-- /wp:html -->')

def digest(s):return hashlib.sha256(s.encode("utf-8")).hexdigest()
def request(path,token,payload=None):
    headers={"Authorization":token,"Accept":"application/json","User-Agent":"tsurikue-ctn-official-002/20261110"}
    if payload is not None:headers["Content-Type"]="application/json; charset=utf-8"
    req=urllib.request.Request(SITE+path,headers=headers,
        method="POST" if payload is not None else "GET",
        data=json.dumps(payload,ensure_ascii=False).encode("utf-8") if payload is not None else None)
    with urllib.request.urlopen(req,timeout=60) as res:return json.load(res),dict(res.headers)
def token():
    user=os.environ.get("TSURIKUE_WP_USER")
    pw=os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not pw:raise RuntimeError("Missing WP credentials")
    return "Basic "+base64.b64encode((user+":"+pw).encode()).decode()
def fetch(pid,auth):
    q=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,featured_media,categories,author,content"})
    return request("/wp-json/wp/v2/posts/"+str(pid)+"?"+q,auth)[0]
def raw(p):return p["content"]["raw"]
def total(auth):
    _,h=request("/wp-json/wp/v2/posts?status=publish&per_page=1&_fields=id",auth)
    return int(h["X-WP-Total"])
def transform(pid,current,expected):
    old_count=len(OLD_SC.findall(current))
    if old_count!=expected:raise RuntimeError(f"{pid}: shortcode count {old_count} != {expected}")
    if current.count(TOP)!=expected or current.count(BOTTOM)!=expected:
        raise RuntimeError(f"{pid}: expected top/bottom wrapper count {expected}")
    if NEW_MARKER in current:raise RuntimeError(f"{pid}: new CTA appears already applied")
    if expected==0:return current
    m=OLD_SC.search(current)
    if not m:raise RuntimeError(f"{pid}: missing shortcode")
    # Scope to the CTN copy sandwich.  Do not change unrelated shortcodes anywhere.
    before=current[:m.start()]
    after=current[m.end():]
    if TOP not in before[-900:] or BOTTOM not in after[:900]:
        raise RuntimeError(f"{pid}: shortcode not between approved CTN microcopies")
    revised=before+NEW_BLOCK+after
    if revised.replace(NEW_BLOCK,m.group(0),1)!=current:
        raise RuntimeError(f"{pid}: modification outside CTA button")
    if revised.count(A8)!=1:raise RuntimeError(f"{pid}: official A8 material not intact")
    if len(OLD_SC.findall(revised))!=0:raise RuntimeError(f"{pid}: old CTN shortcodes left")
    if revised.count(NEW_MARKER)!=STYLE.count(NEW_MARKER)+1:
        raise RuntimeError(f"{pid}: unexpected new CTA markup count")
    for token in ("<!-- wp:","<!-- /wp:"):
        if revised.count(token)!=current.count(token):
            raise RuntimeError(f"{pid}: Gutenberg block count drift")
    return revised

def main(mode):
    if mode not in ("check","apply"):raise RuntimeError("Expected check or apply")
    auth=token()
    start_total=total(auth)
    ready=[]; unchanged=[]
    for pid,(slug,expected) in POSTS.items():
        p=fetch(pid,auth)
        if (p["id"],p["slug"],p["status"])!=(pid,slug,"publish"):
            raise RuntimeError(f"{pid}: WordPress identity/status drift")
        proposed=transform(pid,raw(p),expected)
        if expected:ready.append((pid,p,proposed))
        else:unchanged.append((pid,p))
    if len(ready)!=19 or len(unchanged)!=4:raise RuntimeError("Expected 19 CTA + 4 no-CTA posts")
    OUT.mkdir(parents=True,exist_ok=True)
    record={"stage":"PREFLIGHT_OK","total_posts":23,"target_ctas":19,"unchanged_posts":4,
            "published_total_before":start_total,
            "targets":[{"id":pid,"slug":p["slug"],"old_sha":digest(raw(p)),
                        "new_sha":digest(new)} for pid,p,new in ready],
            "no_cta_post_ids":[pid for pid,_ in unchanged]}
    (OUT/"preflight.json").write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("CTN_OFFICIAL_002_PREFLIGHT_OK",len(ready),"no CTA",len(unchanged),flush=True)
    if mode=="check":return
    written=[]
    try:
        for pid,p,new in ready:
            latest=fetch(pid,auth)
            if digest(raw(latest))!=digest(raw(p)) or any(latest[k]!=p[k] for k in META):
                raise RuntimeError(f"{pid}: concurrent edit (stop)")
            # Mark as possibly written BEFORE submitting for error/uncertain response safety.
            written.append((pid,p,new))
            request("/wp-json/wp/v2/posts/"+str(pid),auth,{"content":new})
            saved=fetch(pid,auth)
            if raw(saved)!=new or any(saved[k]!=p[k] for k in META):
                raise RuntimeError(f"{pid}: WordPress saved content/meta mismatch")
            rendered=saved["content"]["rendered"]
            if (NEW_MARKER not in rendered or "無料で試してみる" not in rendered
                    or "【CTN一括車査定】" not in rendered
                    or "www11.a8.net/0.gif" not in rendered):
                raise RuntimeError(f"{pid}: WordPress rendered ad tag missing")
            print("CTN_OFFICIAL_002_SAVED_VERIFIED",pid,p["slug"],flush=True)
        for pid,p in unchanged:
            latest=fetch(pid,auth)
            if digest(raw(latest))!=digest(raw(p)) or any(latest[k]!=p[k] for k in META):
                raise RuntimeError(f"{pid}: non-target post changed during update")
        if total(auth)!=start_total:raise RuntimeError("Published total changed")
        record["stage"]="SAVED_AND_VERIFIED"
        record["posts_verified"]=len(written)
        (OUT/"result.json").write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("CTN_OFFICIAL_002_ALL_SAVED_VERIFIED",len(written),flush=True)
    except Exception:
        for pid,p,new in reversed(written):
            try:
                latest=fetch(pid,auth)
                if digest(raw(latest))==digest(new):
                    request("/wp-json/wp/v2/posts/"+str(pid),auth,{"content":raw(p)})
                    print("CTN_OFFICIAL_002_ROLLBACK",pid,flush=True)
                else:
                    print("CTN_OFFICIAL_002_MANUAL_RECOVERY_REQUIRED",pid,flush=True)
            except Exception as e:
                print("CTN_OFFICIAL_002_ROLLBACK_FAILED",pid,type(e).__name__,flush=True)
        raise

if __name__=="__main__":main(sys.argv[1] if len(sys.argv)>1 else "check")
