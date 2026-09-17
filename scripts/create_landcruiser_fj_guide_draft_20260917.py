#!/usr/bin/env python3
from __future__ import annotations

import base64, hashlib, html, json, os, re, socket, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

SITE = "https://tsurikue.com"
UA = "tsurikue-create-fj-guide-20260917/1.0"
TITLE = "ランドクルーザーFJとは？価格・サイズ・燃費・特徴を実車オーナーがまとめて解説"
SLUG = "landcruiser-fj-guide"
EXCERPT = "ランドクルーザーFJとはどんな車？2026年5月発売のFJについて、価格、サイズ、燃費、2.7Lエンジン、5人乗り、ラダーフレーム、ボディカラー、安全装備、FJクルーザーとの違いまで一覧でまとめます。実際にFJを買った体験記事にもつなげています。"
CONTENT_PATH = Path("packages/landcruiser-fj-guide/content.html")
FEATURED = 3757
FEATURED_PATH = "/wp-content/uploads/2026/09/img_8130.jpg"
CATEGORY_SLUGS = ["car", "landcruiser-fj"]
SOURCE_FJ_POST_ID = 3767
SOURCE_FJ_SLUG = "landcruiser-fj-price"
REPORT = Path("reports/landcruiser-fj-guide-create-20260917")

TOKEN = re.compile(r"<!--\s+/?wp:[\s\S]*?-->")
OPEN = re.compile(r"<!--\s+wp:([\w\-/]+)(?:\s+\{.*?\})?\s*(/)?-->")
CLOSE = re.compile(r"<!--\s+/wp:([\w\-/]+)\s+-->")


def auth_header():
    u, p = os.environ.get("TSURIKUE_WP_USER"), os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not u or not p: raise RuntimeError("missing WordPress secrets")
    return "Basic " + base64.b64encode(f"{u}:{p}".encode()).decode()


def request(method, path, payload=None):
    headers = {"Authorization": auth_header(), "Accept": "application/json", "User-Agent": UA}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    last = None
    for n in range(8):
        req = urllib.request.Request(SITE + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                body = resp.read().decode("utf-8")
                return (json.loads(body) if body else None), dict(resp.headers.items())
        except urllib.error.HTTPError as exc:
            last = exc
            if 400 <= exc.code < 500 and exc.code not in {408, 429}: raise
        except (urllib.error.URLError, TimeoutError, socket.gaierror, OSError) as exc:
            last = exc
        if n < 7: time.sleep(min(3+n, 10))
    raise last


def raw(row, key):
    v = row.get(key) or {}
    return (v.get("raw") or v.get("rendered") or "") if isinstance(v, dict) else str(v)


def sha256(text): return hashlib.sha256((text or "").encode()).hexdigest()


def gutenberg_ok(text):
    stack=[]
    for m in TOKEN.finditer(text):
        tok=m.group(0); op=OPEN.fullmatch(tok); cl=CLOSE.fullmatch(tok)
        if op and not op.group(2): stack.append(op.group(1))
        elif cl:
            if not stack or stack[-1] != cl.group(1): return False
            stack.pop()
    return not stack


def validate_content(c):
    if "<h1" in c.casefold() or '"level":1' in c: raise RuntimeError("body h1 forbidden")
    if not gutenberg_ok(c): raise RuntimeError("Gutenberg mismatch")
    if any(x in c for x in ["普通に", "🔥", "🤣", "😁", "😏", "😂", "😊"]): raise RuntimeError("banned wording/emoji")
    required = [
        "2026年5月14日", "4,500,100円", "4,575mm", "1,855mm", "1,960mm", "2,580mm",
        "1,960kg", "5.5m", "163PS", "246N・m", "8.7km/L", "63L", "Freedom＆Joy",
        "プラチナホワイトパールマイカ", "Toyota Safety Sense", "ランドクルーザーFJとFJクルーザーは別のクルマ",
        "https://tsurikue.com/landcruiser-fj-price/", "https://tsurikue.com/landcruiser-fj-review/",
        "https://tsurikue.com/landcruiser-fj-drawbacks/", "https://tsurikue.com/landcruiser-fj-cheap/",
        "https://tsurikue.com/landcruiser-fj-cool/", "https://tsurikue.com/landcruiser-fj-rear-seat/"
    ]
    for x in required:
        if x not in c: raise RuntimeError(f"required phrase missing: {x}")


def public_count(endpoint):
    q=urllib.parse.urlencode({"status":"publish","per_page":1,"_fields":"id"})
    _, h=request("GET", f"/wp-json/wp/v2/{endpoint}?{q}")
    for k,v in h.items():
        if k.lower()=="x-wp-total": return int(v)
    raise RuntimeError("missing public count")


def public_counts(): return {"posts":public_count("posts"),"pages":public_count("pages")}


def resolve_category(slug):
    q=urllib.parse.urlencode({"context":"edit","slug":slug,"per_page":10,"_fields":"id,slug"})
    rows,_=request("GET", f"/wp-json/wp/v2/categories?{q}")
    if len(rows)!=1 or rows[0].get("slug")!=slug: raise RuntimeError(f"category resolution failed: {slug}")
    return int(rows[0]["id"])


def source_author():
    q=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,author"})
    row,_=request("GET", f"/wp-json/wp/v2/posts/{SOURCE_FJ_POST_ID}?{q}")
    if row.get("slug") != SOURCE_FJ_SLUG: raise RuntimeError("source FJ mismatch")
    return int(row.get("author") or 0)


def validate_media():
    q=urllib.parse.urlencode({"context":"edit","_fields":"id,source_url"})
    row,_=request("GET", f"/wp-json/wp/v2/media/{FEATURED}?{q}")
    path=urllib.parse.unquote(urllib.parse.urlparse(row.get("source_url") or "").path)
    if int(row.get("id") or 0)!=FEATURED or path.casefold()!=FEATURED_PATH.casefold(): raise RuntimeError("featured media mismatch")


def find_post():
    q=urllib.parse.urlencode({"context":"edit","slug":SLUG,"status":"any","per_page":10,"_fields":"id,slug,status,title,content,author,featured_media,categories,excerpt"})
    rows,_=request("GET", f"/wp-json/wp/v2/posts?{q}")
    return rows


def norm_excerpt(v): return re.sub(r"<[^>]+>", "", html.unescape(v or "")).strip()


def write_report(d):
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT/"result.json").write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# FJ database guide create 2026-09-17","",f"- result: **{d['result']}**",f"- article_action: **{d['action']}**",f"- post_id: **{d['post_id']}**",f"- status: **{d['status']}**",f"- slug: **{SLUG}**",f"- published posts before/after: **{d['before']['posts']} / {d['after']['posts']}**",f"- published pages before/after: **{d['before']['pages']} / {d['after']['pages']}**",f"- content sha256: **{d['sha']}**"]
    (REPORT/"summary.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines))


def main():
    content=CONTENT_PATH.read_text(encoding="utf-8").strip()+"\n"
    validate_content(content)
    before=public_counts(); author=source_author(); categories=[resolve_category(s) for s in CATEGORY_SLUGS]; validate_media()
    rows=find_post()
    if rows:
        if len(rows)!=1: raise RuntimeError("slug collision")
        row=rows[0]
        if row.get("status")!="draft": raise RuntimeError(f"existing slug is not draft: {row.get('status')}")
        if html.unescape(raw(row,"title"))!=TITLE or raw(row,"content").strip()!=content.strip(): raise RuntimeError("existing draft differs")
        post=row; action="REUSE_EXACT_DRAFT"
    else:
        post,_=request("POST","/wp-json/wp/v2/posts",{"title":TITLE,"slug":SLUG,"content":content,"excerpt":EXCERPT,"status":"draft","author":author,"featured_media":FEATURED,"categories":categories})
        action="CREATE_DRAFT"
    pid=int(post.get("id") or 0)
    q=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,content,author,featured_media,categories,excerpt"})
    check,_=request("GET", f"/wp-json/wp/v2/posts/{pid}?{q}")
    if check.get("slug")!=SLUG or check.get("status")!="draft": raise RuntimeError("final identity/status mismatch")
    if html.unescape(raw(check,"title"))!=TITLE or raw(check,"content").strip()!=content.strip(): raise RuntimeError("final title/content mismatch")
    if norm_excerpt(raw(check,"excerpt"))!=EXCERPT: raise RuntimeError("final excerpt mismatch")
    if int(check.get("author") or 0)!=author or int(check.get("featured_media") or 0)!=FEATURED: raise RuntimeError("final metadata mismatch")
    if sorted(check.get("categories") or [])!=sorted(categories): raise RuntimeError("final categories mismatch")
    after=public_counts()
    if after!=before: raise RuntimeError(f"public counts changed: {before}->{after}")
    write_report({"result":"SUCCESS","action":action,"post_id":pid,"status":"draft","before":before,"after":after,"sha":sha256(raw(check,"content"))})

if __name__ == "__main__": main()
