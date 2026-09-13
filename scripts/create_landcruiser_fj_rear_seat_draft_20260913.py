#!/usr/bin/env python3
from __future__ import annotations

import base64, hashlib, html, json, os, re, time, urllib.parse, urllib.request
from pathlib import Path

SITE="https://tsurikue.com"
UA="tsurikue-create-landcruiser-fj-rear-seat-20260913/1.0"
TITLE="ランドクルーザーFJの後部座席は狭い？実車写真で広さを確認"
SLUG="landcruiser-fj-rear-seat"
CONTENT_PATH=Path("packages/landcruiser-fj-rear-seat/content.html")
EXCERPT="ランドクルーザーFJの後部座席は狭い？後席を一番後ろまでスライドし、前席を一番後ろまで下げた状態と、身長約160cmの運転位置を実車写真で比較します。"
FEATURED=3760
CATEGORY_SLUGS=["car"]
EXPECTED_MEDIA={
    3757:"/wp-content/uploads/2026/09/img_8130.jpg",
    3760:"/wp-content/uploads/2026/09/img_8310.jpg",
    3754:"/wp-content/uploads/2026/09/img_8309.jpg",
}
BODY_MEDIA={3757,3760,3754}
SOURCE_MARKER="<!-- tsurikue-original:v1 slug=landcruiser-fj-rear-seat source=user-provided-20260913 -->"
EDITORIAL_MARKER="<!-- tsurikue-editorial:v1 slug=landcruiser-fj-rear-seat -->"
EXPECTED_H2=[
    "FJの後部座席は見た目ほど狭くない",
    "今回確認した条件",
    "前席を一番後ろまで下げると余裕は少なめ",
    "身長160cmくらいの運転位置なら後ろは案外広い",
    "運転席側と助手席側の両方を見た感想",
    "FJの後席を見るなら前席位置もセットで見る",
    "まとめ｜FJの後部座席は「見た目よりちゃんと使える」",
]
REQUIRED_SHORTCODE='[blog_parts id="2184"]'

TOKEN=re.compile(r"<!--\s+/?wp:[\s\S]*?-->")
OPEN=re.compile(r"<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->")
CLOSE=re.compile(r"<!--\s+/wp:([\w\-/]+)\s+-->")
IMAGE_ID=re.compile(r"wp-image-(\d+)")
H2_RE=re.compile(r"<h2[^>]*>(.*?)</h2>",re.I|re.S)

def auth():
    user=os.environ.get("TSURIKUE_WP_USER")
    pw=os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not pw:
        raise SystemExit("BLOCKED_MISSING_SECRETS")
    return "Basic "+base64.b64encode(f"{user}:{pw}".encode()).decode()

def req(url,method="GET",payload=None,timeout=60):
    headers={"Authorization":auth(),"Accept":"application/json","User-Agent":UA}
    data=None
    if payload is not None:
        data=json.dumps(payload,ensure_ascii=False).encode()
        headers["Content-Type"]="application/json; charset=utf-8"
    last=None
    for n in range(3):
        try:
            r=urllib.request.Request(url,data=data,headers=headers,method=method)
            with urllib.request.urlopen(r,timeout=timeout) as resp:
                body=resp.read().decode()
                return (json.loads(body) if body else None),dict(resp.headers)
        except Exception as exc:
            last=exc
            if n<2:
                time.sleep(3*(n+1))
    raise last

def raw(row,key):
    v=row.get(key) or {}
    if isinstance(v,dict):
        return v.get("raw") or v.get("rendered") or ""
    return str(v)

def gutenberg_problems(text):
    stack=[]
    for m in TOKEN.finditer(text):
        token=m.group(0)
        opened=OPEN.fullmatch(token)
        closed=CLOSE.fullmatch(token)
        if opened:
            if not opened.group(2): stack.append(opened.group(1))
        elif closed:
            if not stack or stack[-1]!=closed.group(1): return 1
            stack.pop()
    return len(stack)

def count_published(endpoint):
    q=urllib.parse.urlencode({"status":"publish","per_page":1,"_fields":"id"})
    _,headers=req(f"{SITE}/wp-json/wp/v2/{endpoint}?{q}",timeout=45)
    return int(headers.get("X-WP-Total","0"))

def public_counts():
    posts=count_published("posts"); pages=count_published("pages")
    return {"published_posts":posts,"published_pages":pages,"published_total":posts+pages}

def resolve_term(endpoint,slug):
    q=urllib.parse.urlencode({"context":"edit","slug":slug,"per_page":10,"_fields":"id,slug,name"})
    rows,_=req(f"{SITE}/wp-json/wp/v2/{endpoint}?{q}",timeout=45)
    if len(rows)!=1 or rows[0].get("slug")!=slug:
        raise RuntimeError(f"term resolution failed endpoint={endpoint} slug={slug}: {rows}")
    return int(rows[0]["id"])

def validate_media():
    q=urllib.parse.urlencode({
        "context":"edit",
        "include":",".join(str(x) for x in sorted(EXPECTED_MEDIA)),
        "per_page":100,
        "_fields":"id,status,source_url",
    })
    rows,_=req(f"{SITE}/wp-json/wp/v2/media?{q}",timeout=60)
    by_id={int(row.get("id") or 0):row for row in rows}
    if set(by_id)!=set(EXPECTED_MEDIA):
        raise RuntimeError(f"media id set mismatch got={sorted(by_id)} expected={sorted(EXPECTED_MEDIA)}")
    for mid,expected_path in EXPECTED_MEDIA.items():
        actual=urllib.parse.unquote(urllib.parse.urlparse(by_id[mid].get("source_url") or "").path)
        if actual.casefold()!=expected_path.casefold():
            raise RuntimeError(f"media mismatch id={mid}: {actual} != {expected_path}")

def find_existing():
    q=urllib.parse.urlencode({
        "context":"edit","slug":SLUG,"status":"any","per_page":10,
        "_fields":"id,slug,status,title,content,featured_media,categories,excerpt"
    })
    rows,_=req(f"{SITE}/wp-json/wp/v2/posts?{q}",timeout=45)
    return rows

def normalized_excerpt(value):
    return re.sub(r"<[^>]+>","",html.unescape(value or "")).strip()

def validate_content(content):
    if "<h1" in content.casefold() or '"level":1' in content:
        raise RuntimeError("body h1 is forbidden")
    if gutenberg_problems(content)!=0:
        raise RuntimeError("Gutenberg block balance failed")
    if content.count(SOURCE_MARKER)!=1 or content.count(EDITORIAL_MARKER)!=1:
        raise RuntimeError("marker count mismatch")
    for banned in ["普通に","🤣","😏","🔥","😂","😊"]:
        if banned in content:
            raise RuntimeError("banned wording/emoji present: "+banned)
    h2=[re.sub(r"<[^>]+>","",x).strip() for x in H2_RE.findall(content)]
    if h2!=EXPECTED_H2:
        raise RuntimeError("H2 structure mismatch: "+repr(h2))
    used={int(x) for x in IMAGE_ID.findall(content)}
    if used!=BODY_MEDIA:
        raise RuntimeError(f"body media mismatch used={sorted(used)} expected={sorted(BODY_MEDIA)}")
    if content.count(REQUIRED_SHORTCODE)!=1:
        raise RuntimeError("CTN shortcode count mismatch")
    for phrase in [
        "後部座席を一番後ろまでスライド",
        "前席を一番後ろまで下げた状態",
        "身長約160cm",
        "運転席側の後ろ・助手席側の後ろ",
        "https://tsurikue.com/landcruiser-fj-price/",
    ]:
        if phrase not in content:
            raise RuntimeError("missing required phrase: "+phrase)

def same_draft(row,content,categories):
    return (
        row.get("status")=="draft"
        and row.get("slug")==SLUG
        and html.unescape(raw(row,"title"))==TITLE
        and raw(row,"content").strip()==content.strip()
        and int(row.get("featured_media") or 0)==FEATURED
        and sorted(row.get("categories") or [])==sorted(categories)
        and normalized_excerpt(raw(row,"excerpt"))==EXCERPT
    )

def main():
    content=CONTENT_PATH.read_text(encoding="utf-8").strip()+"\n"
    validate_content(content); validate_media()
    categories=[resolve_term("categories",slug) for slug in CATEGORY_SLUGS]
    before=public_counts()
    existing=find_existing()
    action="CREATE"

    if existing:
        if len(existing)!=1:
            raise RuntimeError(f"multiple slug collisions: {len(existing)}")
        if not same_draft(existing[0],content,categories):
            raise RuntimeError(f"slug already exists but differs: id={existing[0].get('id')} status={existing[0].get('status')}")
        created=existing[0]; action="ALREADY_UP_TO_DATE"
    else:
        created,_=req(
            f"{SITE}/wp-json/wp/v2/posts",
            method="POST",
            payload={
                "title":TITLE,"slug":SLUG,"content":content,"status":"draft",
                "featured_media":FEATURED,"categories":categories,"excerpt":EXCERPT,
            },
            timeout=90,
        )
        if created.get("status")!="draft" or created.get("slug")!=SLUG:
            raise RuntimeError("create response validation failed")

    pid=int(created["id"])
    q=urllib.parse.urlencode({
        "context":"edit",
        "_fields":"id,slug,status,title,content,featured_media,categories,excerpt,link"
    })
    after,_=req(f"{SITE}/wp-json/wp/v2/posts/{pid}?{q}",timeout=60)
    after_counts=public_counts()
    if before!=after_counts:
        raise RuntimeError(f"published counts changed: {before} -> {after_counts}")
    if not same_draft(after,content,categories):
        raise RuntimeError("post verification failed")

    report={
        "result":"SUCCESS","action":action,"post_id":pid,"slug":SLUG,"status":"draft",
        "title":TITLE,"featured_media":FEATURED,"categories":categories,
        "media_checked":len(EXPECTED_MEDIA),"body_images":len(BODY_MEDIA),
        "gutenberg_problems":0,"published_before":before,"published_after":after_counts,
        "content_sha256":hashlib.sha256(raw(after,"content").encode()).hexdigest(),
        "wordpress_write_count":0 if action=="ALREADY_UP_TO_DATE" else 1,
        "publish_count":0,"media_upload_count":0,
    }
    print("# Land Cruiser FJ rear-seat draft creation")
    for k,v in report.items():
        print(f"- {k}: **{v}**")

if __name__=="__main__":
    main()
