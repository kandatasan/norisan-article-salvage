#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

SITE="https://tsurikue.com"
UA="tsurikue-create-landcruiser-fj-review-20260913/1.0"
TITLE="ランドクルーザーFJ実車レビュー｜実際に乗って分かった良い点・残念な点"
SLUG="landcruiser-fj-review"
CONTENT_PATH=Path("packages/landcruiser-fj-review/content.html")
EXCERPT="ランドクルーザーFJを実際に購入して乗ってみた感想を、実車写真つきでレビュー。走り、見晴らし、後部座席、デジタルインナーミラーの良かった点と、ドア解錠・コンソール・タイヤハウスなど気になった点をまとめます。"
FEATURED=3756
CATEGORY_SLUGS=["car"]
EXPECTED_MEDIA={
    3756:"/wp-content/uploads/2026/09/img_8129.jpg",
    3757:"/wp-content/uploads/2026/09/img_8130.jpg",
    3759:"/wp-content/uploads/2026/09/img_8123.jpg",
    3764:"/wp-content/uploads/2026/09/img_8313.jpg",
    3750:"/wp-content/uploads/2026/09/img_8317.jpg",
    3760:"/wp-content/uploads/2026/09/img_8310.jpg",
    3754:"/wp-content/uploads/2026/09/img_8309.jpg",
    3758:"/wp-content/uploads/2026/09/img_8122.jpg",
    3751:"/wp-content/uploads/2026/09/img_8315.jpg",
    3761:"/wp-content/uploads/2026/09/img_8125.jpg",
}
BODY_MEDIA=set(EXPECTED_MEDIA)-{FEATURED}
SOURCE_MARKER="<!-- tsurikue-original:v1 slug=landcruiser-fj-review source=user-provided-20260913 -->"
EDITORIAL_MARKER="<!-- tsurikue-editorial:v1 slug=landcruiser-fj-review -->"
EXPECTED_H2=[
    "ランドクルーザーFJを実際に乗ってみた感想",
    "良かったところ1｜見た目ほど重たさを感じない",
    "良かったところ2｜運転席が高くて見渡しやすい",
    "良かったところ3｜後部座席は一見狭そうでも案外広い",
    "良かったところ4｜デジタルインナーミラーが見やすい",
    "残念だったところ｜細かいところはちょっと惜しい",
    "実際に乗ると「思ったより乗りやすい」が一番近い",
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
                raw=resp.read().decode()
                return (json.loads(raw) if raw else None),dict(resp.headers)
        except Exception as exc:
            last=exc
            if n<2:
                time.sleep(3*(n+1))
    raise last

def raw(row,key):
    value=row.get(key) or {}
    if isinstance(value,dict):
        return value.get("raw") or value.get("rendered") or ""
    return str(value)

def gutenberg_problems(text):
    stack=[]
    for m in TOKEN.finditer(text):
        token=m.group(0)
        opened=OPEN.fullmatch(token)
        closed=CLOSE.fullmatch(token)
        if opened:
            if not opened.group(2):
                stack.append(opened.group(1))
        elif closed:
            if not stack or stack[-1]!=closed.group(1):
                return 1
            stack.pop()
    return len(stack)

def count_published(endpoint):
    q=urllib.parse.urlencode({"status":"publish","per_page":1,"_fields":"id"})
    _,headers=req(f"{SITE}/wp-json/wp/v2/{endpoint}?{q}",timeout=45)
    return int(headers.get("X-WP-Total","0"))

def public_counts():
    posts=count_published("posts")
    pages=count_published("pages")
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
        row=by_id[mid]
        actual=urllib.parse.unquote(urllib.parse.urlparse(row.get("source_url") or "").path)
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
    for banned in ["普通に","もちろん","🤣","😏","🔥","😂","😊"]:
        if banned in content:
            raise RuntimeError("banned wording/emoji present: "+banned)
    if content.count("かなり")>1 or content.count("めちゃくちゃ")>1:
        raise RuntimeError("intensifier overuse")
    h2=[re.sub(r"<[^>]+>","",x).strip() for x in H2_RE.findall(content)]
    if h2!=EXPECTED_H2:
        raise RuntimeError("H2 structure mismatch: "+repr(h2))
    used={int(x) for x in IMAGE_ID.findall(content)}
    if used!=BODY_MEDIA:
        raise RuntimeError(f"body media mismatch used={sorted(used)} expected={sorted(BODY_MEDIA)}")
    if content.count(REQUIRED_SHORTCODE)!=1:
        raise RuntimeError("CTN shortcode count mismatch")
    required=[
        "踏めばそれなりに走る",
        "油圧パワーステアリング",
        "身長約160cm",
        "後部座席を一番後ろまでスライド",
        "デジタルインナーミラー",
        "ケーブルを外へ出す穴がない",
        "タイヤハウス",
        "https://tsurikue.com/landcruiser-fj-price/",
        "https://toyota.jp/landcruiserfj/",
        "https://toyota.jp/request/webcatalog/landcruiserfj/",
    ]
    for phrase in required:
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
    validate_content(content)
    validate_media()
    categories=[resolve_term("categories",slug) for slug in CATEGORY_SLUGS]
    before=public_counts()
    existing=find_existing()
    action="CREATE"

    if existing:
        if len(existing)!=1:
            raise RuntimeError(f"multiple slug collisions: {len(existing)}")
        if not same_draft(existing[0],content,categories):
            raise RuntimeError(f"slug already exists but differs: id={existing[0].get('id')} status={existing[0].get('status')}")
        created=existing[0]
        action="ALREADY_UP_TO_DATE"
    else:
        payload={
            "title":TITLE,
            "slug":SLUG,
            "content":content,
            "status":"draft",
            "featured_media":FEATURED,
            "categories":categories,
            "excerpt":EXCERPT,
        }
        created,_=req(f"{SITE}/wp-json/wp/v2/posts",method="POST",payload=payload,timeout=90)
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

    print("# Land Cruiser FJ review draft creation")
    report={
        "result":"SUCCESS",
        "action":action,
        "post_id":pid,
        "slug":SLUG,
        "status":"draft",
        "title":TITLE,
        "featured_media":FEATURED,
        "categories":categories,
        "media_checked":len(EXPECTED_MEDIA),
        "body_images":len(BODY_MEDIA),
        "gutenberg_problems":0,
        "published_before":before,
        "published_after":after_counts,
        "content_sha256":hashlib.sha256(raw(after,"content").encode()).hexdigest(),
        "wordpress_write_count":0 if action=="ALREADY_UP_TO_DATE" else 1,
        "publish_count":0,
        "media_upload_count":0,
        "tone_check":"frank_v1_no_emoji",
    }
    for k,v in report.items():
        print(f"- {k}: **{v}**")

if __name__=="__main__":
    main()
