#!/usr/bin/env python3
"""Surgically edit ONLY Gutenberg prose in existing published WP post 4240.

Do NOT change custom HTML, atlas JS/CSS, banners, links, sources, tables, headings
outside approved editorial changes, metadata, or media. A fully pinned preimage
checksum and last-minute WordPress reread prevent stale overwrites.
On PR: authenticated GET only; on main: guarded content-only edit.
"""
from __future__ import annotations
import base64,hashlib,json,os,re,sys,time,urllib.parse,urllib.request
from pathlib import Path

SITE="https://tsurikue.com"
POST_ID=4240
SOURCE=Path("content/revisions/japan-river-atlas-editorial-20261021.json")
# Filled after read-only PR preflight against the CURRENT WordPress article.
EXPECTED_BEFORE_SHA=""
def sha(s):return hashlib.sha256(s.encode("utf-8")).hexdigest()
def request(path,auth,payload=None):
    headers={"Authorization":auth,"Accept":"application/json","User-Agent":"tsurikue-river-atlas-editor/1.0"}
    if payload is not None:headers["Content-Type"]="application/json; charset=utf-8"
    req=urllib.request.Request(SITE+path,headers=headers,
        data=json.dumps(payload,ensure_ascii=False).encode("utf-8") if payload is not None else None,
        method="POST" if payload is not None else "GET")
    with urllib.request.urlopen(req,timeout=90) as resp:return json.load(resp)
def fetch(auth):
    query=urllib.parse.urlencode({"context":"edit",
        "_fields":"id,slug,status,title,content,excerpt,featured_media,categories,author,template,modified"})
    return request(f"/wp-json/wp/v2/posts/{POST_ID}?{query}",auth)
def custom_html(body):
    return re.findall(r'<!-- wp:html -->.*?<!-- /wp:html -->',body,re.S)
def structure(body,kind):
    return re.findall(rf'<!-- wp:{kind}(?: [^>]*)? -->.*?<!-- /wp:{kind} -->',body,re.S)
def apply_edit(raw,spec):
    if (spec["target_post_id"],spec["target_slug"],spec["status_expected"])!=(POST_ID,"japan-river-atlas","publish"):
        raise RuntimeError("Approval file mismatches WordPress target")
    edited=raw
    for idx,change in enumerate(spec["changes"]):
        old=change["old"];new=change["new"]
        if edited.count(old)!=1:
            raise RuntimeError(f"Source fragment #{idx} absent or ambiguous; no write. Count {edited.count(old)}")
        if not new:
            # Remove a whole Gutenberg paragraph plus one separating blank line.
            if edited.count(old+"\n\n")==1:
                edited=edited.replace(old+"\n\n","",1)
            elif edited.count("\n\n"+old)==1:
                edited=edited.replace("\n\n"+old,"",1)
            else:
                raise RuntimeError("Cannot safely remove paragraph "+str(idx))
        else:
            edited=edited.replace(old,new,1)
    if custom_html(raw)!=custom_html(edited) or len(custom_html(raw))!=2:
        raise RuntimeError("Atlas app, its JS, or 47-prefecture list modified")
    for kind in ("table","list","image","shortcode","columns","buttons"):
        if structure(raw,kind)!=structure(edited,kind):
            raise RuntimeError("Unexpected modification to protected Gutenberg block: "+kind)
    if re.findall(r'<a\b[^>]*href="([^"]+)"',raw)!=re.findall(r'<a\b[^>]*href="([^"]+)"',edited):
        raise RuntimeError("Existing links changed")
    if raw.count("<!-- wp:heading")!=edited.count("<!-- wp:heading"):
        raise RuntimeError("Heading count changed")
    if raw.count("<!-- wp:paragraph")-edited.count("<!-- wp:paragraph")!=3:
        raise RuntimeError("Expected exactly three redundant paragraphs removed")
    if len(edited)>=len(raw)+350:
        raise RuntimeError("No-go: prose grew too much rather than being subtracted")
    for text in ("祖父","ミミズ","クモ","ガン玉","ドロバイ","タカハヤ",
                 "アマゴ","爺ちゃん","4〜5歳","塩焼き","40代半ば","調査記録"):
        if text not in edited:raise RuntimeError("Primary memory or useful data missing "+text)
    if "広島・湯来町の渓流へ祖父" in edited or "ヤマメやアマゴを釣った" in edited:
        raise RuntimeError("Unverified fish identity/location still present")
    # This atlas article is an interactive tool; no forced line-breaks anywhere in
    # the human prose modifications.
    for change in spec["changes"]:
        if '<br' in change["new"].lower():
            raise RuntimeError("Forced HTML break introduced by editorial change")
    print("RIVER_PROSE_DIFF_PREFLIGHT_OK",json.dumps({
        "target_id":POST_ID,"status":"publish","removed_paragraphs":3,
        "before_chars":len(raw),"after_chars":len(edited),
        "custom_html_blocks_unchanged":2,"tool_ui_untouched":True,
        "links_unchanged":True,"tables_unchanged":True,
        "before_sha":sha(raw),"after_sha":sha(edited)
    },ensure_ascii=False),flush=True)
    return edited
def main(mode):
    username=os.environ.get("TSURIKUE_WP_USER")
    password=os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not username or not password:raise RuntimeError("No Wordpress credentials")
    auth="Basic "+base64.b64encode((username+":"+password).encode()).decode()
    spec=json.loads(SOURCE.read_text(encoding="utf-8"))
    existing=fetch(auth)
    if (existing["id"],existing["slug"],existing["status"])!=(POST_ID,spec["target_slug"],"publish"):
        raise RuntimeError("Live post id, slug or status changed")
    if existing["title"]["raw"]!=spec["title_expected"] or existing["featured_media"]!=4238:
        raise RuntimeError("Current article title or hero image changed")
    before=existing["content"]["raw"]
    after=apply_edit(before,spec)
    print("CURRENT_RIVER_ATLAS_WORDPRESS_SHA",sha(before),"modified",existing["modified"],flush=True)
    if mode=="check":
        if EXPECTED_BEFORE_SHA and sha(before)!=EXPECTED_BEFORE_SHA:
            raise RuntimeError("WordPress updated after preflight; revise proposed diff")
        return
    if not EXPECTED_BEFORE_SHA or sha(before)!=EXPECTED_BEFORE_SHA:
        raise RuntimeError("Preimage SHA not pinned or live editor changed. No update allowed")
    # Confirm exact content and protected metadata again immediately before write.
    just_before=fetch(auth)
    if just_before["content"]["raw"]!=before or just_before["modified"]!=existing["modified"]:
        raise RuntimeError("Human has edited WP after preflight; no update")
    saved=request(f"/wp-json/wp/v2/posts/{POST_ID}",auth,{"content":after})
    final=fetch(auth)
    for field in ("id","slug","status","title","excerpt","featured_media","categories","author","template"):
        if final[field]!=existing[field]:
            raise RuntimeError("Protected field changed: "+field)
    if final["content"]["raw"]!=after:
        raise RuntimeError("WP saved a different body; require manual review")
    if custom_html(final["content"]["raw"])!=custom_html(before):
        raise RuntimeError("Interactive river atlas tool modified")
    rendered=final["content"]["rendered"]
    for term in ("爺ちゃん、ドロバイも美味しいね！","河川図鑑","都道府県"):
        if term not in rendered:raise RuntimeError("Rendered text missing "+term)
    print("FINAL_RIVER_ATLAS_WORDPRESS_VERIFIED",json.dumps({
       "post_id":POST_ID,"slug":final["slug"],"status":final["status"],
       "title":final["title"]["raw"],"featured_media":final["featured_media"],
       "custom_html_blocks_unchanged":2,"removed_paragraphs":3,
       "content_sha256":sha(after),
       "editor_url":SITE+"/wp-admin/post.php?post=4240&action=edit"
    },ensure_ascii=False),flush=True)
if __name__=="__main__":
    mode=sys.argv[1] if len(sys.argv)>1 else "check"
    if mode not in ("check","apply"):raise SystemExit("check or apply")
    main(mode)
