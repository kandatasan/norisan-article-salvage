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
        keys=("分か","覚え","説明","名称","名前","部位","肉","旨","記憶","<h2")
    else:
        keys=("東広島","可部","通","遠","距離","ここまで","行く","和牛","カルビ","ごはん","ご飯","白","<h2")
    for line in content.splitlines():
        if any(k in line for k in keys):
            print(line)
