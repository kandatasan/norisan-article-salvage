#!/usr/bin/env python3
"""Surgically add Google satellite iframe to EXISTING draft 4138.
PR: authenticated read-only preflight. main: conditional write and live verification.
Never publishes. No Google Maps screen capture, only interactive Google Maps itself.
"""
from __future__ import annotations
import os,sys,json,re,hashlib,base64,urllib.parse,urllib.request,html

SITE="https://tsurikue.com"
ID=4138
SLUG="sakaiminato-station-sightseeing"
ORIGINAL_SHA="cf15161e42d382529e971f21693567efd9d3a02067d365b143e8c8951102137f"
OLD='<p>偶然そう見えるのか、狙って作ったのかは分かりません。でも、一度そう思うともう一反もめんにしか見えない。</p>'
PLACE="〒684-0004 鳥取県境港市大正町駅前公園"
MAP_URL="https://www.google.com/maps?"+urllib.parse.urlencode({
    "q":PLACE,"t":"k","z":"18","output":"embed"
})
GOOGLE_LINK="https://maps.app.goo.gl/XUF1NJtfrGU5KehYA?g_st=ic"
MAP_BLOCK=(
    '<!-- wp:html -->\n'
    '<iframe title="境港駅前公園の一反もめんを航空写真で見る（Googleマップ）" '
    'src="'+html.escape(MAP_URL,quote=True)+'" '
    'width="100%" height="420" '
    'style="width:100%;max-width:100%;border:0;border-radius:8px;" '
    'loading="lazy" referrerpolicy="strict-origin-when-cross-origin" '
    'allowfullscreen></iframe>\n'
    '<!-- /wp:html -->'
)
NEWPARA=(
    '<p>実はこれ、偶然じゃない。境港市が一反もめんを意識して整備した道なんです。'
    '2020年には目と手まで追加したそう。'
    '<strong>上空から見ないと分からない遊び心！</strong>'
    '<br><a href="'+html.escape(GOOGLE_LINK,quote=True)+'" target="_blank" rel="noopener">'
    'Googleマップで拡大して見る</a></p>'
)
# City explanation: https://sirabee.com/2026/09/22/20163584582/
def sha(s):return hashlib.sha256(s.encode("utf-8")).hexdigest()
def edit(body):
    if body.count(OLD)!=1:
        raise RuntimeError("Unexpected count of old Ittanmomen paragraph; refuse edit")
    if "Googleマップで拡大して見る" in body:
        raise RuntimeError("Existing Maps embed detected; refuse duplicate")
    new=body.replace(OLD,MAP_BLOCK+"\n\n<!-- wp:paragraph -->\n"+NEWPARA+"\n<!-- /wp:paragraph -->",1)
    # This replaces content INSIDE original paragraph block, so need remove duplicated wrapper.
    # Keep the existing comment pair around the original paragraph by using a block-level replace.
    old_block="<!-- wp:paragraph -->\n"+OLD+"\n<!-- /wp:paragraph -->"
    new_block=MAP_BLOCK+"\n\n<!-- wp:paragraph -->\n"+NEWPARA+"\n<!-- /wp:paragraph -->"
    if body.count(old_block)!=1:
        raise RuntimeError("Unexpected WordPress paragraph/block shape; stop")
    new=body.replace(old_block,new_block,1)
    for pat in (
      r'wp-image-\d+',r'<img\b[^>]*src="([^"]+)"',
      r'<!-- wp:table.*?<!-- /wp:table -->',
      r'<!-- wp:heading.*?<!-- /wp:heading -->'
    ):
        if re.findall(pat,body,re.I|re.S)!=re.findall(pat,new,re.I|re.S):
            raise RuntimeError("Unexpected photo/table/heading change: "+pat)
    original_links=re.findall(r'href="([^"]+)"',body)
    changed_links=re.findall(r'href="([^"]+)"',new)
    if changed_links!=original_links[:4]+[html.escape(GOOGLE_LINK,quote=True)]+original_links[4:]:
        # Precise list insertion location is not stable across unrelated earlier content,
        # so fall back to confirming one added link and original order unchanged.
        remainder=changed_links.copy()
        try:remainder.remove(html.escape(GOOGLE_LINK,quote=True))
        except ValueError:raise RuntimeError("Map external link absent")
        if remainder!=original_links:raise RuntimeError("Existing content links changed")
    if len(re.findall(r'<iframe\b',new))!=len(re.findall(r'<iframe\b',body))+1:
        raise RuntimeError("Expected exactly one new iframe")
    if new.count("<!-- wp:html -->")!=body.count("<!-- wp:html -->")+1:
        raise RuntimeError("Missing Gutenberg custom HTML block")
    if new.count("<!-- /wp:html -->")!=body.count("<!-- /wp:html -->")+1:
        raise RuntimeError("Unbalanced custom HTML block")
    for phrase in ("一反もめんみたいな形","鏡の間","摩尼車","主印","みなとーる"):
        if phrase not in new:raise RuntimeError("Owner's travel experience missing "+phrase)
    return new
def request(path,auth,payload=None):
    hdr={"Authorization":auth,"Accept":"application/json","User-Agent":"tsurikue-maps-ittanmomen/1.0"}
    if payload is not None:hdr["Content-Type"]="application/json; charset=utf-8"
    req=urllib.request.Request(SITE+path,headers=hdr,
      data=json.dumps(payload,ensure_ascii=False).encode("utf-8") if payload is not None else None,
      method="POST" if payload is not None else "GET")
    with urllib.request.urlopen(req,timeout=90) as r:return json.load(r)
def read(auth):
    q=urllib.parse.urlencode({"context":"edit",
      "_fields":"id,slug,status,title,categories,featured_media,author,content"})
    return request(f"/wp-json/wp/v2/posts/{ID}?{q}",auth)
def verify_map_url():
    req=urllib.request.Request(MAP_URL,headers={"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req,timeout=25) as r:
        target=r.geturl()
        if r.status!=200 or "/maps/embed" not in target or "!5e1" not in target:
            raise RuntimeError("Legacy Google satellite embed not confirmed: "+target)
        print("GOOGLE_SATELLITE_IFRAME_CONFIRMED",target[:280],flush=True)
def main(mode):
    user=os.getenv("TSURIKUE_WP_USER");pw=os.getenv("TSURIKUE_WP_APP_PASSWORD")
    if not user or not pw:raise RuntimeError("WordPress credentials unavailable")
    token="Basic "+base64.b64encode((user+":"+pw).encode()).decode()
    post=read(token)
    if (post["id"],post["slug"],post["status"])!=(ID,SLUG,"draft"):
        raise RuntimeError("Wrong post ID/slug/draft status")
    old=post["content"]["raw"]
    if sha(old)!=ORIGINAL_SHA:
        raise RuntimeError("Existing draft changed; DO NOT overwrite. Hash: "+sha(old))
    new=edit(old)
    verify_map_url()
    print("MAP_EDIT_PREFLIGHT_OK",json.dumps({
        "post_id":ID,"status":"draft","previous_chars":len(old),"next_chars":len(new),
        "original_images":old.count("<!-- wp:image "),"new_images":new.count("<!-- wp:image "),
        "tables":new.count("<!-- wp:table "),
        "map_mode":"Google satellite zoom 18","map_place":PLACE,
        "sha256_after":sha(new)
    },ensure_ascii=False),flush=True)
    if mode=="check":return
    current=read(token)
    if sha(current["content"]["raw"])!=ORIGINAL_SHA or current["status"]!="draft":
        raise RuntimeError("Concurrent editor change before update")
    attempted=False
    try:
        attempted=True
        request(f"/wp-json/wp/v2/posts/{ID}",token,{"content":new})
        saved=read(token)
        for field in ("id","slug","status","title","categories","featured_media","author"):
            if saved[field]!=post[field]:
                raise RuntimeError("Protected post metadata changed: "+field)
        if saved["content"]["raw"]!=new:
            raise RuntimeError("Saved WordPress raw article differs from intended body")
        rendered=saved["content"].get("rendered","")
        if "<iframe" not in rendered or "output=embed" not in rendered:
            raise RuntimeError("WordPress rendered iframe not present")
        if "Googleマップで拡大して見る" not in rendered:
            raise RuntimeError("Clickable backup map link missing")
        if saved["content"]["raw"].count("<!-- wp:image ")!=15:
            raise RuntimeError("Previous 15 photos changed")
        print("FINAL_DRAFT_GOOGLE_MAP_VERIFIED",json.dumps({
            "post_id":ID,"status":"draft","images":15,"info_tables":2,
            "Google_Map_iframes":1,"satellite":"!5e1",
            "result_sha256":sha(new),
            "editor_url":SITE+"/wp-admin/post.php?post=4138&action=edit"
        },ensure_ascii=False),flush=True)
    except Exception:
        if attempted:
            try:
                updated=read(token)
                if updated["content"]["raw"]==new:
                    request(f"/wp-json/wp/v2/posts/{ID}",token,{"content":old})
                    print("CONDITIONAL_ROLLBACK_COMPLETED",flush=True)
                else:print("ROLLBACK_SKIPPED_POSSIBLE_HUMAN_EDITS",flush=True)
            except Exception as exc:print("ROLLBACK_FAILED_REQUIRES_REVIEW",str(exc),flush=True)
        raise
if __name__=="__main__":
    mode=sys.argv[1] if len(sys.argv)>1 else "check"
    if mode not in ("check","apply"):raise SystemExit("check/apply only")
    main(mode)
