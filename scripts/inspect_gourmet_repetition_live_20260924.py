#!/usr/bin/env python3
from __future__ import annotations
import base64,json,os,re,urllib.parse,urllib.request

SITE="https://tsurikue.com"
UA="tsurikue-inspect-gourmet-repetition-live-20260924/1.0"
TARGETS={"ask-the-meat":3463,"yakinikucenter":2662}

def auth():
    raw=f"{os.environ['TSURIKUE_WP_USER']}:{os.environ['TSURIKUE_WP_APP_PASSWORD']}".encode()
    return "Basic "+base64.b64encode(raw).decode()

def req(url):
    r=urllib.request.Request(url,headers={"Accept":"application/json","Authorization":auth(),"User-Agent":UA})
    with urllib.request.urlopen(r,timeout=60) as x:
        return json.loads(x.read().decode())

for slug,pid in TARGETS.items():
    q=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,content,featured_media"})
    row=req(f"{SITE}/wp-json/wp/v2/posts/{pid}?{q}")
    content=(row.get("content") or {}).get("raw") or ""
    print(f"## {slug}")
    print("title:",(row.get("title") or {}).get("raw"))
    print("status:",row.get("status"),"featured:",row.get("featured_media"))
    if slug=="ask-the-meat":
        keys=("名前","部位","旨かった記憶","また食べたい","wp:heading")
    else:
        keys=("東広島","可部まで","通い","わざわざ","ここで食べたい","和牛カルビ","白ごはん","ご飯","wp:heading")
    for line in content.splitlines():
        if any(k in line for k in keys):
            print(line)
