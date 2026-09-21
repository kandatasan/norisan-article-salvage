#!/usr/bin/env python3
from __future__ import annotations

import base64, hashlib, html, json, os, urllib.parse, urllib.request
from pathlib import Path

SITE="https://tsurikue.com"
UA="tsurikue-patch-kurahashijima-salt-20260921/1.0"
POST_ID=3882
SLUG="kurahashijima-autumn-drive"
TITLE="倉橋島を秋にドライブ！桂浜散策・海鮮ランチ・鹿島大橋まで楽しんできた"
EXPECTED_SHA="47f8d54aca486ce60c1f63741fd76c35975b31b2921529ae0dfd133d1da0a293"
MEDIA_ID=3867
MEDIA_PATH="/wp-content/uploads/2026/09/img_8450.jpg"
MEDIA_WIDTH=1920
MEDIA_HEIGHT=1440
REPORT=Path("reports/kurahashijima-salt-patch-20260921")

ANCHOR='''<!-- wp:paragraph -->
<p>橋を渡ったあたりから、海がどんどん近くなってきます。</p>
<!-- /wp:paragraph -->'''

BLOCK='''<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">道中に突然現れる「塩の山」</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>海沿いを走っていると、向こうに真っ白な山が見えてきます。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>雪でも砂でもなく、<strong>これ、実は塩です。</strong></p>
<!-- /wp:paragraph -->

<!-- wp:image {"id":3867,"sizeSlug":"full","linkDestination":"none"} -->
<figure class="wp-block-image size-full"><img src="https://tsurikue.com/wp-content/uploads/2026/09/img_8450.jpg" alt="三ツ子島埠頭に積まれた巨大な輸入塩の山" class="wp-image-3867"/></figure>
<!-- /wp:image -->

<!-- wp:paragraph -->
<p>三ツ子島埠頭は、国内最大の輸入塩の中継基地。主にメキシコで作られた天日塩を保管し、各地へ積み替える物流拠点です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>海と山を眺めながら走っていたら、急に真っ白な山。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>こういう「なんだあれ？」が出てくるのも、倉橋島方面へのドライブの面白いところ。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><a href="https://mitsukojimafuto.co.jp/" target="_blank" rel="noopener">塩の中継基地については三ツ子島埠頭の公式サイトで確認できます。</a></p>
<!-- /wp:paragraph -->'''

def auth():
    u=os.environ["TSURIKUE_WP_USER"]; p=os.environ["TSURIKUE_WP_APP_PASSWORD"]
    return "Basic "+base64.b64encode(f"{u}:{p}".encode()).decode()

def req(method,path,payload=None):
    headers={"Authorization":auth(),"Accept":"application/json","User-Agent":UA}
    data=None
    if payload is not None:
        headers["Content-Type"]="application/json; charset=utf-8"
        data=json.dumps(payload,ensure_ascii=False).encode("utf-8")
    r=urllib.request.Request(SITE+path,data=data,headers=headers,method=method)
    with urllib.request.urlopen(r,timeout=60) as resp:
        body=resp.read().decode("utf-8")
        return (json.loads(body) if body else None),dict(resp.headers.items())

def raw(row,key):
    v=row.get(key) or {}
    return (v.get("raw") or v.get("rendered") or "") if isinstance(v,dict) else str(v)

def pubcount(endpoint):
    q=urllib.parse.urlencode({"context":"edit","status":"publish","per_page":1,"_fields":"id"})
    _,h=req("GET",f"/wp-json/wp/v2/{endpoint}?{q}")
    for k,v in h.items():
        if k.lower()=="x-wp-total":
            return int(v)
    raise RuntimeError("missing X-WP-Total")

def counts():
    return {"posts":pubcount("posts"),"pages":pubcount("pages")}

def fetch_post():
    q=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,content,featured_media"})
    row,_=req("GET",f"/wp-json/wp/v2/posts/{POST_ID}?{q}")
    return row

def validate_media():
    q=urllib.parse.urlencode({"context":"edit","_fields":"id,source_url,media_details"})
    row,_=req("GET",f"/wp-json/wp/v2/media/{MEDIA_ID}?{q}")
    if int(row.get("id") or 0)!=MEDIA_ID:
        raise RuntimeError("media id mismatch")
    actual=urllib.parse.unquote(urllib.parse.urlparse(row.get("source_url") or "").path).casefold()
    if actual!=MEDIA_PATH.casefold():
        raise RuntimeError(f"media path mismatch: {actual}")
    d=row.get("media_details") or {}
    if int(d.get("width") or 0)!=MEDIA_WIDTH or int(d.get("height") or 0)!=MEDIA_HEIGHT:
        raise RuntimeError("media dimensions mismatch")

def main():
    before_counts=counts()
    before=fetch_post()
    title=html.unescape(raw(before,"title"))
    content=raw(before,"content")

    if before.get("slug")!=SLUG or before.get("status")!="draft" or title!=TITLE:
        raise RuntimeError("target draft identity mismatch")
    if hashlib.sha256(content.encode()).hexdigest()!=EXPECTED_SHA:
        raise RuntimeError("current content SHA changed")
    if f"wp-image-{MEDIA_ID}" in content:
        raise RuntimeError("salt image already present")
    if content.count(ANCHOR)!=1:
        raise RuntimeError(f"anchor mismatch: {content.count(ANCHOR)}")

    validate_media()
    patched=content.replace(ANCHOR,ANCHOR+"\n\n"+BLOCK,1)

    response,_=req("POST",f"/wp-json/wp/v2/posts/{POST_ID}",{
        "content":patched,
        "status":"draft",
    })
    if int(response.get("id") or 0)!=POST_ID or response.get("slug")!=SLUG or response.get("status")!="draft":
        raise RuntimeError("update response identity/status mismatch")

    after=fetch_post()
    after_content=raw(after,"content")
    after_counts=counts()
    if after_counts!=before_counts:
        raise RuntimeError(f"published counts changed: {before_counts}->{after_counts}")
    if after.get("status")!="draft" or after.get("slug")!=SLUG:
        raise RuntimeError("final draft identity mismatch")
    if html.unescape(raw(after,"title"))!=TITLE:
        raise RuntimeError("final title mismatch")
    if f"wp-image-{MEDIA_ID}" not in after_content or "三ツ子島埠頭は、国内最大の輸入塩の中継基地" not in after_content:
        raise RuntimeError("salt section missing after update")
    if after_content.strip()!=patched.strip():
        raise RuntimeError("final content differs from patch target")

    REPORT.mkdir(parents=True,exist_ok=True)
    result={
        "result":"SUCCESS","action":"INSERT_SALT_MOUNTAIN_SECTION","post_id":POST_ID,
        "slug":SLUG,"status":"draft","inserted_media":MEDIA_ID,
        "public_before":before_counts,"public_after":after_counts,
        "content_sha256":hashlib.sha256(after_content.encode()).hexdigest(),
    }
    (REPORT/"result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=[
        "# Kurahashijima salt-mountain patch 2026-09-21","",
        "- result: **SUCCESS**","- action: **INSERT_SALT_MOUNTAIN_SECTION**",
        f"- post_id: **{POST_ID}**","- status: **draft**",f"- slug: **{SLUG}**",
        f"- inserted_media: **{MEDIA_ID} / img_8450.jpg**",
        f"- published posts before/after: **{before_counts['posts']} / {after_counts['posts']}**",
        f"- published pages before/after: **{before_counts['pages']} / {after_counts['pages']}**",
        f"- content sha256: **{result['content_sha256']}**",
    ]
    (REPORT/"summary.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
