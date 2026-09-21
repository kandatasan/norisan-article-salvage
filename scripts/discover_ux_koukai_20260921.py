#!/usr/bin/env python3
import base64, hashlib, json, os, urllib.parse, urllib.request

SITE="https://tsurikue.com"
POST_ID=2517
UA="tsurikue-discover-ux-koukai-20260921/1.0"

def auth():
    u=os.environ["TSURIKUE_WP_USER"]; p=os.environ["TSURIKUE_WP_APP_PASSWORD"]
    return "Basic "+base64.b64encode(f"{u}:{p}".encode()).decode()

q=urllib.parse.urlencode({
    "context":"edit",
    "_fields":"id,slug,status,title,content,author,featured_media,categories,tags,excerpt"
})
req=urllib.request.Request(
    f"{SITE}/wp-json/wp/v2/posts/{POST_ID}?{q}",
    headers={"Authorization":auth(),"Accept":"application/json","User-Agent":UA}
)
with urllib.request.urlopen(req,timeout=90) as r:
    row=json.loads(r.read().decode())
content=(row.get("content") or {}).get("raw") or (row.get("content") or {}).get("rendered") or ""
title=(row.get("title") or {}).get("raw") or (row.get("title") or {}).get("rendered") or ""
print("META",json.dumps({
    "id":row.get("id"),"slug":row.get("slug"),"status":row.get("status"),"title":title,
    "author":row.get("author"),"featured_media":row.get("featured_media"),
    "categories":row.get("categories"),"tags":row.get("tags"),
    "sha256":hashlib.sha256(content.encode()).hexdigest(),
    "length":len(content)
},ensure_ascii=False))
print("CONTENT_BASE64_BEGIN")
print(base64.b64encode(content.encode()).decode())
print("CONTENT_BASE64_END")
