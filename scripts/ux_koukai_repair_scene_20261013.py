#!/usr/bin/env python3
"""Guarded 2-point fix on published UX owner review, PR read-only / main apply."""
from __future__ import annotations
import base64, hashlib, json, os, re, sys, urllib.parse, urllib.request

SITE="https://tsurikue.com"
PID=2517
SLUG="ux-koukai"
# Independent read-only audit after PR #632, 2026-10-13.
BASE_SHA="9fd6c5254c1e61bfed1a6f6f7aaab389a16ebd8e6182d2eff973816693241096"
MARKER="<!-- tsurikue-internal-links:lexus-20260830:ux-koukai -->"

def sha(s):return hashlib.sha256(s.encode("utf-8")).hexdigest()
def one(s,old,new,what):
    count=s.count(old)
    if count!=1:raise RuntimeError(f"{what}: expected exactly once, got {count}")
    return s.replace(old,new,1)

def transform(old):
    before=old
    broken=('<!-- wp:paragraph -->\n'
            '<p>レクサスUXの後席は狭いです。<br>\n'
            'ここは、かばえません</p>\n\n'
            +MARKER+'\n'
            '<!-- /wp:paragraph --><!-- wp:paragraph -->')
    repaired=('<!-- wp:paragraph -->\n'
              '<p>レクサスUXの後席は狭いです。<br>ここは、かばえません。</p>\n'
              '<!-- /wp:paragraph -->\n\n'
              '<!-- wp:paragraph -->')
    new=one(old,broken,repaired,"stray editorial marker / malformed block")
    image_start=('<!-- wp:image {"id":2190,"sizeSlug":"large",'
                 '"linkDestination":"none","className":"u-mb-ctrl u-mb-5"} -->')
    scenic=('<!-- wp:paragraph -->\n'
            '<p>高知県の仁淀川・水晶淵。<br>'
            '狭い山道を抜けた先で出会えたのが、この景色です。</p>\n'
            '<!-- /wp:paragraph -->\n\n')
    new=one(new,image_start,scenic+image_start,"Niyodo photo setup")
    new=one(new,'alt="雪の残る道を走るレクサスUX" class="wp-image-2190"',
            'alt="高知県・仁淀川の水晶淵の風景" class="wp-image-2190"',
            "Niyodo photo wrong alt")
    new=one(new,
            '<p>UXを一言でいうなら、<strong>小さな高級車</strong>です。</p>',
            '<p>こういう場所へ行くとき、UXの取り回しの良さは本当にありがたい。<br>'
            '静かで乗り心地もいい。<strong>小さな高級車</strong>という言葉がしっくりきます。</p>',
            "photo-to-UX bridge")
    if MARKER in new:raise RuntimeError("hidden marker remains in content")
    # No URL, original photographic evidence, affiliates, headlines or shortcodes removed.
    for pat in (
        r'wp-image-\d+',r'<img\b[^>]*src="([^"]+)"',
        r'<a\b[^>]*href="([^"]+)"',
        r'\[blog_parts id="(\d+)"\]',
        r'<h[123]\b[^>]*>.*?</h[123]>'
    ):
        if re.findall(pat,new,re.I|re.S)!=re.findall(pat,before,re.I|re.S):
            raise RuntimeError("Protected source changed: "+pat)
    if new.count('<!-- wp:paragraph -->')!=old.count('<!-- wp:paragraph -->')+1:
        raise RuntimeError("Paragraph open count changed unexpectedly")
    if new.count('<!-- /wp:paragraph -->')!=old.count('<!-- /wp:paragraph -->')+1:
        raise RuntimeError("Paragraph close count changed unexpectedly")
    for phrase in ("荷室でテトリスが始まります","文句はある。でも私はUXが好きだった",
                   "レクサスUXの後部座席レビュー","ここは、かばえません。",
                   "狭い山道を抜けた先で出会えたのが、この景色です。"):
        if phrase not in new:raise RuntimeError("Expected primary text missing: "+phrase)
    print("EDITORIAL_DIFF",json.dumps({
        "post":PID,"slug":SLUG,
        "before_characters":len(old),"after_characters":len(new),
        "original_image_count":len(re.findall(r'wp-image-\d+',before)),
        "after_image_count":len(re.findall(r'wp-image-\d+',new)),
        "comment_removed":True,"image_2190_alt_corrected":True,
        "paragraph_repair":True,"scene_and_car_benefit_linked":True
    },ensure_ascii=False),flush=True)
    return new

def request(path,auth,payload=None):
    hdr={"Authorization":auth,"Accept":"application/json","User-Agent":"tsurikue-ux-scene-editor/1.0"}
    if payload is not None:hdr["Content-Type"]="application/json; charset=utf-8"
    req=urllib.request.Request(
        SITE+path,headers=hdr,method="POST" if payload is not None else "GET",
        data=json.dumps(payload,ensure_ascii=False).encode() if payload is not None else None)
    with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)

def fetch(auth):
    q=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,content,featured_media,author,categories"})
    return request(f"/wp-json/wp/v2/posts/{PID}?{q}",auth)

def main(mode):
    u=os.getenv("TSURIKUE_WP_USER");p=os.getenv("TSURIKUE_WP_APP_PASSWORD")
    if not u or not p:raise RuntimeError("WordPress credentials absent")
    auth="Basic "+base64.b64encode((u+":"+p).encode()).decode()
    row=fetch(auth)
    if (row["id"],row["slug"],row["status"])!=(PID,SLUG,"publish"):
        raise RuntimeError("Unexpected post identity or status")
    old=row["content"]["raw"]
    if sha(old)!=BASE_SHA:
        raise RuntimeError("Live body changed from 2026-10-13 audit SHA; no write")
    new=transform(old)
    print("READ_ONLY_PREFLIGHT_OK",sha(old),sha(new),flush=True)
    if mode=="check":return
    latest=fetch(auth)
    if sha(latest["content"]["raw"])!=BASE_SHA:
        raise RuntimeError("Concurrent editor update; refuse overwrite")
    try:
        request(f"/wp-json/wp/v2/posts/{PID}",auth,{"content":new})
        saved=fetch(auth)
        for k in ("id","slug","status","title","featured_media","author","categories"):
            if saved[k]!=row[k]:raise RuntimeError("Protected WP field modified: "+k)
        if saved["content"]["raw"]!=new:raise RuntimeError("WordPress body not exact")
        rendered=saved["content"].get("rendered","")
        if MARKER in rendered or "狭い山道を抜けた先で出会えた" not in rendered:
            raise RuntimeError("Rendered WordPress verification failed")
        print("LIVE_WORDPRESS_VERIFIED",PID,SLUG,"status=publish","post_sha",sha(new),flush=True)
    except Exception:
        try:
            current=fetch(auth)
            if sha(current["content"]["raw"])==sha(new):
                request(f"/wp-json/wp/v2/posts/{PID}",auth,{"content":old})
                print("CONDITIONAL_ROLLBACK_OK",flush=True)
        except Exception as e:
            print("CONDITIONAL_ROLLBACK_FAILED",str(e),flush=True)
        raise

if __name__=="__main__":
    mode=sys.argv[1] if len(sys.argv)>1 else "check"
    if mode not in ("check","apply"):raise SystemExit("mode must be check|apply")
    main(mode)
