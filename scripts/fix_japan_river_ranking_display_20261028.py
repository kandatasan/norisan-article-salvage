#!/usr/bin/env python3
"""Repair only the already-published river ranking CSS scope and click delegation.

The original ranking tables were placed BEFORE the separate CSS/JS custom HTML
div. Selectors and the listener therefore only applied INSIDE that empty div.
Read-only on pull requests, mutation only after merge and exact WP SHA guard.
"""
from __future__ import annotations
import base64
import hashlib
import importlib.util
import json
import os
import sys
import urllib.request
from pathlib import Path

SITE = "https://tsurikue.com"
POST_ID = 4240
EXPECTED = "a1e18dab2150da0c00c3e0759062da9f013a36707de3292d634f028cbf525361"
PATCH_MARK = "tsurikue-rank-visible-css-fix-20261028"
SOURCE = Path("content/revisions/japan-river-atlas-rankings-20261028.json")
PRIOR_SCRIPT = Path("scripts/add_japan_river_atlas_rankings_20261028.py")
CSS_FIX = r"""
/* tsurikue-rank-visible-css-fix-20261028: target the actual table OUTSIDE the old style container */
.tsu-rank-scroll {
 display:block!important;width:100%;max-width:100%;overflow-x:auto!important;
 overflow-y:hidden!important;-webkit-overflow-scrolling:touch;
 overscroll-behavior-x:contain;scrollbar-gutter:stable;
 border:1px solid #dae6e3;border-radius:12px;background:#fff;
 margin:12px 0 18px;
}
.tsu-rank-scroll *{box-sizing:border-box}
.tsu-rank-scroll table.tsu-rank-table {
 display:table!important;width:max-content!important;min-width:710px!important;
 table-layout:auto!important;border-collapse:separate!important;
 border-spacing:0!important;margin:0!important;border:0!important;
 background:#fff;font-size:14px!important;
}
.tsu-rank-scroll .tsu-rank-table th,
.tsu-rank-scroll .tsu-rank-table td {
 display:table-cell!important;padding:11px 12px!important;line-height:1.5!important;
 text-align:left!important;vertical-align:middle!important;
 white-space:nowrap!important;word-break:keep-all!important;
 overflow-wrap:normal!important;hyphens:none!important;
 border:0!important;border-bottom:1px solid #e6eeeb!important;
}
.tsu-rank-scroll .tsu-rank-table thead th {
 background:#ecf5f3!important;color:#244c53!important;font-weight:800!important;
}
.tsu-rank-scroll .tsu-rank-table tbody tr:last-child > * {border-bottom:0!important}
.tsu-rank-scroll .tsu-rank-table tr > th:first-child {
 position:sticky!important;left:0!important;z-index:2;
 width:136px!important;min-width:136px!important;max-width:136px!important;
 white-space:nowrap!important;background:#fff!important;
 box-shadow:3px 0 6px -5px #344;
}
.tsu-rank-scroll .tsu-rank-table thead tr > th:first-child{
 background:#ecf5f3!important;z-index:3;
}
.tsu-rank-scroll .tsu-rank-no{
 display:inline-block;min-width:23px;margin-right:4px;
 font-size:11px;color:#647879;font-weight:650;
}
.tsu-rank-scroll .tsu-rank-table a.tsurikue-river-rank-link{
 white-space:nowrap!important;word-break:keep-all!important;
 font-weight:750;color:#226c77;text-decoration:underline;text-underline-offset:3px;
}
.tsu-rank-scroll .tsu-rank-value{font-variant-numeric:tabular-nums;font-weight:750}
.tsu-rank-scroll .tsu-pref{min-width:310px}
.tsu-rank-scroll table.tsu-rank-table.quality{min-width:560px!important}
.tsu-rank-scroll table.tsu-rank-table.quality .tsu-pref{min-width:160px}
@media(max-width:600px){
 .tsu-rank-scroll .tsu-rank-table th,.tsu-rank-scroll .tsu-rank-table td{
  padding:10px 9px!important;font-size:13px!important;
 }
 .tsu-rank-scroll .tsu-rank-table tr > th:first-child{
  width:128px!important;min-width:128px!important;max-width:128px!important;
 }
}
"""
def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()
def old_component():
    spec=importlib.util.spec_from_file_location("atlas_ranking",PRIOR_SCRIPT)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source=module.make_block(json.loads(SOURCE.read_text(encoding="utf-8")))
    opening='<!-- wp:html -->\n<div class="tsurikue-river-rankings-20261028" id="tsurikue-river-rankings-20261028">'
    if source.count(opening)!=1:raise RuntimeError("Source ranking style container absent")
    return source[source.index(opening):].strip()
def patch_component(old):
    if PATCH_MARK in old:raise RuntimeError("Source component unexpectedly already patched")
    if old.count("</style>")!=1:raise RuntimeError("Style tag count mismatch")
    s=old.replace("</style>",CSS_FIX+"\n</style>",1)
    expected1='container.addEventListener("click",function(event){'
    expected2='const a=event.target.closest("a[data-river]");\n  if(!a||!container.contains(a))return;'
    if s.count(expected1)!=1 or s.count(expected2)!=1:
        raise RuntimeError("Expected original incorrectly scoped listener absent")
    s=s.replace(expected1,'document.addEventListener("click",function(event){',1)
    s=s.replace(expected2,'''const a=event.target.closest("a.tsurikue-river-rank-link[data-river]");
  if(!a||!a.closest(".tsu-rank-scroll"))return;''',1)
    return s
def fetch(auth):
    url=SITE+f"/wp-json/wp/v2/posts/{POST_ID}?context=edit&_fields=id,slug,status,title,excerpt,content,featured_media,categories,author,template,modified"
    req=urllib.request.Request(url,headers={
        "Authorization":auth,"Accept":"application/json",
        "User-Agent":"tsurikue-ranking-display-fix-20261028/1.0"})
    with urllib.request.urlopen(req,timeout=90) as response:
        return json.load(response)
def write(auth,content):
    data=json.dumps({"content":content},ensure_ascii=False).encode("utf-8")
    req=urllib.request.Request(SITE+f"/wp-json/wp/v2/posts/{POST_ID}",
       data=data,method="POST",headers={
       "Authorization":auth,"Accept":"application/json",
       "Content-Type":"application/json; charset=utf-8",
       "User-Agent":"tsurikue-ranking-display-fix-20261028/1.0"})
    with urllib.request.urlopen(req,timeout=90) as response:
        return json.load(response)
def check_meta(post):
    if (post["id"],post["slug"],post["status"],post["title"]["raw"],post["featured_media"])!=(
        POST_ID,"japan-river-atlas","publish",
        "日本の河川図鑑｜全国の河川名・水系・生き物を都道府県から探す",4238):
        raise RuntimeError("Unexpected WordPress target or metadata")
    body=post["content"]["raw"]
    for t in ("tsurikue-river-atlas-inline-v26","tsurikue-pref-list","ドロバイ","タカハヤ"):
        if t not in body:raise RuntimeError("Protected original atlas section absent")
    if body.count('class="tsu-rank-scroll"')!=3:
        raise RuntimeError("Expected precisely three already published ranking tables")
    if body.count('class="tsurikue-river-rank-link"')!=33:
        raise RuntimeError("Expected precisely 33 existing linked river names")
    return body
def transform(raw):
    old=old_component()
    new=patch_component(old)
    if PATCH_MARK in raw:
        if raw.count(PATCH_MARK)!=1 or raw.count(new)!=1:
            raise RuntimeError("Already patched but WordPress markup differs")
        return raw,"ALREADY_FIXED"
    if raw.count(old)!=1:raise RuntimeError("Original published CSS+JS block not exact; no write")
    result=raw.replace(old,new,1)
    if result.replace(new,old,1)!=raw:raise RuntimeError("Patch changed any other article content")
    if raw.count("<!-- wp:html -->")!=result.count("<!-- wp:html -->"):
        raise RuntimeError("Protected Gutenberg HTML count changed")
    return result,"FIX_STICKY_SCROLL_AND_CLICK"
def main(mode):
    if mode not in ("check","apply"):raise RuntimeError("check/apply only")
    user=os.environ.get("TSURIKUE_WP_USER")
    pw=os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not pw:raise RuntimeError("No WordPress credentials")
    auth="Basic "+base64.b64encode((user+":"+pw).encode()).decode()
    before_post=fetch(auth)
    before=check_meta(before_post)
    after,action=transform(before)
    print("RANKING_DISPLAY_FIX_PREFLIGHT",json.dumps({
        "post_id":POST_ID,"status":before_post["status"],"action":action,
        "before_sha256":sha(before),"after_sha256":sha(after),
        "before_modified":before_post["modified"],"old_tool_preserved":True,
        "tables":3,"links":33,"changed_chars":len(after)-len(before)
    },ensure_ascii=False),flush=True)
    if action!="ALREADY_FIXED" and sha(before)!=EXPECTED:
        raise RuntimeError("Current WP body SHA is not the audited published version")
    if mode=="check" or action=="ALREADY_FIXED":return
    immediate=fetch(auth)
    if (immediate["modified"]!=before_post["modified"]
        or check_meta(immediate)!=before):
        raise RuntimeError("Concurrent WordPress change")
    write(auth,after)
    final=fetch(auth)
    for field in ("id","slug","status","title","excerpt","featured_media","categories","author","template"):
        if final[field]!=before_post[field]:
            raise RuntimeError("Protected WordPress field changed: "+field)
    if final["content"]["raw"]!=after:
        raise RuntimeError("WordPress did not preserve exact CSS+JS patch")
    for token in (PATCH_MARK,'document.addEventListener("click"',
                  "white-space:nowrap!important",
                  "position:sticky!important"):
        if token not in final["content"]["rendered"]:
            raise RuntimeError("Rendered article is missing "+token)
    print("RANKING_DISPLAY_FIX_WORDPRESS_VERIFIED",json.dumps({
        "post_id":final["id"],"slug":final["slug"],"status":final["status"],
        "featured_media":final["featured_media"],"sha256":sha(after),
        "untouched_original_article":True,"sticky_css":True,"click_delegation":True
    },ensure_ascii=False),flush=True)
if __name__=="__main__":
    main(sys.argv[1] if len(sys.argv)>1 else "check")
