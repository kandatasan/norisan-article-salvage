#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, os, re, time, urllib.parse, urllib.request
from pathlib import Path
SITE="https://tsurikue.com"; BASE=SITE+"/wp-json/wp/v2"; UA="tsurikue-emotional-media-swell-patch/1.0"
POST_ID=3570; SLUG="lexus-ux-emotional-explorer"; TITLE="レクサスUXの特別仕様車エモーショナルエクスプローラーはお得？実際に選んだ理由"
EXPECTED_CURRENT_SHA="dfa56ea8aecb0644407e09350d6d871ef42ee414c81ff7a02b3ff4e9638488e3"; EXPECTED_CURRENT_FEATURED=2197; NEW_FEATURED=2223
MEDIA={2244:"/wp-content/uploads/2026/06/IMG_2045.jpeg",2223:"/wp-content/uploads/2026/06/IMG_1250.jpeg",2246:"/wp-content/uploads/2026/06/IMG_3286.jpeg",2247:"/wp-content/uploads/2026/06/IMG_0847.jpeg",2248:"/wp-content/uploads/2026/06/IMG_1090.jpeg"}
REPORT=Path("reports/lexus-emotional-media-swell-patch")
def auth_header(u,p): return "Basic "+base64.b64encode(f"{u}:{p}".encode()).decode()
def req(path,auth,method="GET",payload=None):
    data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode("utf-8"); headers={"Authorization":auth,"Accept":"application/json","User-Agent":UA}
    if data is not None: headers["Content-Type"]="application/json; charset=utf-8"
    attempts=3 if method=="GET" else 1; last=None
    for i in range(attempts):
        try:
            r=urllib.request.Request(BASE+path,data=data,headers=headers,method=method)
            with urllib.request.urlopen(r,timeout=60) as x: return json.loads(x.read().decode()),dict(x.headers)
        except Exception as e:
            last=e
            if i+1<attempts: time.sleep(2*(i+1))
    raise last
def raw(row,key):
    v=row.get(key) or {}; return (v.get("raw") or v.get("rendered") or "") if isinstance(v,dict) else str(v)
def count_published(ep,auth):
    q=urllib.parse.urlencode({"context":"edit","status":"publish","per_page":"1","_fields":"id"}); _,h=req(f"/{ep}?{q}",auth); return int(h.get("X-WP-Total","0"))
def totals(auth):
    p=count_published("posts",auth); g=count_published("pages",auth); return {"posts":p,"pages":g,"total":p+g}
def fetch_post(auth):
    q=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,content,featured_media,categories"}); row,_=req(f"/posts/{POST_ID}?{q}",auth); return row
def validate_media(auth):
    for mid,path in MEDIA.items():
        q=urllib.parse.urlencode({"context":"edit","_fields":"id,status,source_url"}); row,_=req(f"/media/{mid}?{q}",auth); actual=urllib.parse.unquote(urllib.parse.urlparse(row.get("source_url") or "").path)
        if int(row.get("id") or 0)!=mid or actual.casefold()!=path.casefold(): raise RuntimeError(f"MEDIA_MISMATCH {mid} {actual}")
def img(mid,src,alt): return f'<!-- wp:image {{"id":{mid},"sizeSlug":"large","linkDestination":"none"}} -->\n<figure class="wp-block-image size-large"><img src="{src}" alt="{alt}" class="wp-image-{mid}"/></figure>\n<!-- /wp:image -->'
def patch(content):
    if hashlib.sha256(content.encode()).hexdigest()!=EXPECTED_CURRENT_SHA: raise RuntimeError("CURRENT_CONTENT_CHANGED_REFUSING_OVERWRITE")
    new=content
    b2244=img(2244,"https://tsurikue.com/wp-content/uploads/2026/06/IMG_2045-1024x769.jpeg","ドライブ先で撮影したレクサスUX250h F SPORT Emotional Explorer")
    b2223=img(2223,"https://tsurikue.com/wp-content/uploads/2026/06/IMG_1250-1024x769.jpeg","レクサスUX250h F SPORT Emotional Explorerの外観")
    b2246=img(2246,"https://tsurikue.com/wp-content/uploads/2026/06/IMG_3286-1024x768.jpeg","レクサスUXに装着したF SPORT専用オレンジブレーキキャリパー")
    b2247=img(2247,"https://tsurikue.com/wp-content/uploads/2026/06/IMG_0847-1024x450.jpeg","レクサスUXに装着した三眼フルLEDヘッドランプ")
    b2248=img(2248,"https://tsurikue.com/wp-content/uploads/2026/06/IMG_1090-1024x768.jpeg","レクサスUXに装着したムーンルーフ")
    new,n=re.subn(r'<!-- wp:image \{"id":2197.*?<!-- /wp:image -->',b2244,new,count=1,flags=re.S)
    if n!=1: raise RuntimeError("INTRO_IMAGE_NOT_FOUND")
    new,n=re.subn(r'<!-- wp:image \{"id":2211.*?<!-- /wp:image -->',b2223,new,count=1,flags=re.S)
    if n!=1: raise RuntimeError("FENDER_IMAGE_NOT_FOUND")
    new,n=re.subn(r'\n<!-- wp:image \{"id":2210.*?<!-- /wp:image -->\n','\n',new,count=1,flags=re.S)
    if n!=1: raise RuntimeError("INTERIOR_IMAGE_NOT_FOUND")
    needle='<!-- wp:paragraph -->\n<p><strong>見た目だけの特別仕様車ではなく、所有してからも良さを感じやすい仕様でした。</strong></p>\n<!-- /wp:paragraph -->'
    if new.count(needle)!=1: raise RuntimeError("OWNERSHIP_INSERT_POINT_CHANGED")
    extra=needle+'\n\n<!-- wp:paragraph -->\n<p>ちなみに私の車は、F SPORT専用オレンジブレーキキャリパー、三眼フルLEDヘッドランプ、ムーンルーフなども追加しています。<br>この3つはEmotional Explorerの標準装備ではなく、私が選んだメーカーオプションです。</p>\n<!-- /wp:paragraph -->\n\n'+b2246+'\n\n'+b2247+'\n\n'+b2248
    new=new.replace(needle,extra,1)
    old=re.search(r'<!-- wp:buttons.*?<!-- /wp:buttons -->',new,re.S)
    if not old: raise RuntimeError("CORE_BUTTON_NOT_FOUND")
    swell='<!-- wp:loos/button {"isNewTab":true,"className":"is-style-btn_solid -size-l"} -->\n<div class="swell-block-button is-style-btn_solid -size-l"><a href="https://px.a8.net/svt/ejp?a8mat=4B65SD+8DUSHE+9QU+NVHCY" class="swell-block-button__link" target="_blank" rel="nofollow noopener"><span>非公開車両も含めてUXを探してみる</span></a></div>\n<!-- /wp:loos/button -->'
    new=new.replace(old.group(0),swell,1)
    ids=[int(x) for x in re.findall(r'wp:image \{"id":(\d+)',new)]
    if ids!=[2244,2223,2246,2247,2248]: raise RuntimeError(f"IMAGE_SEQUENCE_BAD {ids}")
    if 'wp:buttons' in new or 'wp:button' in new: raise RuntimeError("CORE_BUTTON_REMAINS")
    if 'wp:loos/button' not in new or 'swell-block-button__link' not in new: raise RuntimeError("SWELL_BUTTON_MISSING")
    if '4B65SD+8DUSHE+9QU+NVHCY' not in new: raise RuntimeError("A8_CODE_MISSING")
    return new
def write_report(r):
    REPORT.mkdir(parents=True,exist_ok=True); (REPORT/"result.json").write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (REPORT/"summary.md").write_text(f"# Lexus Emotional Explorer media + SWELL patch\n\n- result: **{r['result']}**\n- post_id: **{r.get('post_id')}**\n- status: **{r.get('status')}**\n- featured_media: **{r.get('featured_media')}**\n- images: **{r.get('images')}**\n- public_before: **{r.get('public_before')}**\n- public_after: **{r.get('public_after')}**\n",encoding="utf-8")
def main():
    r={"result":"BLOCKED"}
    try:
        u=os.environ.get("TSURIKUE_WP_USER"); p=os.environ.get("TSURIKUE_WP_APP_PASSWORD")
        if not u or not p: raise RuntimeError("MISSING_SECRETS")
        auth=auth_header(u,p); before=totals(auth); row=fetch_post(auth)
        if int(row.get("id") or 0)!=POST_ID or row.get("slug")!=SLUG: raise RuntimeError("POST_ID_SLUG_MISMATCH")
        if row.get("status")!="draft": raise RuntimeError("TARGET_NOT_DRAFT")
        if html.unescape(raw(row,"title"))!=TITLE: raise RuntimeError("TITLE_CHANGED")
        if int(row.get("featured_media") or 0)!=EXPECTED_CURRENT_FEATURED: raise RuntimeError("FEATURED_CHANGED")
        validate_media(auth); desired=patch(raw(row,"content"))
        response,_=req(f"/posts/{POST_ID}",auth,method="POST",payload={"content":desired,"featured_media":NEW_FEATURED,"status":"draft"})
        if int(response.get("id") or 0)!=POST_ID or response.get("status")!="draft": raise RuntimeError("UPDATE_RESPONSE_INVALID")
        row2=fetch_post(auth); after=totals(auth)
        if before!=after: raise RuntimeError(f"PUBLISHED_TOTALS_CHANGED {before}->{after}")
        c2=raw(row2,"content")
        if c2.strip()!=desired.strip(): raise RuntimeError("CONTENT_POSTWRITE_MISMATCH")
        if int(row2.get("featured_media") or 0)!=NEW_FEATURED: raise RuntimeError("FEATURED_POSTWRITE_MISMATCH")
        r={"result":"SUCCESS","post_id":POST_ID,"status":"draft","featured_media":NEW_FEATURED,"images":[2244,2223,2246,2247,2248],"swell_button":True,"public_before":before["total"],"public_after":after["total"],"content_sha256":hashlib.sha256(c2.encode()).hexdigest()}
        write_report(r); print(json.dumps(r,ensure_ascii=False,indent=2))
    except Exception as e:
        r["error"]=str(e); write_report(r); print(json.dumps(r,ensure_ascii=False,indent=2)); raise
if __name__=="__main__": main()
