#!/usr/bin/env python3
"""Correct only the NX350h version L HUD cell in WP article 4268."""
import os, re, json, base64, hashlib, urllib.request, urllib.parse
from pathlib import Path

BASE = "https://tsurikue.com"
POST_ID = 4268
SLUG = "lexus-nx-rival-suv"
LABEL = "フロントガラスに<br>速度などを表示"
CELL = re.compile(r'(<tr><th scope="row"[^>]*>'+LABEL+r'</th><td style=")([^"]+)(">)([—○])(</td>)')

def api(path, auth, payload=None):
    data = None if payload is None else json.dumps(payload,ensure_ascii=False).encode()
    req = urllib.request.Request(BASE+path, data=data, method="GET" if data is None else "POST",
        headers={"Authorization":auth,"User-Agent":"tsurikue-nx-hud-fix/1.0",
        "Content-Type":"application/json; charset=utf-8","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=60) as r:
        return json.loads(r.read().decode()),dict(r.headers)

def fetch(auth):
    query=urllib.parse.urlencode({"context":"edit","_fields":"id,slug,status,title,content,featured_media,categories,author"})
    return api("/wp-json/wp/v2/posts/"+str(POST_ID)+"?"+query,auth)[0]

def raw(row):
    return row["content"]["raw"]

def signature(row):
    return (row["id"],row["slug"],row["status"],row["title"].get("raw"),
      row["featured_media"],tuple(sorted(row["categories"])),row["author"])

def counts(auth):
    result=[]
    for kind in ("posts","pages"):
        p=urllib.parse.urlencode({"context":"edit","status":"publish","per_page":1,"_fields":"id"})
        _, headers=api("/wp-json/wp/v2/"+kind+"?"+p,auth)
        result.append(int(headers.get("X-WP-Total",0)))
    return result

def patch(s):
    if "<!-- tsurikue-editorial:v1 slug=lexus-nx-rival-suv -->" not in s:
        raise RuntimeError("Editorial source marker absent")
    if s.count(LABEL)!=1:
        raise RuntimeError("HUD label not unique")
    m=list(CELL.finditer(s))
    if len(m)!=1:
        raise RuntimeError("HUD cell not uniquely located")
    item=m[0]
    style,symbol=item.group(2),item.group(4)
    if symbol=="○" and "color:#19634b!important" in style:
        return s,"ALREADY_CORRECT"
    if symbol!="—" or style.count("color:#6b7280!important")!=1:
        raise RuntimeError("HUD cell no longer matches expected old value")
    changed=item.group(1)+style.replace("color:#6b7280!important","color:#19634b!important")+item.group(3)+"○"+item.group(5)
    updated=s[:item.start()]+changed+s[item.end():]
    if updated.count('class="tsq-nx-rival-table"')!=3:
        raise RuntimeError("Comparison table count changed")
    if updated.count('[blog_parts id="2843"]')!=s.count('[blog_parts id="2843"]'):
        raise RuntimeError("Affiliate changed")
    return updated,"UPDATE"

def main():
    u=os.environ["TSURIKUE_WP_USER"]; p=os.environ["TSURIKUE_WP_APP_PASSWORD"]
    auth="Basic "+base64.b64encode((u+":"+p).encode()).decode()
    before=fetch(auth)
    if before["id"]!=POST_ID or before["slug"]!=SLUG or before["status"] not in ("draft","publish"):
        raise RuntimeError("Wrong article or status")
    old=raw(before); new,action=patch(old); totals=counts(auth)
    latest=fetch(auth)
    if signature(latest)!=signature(before) or raw(latest)!=old:
        raise RuntimeError("Concurrent changes: abort")
    if action=="UPDATE":
        response,_=api("/wp-json/wp/v2/posts/"+str(POST_ID),auth,{"content":new})
        if response["id"]!=POST_ID or response["status"]!=before["status"]:
            raise RuntimeError("Save response mismatch")
    after=fetch(auth)
    if signature(after)!=signature(before) or raw(after)!=new or counts(auth)!=totals:
        raise RuntimeError("Saved content or metadata changed")
    report={"post_id":POST_ID,"slug":SLUG,"status":after["status"],"action":action,
      "before_sha256":hashlib.sha256(old.encode()).hexdigest(),
      "after_sha256":hashlib.sha256(new.encode()).hexdigest(),
      "published_counts":totals,"publish_count":0}
    out=Path("reports/nx-hud-20261026");out.mkdir(parents=True,exist_ok=True)
    (out/"result.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print("NX_HUD_VERIFIED",json.dumps(report,ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
