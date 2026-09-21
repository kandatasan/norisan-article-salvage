#!/usr/bin/env python3
from __future__ import annotations

import base64, hashlib, html, json, os, re, socket, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

SITE="https://tsurikue.com"
UA="tsurikue-create-kurahashijima-autumn-drive-20260921/1.0"
TITLE="倉橋島を秋にドライブ！桂浜散策・海鮮ランチ・鹿島大橋まで楽しんできた"
SLUG="kurahashijima-autumn-drive"
EXCERPT="9月の倉橋島をドライブ。お食事処かずの刺身定食、厳島神社管絃祭の御座船、桂浜散策、桂浜温泉館での休憩、鹿島大橋まで、実際に回った順番で紹介します。秋の海は散歩するだけでも気持ちいい。"
CONTENT_PATH=Path("packages/kurahashijima-autumn-drive/content.html")
CATEGORY_SLUGS=["sightseeing-leisure"]
TAG_SLUGS=["hiroshima","road-trip"]
FEATURED=3881
REPORT=Path("reports/kurahashijima-autumn-drive-create-20260921")

EXPECTED_MEDIA={
    3868:("/wp-content/uploads/2026/09/img_8448.jpg",1920,1440),
    3869:("/wp-content/uploads/2026/09/img_8452.jpg",1920,1440),
    3873:("/wp-content/uploads/2026/09/img_8453.jpg",1920,1440),
    3876:("/wp-content/uploads/2026/09/img_8456.jpg",1440,1920),
    3878:("/wp-content/uploads/2026/09/img_8457.jpg",1920,1440),
    3874:("/wp-content/uploads/2026/09/img_8459.jpg",1920,1440),
    3880:("/wp-content/uploads/2026/09/img_8462.jpg",1920,1440),
    3879:("/wp-content/uploads/2026/09/img_8463.jpg",1920,1440),
    3881:("/wp-content/uploads/2026/09/img_8464.jpg",1920,1440),
    3872:("/wp-content/uploads/2026/09/img_8465.jpg",1920,1440),
    3877:("/wp-content/uploads/2026/09/img_8466.jpg",1920,1440),
}

TOKEN=re.compile(r"<!--\s+/?wp:[\s\S]*?-->")
OPEN=re.compile(r"<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->")
CLOSE=re.compile(r"<!--\s+/wp:([\w\-/]+)\s+-->")
IMAGE_ID=re.compile(r"wp-image-(\d+)")

def auth_header():
    u=os.environ.get("TSURIKUE_WP_USER")
    p=os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not u or not p:
        raise RuntimeError("missing WordPress secrets")
    return "Basic "+base64.b64encode(f"{u}:{p}".encode()).decode()

def request(method,path,payload=None):
    headers={"Authorization":auth_header(),"Accept":"application/json","User-Agent":UA}
    data=None
    if payload is not None:
        headers["Content-Type"]="application/json; charset=utf-8"
        data=json.dumps(payload,ensure_ascii=False).encode("utf-8")
    last=None
    for n in range(8):
        req=urllib.request.Request(SITE+path,data=data,headers=headers,method=method)
        try:
            with urllib.request.urlopen(req,timeout=60) as resp:
                body=resp.read().decode("utf-8")
                return (json.loads(body) if body else None),dict(resp.headers.items())
        except urllib.error.HTTPError as exc:
            last=exc
            if 400<=exc.code<500 and exc.code not in {408,429}:
                raise
        except (urllib.error.URLError,TimeoutError,socket.gaierror,OSError) as exc:
            last=exc
        if n<7: time.sleep(min(3+n,10))
    raise last

def raw(row,key):
    v=row.get(key) or {}
    return (v.get("raw") or v.get("rendered") or "") if isinstance(v,dict) else str(v)

def sha256(text):
    return hashlib.sha256((text or "").encode()).hexdigest()

def gutenberg_ok(text):
    stack=[]
    for m in TOKEN.finditer(text):
        tok=m.group(0); op=OPEN.fullmatch(tok); cl=CLOSE.fullmatch(tok)
        if op and not op.group(2):
            stack.append(op.group(1))
        elif cl:
            if not stack or stack[-1]!=cl.group(1):
                return False
            stack.pop()
    return not stack

def validate_content(c):
    if "<h1" in c.casefold() or '"level":1' in c:
        raise RuntimeError("body h1 forbidden")
    if not gutenberg_ok(c):
        raise RuntimeError("Gutenberg mismatch")
    if any(x in c for x in ["普通に","🔥","🤣","😁","😏","😂","😊"]):
        raise RuntimeError("banned wording/emoji")
    required=[
        "お食事処 かず","刺身定食","厳島神社の管絃祭で使われた御座船",
        "アオリイカの子どもたち","くらはし桂浜温泉館","鹿島大橋",
        "海は夏だけじゃありません。","なんせ気持ちが良い！",
        "https://kure-trip.jp/spots/488",
        "https://www.city.kure.lg.jp/site/bunkazai/siyuminbun-1.html",
        "https://kure-trip.jp/spots/53",
        "https://icou-kurahashi.com/",
    ]
    for x in required:
        if x not in c:
            raise RuntimeError(f"required phrase missing: {x}")
    used={int(x) for x in IMAGE_ID.findall(c)}
    expected=set(EXPECTED_MEDIA)
    if used!=expected:
        raise RuntimeError(f"body media mismatch used={sorted(used)} expected={sorted(expected)}")
    for forbidden in ["img_8454","img_8455","img_8458"]:
        if forbidden in c:
            raise RuntimeError(f"reserved photo accidentally used: {forbidden}")

def public_count(endpoint):
    q=urllib.parse.urlencode({"status":"publish","per_page":1,"_fields":"id"})
    _,headers=request("GET",f"/wp-json/wp/v2/{endpoint}?{q}")
    for k,v in headers.items():
        if k.lower()=="x-wp-total":
            return int(v)
    raise RuntimeError("missing X-WP-Total")

def public_counts():
    return {"posts":public_count("posts"),"pages":public_count("pages")}

def resolve_term(endpoint,slug):
    q=urllib.parse.urlencode({"context":"edit","slug":slug,"per_page":10,"_fields":"id,name,slug"})
    rows,_=request("GET",f"/wp-json/wp/v2/{endpoint}?{q}")
    if len(rows)!=1 or rows[0].get("slug")!=slug:
        raise RuntimeError(f"term resolution failed: {endpoint}/{slug}")
    return int(rows[0]["id"])

def validate_media():
    for mid,(path,width,height) in EXPECTED_MEDIA.items():
        q=urllib.parse.urlencode({"context":"edit","_fields":"id,source_url,media_details"})
        row,_=request("GET",f"/wp-json/wp/v2/media/{mid}?{q}")
        if int(row.get("id") or 0)!=mid:
            raise RuntimeError(f"media id mismatch {mid}")
        actual=urllib.parse.unquote(urllib.parse.urlparse(row.get("source_url") or "").path).casefold()
        if actual!=path.casefold():
            raise RuntimeError(f"media path mismatch {mid}: {actual} != {path}")
        d=row.get("media_details") or {}
        if int(d.get("width") or 0)!=width or int(d.get("height") or 0)!=height:
            raise RuntimeError(f"media dimensions mismatch {mid}")

def find_post():
    q=urllib.parse.urlencode({
        "context":"edit","slug":SLUG,"status":"any","per_page":10,
        "_fields":"id,slug,status,title,content,featured_media,categories,tags,excerpt"
    })
    rows,_=request("GET",f"/wp-json/wp/v2/posts?{q}")
    return rows

def related_posts():
    q=urllib.parse.urlencode({
        "context":"edit","search":"倉橋","status":"any","per_page":100,
        "_fields":"id,slug,status,title"
    })
    rows,_=request("GET",f"/wp-json/wp/v2/posts?{q}")
    return rows

def norm_excerpt(v):
    return re.sub(r"<[^>]+>","",html.unescape(v or "")).strip()

def write_report(d):
    REPORT.mkdir(parents=True,exist_ok=True)
    (REPORT/"result.json").write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=[
        "# Kurahashijima autumn-drive article draft create 2026-09-21","",
        f"- result: **{d['result']}**",
        f"- article_action: **{d['action']}**",
        f"- post_id: **{d['post_id']}**",
        f"- status: **{d['status']}**",
        f"- slug: **{SLUG}**",
        f"- title: **{TITLE}**",
        f"- featured_media: **{FEATURED}**",
        f"- category_ids: **{d['categories']}**",
        f"- tag_ids: **{d['tags']}**",
        f"- confirmed_media_checked: **{len(EXPECTED_MEDIA)}**",
        f"- published posts before/after: **{d['before']['posts']} / {d['after']['posts']}**",
        f"- published pages before/after: **{d['before']['pages']} / {d['after']['pages']}**",
        f"- content sha256: **{d['sha']}**",
        "- reserved for later Kazu article: **img_8454 / img_8455**",
        "- unused in this article: **img_8450 / img_8458**",
    ]
    (REPORT/"summary.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines))

def main():
    content=CONTENT_PATH.read_text(encoding="utf-8").strip()+"\n"
    validate_content(content)
    validate_media()
    categories=[resolve_term("categories",x) for x in CATEGORY_SLUGS]
    tags=[resolve_term("tags",x) for x in TAG_SLUGS]
    if categories!=[7]:
        raise RuntimeError(f"unexpected outing category id: {categories}")
    if sorted(tags)!=[28,29]:
        raise RuntimeError(f"unexpected tag ids: {tags}")

    before=public_counts()
    rows=find_post()
    if rows:
        if len(rows)!=1:
            raise RuntimeError("slug collision")
        row=rows[0]
        exact=(
            row.get("status")=="draft"
            and html.unescape(raw(row,"title"))==TITLE
            and raw(row,"content").strip()==content.strip()
            and norm_excerpt(raw(row,"excerpt"))==EXCERPT
            and int(row.get("featured_media") or 0)==FEATURED
            and sorted(row.get("categories") or [])==sorted(categories)
            and sorted(row.get("tags") or [])==sorted(tags)
        )
        if not exact:
            raise RuntimeError("existing draft differs")
        post=row; action="REUSE_EXACT_DRAFT"
    else:
        rel=related_posts()
        collisions=[]
        for r in rel:
            t=html.unescape(raw(r,"title"))
            if "倉橋島を秋にドライブ" in t or r.get("slug")==SLUG:
                collisions.append({"id":r.get("id"),"slug":r.get("slug"),"status":r.get("status"),"title":t})
        if collisions:
            raise RuntimeError(f"possible duplicate found: {collisions}")
        payload={
            "title":TITLE,"slug":SLUG,"content":content,"excerpt":EXCERPT,
            "status":"draft","featured_media":FEATURED,
            "categories":categories,"tags":tags,
        }
        post,_=request("POST","/wp-json/wp/v2/posts",payload)
        action="CREATE_DRAFT"

    pid=int(post.get("id") or 0)
    q=urllib.parse.urlencode({
        "context":"edit",
        "_fields":"id,slug,status,title,content,featured_media,categories,tags,excerpt"
    })
    check,_=request("GET",f"/wp-json/wp/v2/posts/{pid}?{q}")
    if check.get("slug")!=SLUG or check.get("status")!="draft":
        raise RuntimeError("final identity/status mismatch")
    if html.unescape(raw(check,"title"))!=TITLE or raw(check,"content").strip()!=content.strip():
        raise RuntimeError("final title/content mismatch")
    if norm_excerpt(raw(check,"excerpt"))!=EXCERPT:
        raise RuntimeError("final excerpt mismatch")
    if int(check.get("featured_media") or 0)!=FEATURED:
        raise RuntimeError("final featured media mismatch")
    if sorted(check.get("categories") or [])!=sorted(categories):
        raise RuntimeError("final category mismatch")
    if sorted(check.get("tags") or [])!=sorted(tags):
        raise RuntimeError("final tags mismatch")

    after=public_counts()
    if before!=after:
        raise RuntimeError(f"published counts changed: {before}->{after}")

    write_report({
        "result":"SUCCESS","action":action,"post_id":pid,"status":"draft",
        "categories":categories,"tags":tags,"before":before,"after":after,
        "sha":sha256(raw(check,"content"))
    })

if __name__=="__main__":
    main()
