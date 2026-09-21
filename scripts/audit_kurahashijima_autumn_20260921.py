#!/usr/bin/env python3
from __future__ import annotations

import base64, html, json, os, urllib.parse, urllib.request
from pathlib import Path

SITE="https://tsurikue.com"
UA="tsurikue-audit-kurahashijima-autumn-20260921/1.0"
SLUG="kurahashijima-autumn-drive"
TITLE="倉橋島を秋にドライブ！桂浜散策・海鮮ランチ・鹿島大橋まで楽しんできた"
MEDIA_STEMS={f"img_{n}" for n in [8448,8450,8452,8453,8454,8455,8456,8457,8458,8459,8462,8463,8464,8465,8466]}
REPORT=Path("reports/kurahashijima-autumn-audit-20260921")

def auth():
    u=os.environ["TSURIKUE_WP_USER"]; p=os.environ["TSURIKUE_WP_APP_PASSWORD"]
    return "Basic "+base64.b64encode(f"{u}:{p}".encode()).decode()

def get(path):
    req=urllib.request.Request(SITE+path,headers={"Authorization":auth(),"Accept":"application/json","User-Agent":UA},method="GET")
    with urllib.request.urlopen(req,timeout=60) as r:
        body=r.read().decode()
        return json.loads(body) if body else None, dict(r.headers.items())

def resolve(endpoint, slug):
    q=urllib.parse.urlencode({"context":"edit","slug":slug,"per_page":10,"_fields":"id,name,slug"})
    rows,_=get(f"/wp-json/wp/v2/{endpoint}?{q}")
    if len(rows)!=1 or rows[0].get("slug")!=slug:
        raise RuntimeError(f"term resolution failed: {endpoint}/{slug}: {rows}")
    return rows[0]

def main():
    # Draft/duplicate audit.
    q=urllib.parse.urlencode({"context":"edit","slug":SLUG,"status":"any","per_page":20,"_fields":"id,slug,status,title,link"})
    exact,_=get(f"/wp-json/wp/v2/posts?{q}")
    q=urllib.parse.urlencode({"context":"edit","search":"倉橋","status":"any","per_page":100,"_fields":"id,slug,status,title,link"})
    related,_=get(f"/wp-json/wp/v2/posts?{q}")

    # Taxonomy audit.
    category=resolve("categories","sightseeing-leisure")
    hiroshima=resolve("tags","hiroshima")
    road_trip=resolve("tags","road-trip")

    # Recent media audit.
    matches=[]
    page=1
    while page<=3:
        q=urllib.parse.urlencode({
            "context":"edit","per_page":100,"page":page,"orderby":"date","order":"desc",
            "_fields":"id,date,slug,source_url,media_details,alt_text,title"
        })
        rows,headers=get(f"/wp-json/wp/v2/media?{q}")
        if not rows: break
        for row in rows:
            url=row.get("source_url") or ""
            filename=urllib.parse.unquote(urllib.parse.urlparse(url).path.rsplit("/",1)[-1]).casefold()
            stem=filename.rsplit(".",1)[0]
            if stem in MEDIA_STEMS:
                d=row.get("media_details") or {}
                matches.append({
                    "id":int(row.get("id") or 0),
                    "date":row.get("date"),
                    "filename":filename,
                    "source_url":url,
                    "width":int(d.get("width") or 0),
                    "height":int(d.get("height") or 0),
                    "alt_text":row.get("alt_text") or "",
                })
        if len(rows)<100: break
        page+=1

    by_stem={m["filename"].rsplit(".",1)[0]:m for m in matches}
    missing=sorted(MEDIA_STEMS-set(by_stem))
    duplicates=[s for s in MEDIA_STEMS if sum(1 for m in matches if m["filename"].rsplit(".",1)[0]==s)>1]
    if missing or duplicates:
        raise RuntimeError(f"media audit failed missing={missing} duplicates={duplicates} matches={matches}")

    data={
        "result":"SUCCESS","slug":SLUG,"title":TITLE,
        "exact_slug_posts":exact,"related_kurahashi_posts":related,
        "category":category,"tags":[hiroshima,road_trip],
        "matches":[by_stem[s] for s in sorted(by_stem)],
        "wordpress_write_count":0,
    }
    REPORT.mkdir(parents=True,exist_ok=True)
    (REPORT/"result.json").write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=[
        "# Kurahashijima autumn-drive media audit 2026-09-21","",
        "- result: **SUCCESS**",
        f"- exact slug collisions: **{len(exact)}**",
        f"- related 倉橋 posts: **{len(related)}**",
        f"- category: **{category['name']} / {category['id']} / {category['slug']}**",
        f"- tags: **{hiroshima['name']} / {hiroshima['id']}**, **{road_trip['name']} / {road_trip['id']}**",
        "- wordpress_write_count: **0**","",
        "## Matched uploads"
    ]
    for m in data["matches"]:
        lines.append(f"- media #{m['id']} / {m['filename']} / {m['width']}x{m['height']} / {m['source_url']}")
    if related:
        lines += ["","## Related 倉橋 posts"]
        for row in related:
            title=html.unescape(((row.get("title") or {}).get("rendered") or ""))
            lines.append(f"- #{row.get('id')} / {row.get('status')} / {row.get('slug')} / {title}")
    (REPORT/"summary.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps(data,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
