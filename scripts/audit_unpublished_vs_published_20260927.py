#!/usr/bin/env python3
import base64, difflib, html, json, os, re, urllib.parse, urllib.request

SITE="https://tsurikue.com"
UA="tsurikue-unpublished-vs-published-audit/1.0"

def auth():
    u=os.environ["TSURIKUE_WP_USER"]; p=os.environ["TSURIKUE_WP_APP_PASSWORD"]
    return "Basic "+base64.b64encode(f"{u}:{p}".encode()).decode()

def get_json(url,a):
    req=urllib.request.Request(url,headers={"Authorization":a,"Accept":"application/json","User-Agent":UA})
    with urllib.request.urlopen(req,timeout=60) as r:
        return json.loads(r.read().decode()),dict(r.headers)

def raw(r,k):
    v=r.get(k) or {}
    return (v.get("raw") or v.get("rendered") or "") if isinstance(v,dict) else str(v)

def plain(s):
    s=html.unescape(s or "")
    s=re.sub(r"<!--.*?-->"," ",s,flags=re.S)
    s=re.sub(r"<[^>]+>"," ",s)
    return re.sub(r"\s+"," ",s).strip()

def fetch(status,a):
    out=[]; page=1
    while True:
        q=urllib.parse.urlencode({"context":"edit","status":status,"per_page":100,"page":page,"_fields":"id,slug,status,title,content,modified"})
        rows,h=get_json(f"{SITE}/wp-json/wp/v2/posts?{q}",a)
        out+=rows
        if page>=int(h.get("X-WP-TotalPages","1")): break
        page+=1
    return out

def sim(a,b):
    return difflib.SequenceMatcher(None,a,b).ratio() if a and b else 0.0

def main():
    a=auth()
    drafts=[]
    for s in ["draft","pending","private","future"]: drafts += fetch(s,a)
    pubs=fetch("publish",a)
    print("# Unpublished vs published duplicate audit 2026-09-27")
    print("- mode: **GET ONLY**")
    print("- wordpress_write_count: **0**")
    print(f"- unpublished_posts: **{len(drafts)}**")
    print(f"- published_posts: **{len(pubs)}**")
    print()
    for d in drafts:
        dt=plain(raw(d,"title")); dc=plain(raw(d,"content"))
        scored=[]
        for p in pubs:
            pt=plain(raw(p,"title")); pc=plain(raw(p,"content"))
            ts=sim(dt,pt)
            cs=sim(dc[:2500],pc[:2500])
            score=max(ts,cs)
            scored.append((score,ts,cs,p,pt))
        scored.sort(key=lambda x:x[0],reverse=True)
        top=scored[:3]
        flag="CLEAR"
        if top and (top[0][1]>=0.72 or top[0][2]>=0.72): flag="LIKELY_DUPLICATE"
        elif top and (top[0][1]>=0.52 or top[0][2]>=0.48): flag="POSSIBLE_OVERLAP"
        print(f"## {d['id']} {d.get('slug') or '(no-slug)'} — {dt}")
        print(f"- status: {d.get('status')} / modified: {d.get('modified')} / flag: **{flag}**")
        for score,ts,cs,p,pt in top:
            print(f"- match: {p['id']} {p.get('slug')} title_sim={ts:.3f} content_sim={cs:.3f} — {pt}")
        print()

if __name__=="__main__": main()
