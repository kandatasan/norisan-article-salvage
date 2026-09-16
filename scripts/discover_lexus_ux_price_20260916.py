#!/usr/bin/env python3
import base64,json,os,urllib.request,hashlib
SITE="https://tsurikue.com"; POST_ID=2956
def auth():
    raw=f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()
    return "Basic "+base64.b64encode(raw).decode()
def get():
    req=urllib.request.Request(f"{SITE}/wp-json/wp/v2/posts/{POST_ID}?context=edit",
      headers={"Authorization":auth(),"Accept":"application/json","User-Agent":"tsurikue-price-discovery-20260916/1.0"})
    with urllib.request.urlopen(req,timeout=90) as r:return json.loads(r.read().decode())
row=get()
c=(row.get("content") or {}).get("raw") or (row.get("content") or {}).get("rendered") or ""
t=(row.get("title") or {}).get("raw") or (row.get("title") or {}).get("rendered") or ""
print("META",json.dumps({"id":row["id"],"slug":row["slug"],"status":row["status"],"title":t,"featured_media":row.get("featured_media"),"sha256":hashlib.sha256(c.encode()).hexdigest()},ensure_ascii=False))
print("CONTENT_BASE64_BEGIN")
print(base64.b64encode(c.encode()).decode())
print("CONTENT_BASE64_END")
