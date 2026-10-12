#!/usr/bin/env python3
"""Final CTA relevancy fix: remove only unwanted CTN shortcode from three FJ experience articles.
Never edits issued A8 creatives. WP exact SHA+metadata guard; preserve 20 other CTN posts.
"""
from __future__ import annotations
import base64,hashlib,html,json,os,re,sys,urllib.parse,urllib.request
from pathlib import Path
import importlib.util

SITE="https://tsurikue.com"
TARGETS={
3774:("landcruiser-fj-review","ed2fac0d6c00e14e8b1eadc13f4bb6261f74e84bb9ced2f3fa6774ed3fbd6b27"),
3777:("landcruiser-fj-rear-seat","94ecf1d71a5e46d1744a58070b42dcf448d25a7c4dcf25726f33f47e5bb2dc05"),
3778:("landcruiser-fj-drawbacks","498d0992f9e815751972ab670f1902d6b1801f0efcce270756a59b35c9cd7613")}
LINK_BLOCK=re.compile(r'<!-- wp:shortcode -->\s*\[blog_parts id="3788"\]\s*<!-- /wp:shortcode -->',re.S)
REVIEW_P=re.compile(r'<!-- wp:paragraph(?:\s+\{[^\n]*\})? -->\s*<p[^>]*>.*?乗り換えでFJを考えているなら、今の車の査定額も先に見ておくと予算を組みやすいです。.*?</p>\s*<!-- /wp:paragraph -->',re.S)
OUT=Path("reports/ctn-fj-final-20261012")
def sha(x):return hashlib.sha256(x.encode()).hexdigest()
def req(path,auth,payload=None):
    headers={"Authorization":auth,"User-Agent":"tsurikue-ctn-fj-final-20261012","Accept":"application/json"}
    if payload is not None:headers["Content-Type"]="application/json; charset=utf-8"
    request=urllib.request.Request(SITE+path,headers=headers,method="GET" if payload is None else "POST",
        data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode())
    with urllib.request.urlopen(request,timeout=45) as response:
        return json.loads(response.read().decode()),dict(response.headers)
def fetch(pid,auth):
    q=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,content,featured_media,categories,author"})
    return req(f"/wp-json/wp/v2/posts/{pid}?{q}",auth)[0]
def count(auth):
    q=urllib.parse.urlencode({"context":"edit","status":"publish","per_page":1,"_fields":"id"})
    return int(req("/wp-json/wp/v2/posts?"+q,auth)[1]["X-WP-Total"])
def render(original,pid,slug):
    if len(LINK_BLOCK.findall(original))!=1:raise RuntimeError(f"{slug}: expected exactly one FJ CTN 3788 blog part")
    new=LINK_BLOCK.sub("",original,count=1)
    if pid==3774:
        if len(REVIEW_P.findall(new))!=1:
            raise RuntimeError(f"{slug}: lead-in CTN paragraph count does not equal one")
        new=REVIEW_P.sub("",new,count=1)
    if "[blog_parts id=\"3788\"]" in new:raise RuntimeError(f"{slug}: CTN shortcode remains")
    # No external A8 URLs, headings, media, or remaining blog parts may change.
    for patt in (r'<a\b[^>]*href=["\'][^"\']+',r'<h[123]\b[^>]*>.*?</h[123]>',
                 r'<img\b[^>]*>',r'\bwp-image-\d+',r'\[blog_parts id="\d+"\]'):
        original_items=re.findall(patt,original,re.S|re.I)
        new_items=re.findall(patt,new,re.S|re.I)
        if patt.endswith(r'\d+"\]'):
            original_items=[s for s in original_items if s!='[blog_parts id="3788"]']
        if original_items!=new_items:raise RuntimeError(f"{slug}: protected links/headings/media changed: {patt}")
    if new==original:raise RuntimeError("unexpected noop")
    return new
def main(mode):
    user=os.getenv("TSURIKUE_WP_USER");pwd=os.getenv("TSURIKUE_WP_APP_PASSWORD")
    if not user or not pwd:raise RuntimeError("Missing WP credentials")
    auth="Basic "+base64.b64encode(f"{user}:{pwd}".encode()).decode()
    total=count(auth)
    spec=importlib.util.spec_from_file_location("ctn_review","scripts/ctn_h2_declutter_20261012.py")
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    before={}
    for pid,slug in mod.POSTS.items():
        row=fetch(pid,auth)
        if (row["id"],row["slug"],row["status"])!=(pid,slug,"publish"):
            raise RuntimeError(f"{slug}: id/slug/status guard failure")
        before[pid]=row
    proposal={}
    for pid,(slug,expected) in TARGETS.items():
        row=before[pid];raw=row["content"]["raw"]
        if sha(raw)!=expected:raise RuntimeError(f"{slug}: current content SHA differs from prior browser audit")
        proposal[pid]=render(raw,pid,slug)
        print("PREPARED",pid,slug,len(raw),"=>",len(proposal[pid]),flush=True)
    for pid,row in before.items():
        raw=proposal.get(pid,row["content"]["raw"])
        n=len(mod.ad_sections(raw))
        if n>3:raise RuntimeError(f"{mod.POSTS[pid]}: {n} affiliate-bearing H2s > 3")
    print("PREFLIGHT_OK three removals + other 20 preserved; published posts",total,flush=True)
    if mode=="check":return
    done=[]
    try:
        for pid,(slug,expected) in TARGETS.items():
            current=fetch(pid,auth)
            if sha(current["content"]["raw"])!=expected or current["status"]!="publish":
                raise RuntimeError(f"{slug}: content changed since preflight")
            done.append(pid)
            req(f"/wp-json/wp/v2/posts/{pid}",auth,{"content":proposal[pid]})
            latest=fetch(pid,auth)
            if latest["content"]["raw"]!=proposal[pid]:
                raise RuntimeError(f"{slug}: WordPress raw mismatch")
            for key in ("id","slug","status","title","featured_media","categories","author"):
                if latest[key]!=before[pid][key]:
                    raise RuntimeError(f"{slug}: protected WP field changed {key}")
            if "3Z8YF4" in latest["content"]["raw"] or '[blog_parts id="3788"]' in latest["content"]["raw"]:
                raise RuntimeError(f"{slug}: CTN link still in raw")
            print("APPLIED_VERIFIED",pid,slug,flush=True)
        for pid,orig in before.items():
            post=fetch(pid,auth)
            original=proposal.get(pid,orig["content"]["raw"])
            if post["content"]["raw"]!=original or post["status"]!="publish":
                raise RuntimeError(f"post {pid}: final 23-post audit mismatch")
            if len(mod.ad_sections(original))>3:
                raise RuntimeError(f"post {pid}: too many affiliate H2s")
            print("FINAL_23_OK",pid,mod.POSTS[pid],flush=True)
        if count(auth)!=total:raise RuntimeError("published count modified")
    except Exception:
        for pid in reversed(done):
            try:
                if sha(fetch(pid,auth)["content"]["raw"])==sha(proposal[pid]):
                    req(f"/wp-json/wp/v2/posts/{pid}",auth,{"content":before[pid]["content"]["raw"]})
                    print("ROLLED_BACK",pid,flush=True)
            except Exception as err:print("ROLLBACK_FAILED",pid,str(err),flush=True)
        raise
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"result.json").write_text(json.dumps({"changed_posts":list(TARGETS),
          "published_post_count":total,"final_qa":23,"status":"success",
          "changed_hashes":{str(pid):sha(proposal[pid]) for pid in TARGETS}},indent=2)+"\n",encoding="utf-8")
    print("FINAL_SUCCESS three FJ CTN-only blocks removed, all 23 audited",flush=True)
if __name__=="__main__":
    mode=sys.argv[1] if len(sys.argv)>1 else "check"
    if mode not in ("check","apply"):raise SystemExit("Usage check|apply")
    main(mode)
