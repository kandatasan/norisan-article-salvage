#!/usr/bin/env python3
from __future__ import annotations

import base64, hashlib, html, json, os, urllib.parse, urllib.request
from pathlib import Path

SITE="https://tsurikue.com"
UA="tsurikue-patch-sugai-media-20260921/1.0"
POST_ID=3865
SLUG="sugai-tsubugai"
TITLE='広島で「ツブガイ」と呼ぶスガイはうまい！味・茹で方と磯遊びの思い出'
EXPECTED_SHA="09fc1aeb17c57f534f1ced859cf432dbd88d16e3779ba8d72c6183342073ea83"
FEATURED=3862
REPORT=Path("reports/sugai-media-patch-20260921")

MEDIA={
    3861: {"path":"/wp-content/uploads/2026/09/img_8439.jpg","width":1440,"height":1920},
    3862: {"path":"/wp-content/uploads/2026/09/img_8440.jpg","width":1440,"height":1920},
    3859: {"path":"/wp-content/uploads/2026/09/img_8441.jpg","width":1920,"height":1440},
    3860: {"path":"/wp-content/uploads/2026/09/img_8442.jpg","width":1440,"height":1920},
}

INSERTIONS=[
    (
        "<!-- wp:paragraph -->\n<p>潮が引いた岩場を見ていると、岩の表面や隙間にちょこんと付いています。</p>\n<!-- /wp:paragraph -->",
        '<!-- wp:image {"id":3861,"sizeSlug":"full","linkDestination":"none"} -->\n<figure class="wp-block-image size-full"><img src="https://tsurikue.com/wp-content/uploads/2026/09/img_8439.jpg" alt="磯の岩の隙間にいるスガイ" class="wp-image-3861"/></figure>\n<!-- /wp:image -->'
    ),
    (
        "<!-- wp:paragraph -->\n<p>広島大学の竹原ステーションでも、竹原市で採集されたスガイが紹介されています。特徴のひとつが、<strong>丸くて石灰質のフタ</strong>です。</p>\n<!-- /wp:paragraph -->",
        '<!-- wp:image {"id":3859,"sizeSlug":"full","linkDestination":"none"} -->\n<figure class="wp-block-image size-full"><img src="https://tsurikue.com/wp-content/uploads/2026/09/img_8441.jpg" alt="スガイの殻の中に見える丸いフタ" class="wp-image-3859"/></figure>\n<!-- /wp:image -->'
    ),
    (
        "<!-- wp:paragraph -->\n<p>今回のスガイも、殻の中をのぞくと丸いフタがよく分かりました。</p>\n<!-- /wp:paragraph -->",
        '<!-- wp:image {"id":3862,"sizeSlug":"full","linkDestination":"none"} -->\n<figure class="wp-block-image size-full"><img src="https://tsurikue.com/wp-content/uploads/2026/09/img_8440.jpg" alt="磯で集めたスガイ" class="wp-image-3862"/></figure>\n<!-- /wp:image -->'
    ),
    (
        "<!-- wp:paragraph -->\n<p>うまくいくと、スポッと身が出てきます。</p>\n<!-- /wp:paragraph -->",
        '<!-- wp:image {"id":3860,"sizeSlug":"full","linkDestination":"none"} -->\n<figure class="wp-block-image size-full"><img src="https://tsurikue.com/wp-content/uploads/2026/09/img_8442.jpg" alt="爪楊枝で取り出したスガイの身" class="wp-image-3860"/></figure>\n<!-- /wp:image -->'
    ),
]

def auth():
    u=os.environ["TSURIKUE_WP_USER"]; p=os.environ["TSURIKUE_WP_APP_PASSWORD"]
    return "Basic "+base64.b64encode(f"{u}:{p}".encode()).decode()

def req(method,path,payload=None):
    headers={"Authorization":auth(),"Accept":"application/json","User-Agent":UA}
    data=None
    if payload is not None:
        headers["Content-Type"]="application/json; charset=utf-8"
        data=json.dumps(payload,ensure_ascii=False).encode("utf-8")
    request=urllib.request.Request(SITE+path,data=data,headers=headers,method=method)
    with urllib.request.urlopen(request,timeout=60) as r:
        body=r.read().decode()
        return json.loads(body) if body else None, dict(r.headers.items())

def raw(row,key):
    v=row.get(key) or {}
    return (v.get("raw") or v.get("rendered") or "") if isinstance(v,dict) else str(v)

def pubcount(endpoint):
    q=urllib.parse.urlencode({"context":"edit","status":"publish","per_page":1,"_fields":"id"})
    _,h=req("GET",f"/wp-json/wp/v2/{endpoint}?{q}")
    for k,v in h.items():
        if k.lower()=="x-wp-total": return int(v)
    raise RuntimeError("missing X-WP-Total")

def counts():
    return {"posts":pubcount("posts"),"pages":pubcount("pages")}

def fetch_post():
    q=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,content,featured_media"})
    row,_=req("GET",f"/wp-json/wp/v2/posts/{POST_ID}?{q}")
    return row

def validate_media():
    for mid,spec in MEDIA.items():
        q=urllib.parse.urlencode({"context":"edit","_fields":"id,source_url,media_details"})
        row,_=req("GET",f"/wp-json/wp/v2/media/{mid}?{q}")
        if int(row.get("id") or 0)!=mid: raise RuntimeError(f"media id mismatch {mid}")
        path=urllib.parse.unquote(urllib.parse.urlparse(row.get("source_url") or "").path).casefold()
        if path!=spec["path"].casefold(): raise RuntimeError(f"media path mismatch {mid}: {path}")
        d=row.get("media_details") or {}
        if int(d.get("width") or 0)!=spec["width"] or int(d.get("height") or 0)!=spec["height"]:
            raise RuntimeError(f"media dimensions mismatch {mid}")

def main():
    before_counts=counts()
    before=fetch_post()
    title=html.unescape(raw(before,"title"))
    content=raw(before,"content")

    if before.get("slug")!=SLUG or before.get("status")!="draft" or title!=TITLE:
        raise RuntimeError("target draft identity mismatch")
    if int(before.get("featured_media") or 0)!=0:
        raise RuntimeError("featured media already changed")
    if hashlib.sha256(content.encode()).hexdigest()!=EXPECTED_SHA:
        raise RuntimeError("current content SHA changed")
    for mid in MEDIA:
        if f"wp-image-{mid}" in content:
            raise RuntimeError(f"media already present {mid}")

    validate_media()
    patched=content
    for anchor,block in INSERTIONS:
        if patched.count(anchor)!=1:
            raise RuntimeError(f"anchor mismatch count={patched.count(anchor)}")
        patched=patched.replace(anchor,anchor+"\n\n"+block,1)

    response,_=req("POST",f"/wp-json/wp/v2/posts/{POST_ID}",{
        "content":patched,
        "status":"draft",
        "featured_media":FEATURED,
    })
    if int(response.get("id") or 0)!=POST_ID or response.get("slug")!=SLUG or response.get("status")!="draft":
        raise RuntimeError("update response identity/status mismatch")
    if int(response.get("featured_media") or 0)!=FEATURED:
        raise RuntimeError("featured media mismatch after write")

    after=fetch_post()
    after_content=raw(after,"content")
    after_counts=counts()
    if after_counts!=before_counts:
        raise RuntimeError(f"published counts changed {before_counts}->{after_counts}")
    if after.get("status")!="draft" or after.get("slug")!=SLUG:
        raise RuntimeError("final draft identity mismatch")
    if html.unescape(raw(after,"title"))!=TITLE:
        raise RuntimeError("final title mismatch")
    if int(after.get("featured_media") or 0)!=FEATURED:
        raise RuntimeError("final featured mismatch")
    for mid in MEDIA:
        if f"wp-image-{mid}" not in after_content:
            raise RuntimeError(f"inserted image missing {mid}")
    if after_content.strip()!=patched.strip():
        raise RuntimeError("final content differs from target patch")

    REPORT.mkdir(parents=True,exist_ok=True)
    result={
        "result":"SUCCESS","action":"UPDATE_MEDIA_ONLY","post_id":POST_ID,"slug":SLUG,
        "status":"draft","featured_media":FEATURED,"inserted_media":sorted(MEDIA),
        "public_before":before_counts,"public_after":after_counts,
        "content_sha256":hashlib.sha256(after_content.encode()).hexdigest(),
    }
    (REPORT/"result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=[
        "# Sugai media patch 2026-09-21","",
        "- result: **SUCCESS**","- action: **UPDATE_MEDIA_ONLY**",
        f"- post_id: **{POST_ID}**","- status: **draft**",f"- slug: **{SLUG}**",
        f"- featured_media: **{FEATURED}**",
        f"- inserted_media: **{', '.join(str(x) for x in sorted(MEDIA))}**",
        f"- published posts before/after: **{before_counts['posts']} / {after_counts['posts']}**",
        f"- published pages before/after: **{before_counts['pages']} / {after_counts['pages']}**",
        f"- content sha256: **{result['content_sha256']}**",
    ]
    (REPORT/"summary.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
